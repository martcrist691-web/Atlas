"""Módulo 4 — Redator: gera o artigo completo em HTML no padrão do site.

Cruza três insumos:
  1. o documento de padrão (modelo/padrao_artigo.md);
  2. a ficha técnica do produto (dados/pesquisas/ficha_*.json);
  3. a pauta (título, palavras-chave) + links de afiliado informados por você.

O resultado é um arquivo .html pronto para colar no editor do WordPress
(ou publicar via API com o módulo publicador), mais um *_meta.json com
título SEO, slug, descrição e categorias sugeridas.
"""
import json
import re
from datetime import datetime

from . import config, llm

SISTEMA = """Você é o redator-chefe do Curadoria Prime (curadoriaprime.com),
site brasileiro de reviews de tecnologia. Você escreve como a equipe do site:
tom técnico mas acessível, direto, honesto ("analisamos", "nossa análise"),
sempre com transparência sobre links de afiliado. Segue RIGOROSAMENTE o
documento de padrão de artigo fornecido: mesma ordem de seções, mesmos emojis
de cabeçalho, tabelas de especificações, blocos de prova social e de ofertas,
seção de fontes E-E-A-T. Gera HTML limpo para colar no WordPress. Nunca
inventa URLs de imagem: usa <!-- IMAGEM: descrição --> onde falta foto.
Nunca inventa números: usa apenas os dados da ficha técnica fornecida.
Escreve em português do Brasil."""


def _slug(texto: str) -> str:
    texto = texto.lower()
    mapa = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüçñ",
                         "aaaaaeeeeiiiiooooouuuucn")
    texto = texto.translate(mapa)
    texto = re.sub(r"[^a-z0-9\s-]", "", texto)
    return re.sub(r"[\s_]+", "-", texto).strip("-")[:70]


def escrever_artigo(ficha: dict, pauta: dict | None = None,
                    link_amazon: str = "{{LINK_AMAZON}}",
                    link_ml: str = "{{LINK_ML}}",
                    instrucoes_extras: str = "",
                    notas_lojas: str = "") -> tuple[str, dict] | None:
    """Gera o HTML do artigo. Devolve (html, metadados) ou None.

    notas_lojas: texto livre copiado pelo editor com as notas/avaliações
    reais da Amazon e do Mercado Livre. Quando presente, o bloco de prova
    social sai preenchido com números reais (sem placeholders "X,X").
    """
    padrao = config.MODELO_PADRAO.read_text(encoding="utf-8")
    titulo_pauta = (pauta or {}).get("titulo") or \
        f"{ficha.get('nome', 'Produto')} Vale a Pena em 2026? Review Completo"
    palavras = (pauta or {}).get("palavras_chave", "")

    if notas_lojas:
        bloco_notas = (
            "NOTAS REAIS DAS LOJAS (copiadas pelo editor das páginas oficiais "
            "da Amazon e do Mercado Livre — use EXATAMENTE estes números, "
            "textos e citações no bloco '🏆 Aprovado por +X Compradores'; "
            "não arredonde nem invente nada fora delas):\n"
            f"---\n{notas_lojas.strip()}\n---\n"
        )
        regra_notas = ("- Preencha TODO o bloco de prova social com as NOTAS "
                       "REAIS DAS LOJAS acima (notas, totais, percentuais, "
                       "resumo da IA do ML e citação de avaliação).")
    else:
        bloco_notas = ""
        regra_notas = ("- Se alguma nota de loja for null na ficha, escreva o "
                       "bloco de prova social com placeholder \"X,X\" para eu "
                       "preencher manualmente (não invente números).")

    usuario = f"""DOCUMENTO DE PADRÃO DO ARTIGO (siga à risca):
---
{padrao}
---

FICHA TÉCNICA PESQUISADA (fonte dos dados — não invente nada fora dela):
---
{json.dumps(ficha, ensure_ascii=False, indent=2)}
---

TÍTULO DE SEO DESEJADO: {titulo_pauta}
PALAVRAS-CHAVE ALVO: {palavras or 'livre, baseadas no produto'}
{bloco_notas}LINK AFILIADO AMAZON: {link_amazon}
LINK AFILIADO MERCADO LIVRE: {link_ml}
{f'INSTRUÇÕES EXTRAS DO EDITOR: {instrucoes_extras}' if instrucoes_extras else ''}

TAREFA: escreva o artigo COMPLETO em HTML seguindo a estrutura do documento
de padrão, seções 1 a 17, preenchendo com os dados da ficha técnica.
Requisitos finais:
- Comece direto pelo selo (📌 ...), sem <html>/<body> e sem comentário inicial.
- Todos os <h2> numerados no índice devem ter o id correspondente.
- Substitua os placeholders de link pelos links informados acima.
{regra_notas}
- Termine com a seção de fontes e a frase de engajamento.

Depois do HTML, em uma linha final, escreva:
META: {{"slug": "...", "descricao": "meta description de até 155 caracteres",
"categoria": "...", "tags": ["...", "..."]}}"""

    print("✍️  Escrevendo o artigo completo (isso pode levar 1-3 minutos)...")
    try:
        resposta = llm.gerar(SISTEMA, usuario, temperatura=0.6,
                             max_tokens=12000)
    except llm.ErroLLM as exc:
        print(f"❌ {exc}")
        return None

    html, meta = _separar_meta(resposta)
    meta.setdefault("slug", _slug(titulo_pauta))
    meta.setdefault("descricao",
                    (ficha.get("resumo") or titulo_pauta)[:155])
    meta.setdefault("categoria",
                    _categoria_padrao(ficha.get("categoria", "")))
    meta["titulo"] = titulo_pauta

    slug = meta["slug"]
    caminho_html = config.PASTA_ARTIGOS / f"{slug}.html"
    caminho_html.write_text(html, encoding="utf-8")
    caminho_meta = config.PASTA_ARTIGOS / f"{slug}_meta.json"
    caminho_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                            encoding="utf-8")

    palavras_total = len(re.sub(r"<[^>]+>", " ", html).split())
    pendencias = html.count("{{LINK_") + html.count("X,X") + \
        html.count("<!-- IMAGEM")
    print(f"\n✅ Artigo gerado ({palavras_total} palavras):")
    print(f"   HTML: {caminho_html.relative_to(config.RAIZ)}")
    print(f"   Meta: {caminho_meta.relative_to(config.RAIZ)}")
    if pendencias:
        print(f"   ⚠️  {pendencias} pendência(s) para revisão manual "
              f"(placeholders de link, notas de loja ou imagens).")
        print("      Procure por {{LINK_, \"X,X\" e <!-- IMAGEM no HTML.")
    return html, meta


def _separar_meta(resposta: str) -> tuple[str, dict]:
    """Separa o HTML do bloco META: {...} no final da resposta."""
    m = re.search(r"META:\s*(\{.*\})\s*$", resposta, re.DOTALL)
    if m:
        html = resposta[: m.start()].strip()
        try:
            return html, json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return resposta.strip(), {}


def _categoria_padrao(categoria: str) -> str:
    mapa = {
        "smartphone": "Smartphones & Wearables",
        "fone": "Áudio",
        "notebook": "Computadores",
        "tablet": "Tablets",
        "eletroportatil": "Casa Inteligente",
    }
    categoria = (categoria or "").lower()
    for chave, nome in mapa.items():
        if chave in categoria:
            return nome
    return "Tecnologia"


def listar_artigos() -> list[str]:
    return [c.stem for c in sorted(config.PASTA_ARTIGOS.glob("*.html"))]


def carregar_artigo(slug: str) -> tuple[str, dict] | None:
    caminho = config.PASTA_ARTIGOS / f"{slug}.html"
    if not caminho.exists():
        return None
    html = caminho.read_text(encoding="utf-8")
    meta_c = config.PASTA_ARTIGOS / f"{slug}_meta.json"
    meta = json.loads(meta_c.read_text(encoding="utf-8")) \
        if meta_c.exists() else {}
    return html, meta


def gerar_atualizacao(html_antigo: str, instrucoes: str,
                      contexto: str = "") -> str | None:
    """Reesver/atualiza um artigo existente (uso: artigos desatualizados)."""
    usuario = f"""ARTIGO ATUAL EM HTML (publicado no site):
---
{html_antigo[:30000]}
---

O QUE PRECISA SER ATUALIZADO:
{instrucoes}

{f'CONTEXTO EXTRA (ex.: dados novos da web):{chr(10)}{contexto}' if contexto else ''}

TAREFA: devolva o artigo COMPLETO corrigido, mantendo o padrão, os ids dos
<h2> e o estilo originais. Atualize o ano nos títulos e no selo para o ano
corrente ({datetime.now().year}) quando fizer sentido. Não remova links de
afiliado existentes."""
    print("✍️  Reescrevendo o artigo com as atualizações...")
    try:
        return llm.gerar(SISTEMA, usuario, temperatura=0.4, max_tokens=12000)
    except llm.ErroLLM as exc:
        print(f"❌ {exc}")
        return None
