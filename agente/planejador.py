"""Módulo 2 — Sugestão e programação de pautas.

Lê o relatório mais recente do analisador (se existir) + a lista de artigos
já publicados e pede à IA sugestões de pautas alinhadas ao calendário
(datas comemorativas, lançamentos, lacunas de conteúdo).

As pautas ficam salvas em dados/pautas/pautas.csv com status e data
programada — é o "calendário editorial" do site.
"""
import csv
import json
from datetime import datetime, timedelta

from . import analisador, config, llm

ARQUIVO_CSV = config.PASTA_PAUTAS / "pautas.csv"
ARQUIVO_JSON = config.PASTA_PAUTAS / "pautas.json"

CAMPOS = ["id", "data_programada", "titulo", "tipo", "prioridade",
          "justificativa", "palavras_chave", "produtos_alvo", "origem",
          "status"]

SISTEMA = """Você é o editor-chefe do Curadoria Prime (curadoriaprime.com),
um site brasileiro de reviews de tecnologia e guias de presentes (smartphones,
fones Bluetooth, notebooks, tablets, wearables e eletroportáteis).
Sua função é propor pautas realistas e ranqueáveis no Google Brasil:
reviews de produtos vendidos na Amazon/Mercado Livre brasileiros, comparativos,
guias sazonais (Dia das Mães, Dia dos Namorados, Dia dos Pais, Dia das
Crianças, Black Friday, Natal, Volta às Aulas) e atualizações de artigos
antigos. Sempre responda em português do Brasil."""


def _contexto(analise: dict | None, pautas_existentes: list[dict]) -> str:
    partes = []
    if analise:
        artigos = analise["artigos"]
        partes.append("ARTIGOS JÁ PUBLICADOS (não repetir):")
        for a in artigos:
            partes.append(f"- {a['titulo']} ({a['url']})")
        desatualizados = [a for a in artigos if a["sinais_desatualizacao"]]
        if desatualizados:
            partes.append("\nARTIGOS COM SINAL DE DESATUALIZAÇÃO "
                          "(candidatos a pauta de ATUALIZAÇÃO):")
            for a in desatualizados:
                motivos = "; ".join(a["sinais_desatualizacao"])
                partes.append(f"- {a['titulo']} -> {motivos}")
        quebrados = [a for a in artigos if a["links_quebrados"]]
        if quebrados:
            partes.append("\nARTIGOS COM LINKS QUEBRADOS (correção urgente):")
            for a in quebrados:
                partes.append(
                    f"- {a['titulo']} -> {len(a['links_quebrados'])} quebrados")
    else:
        partes.append("(Nenhuma análise do site disponível ainda. Considere "
                      "o nicho geral do site descrito nas instruções.)")
    if pautas_existentes:
        partes.append("\nPAUTAS JÁ PROGRAMADAS (não repetir):")
        for p in pautas_existentes:
            partes.append(f"- [{p['status']}] {p['titulo']}")
    return "\n".join(partes)


def carregar_pautas() -> list[dict]:
    if not ARQUIVO_CSV.exists():
        return []
    with ARQUIVO_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def salvar_pautas(pautas: list[dict]) -> None:
    with ARQUIVO_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        for p in pautas:
            w.writerow({c: p.get(c, "") for c in CAMPOS})
    ARQUIVO_JSON.write_text(
        json.dumps(pautas, ensure_ascii=False, indent=2), encoding="utf-8")


def sugerir_pautas(quantidade: int = 8) -> list[dict]:
    """Pede à IA novas pautas, programa as datas e grava no CSV."""
    print("📊 Carregando contexto (última análise + pautas existentes)...")
    analise = analisador.carregar_ultima_analise()
    existentes = carregar_pautas()
    if analise is None:
        print("   ⚠️  Nenhuma análise encontrada. Dica: rode primeiro "
              "'python atlas.py analisar' para sugestões mais precisas.")

    hoje = datetime.now()
    usuario = f"""Data de hoje: {hoje.strftime('%d/%m/%Y')}.

{_contexto(analise, existentes)}

TAREFA: sugira {quantidade} novas pautas para as próximas 4 semanas.
Regras:
- Misture tipos: review de produto, comparativo, guia sazonal e
  ATUALIZAÇÃO de artigo desatualizado (quando houver).
- Priorize o que tem deadline perto (sazonalidades) e correções urgentes.
- Produtos devem existir de verdade e estar à venda no Brasil (2025/2026).
- Não repita artigos já publicados nem pautas já programadas.

Devolva um JSON array com objetos neste formato exato:
[{{
  "titulo": "título otimizado para SEO (ex.: 'X Vale a Pena em 2026? Review')",
  "tipo": "review | comparativo | guia_sazonal | atualizacao",
  "prioridade": "alta | media | baixa",
  "justificativa": "1-2 frases: por que essa pauta agora",
  "palavras_chave": "palavra1, palavra2, palavra3",
  "produtos_alvo": "produto principal e concorrentes, separados por vírgula"
}}]"""

    print(f"🧠 Pedindo {quantidade} sugestões de pauta à IA...")
    try:
        sugestoes = llm.gerar_json(SISTEMA, usuario)
    except llm.ErroLLM as exc:
        print(f"❌ {exc}")
        return []

    if not isinstance(sugestoes, list):
        print("❌ A IA devolveu um formato inesperado. Tente novamente.")
        return []

    # Programação: espalha pautas a partir de amanhã, prioridade alta antes
    ordem = {"alta": 0, "media": 1, "média": 1, "baixa": 2}
    sugestoes.sort(key=lambda s: ordem.get(str(s.get("prioridade", ""))
                                            .lower(), 1))
    proximo_id = max([int(p["id"]) for p in existentes
                      if p["id"].isdigit()] or [0])
    novas = []
    for i, s in enumerate(sugestoes):
        if not isinstance(s, dict) or not s.get("titulo"):
            continue
        proximo_id += 1
        data = hoje + timedelta(days=1 + i * 3)  # 1 pauta a cada 3 dias
        novas.append({
            "id": str(proximo_id),
            "data_programada": data.strftime("%Y-%m-%d"),
            "titulo": str(s.get("titulo", "")).strip(),
            "tipo": str(s.get("tipo", "review")).strip(),
            "prioridade": str(s.get("prioridade", "media")).strip(),
            "justificativa": str(s.get("justificativa", "")).strip(),
            "palavras_chave": str(s.get("palavras_chave", "")).strip(),
            "produtos_alvo": str(s.get("produtos_alvo", "")).strip(),
            "origem": "atlas",
            "status": "sugerida",
        })

    todas = existentes + novas
    salvar_pautas(todas)

    print(f"\n✅ {len(novas)} pautas adicionadas a "
          f"{ARQUIVO_CSV.relative_to(config.RAIZ)}\n")
    _listar(novas)
    return novas


def _listar(pautas: list[dict]) -> None:
    for p in pautas:
        print(f"  [{p['id']:>3}] {p['data_programada']} "
              f"({p['prioridade']:<6}) {p['titulo']}")
        if p.get("justificativa"):
            print(f"        ↳ {p['justificativa'][:90]}")


def listar_pautas() -> None:
    pautas = carregar_pautas()
    if not pautas:
        print("Nenhuma pauta cadastrada ainda. Use a opção de sugerir pautas.")
        return
    print(f"\n📅 Calendário editorial ({len(pautas)} pautas):\n")
    _listar(pautas)


def pauta_por_id(id_pauta: str) -> dict | None:
    for p in carregar_pautas():
        if p["id"] == str(id_pauta):
            return p
    return None


def marcar_status(id_pauta: str, status: str) -> None:
    pautas = carregar_pautas()
    for p in pautas:
        if p["id"] == str(id_pauta):
            p["status"] = status
    salvar_pautas(pautas)
