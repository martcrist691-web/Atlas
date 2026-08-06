"""Módulo 3 — Pesquisa de produto e ficha técnica.

Dado o nome de um produto, monta a ficha técnica completa que alimentará o
redator: especificações, prós/contras, concorrentes, público-alvo, FAQ...

Se houver TAVILY_API_KEY no .env, busca dados atualizados na web antes de
gerar a ficha (recomendado). Sem a chave, usa apenas o conhecimento do
modelo de IA — revise os dados antes de publicar.
"""
import json
import re

import requests

from . import config, llm

SISTEMA = """Você é um pesquisador de produtos de tecnologia do site
Curadoria Prime (Brasil). Sua função é montar fichas técnicas PRECISAS de
produtos vendidos no Brasil, com dados verificáveis (especificações
oficiais do fabricante, faixas de preço realistas em R$ para 2025/2026,
concorrentes reais à venda). Nunca invente marcas ou modelos. Em caso de
dúvida sobre um dado, use o valor mais provável e sinalize com "(confirmar)".
Responda sempre em português do Brasil."""


def _buscar_na_web(termo: str, max_resultados: int = 6) -> str:
    """Pesquisa opcional via Tavily. Devolve trechos de texto ou ''."""
    if not config.TAVILY_API_KEY:
        return ""
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": config.TAVILY_API_KEY,
                "query": f"{termo} especificações técnicas preço Brasil review",
                "max_results": max_resultados,
                "search_depth": "advanced",
            },
            timeout=30,
        )
        r.raise_for_status()
        trechos = [f"- {it.get('title', '')}: {it.get('content', '')[:400]}"
                   for it in r.json().get("results", [])]
        return "DADOS ENCONTRADOS NA WEB HOJE:\n" + "\n".join(trechos)
    except requests.RequestException as exc:
        print(f"   ⚠️  Busca web falhou ({exc}). Seguindo sem ela.")
        return ""


def _slug(texto: str) -> str:
    texto = re.sub(r"[^\w\s-]", "", texto.lower())
    return re.sub(r"[\s_]+", "-", texto).strip("-")[:60]


def pesquisar_produto(produto: str, salvar: bool = True) -> dict | None:
    """Gera (e salva) a ficha técnica do produto em JSON."""
    print(f"🔎 Pesquisando: {produto} ...")
    contexto_web = _buscar_na_web(produto)
    if not contexto_web:
        print("   (sem chave Tavily: usando só o conhecimento da IA — "
              "revise os dados!)")

    usuario = f"""Produto a pesquisar: {produto}

{contexto_web}

Monte a ficha técnica completa deste produto para um review brasileiro de 2026.
Devolva APENAS um JSON objeto neste formato exato:
{{
  "nome": "nome oficial completo do produto",
  "categoria": "smartphone | fone | notebook | tablet | eletroportatil | ...",
  "fabricante": "marca",
  "lancamento": "ano/versão",
  "preco_referencia": "faixa em R$ (ex.: R$ 1.800 a R$ 2.200)",
  "nota_sugerida": 8.5,
  "resumo": "2-3 frases: o que é, principal apelo, posicionamento de preço",
  "especificacoes": [
    {{"item": "Processador", "detalhe": "..."}},
    {{"item": "Tela", "detalhe": "..."}}
  ],
  "pros": ["5-6 pontos positivos, cada um: 'Característica: explicação curta'"],
  "contras": ["4-5 pontos de atenção no mesmo formato"],
  "concorrentes": [
    {{"nome": "...", "preco_aprox": "R$ ...", "diferencial": "..."}}
  ],
  "publico_ideal": ["4 perfis 'Compre se você...'"],
  "publico_evite": ["3 perfis 'Evite se você...'"],
  "faq": [
    {{"pergunta": "pergunta real que usuários fazem no Google",
      "resposta": "resposta direta em 2-3 frases"}}
  ],
  "avaliacoes_lojas": {{
    "amazon": {{"nota": 0.0, "total": "nº aproximado"}},
    "mercado_livre": {{"nota": 0.0, "total": "nº aproximado"}}
  }},
  "fontes": ["4-6 fontes para a seção E-E-A-T: fabricante, GSMArena etc."]
}}
Regras:
- 'especificacoes': 12 a 15 linhas relevantes para a categoria.
- 'faq': 5 a 6 perguntas reais.
- 'nota_sugerida': de 0 a 10 com 1 casa decimal, coerente com pros/contras.
- Se não souber notas de lojas com segurança, use null e eu preencho depois."""

    try:
        ficha = llm.gerar_json(SISTEMA, usuario, temperatura=0.4)
    except llm.ErroLLM as exc:
        print(f"❌ {exc}")
        return None

    if not isinstance(ficha, dict) or "nome" not in ficha:
        print("❌ A IA devolveu um formato inesperado. Tente novamente.")
        return None

    if salvar:
        caminho = config.PASTA_PESQUISAS / f"ficha_{_slug(produto)}.json"
        caminho.write_text(json.dumps(ficha, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        print(f"\n💾 Ficha salva em: {caminho.relative_to(config.RAIZ)}")

    _imprimir_ficha(ficha)
    return ficha


def _imprimir_ficha(ficha: dict) -> None:
    print("\n" + "=" * 60)
    print(f"FICHA: {ficha.get('nome', '?')}")
    print("=" * 60)
    print(f"Categoria: {ficha.get('categoria', '?')} | "
          f"Preço: {ficha.get('preco_referencia', '?')} | "
          f"Nota sugerida: {ficha.get('nota_sugerida', '?')}/10")
    print(f"\n{ficha.get('resumo', '')}\n")
    specs = ficha.get("especificacoes") or []
    if specs:
        print(f"Especificações ({len(specs)} itens):")
        for s in specs[:15]:
            print(f"  • {s.get('item', '')}: {s.get('detalhe', '')}")
    print(f"\nPrós: {len(ficha.get('pros') or [])} | "
          f"Contras: {len(ficha.get('contras') or [])} | "
          f"Concorrentes: {len(ficha.get('concorrentes') or [])} | "
          f"FAQ: {len(ficha.get('faq') or [])}")
    if any("(confirmar)" in json.dumps(v, ensure_ascii=False)
           for v in ficha.values()):
        print("\n⚠️  A ficha contém dados marcados como '(confirmar)'. "
              "Revise o arquivo JSON antes de gerar o artigo.")


def carregar_ficha(produto_ou_caminho: str) -> dict | None:
    """Carrega uma ficha já salva pelo nome do produto."""
    slug = _slug(produto_ou_caminho)
    for caminho in sorted(config.PASTA_PESQUISAS.glob("ficha_*.json")):
        if slug in caminho.stem:
            return json.loads(caminho.read_text(encoding="utf-8"))
    return None


def listar_fichas() -> list[str]:
    return [c.stem.replace("ficha_", "")
            for c in sorted(config.PASTA_PESQUISAS.glob("ficha_*.json"))]


def carregar_notas(produto: str) -> str | None:
    """Procura dados/pesquisas/notas_<produto>.txt e devolve o conteúdo.

    Convenção: o editor copia as notas reais das lojas (Amazon e Mercado
    Livre) em um arquivo .txt cujo nome contenha parte do nome do produto,
    ex.: notas_redmi-note-15-pro.txt. O redator usa esses números reais no
    bloco de prova social em vez de placeholders.
    """
    slug = _slug(produto)
    for caminho in sorted(config.PASTA_PESQUISAS.glob("notas_*.txt")):
        if slug in caminho.stem or caminho.stem.replace("notas_", "") in slug:
            return caminho.read_text(encoding="utf-8")
    return None
