"""Módulo 5 — Publicador: envia/atualiza o HTML no WordPress.

Usa a API REST do WordPress com autenticação por "Senha de Aplicação"
(painel WP -> Usuários -> Perfil -> Senhas de Aplicação).

Por segurança, o padrão é SEMPRE criar/atualizar como RASCUNHO (draft):
você revisa no painel e publica manualmente. Use status="publish" apenas
se quiser publicar direto.
"""
import requests

from . import config


class ErroPublicacao(RuntimeError):
    pass


def _verificar_credenciais() -> None:
    if not config.WP_USER or not config.WP_APP_PASSWORD:
        raise ErroPublicacao(
            "WP_USER e WP_APP_PASSWORD não estão configurados no .env.\n"
            "No painel do WordPress: Usuários -> Perfil -> "
            "'Senhas de Aplicação' -> crie uma senha chamada 'Atlas' "
            "e cole os dois valores no .env."
        )


def _api(metodo: str, endpoint: str, **kwargs) -> requests.Response:
    url = f"{config.SITE_URL}/wp-json/wp/v2/{endpoint.lstrip('/')}"
    try:
        r = SESSAO.request(metodo, url,
                           auth=(config.WP_USER, config.WP_APP_PASSWORD),
                           timeout=30, **kwargs)
    except requests.RequestException as exc:
        raise ErroPublicacao(f"Falha de conexão com a API do WP: {exc}") \
            from exc
    if r.status_code in (401, 403):
        raise ErroPublicacao(
            "Login recusado pelo WordPress (401/403). Confira WP_USER e "
            "WP_APP_PASSWORD no .env, e se a REST API está liberada."
        )
    if r.status_code >= 400:
        raise ErroPublicacao(
            f"Erro {r.status_code} da API do WP: {r.text[:300]}"
        )
    return r


SESSAO = requests.Session()
SESSAO.headers.update({"User-Agent": config.USER_AGENT})


def testar_conexao() -> str:
    """Confere login com a API do WordPress."""
    _verificar_credenciais()
    r = _api("GET", "users/me")
    dados = r.json()
    return (f"OK - conectado como '{dados.get('name')}' "
            f"({dados.get('slug')})")


def buscar_post_por_slug(slug: str) -> dict | None:
    r = _api("GET", f"posts?slug={slug}&status=any")
    lista = r.json()
    return lista[0] if lista else None


def _garantir_categoria(nome: str) -> int | None:
    """Acha (ou cria) o ID da categoria pelo nome. None em caso de falha."""
    if not nome:
        return None
    try:
        r = _api("GET", f"categories?search={nome}&per_page=10")
        for cat in r.json():
            if cat["name"].lower() == nome.lower():
                return cat["id"]
        r = _api("POST", "categories", json={"name": nome})
        return r.json()["id"]
    except ErroPublicacao:
        return None


def publicar(slug: str, html: str, meta: dict,
             status: str = "draft") -> dict:
    """Cria (ou atualiza, se o slug já existir) o post no WordPress."""
    _verificar_credenciais()
    titulo = meta.get("titulo") or slug.replace("-", " ").title()
    payload = {
        "title": titulo,
        "content": html,
        "slug": slug,
        "status": status,  # "draft" (rascunho) ou "publish"
        "excerpt": meta.get("descricao", ""),
    }
    cat_id = _garantir_categoria(meta.get("categoria", ""))
    if cat_id:
        payload["categories"] = [cat_id]

    existente = buscar_post_por_slug(slug)
    if existente:
        r = _api("POST", f"posts/{existente['id']}", json=payload)
        acao = "atualizado"
    else:
        r = _api("POST", "posts", json=payload)
        acao = "criado"

    dados = r.json()
    link = dados.get("link", "")
    return {
        "acao": acao,
        "id": dados.get("id"),
        "status": dados.get("status"),
        "link": link,
    }
