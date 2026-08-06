"""Módulo 1 — Análise do site.

Faz o varrimento completo do site da Curadoria Prime:

1. Lê o sitemap do WordPress (Yoast) e lista todos os artigos publicados.
2. Baixa cada artigo e extrai título, datas e todos os links internos/externos.
3. Testa cada link e aponta os QUEBRADOS (404, domínio fora do ar etc.).
4. Detecta sinais de DESATUALIZAÇÃO:
   - ano antigo citado no título/cabeçalhos (ex.: "2024" quando já é 2026);
   - post sem modificação há muito tempo (DIAS_DESATUALIZADO no config);
   - pauta sazonal fora de época (Dia dos Pais, Black Friday, Natal...).

Gera um relatório em JSON em dados/analises/ e imprime um resumo no terminal.
"""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urldefrag, urlparse

import requests
from bs4 import BeautifulSoup

from . import config

SESSAO = requests.Session()
SESSAO.headers.update({"User-Agent": config.USER_AGENT})

# Palavras-chave sazonais -> mês do evento (Brasil)
SAZONAIS = {
    "volta às aulas": 2, "volta as aulas": 2,
    "dia das mães": 5, "dia das maes": 5,
    "dia dos namorados": 6,
    "dia dos pais": 8,
    "dia das crianças": 10, "dia das criancas": 10,
    "black friday": 11,
    "natal": 12,
}


class ErroAnalise(RuntimeError):
    pass


# ----------------------------------------------------------------------
# 1. Descoberta de URLs via sitemap
# ----------------------------------------------------------------------
def obter_posts_do_sitemap() -> list[dict]:
    """Lê o sitemap do WP e devolve [{url, ultima_modificacao}] dos posts."""
    candidatos = [
        f"{config.SITE_URL}/sitemap_index.xml",   # Yoast SEO
        f"{config.SITE_URL}/wp-sitemap.xml",       # WP nativo
    ]
    indice = None
    for url in candidatos:
        try:
            r = SESSAO.get(url, timeout=config.TIMEOUT_HTTP)
            if r.status_code == 200 and "<sitemapindex" in r.text \
                    or (r.status_code == 200 and "<urlset" in r.text):
                indice = r.text
                break
        except requests.RequestException:
            continue
    if indice is None:
        raise ErroAnalise(
            "Não encontrei o sitemap do site. Confira SITE_URL no .env e "
            "teste no navegador: " + f"{config.SITE_URL}/sitemap_index.xml"
        )

    soup = BeautifulSoup(indice, "xml")

    # Se for um índice de sitemaps, pega apenas os sitemaps de POSTS
    if soup.find("sitemapindex"):
        sitemaps_posts = [
            sm.loc.text for sm in soup.find_all("sitemap")
            if "post" in sm.loc.text and "page" not in sm.loc.text
            and "categor" not in sm.loc.text and "tag" not in sm.loc.text
        ]
    else:
        sitemaps_posts = [candidatos[1]]  # já é um urlset direto

    posts: list[dict] = []
    for sm_url in sitemaps_posts:
        try:
            r = SESSAO.get(sm_url, timeout=config.TIMEOUT_HTTP)
            r.raise_for_status()
        except requests.RequestException as exc:
            print(f"  ⚠️  Falha ao ler sitemap {sm_url}: {exc}")
            continue
        sm_soup = BeautifulSoup(r.text, "xml")
        for u in sm_soup.find_all("url"):
            loc = u.loc.text.strip()
            lastmod = u.lastmod.text.strip() if u.lastmod else ""
            posts.append({
                "url": loc,
                "ultima_modificacao": lastmod[:10],
            })
    # remove a home, se aparecer
    posts = [p for p in posts if p["url"].rstrip("/") != config.SITE_URL]
    return posts


# ----------------------------------------------------------------------
# 2. Extração de dados de cada artigo
# ----------------------------------------------------------------------
def _extrair_dados_post(url: str, ultima_mod_sitemap: str) -> dict | None:
    """Baixa um post e extrai título, datas, links e sinais de desatualização."""
    try:
        r = SESSAO.get(url, timeout=config.TIMEOUT_HTTP)
        r.raise_for_status()
    except requests.RequestException as exc:
        print(f"  ⚠️  Não consegui abrir {url}: {exc}")
        return None

    soup = BeautifulSoup(r.text, "lxml")
    titulo = soup.title.get_text(strip=True) if soup.title else url

    # Datas via meta tags do WordPress (mais confiáveis que o texto)
    meta_mod = soup.find("meta", property="article:modified_time")
    meta_pub = soup.find("meta", property="article:published_time")
    modificacao = (meta_mod["content"][:10] if meta_mod
                   else ultima_mod_sitemap)
    publicacao = meta_pub["content"][:10] if meta_pub else ""

    # Corpo do post (tenta ir direto no conteúdo para não pegar menu/footer)
    corpo = (soup.select_one(".entry-content") or soup.select_one("article")
             or soup.body or soup)

    links = set()
    for a in corpo.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        href, _frag = urldefrag(href)  # ignora âncoras #indice
        if href.startswith("/"):
            href = config.SITE_URL + href
        if href.startswith("http"):
            links.add(href)

    # Áreas de texto usadas na detecção de desatualização
    titulos = " ".join(h.get_text(" ", strip=True)
                       for h in corpo.find_all(["h1", "h2"]))
    texto_check = f"{titulo} {titulos}".lower()

    return {
        "url": url,
        "titulo": titulo,
        "publicado_em": publicacao,
        "ultima_modificacao": modificacao,
        "links": sorted(links),
        "texto_check": texto_check,
    }


def _sinais_desatualizacao(post: dict, hoje: datetime) -> list[str]:
    """Aplica heurísticas de desatualização e explica cada sinal."""
    sinais = []
    ano_atual = hoje.year

    # 1) Ano citado no título/cabeçalhos
    anos = [int(a) for a in re.findall(r"\b(20[12]\d)\b", post["texto_check"])]
    if anos and max(anos) < ano_atual:
        sinais.append(
            f"cita o ano {max(anos)} no título/cabeçalhos (estamos em "
            f"{ano_atual})"
        )

    # 2) Idade da última modificação
    data_mod = post.get("ultima_modificacao") or ""
    try:
        dt_mod = datetime.fromisoformat(data_mod)
        dias = (hoje - dt_mod).days
        if dias > config.DIAS_DESATUALIZADO:
            sinais.append(f"sem atualização há {dias} dias "
                          f"(desde {data_mod})")
    except ValueError:
        pass

    # 3) Sazonalidade fora de época
    mes_atual = hoje.month
    for chave, mes_evento in SAZONAIS.items():
        if chave in post["texto_check"]:
            passou = (mes_atual - mes_evento) % 12
            if 0 < passou <= 5:
                sinais.append(
                    f"pauta sazonal '{chave}' já passou este ano — "
                    f"revisar/renovar para a próxima edição"
                )
            break

    return sinais


# ----------------------------------------------------------------------
# 3. Verificação de links (paralela, 3 baldes: ok / quebrado / indeterminado)
# ----------------------------------------------------------------------
_HEADERS_NAVEGADOR = {
    "User-Agent": config.BROWSER_UA,
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Códigos que normalmente significam "site bloqueando robô" (não são prova
# de link quebrado: no navegador essas páginas abrem normalmente)
_BLOQUEIO_ROBO = {401, 403, 429, 503}


def _falha_dns(exc: BaseException) -> bool:
    """True quando a ConnectionError indica que o domínio NÃO existe."""
    texto = str(exc).lower()
    return any(trecho in texto for trecho in (
        "name or service not known", "nodename nor servname",
        "temporary failure in name resolution", "getaddrinfo failed",
        "getnameinfo failed",
    ))


def _eh_interno(url: str) -> bool:
    """O link aponta para o próprio site analisado?"""
    try:
        host_link = urlparse(url).netloc.lower().removeprefix("www.")
        host_site = urlparse(config.SITE_URL).netloc.lower().removeprefix("www.")
        return host_link == host_site
    except ValueError:
        return False


def _checar_link(url: str) -> dict:
    """Testa um link e classifica: "ok" | "quebrado" | "indeterminado".

    Estratégia para evitar falsos positivos:
    - tenta HEAD primeiro; se der 4xx/5xx, CONFIRMA com GET (encurtadores
      de afiliado como link.amazon/meli.la costumam responder 404/405 a
      HEAD, mas 200 a GET);
    - QUEBRADO exige prova: GET confirmou 404/410 ou o domínio não existe
      (falha de DNS);
    - bloqueios típicos de robô (401/403/429/503), SSL e instabilidades
      viram INDETERMINADO — "provavelmente abre no navegador, conferir a olho".
    """
    def resultado(classe: str, status: int, motivo: str) -> dict:
        return {"url": url, "ok": classe == "ok", "classe": classe,
                "status": status, "motivo": motivo}

    sufixo_interno = (" — POST INTERNO que não existe"
                      if _eh_interno(url) else "")

    # --- tentativa 1: HEAD (rápida, poupa os servidores) ---
    try:
        r = SESSAO.head(url, timeout=config.TIMEOUT_HTTP,
                        allow_redirects=True, headers=_HEADERS_NAVEGADOR)
        if r.status_code < 400:
            return resultado("ok", r.status_code, "")
    except requests.RequestException:
        pass  # segue direto para o GET

    # --- tentativa 2: GET (com 1 retry em caso de timeout) ---
    status = None
    for _tentativa in range(2):
        try:
            g = SESSAO.get(url, timeout=config.TIMEOUT_HTTP + 4,
                           stream=True, allow_redirects=True,
                           headers=_HEADERS_NAVEGADOR)
            status = g.status_code
            g.close()
            break
        except requests.exceptions.SSLError:
            return resultado("indeterminado", 0,
                             "certificado de segurança (SSL) com problema "
                             "no site deles — conferir no navegador")
        except requests.exceptions.ConnectionError as exc:
            if _falha_dns(exc):
                return resultado("quebrado", 0,
                                 "domínio inexistente" + sufixo_interno)
            return resultado("indeterminado", 0,
                             "conexão recusada ou instável — conferir no "
                             "navegador")
        except requests.exceptions.Timeout:
            status = None
        except requests.RequestException as exc:
            return resultado("indeterminado", 0,
                             f"falha na requisição ({type(exc).__name__})")

    if status is None:
        return resultado("indeterminado", 0,
                         "demorou demais para responder (timeout) — conferir "
                         "no navegador")
    if status < 400:
        return resultado("ok", status, "")
    if status == 404:
        return resultado("quebrado", status,
                         "página não encontrada (404)" + sufixo_interno)
    if status == 410:
        return resultado("quebrado", status,
                         "conteúdo removido permanentemente (410)"
                         + sufixo_interno)
    if status in _BLOQUEIO_ROBO:
        return resultado("indeterminado", status,
                         f"site bloqueia verificação automática (HTTP "
                         f"{status}) — provavelmente abre normal no "
                         f"navegador, conferir a olho")
    return resultado("quebrado", status,
                     f"erro HTTP {status}" + sufixo_interno)


# ----------------------------------------------------------------------
# 4. Pipeline completo
# ----------------------------------------------------------------------
def analisar_site() -> dict:
    """Executa a análise completa e salva o relatório em dados/analises/."""
    hoje = datetime.now()
    print(f"🔎 Lendo sitemap de {config.SITE_URL} ...")
    posts_sitemap = obter_posts_do_sitemap()
    print(f"   {len(posts_sitemap)} artigos encontrados.\n")

    print("📄 Baixando e analisando cada artigo...")
    posts = []
    for i, item in enumerate(posts_sitemap, 1):
        print(f"   [{i}/{len(posts_sitemap)}] {item['url']}")
        dados = _extrair_dados_post(item["url"], item["ultima_modificacao"])
        time.sleep(config.PAUSA_ENTRE_POSTS)
        if dados:
            dados["sinais_desatualizacao"] = _sinais_desatualizacao(dados, hoje)
            posts.append(dados)

    # Links únicos de todo o site, com mapa de onde aparecem
    mapa_links: dict[str, list[str]] = {}
    for p in posts:
        for link in p["links"]:
            mapa_links.setdefault(link, []).append(p["url"])

    print(f"\n🔗 Verificando {len(mapa_links)} links únicos (pode levar "
          f"alguns minutos)...")
    resultados: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futuros = {pool.submit(_checar_link, url): url
                   for url in mapa_links}
        feitos = 0
        for fut in as_completed(futuros):
            res = fut.result()
            resultados[res["url"]] = res
            feitos += 1
            if feitos % 25 == 0:
                print(f"   ... {feitos}/{len(mapa_links)} links testados")

    # Monta o relatório final por post (separando quebrado de indeterminado)
    rel_posts = []
    total_quebrados = 0
    total_indeterminados = 0
    for p in posts:
        quebrados = []
        indeterminados = []
        for link in p["links"]:
            res = resultados.get(link)
            if not res:
                continue
            entrada = {"url": res["url"], "status": res["status"],
                       "motivo": res["motivo"]}
            if res["classe"] == "quebrado":
                quebrados.append(entrada)
            elif res["classe"] == "indeterminado":
                indeterminados.append(entrada)
        total_quebrados += len(quebrados)
        total_indeterminados += len(indeterminados)
        rel_posts.append({
            "url": p["url"],
            "titulo": p["titulo"],
            "publicado_em": p["publicado_em"],
            "ultima_modificacao": p["ultima_modificacao"],
            "total_links": len(p["links"]),
            "links_quebrados": quebrados,
            "links_indeterminados": indeterminados,
            "sinais_desatualizacao": p["sinais_desatualizacao"],
        })

    relatorio = {
        "data_analise": hoje.strftime("%Y-%m-%d %H:%M"),
        "site": config.SITE_URL,
        "resumo": {
            "total_artigos": len(rel_posts),
            "links_unicos_verificados": len(mapa_links),
            "links_quebrados": total_quebrados,
            "artigos_com_link_quebrado":
                sum(1 for p in rel_posts if p["links_quebrados"]),
            "links_indeterminados": total_indeterminados,
            "artigos_com_link_indeterminado":
                sum(1 for p in rel_posts if p["links_indeterminados"]),
            "artigos_desatualizados":
                sum(1 for p in rel_posts if p["sinais_desatualizacao"]),
        },
        "artigos": rel_posts,
    }

    caminho = (config.PASTA_ANALISES /
               f"analise_{hoje.strftime('%Y-%m-%d_%H%M')}.json")
    caminho.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    print(f"\n💾 Relatório salvo em: {caminho.relative_to(config.RAIZ)}")
    _imprimir_resumo(relatorio)
    return relatorio


def _imprimir_resumo(rel: dict) -> None:
    r = rel["resumo"]
    print("\n" + "=" * 60)
    print("RESUMO DA ANÁLISE")
    print("=" * 60)
    print(f"Artigos analisados:            {r['total_artigos']}")
    print(f"Links únicos verificados:      {r['links_unicos_verificados']}")
    print(f"Links QUEBRADOS (confirmado):  {r['links_quebrados']} "
          f"(em {r['artigos_com_link_quebrado']} artigos)")
    print(f"Links NÃO VERIFICÁVEIS:        {r.get('links_indeterminados', 0)}"
          f"  <- sites que bloqueiam robôs; abrem no navegador,")
    print(f"{'':34s}conferir a olho só se desconfiar")

    atencao = [p for p in rel["artigos"]
               if p["links_quebrados"] or p["sinais_desatualizacao"]]
    if atencao:
        print("\n--- Artigos que pedem ação (quebrados confirmados) ---")
        for p in atencao:
            print(f"\n• {p['titulo'][:70]}\n  {p['url']}")
            for s in p["sinais_desatualizacao"]:
                print(f"   🕐 {s}")
            for l in p["links_quebrados"][:5]:
                print(f"   ❌ {l['url'][:70]} ({l['motivo']})")
            if len(p["links_quebrados"]) > 5:
                print(f"   ❌ ... e mais {len(p['links_quebrados']) - 5} "
                      f"quebrados (ver relatório completo no painel)")
    else:
        print("\n✅ Nenhum link quebrado confirmado. Site em dia!")

    indet = [p for p in rel["artigos"] if p.get("links_indeterminados")]
    if indet:
        total = sum(len(p["links_indeterminados"]) for p in indet)
        print(f"\n(ℹ️  {total} links em {len(indet)} artigos ficaram como "
              f"'não verificáveis' — detalhes no relatório do painel)")


def carregar_ultima_analise() -> dict | None:
    """Devolve o relatório de análise mais recente (ou None)."""
    arquivos = sorted(config.PASTA_ANALISES.glob("analise_*.json"))
    if not arquivos:
        return None
    return json.loads(arquivos[-1].read_text(encoding="utf-8"))
