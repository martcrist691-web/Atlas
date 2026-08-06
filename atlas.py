#!/usr/bin/env python3
"""ATLAS — Agente Editorial da Curadoria Prime.

Uso interativo (recomendado para começar):
    python atlas.py

Uso por comando (para automatizar):
    python atlas.py status                  -> testa IA + WordPress
    python atlas.py analisar                -> links quebrados + desatualizados
    python atlas.py pautas [--num 8]        -> sugere/programa pautas com IA
    python atlas.py pesquisar "produto"     -> gera ficha técnica
    python atlas.py escrever --ficha produto [--pauta ID]
    python atlas.py atualizar --slug X --motivo "..."
    python atlas.py publicar --slug X [--status draft|publish]
"""
import argparse
import sys
import webbrowser
from pathlib import Path

from agente import (analisador, config, llm, pesquisador, planejador,
                    publicador, redator)

DIV = "-" * 62


def _input(msg: str, padrao: str = "") -> str:
    valor = input(f"{msg}" + (f" [{padrao}]" if padrao else "") + ": ").strip()
    return valor or padrao


# ----------------------------------------------------------------------
# Ações
# ----------------------------------------------------------------------
def acao_status() -> None:
    print(DIV)
    print("VERIFICAÇÃO DO AMBIENTE")
    print(DIV)
    print("IA:      " + llm.verificar_disponibilidade())
    try:
        print("WP:      " + publicador.testar_conexao())
    except publicador.ErroPublicacao as exc:
        print(f"WP:      (não configurado) {exc}")
    web = "configurada" if config.TAVILY_API_KEY else \
        "não configurada (opcional)"
    print(f"Busca web (Tavily): {web}")
    print(f"Site:    {config.SITE_URL}")


def acao_analisar() -> None:
    try:
        analisador.analisar_site()
    except analisador.ErroAnalise as exc:
        print(f"❌ {exc}")


def acao_pautas(num: int) -> None:
    planejador.sugerir_pautas(num)


def acao_listar_pautas() -> None:
    planejador.listar_pautas()


def acao_pesquisar(produto: str | None) -> dict | None:
    produto = produto or _input("Nome do produto para pesquisar")
    if not produto:
        print("Operação cancelada.")
        return None
    return pesquisador.pesquisar_produto(produto)


def _resolver_notas(produto: str, caminho_arg: str | None) -> str:
    """Resolve o texto das notas das lojas (Amazon / Mercado Livre).

    Ordem: 1) caminho passado via --notas; 2) arquivo notas_<produto>.txt
    encontrado automaticamente em dados/pesquisas; 3) pergunta interativa.
    """
    if caminho_arg:
        p = Path(caminho_arg)
        if p.exists():
            print(f"⭐ Usando notas das lojas de: {p}")
            return p.read_text(encoding="utf-8")
        print(f"⚠️  Arquivo de notas não encontrado: {p} "
              f"(seguindo sem notas)")
        return ""

    if produto:
        auto = pesquisador.carregar_notas(produto)
        if auto is not None:
            print("⭐ Encontrei um arquivo notas_<produto>.txt para este "
                  "produto em dados/pesquisas/.")
            if _input("Usar essas notas reais? (s/n)", "s").lower() == "s":
                return auto
            return ""

    caminho = _input("Caminho do .txt com as notas das lojas "
                     "(Enter para pular)")
    if caminho:
        p = Path(caminho)
        if p.exists():
            return p.read_text(encoding="utf-8")
        print(f"⚠️  Não encontrei {p}. Seguindo sem notas.")
    return ""


def _escolher_ficha() -> dict | None:
    fichas = pesquisador.listar_fichas()
    if not fichas:
        print("Nenhuma ficha salva ainda. Pesquise um produto primeiro.")
        return None
    print("\nFichas disponíveis:")
    for i, nome in enumerate(fichas, 1):
        print(f"  [{i}] {nome}")
    escolha = _input("Número da ficha (ou nome)", "1")
    if escolha.isdigit() and 1 <= int(escolha) <= len(fichas):
        nome = fichas[int(escolha) - 1]
    else:
        nome = escolha
    ficha = pesquisador.carregar_ficha(nome)
    if not ficha:
        print(f"❌ Ficha '{nome}' não encontrada.")
    return ficha


def acao_escrever(ficha_nome: str | None = None,
                  id_pauta: str | None = None,
                  notas_caminho: str | None = None) -> None:
    pauta = planejador.pauta_por_id(id_pauta) if id_pauta else None
    if id_pauta and not pauta:
        print(f"⚠️  Pauta {id_pauta} não encontrada, seguindo sem ela.")

    if ficha_nome:
        ficha = pesquisador.carregar_ficha(ficha_nome)
        if not ficha:
            print("❌ Ficha não encontrada. Rode a pesquisa antes.")
            return
    else:
        ficha = _escolher_ficha()
    if not ficha:
        return

    print(f"\nProduto: {ficha.get('nome')}")
    notas = _resolver_notas(ficha_nome or ficha.get("nome", ""),
                            notas_caminho)
    link_amazon = _input("Link de afiliado AMAZON (Enter = placeholder)",
                         "{{LINK_AMAZON}}")
    link_ml = _input("Link de afiliado MERCADO LIVRE (Enter = placeholder)",
                     "{{LINK_ML}}")
    extras = _input("Instruções extras para o redator (opcional)")

    resultado = redator.escrever_artigo(ficha, pauta, link_amazon,
                                        link_ml, extras, notas)
    if resultado and pauta:
        planejador.marcar_status(pauta["id"], "escrita")
        print(f"   Pauta {pauta['id']} marcada como 'escrita'.")

    if resultado and _input("\nAbrir o HTML no navegador para revisar? "
                            "(s/n)", "n").lower() == "s":
        caminho = config.PASTA_ARTIGOS / f"{resultado[1]['slug']}.html"
        webbrowser.open(caminho.resolve().as_uri())


def acao_atualizar(slug: str | None, motivo: str | None,
                   notas_caminho: str | None = None) -> None:
    """Reescreve um artigo JÁ PUBLICADO no site a partir do HTML ao vivo."""
    artigos = redator.listar_artigos()
    slug = slug or _input("Slug do artigo no site (ex.: moto-g56-5g-review)")
    if not slug:
        return

    # tenta baixar o HTML diretamente da API do WP (precisa de credenciais)
    html_antigo = None
    try:
        post = publicador.buscar_post_por_slug(slug)
        if post:
            html_antigo = post["content"]["rendered"]
            print(f"📥 Artigo '{slug}' baixado do WordPress.")
    except (publicador.ErroPublicacao, KeyError) as exc:
        print(f"⚠️  Não consegui baixar do WP ({exc}).")
        print("    Alternativa: salve o HTML do post em dados/artigos/"
              f"{slug}.html e rode de novo.")
        local = config.PASTA_ARTIGOS / f"{slug}.html"
        if local.exists():
            html_antigo = local.read_text(encoding="utf-8")
            print(f"    Usando o arquivo local {local.name}.")
    if not html_antigo:
        return

    motivo = motivo or _input(
        "O que atualizar? (ex.: 'ano 2026, preços e nova versão HyperOS')")
    if not motivo:
        print("Operação cancelada.")
        return

    notas = _resolver_notas(slug, notas_caminho)
    contexto = ""
    if notas:
        contexto = ("NOTAS REAIS ATUALIZADAS das lojas (copiadas pelo editor "
                    "— substitua os dados do bloco de prova social por "
                    "estes exatos números e citações):\n" + notas)

    novo = redator.gerar_atualizacao(html_antigo, motivo, contexto)
    if not novo:
        return
    saida = config.PASTA_ARTIGOS / f"{slug}_ATUALIZADO.html"
    saida.write_text(novo, encoding="utf-8")
    print(f"\n✅ Versão atualizada salva em: {saida.relative_to(config.RAIZ)}")
    print("   Revise e publique com: python atlas.py publicar --slug "
          f"{slug} --arquivo {saida.name}")


def acao_publicar(slug: str | None, arquivo: str | None,
                  status: str) -> None:
    if arquivo:
        caminho = config.PASTA_ARTIGOS / arquivo
        if not caminho.exists():
            print(f"❌ Arquivo não encontrado: {caminho}")
            return
        html = caminho.read_text(encoding="utf-8")
        meta_c = caminho.with_name(caminho.stem.replace("_ATUALIZADO", "")
                                   + "_meta.json")
        meta = (__import__("json").loads(meta_c.read_text(encoding="utf-8"))
                if meta_c.exists() else {})
        slug = slug or caminho.stem.replace("_ATUALIZADO", "")
    else:
        if not slug:
            artigos = redator.listar_artigos()
            if not artigos:
                print("Nenhum artigo gerado ainda.")
                return
            print("\nArtigos gerados:")
            for i, a in enumerate(artigos, 1):
                print(f"  [{i}] {a}")
            escolha = _input("Número do artigo", "1")
            if not (escolha.isdigit() and 1 <= int(escolha) <= len(artigos)):
                return
            slug = artigos[int(escolha) - 1]
        dados = redator.carregar_artigo(slug)
        if not dados:
            print(f"❌ Artigo '{slug}' não encontrado em dados/artigos/.")
            return
        html, meta = dados

    pend = html.count("{{LINK_") + html.count("X,X")
    if pend:
        print(f"⚠️  O HTML tem {pend} placeholder(s) de link/nota por "
              f"preencher.")
        if _input("Publicar mesmo assim? (s/n)", "n").lower() != "s":
            return

    print(f"\nEnviando '{slug}' para o WordPress como "
          f"{'RASCUNHO' if status == 'draft' else 'PUBLICADO'}...")
    try:
        res = publicador.publicar(slug, html, meta, status)
    except publicador.ErroPublicacao as exc:
        print(f"❌ {exc}")
        return
    print(f"✅ Post {res['acao']} no WordPress (id {res['id']}, "
          f"status {res['status']}):\n   {res['link']}")


# ----------------------------------------------------------------------
# Menu interativo
# ----------------------------------------------------------------------
MENU = f"""
{DIV}
  ATLAS — Agente Editorial da Curadoria Prime
  Site: {config.SITE_URL}
{DIV}
  1) Verificar ambiente (IA, WordPress)
  2) Analisar site (links quebrados + desatualizados)
  3) Sugerir e programar pautas (IA)
  4) Ver calendário de pautas
  5) Pesquisar produto (ficha técnica)
  6) Escrever artigo (HTML no padrão do site)
  7) Atualizar artigo já publicado no site
  8) Enviar artigo ao WordPress (rascunho)
  0) Sair
"""


def menu() -> None:
    while True:
        print(MENU)
        op = _input("Escolha uma opção")
        if op == "1":
            acao_status()
        elif op == "2":
            acao_analisar()
        elif op == "3":
            num = _input("Quantas pautas sugerir?", "8")
            acao_pautas(int(num) if num.isdigit() else 8)
        elif op == "4":
            acao_listar_pautas()
        elif op == "5":
            acao_pesquisar(None)
        elif op == "6":
            idp = _input("ID da pauta (Enter para escolher só pela ficha)")
            acao_escrever(id_pauta=idp or None)
        elif op == "7":
            acao_atualizar(None, None)
        elif op == "8":
            acao_publicar(None, None, "draft")
        elif op == "0":
            print("Até mais! 👋")
            return
        else:
            print("Opção inválida.")
        input("\n[Enter para voltar ao menu]")


# ----------------------------------------------------------------------
# CLI por subcomandos
# ----------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Atlas — Agente Editorial da Curadoria Prime")
    sub = parser.add_subparsers(dest="comando")

    sub.add_parser("status")
    sub.add_parser("analisar")
    p_pautas = sub.add_parser("pautas")
    p_pautas.add_argument("--num", type=int, default=8)
    sub.add_parser("listar-pautas")
    p_pesq = sub.add_parser("pesquisar")
    p_pesq.add_argument("produto")
    p_esc = sub.add_parser("escrever")
    p_esc.add_argument("--ficha", default=None)
    p_esc.add_argument("--pauta", default=None)
    p_esc.add_argument("--notas", default=None,
                       help="caminho do .txt com notas reais das lojas")
    p_atu = sub.add_parser("atualizar")
    p_atu.add_argument("--slug", default=None)
    p_atu.add_argument("--motivo", default=None)
    p_atu.add_argument("--notas", default=None,
                       help="caminho do .txt com notas reais atualizadas")
    p_pub = sub.add_parser("publicar")
    p_pub.add_argument("--slug", default=None)
    p_pub.add_argument("--arquivo", default=None)
    p_pub.add_argument("--status", choices=["draft", "publish"],
                       default="draft")

    args = parser.parse_args()

    if args.comando is None:
        menu()
    elif args.comando == "status":
        acao_status()
    elif args.comando == "analisar":
        acao_analisar()
    elif args.comando == "pautas":
        acao_pautas(args.num)
    elif args.comando == "listar-pautas":
        acao_listar_pautas()
    elif args.comando == "pesquisar":
        acao_pesquisar(args.produto)
    elif args.comando == "escrever":
        acao_escrever(args.ficha, args.pauta, args.notas)
    elif args.comando == "atualizar":
        acao_atualizar(args.slug, args.motivo, args.notas)
    elif args.comando == "publicar":
        acao_publicar(args.slug, args.arquivo, args.status)


if __name__ == "__main__":
    sys.exit(main())
