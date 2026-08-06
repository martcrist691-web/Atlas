#!/usr/bin/env python3
"""Painel web do Atlas — use o agente pelo navegador, sem terminal.

Roda um mini-site local na sua máquina (ninguém mais tem acesso):

    python painel.py              -> abre http://127.0.0.1:5000 no Chrome
    python painel.py --porta 8000 -> outra porta
    python painel.py --no-browser -> não abrir o navegador sozinho

No Windows, dê dois cliques em "Abrir Painel Atlas.bat".

Requer: pip install -r requirements.txt  (inclui flask)
"""
import argparse
import io
import logging
import threading
import traceback
import uuid
import webbrowser
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

from flask import (Flask, abort, flash, jsonify, redirect,
                   render_template, request, send_file, url_for)
from markupsafe import escape

from agente import (analisador, config, llm, pesquisador, planejador,
                    publicador, redator)

app = Flask(__name__)
app.secret_key = "atlas-painel-local"  # só para mensagens flash; app é local

# silencia o log de requisições HTTP (para não poluir o log das tarefas)
logging.getLogger("werkzeug").setLevel(logging.ERROR)


# ----------------------------------------------------------------------
# Gerenciador de tarefas (uma por vez, com log ao vivo)
# ----------------------------------------------------------------------
JOBS: dict[str, dict] = {}


class _ColetorLog(io.TextIOBase):
    """Desvia os print() dos módulos para dentro do job."""

    def __init__(self, job: dict):
        self.job = job

    def write(self, s):
        if s:
            self.job["log"] += str(s)

    def flush(self):
        pass


def iniciar_job(tipo: str, funcao, **kwargs) -> str | None:
    """Roda `funcao` em segundo plano capturando a saída. None se ocupado."""
    if any(j["status"] == "rodando" for j in JOBS.values()):
        return None
    jid = uuid.uuid4().hex[:8]
    job = {
        "id": jid, "tipo": tipo, "status": "rodando", "log": "",
        "resultado": None, "erro": None,
        "inicio": datetime.now().strftime("%d/%m %H:%M:%S"),
    }
    JOBS[jid] = job

    def _run():
        try:
            with redirect_stdout(_ColetorLog(job)):
                job["resultado"] = funcao(**kwargs)
            if job["resultado"] is None:
                job["status"] = "erro"
                job["log"] += ("\n❌ A tarefa terminou sem resultado. "
                               "Veja o motivo nas linhas acima.\n")
            else:
                job["status"] = "ok"
        except Exception:
            job["status"] = "erro"
            job["log"] += "\n" + traceback.format_exc(limit=4)

    threading.Thread(target=_run, daemon=True).start()
    return jid


def _iniciar_ou_avisar(tipo: str, funcao, **kwargs):
    jid = iniciar_job(tipo, funcao, **kwargs)
    if jid is None:
        flash("Já existe uma tarefa rodando. Aguarde terminar "
              "(o painel executa uma tarefa por vez).")
        return redirect(request.referrer or url_for("index"))
    return redirect(url_for("pagina_job", jid=jid))


# ----------------------------------------------------------------------
# Adaptadores: transformam os resultados dos módulos em HTML de resultado
# ----------------------------------------------------------------------
def _job_atualizar(slug: str, motivo: str, notas: str) -> dict | None:
    html_antigo = None
    try:
        post = publicador.buscar_post_por_slug(slug)
        if post:
            html_antigo = post["content"]["rendered"]
            print(f"📥 Artigo '{slug}' baixado do WordPress.")
    except Exception as exc:
        print(f"⚠️  Não consegui baixar do WP ({exc}). "
              f"Procurando arquivo local...")
    if html_antigo is None:
        local = config.PASTA_ARTIGOS / f"{slug}.html"
        if local.exists():
            html_antigo = local.read_text(encoding="utf-8")
            print(f"📄 Usando o arquivo local {local.name}.")
    if html_antigo is None:
        print("❌ Artigo não encontrado nem no WP nem em dados/artigos/.")
        return None

    contexto = ""
    if notas:
        contexto = ("NOTAS REAIS ATUALIZADAS das lojas (copiadas pelo editor "
                    "— substitua os dados do bloco de prova social por "
                    "estes exatos números e citações):\n" + notas)
    novo = redator.gerar_atualizacao(html_antigo, motivo, contexto)
    if not novo:
        return None
    saida = config.PASTA_ARTIGOS / f"{slug}_ATUALIZADO.html"
    saida.write_text(novo, encoding="utf-8")
    print(f"\n✅ Versão atualizada salva em: dados/artigos/{saida.name}")
    return {"arquivo": saida.name}


def _job_publicar(slug: str, status: str) -> dict:
    dados = redator.carregar_artigo(slug.replace("_ATUALIZADO", ""))
    caminho = config.PASTA_ARTIGOS / f"{slug}.html"
    if slug.endswith("_ATUALIZADO") and caminho.exists():
        conteudo = caminho.read_text(encoding="utf-8")
        meta = dados[1] if dados else {}
        slug_real = slug.replace("_ATUALIZADO", "")
    else:
        if not dados:
            print("❌ Artigo não encontrado.")
            return None
        conteudo, meta = dados
        slug_real = slug
    pend = conteudo.count("{{LINK_") + conteudo.count("X,X")
    if pend:
        print(f"⚠️  Atenção: {pend} placeholder(s) ainda presentes no HTML.")
    return publicador.publicar(slug_real, conteudo, meta, status)


def _resultado_html(job: dict) -> str:
    """Monta o bloco de resultado exibido ao fim de cada tarefa."""
    r, t = job["resultado"], job["tipo"]
    if r is None:
        return ""
    try:
        if t == "analisar":
            res = r["resumo"]
            ind = res.get("links_indeterminados", 0)
            return (
                f"<h3>📊 Resumo</h3><ul>"
                f"<li>Artigos analisados: <b>{res['total_artigos']}</b></li>"
                f"<li>Links verificados: <b>{res['links_unicos_verificados']}</b></li>"
                f"<li>Links quebrados confirmados: <b class='ruim'>"
                f"{res['links_quebrados']}</b> "
                f"(em {res['artigos_com_link_quebrado']} artigos)</li>"
                f"<li>Não verificáveis (sites que bloqueiam robôs): "
                f"<b class='atencao'>{ind}</b></li>"
                f"<li>Artigos desatualizados: "
                f"<b class='atencao'>{res['artigos_desatualizados']}</b></li></ul>"
                f"<p><a class='botao' href='{url_for('pagina_analisar')}'>"
                f"Ver relatório completo</a></p>"
            )
        if t == "pautas":
            itens = "".join(
                f"<li><b>{escape(p['data_programada'])}</b> "
                f"({escape(p['prioridade'])}) — {escape(p['titulo'])}</li>"
                for p in r)
            return (f"<h3>📅 {len(r)} pautas adicionadas</h3>"
                    f"<ol>{itens}</ol>"
                    f"<p><a class='botao' href='{url_for('pagina_pautas')}'>"
                    f"Ver calendário</a></p>")
        if t == "pesquisar":
            nome = escape(str(r.get("nome", "?")))
            return (
                f"<h3>📋 Ficha pronta: {nome}</h3><ul>"
                f"<li>Preço de referência: "
                f"<b>{escape(str(r.get('preco_referencia', '?')))}</b></li>"
                f"<li>Nota sugerida: <b>{r.get('nota_sugerida', '?')}/10</b></li>"
                f"<li>Especificações: {len(r.get('especificacoes') or [])} itens</li>"
                f"<li>Concorrentes: {len(r.get('concorrentes') or [])}</li></ul>"
                f"<p>Abra a pasta <code>dados/pesquisas/</code> para revisar "
                f"o JSON antes de escrever o artigo.</p>"
            )
        if t == "escrever":
            conteudo, meta = r
            slug = escape(str(meta.get("slug", "artigo")))
            pend = (conteudo.count("{{LINK_") + conteudo.count("X,X")
                    + conteudo.count("<!-- IMAGEM"))
            aviso = (f"<p class='atencao'>⚠️ {pend} pendência(s): procure por "
                     f"<code>{{{{LINK_</code>, <code>X,X</code> e "
                     f"<code>&lt;!-- IMAGEM</code> no arquivo.</p>"
                     if pend else "<p>✅ Sem pendências de revisão.</p>")
            return (
                f"<h3>✍️ Artigo gerado</h3>"
                f"<p><b>{escape(str(meta.get('titulo', slug)))}</b></p>{aviso}"
                f"<p><a class='botao' target='_blank' "
                f"href='{url_for('preview_artigo', slug=slug)}'>"
                f"👁️ Visualizar</a> "
                f"<a class='botao' href='{url_for('download_artigo', slug=slug)}'>"
                f"⬇️ Baixar HTML</a> "
                f"<a class='botao' href='{url_for('pagina_artigos')}'>"
                f"Publicar como rascunho</a></p>"
            )
        if t == "atualizar":
            arq = escape(str(r["arquivo"]))
            return (f"<h3>♻️ Atualização gerada</h3><p>Arquivo: "
                    f"<code>dados/artigos/{arq}</code></p>"
                    f"<p><a class='botao' href='{url_for('pagina_artigos')}'>"
                    f"Revisar e publicar</a></p>")
        if t == "publicar":
            return (f"<h3>🚀 Post {escape(str(r['acao']))} no WordPress</h3>"
                    f"<p>Status: <b>{escape(str(r['status']))}</b> · "
                    f"ID: {r.get('id')}</p>"
                    f"<p><a class='botao' target='_blank' "
                    f"href='{escape(str(r.get('link', '')))}'>Abrir no site"
                    f"</a></p>")
    except Exception:
        return "<p>Tarefa concluída (veja o log).</p>"
    return ""


# ----------------------------------------------------------------------
# Páginas
# ----------------------------------------------------------------------
@app.route("/")
def index():
    try:
        status_ia = llm.verificar_disponibilidade()
    except Exception as exc:
        status_ia = f"erro ao verificar: {exc}"
    status_wp = "(não configurado)"
    if config.WP_USER and config.WP_APP_PASSWORD:
        try:
            status_wp = publicador.testar_conexao()
        except Exception as exc:
            status_wp = f"erro: {exc}"
    ultima = analisador.carregar_ultima_analise()
    return render_template(
        "index.html",
        status_ia=status_ia,
        status_wp=status_wp,
        status_web=("configurada" if config.TAVILY_API_KEY
                    else "não configurada (opcional)"),
        site=config.SITE_URL,
        ultima=ultima,
        pautas=planejador.carregar_pautas()[:6],
        fichas=pesquisador.listar_fichas(),
        artigos=redator.listar_artigos(),
        jobs_rodando=[j for j in JOBS.values() if j["status"] == "rodando"],
    )


@app.route("/analisar")
def pagina_analisar():
    arquivos = sorted((c.name for c in
                       config.PASTA_ANALISES.glob("analise_*.json")),
                      reverse=True)
    relatorio, nome_atual = None, request.args.get("ver")
    if nome_atual:
        seguro = (nome_atual.startswith("analise_")
                  and nome_atual.endswith(".json") and "/" not in nome_atual)
        caminho = config.PASTA_ANALISES / nome_atual
        if seguro and caminho.exists():
            import json
            relatorio = json.loads(caminho.read_text(encoding="utf-8"))
    return render_template("analisar.html", arquivos=arquivos,
                           relatorio=relatorio, nome_atual=nome_atual)


@app.route("/analisar/iniciar", methods=["POST"])
def analisar_iniciar():
    return _iniciar_ou_avisar("analisar", analisador.analisar_site)


@app.route("/pautas")
def pagina_pautas():
    return render_template("pautas.html",
                           pautas=planejador.carregar_pautas())


@app.route("/pautas/gerar", methods=["POST"])
def pautas_gerar():
    try:
        num = max(1, min(20, int(request.form.get("num", 8))))
    except ValueError:
        num = 8
    return _iniciar_ou_avisar("pautas", planejador.sugerir_pautas,
                              quantidade=num)


@app.route("/pesquisar")
def pagina_pesquisar():
    return render_template("pesquisar.html",
                           fichas=pesquisador.listar_fichas())


@app.route("/pesquisar/iniciar", methods=["POST"])
def pesquisar_iniciar():
    produto = request.form.get("produto", "").strip()
    if not produto:
        flash("Informe o nome do produto.")
        return redirect(url_for("pagina_pesquisar"))
    return _iniciar_ou_avisar("pesquisar", pesquisador.pesquisar_produto,
                              produto=produto)


def _notas_do_form() -> str:
    """Notas das lojas: texto colado tem prioridade; senão, arquivo .txt."""
    texto = request.form.get("notas_texto", "").strip()
    if texto:
        return texto
    nome = request.form.get("notas_arquivo", "").strip()
    if nome:
        caminho = config.PASTA_PESQUISAS / Path(nome).name
        if caminho.exists() and caminho.name.startswith("notas_"):
            return caminho.read_text(encoding="utf-8")
    return ""


def _arquivos_notas() -> list[str]:
    return sorted(c.name for c in
                  config.PASTA_PESQUISAS.glob("notas_*.txt"))


@app.route("/escrever")
def pagina_escrever():
    return render_template("escrever.html",
                           fichas=pesquisador.listar_fichas(),
                           pautas=planejador.carregar_pautas(),
                           notas_arquivos=_arquivos_notas())


@app.route("/escrever/iniciar", methods=["POST"])
def escrever_iniciar():
    ficha = pesquisador.carregar_ficha(request.form.get("ficha", ""))
    if not ficha:
        flash("Escolha uma ficha técnica. Se ainda não tem, pesquise o "
              "produto primeiro.")
        return redirect(url_for("pagina_escrever"))
    pauta = planejador.pauta_por_id(request.form.get("pauta", ""))
    return _iniciar_ou_avisar(
        "escrever", redator.escrever_artigo,
        ficha=ficha, pauta=pauta,
        link_amazon=request.form.get("link_amazon", "").strip()
        or "{{LINK_AMAZON}}",
        link_ml=request.form.get("link_ml", "").strip() or "{{LINK_ML}}",
        instrucoes_extras=request.form.get("extras", "").strip(),
        notas_lojas=_notas_do_form(),
    )


@app.route("/atualizar")
def pagina_atualizar():
    return render_template("atualizar.html",
                           notas_arquivos=_arquivos_notas(),
                           artigos=redator.listar_artigos())


@app.route("/atualizar/iniciar", methods=["POST"])
def atualizar_iniciar():
    slug = request.form.get("slug", "").strip()
    motivo = request.form.get("motivo", "").strip()
    if not slug or not motivo:
        flash("Informe o slug do artigo e o motivo da atualização.")
        return redirect(url_for("pagina_atualizar"))
    return _iniciar_ou_avisar("atualizar", _job_atualizar,
                              slug=slug, motivo=motivo,
                              notas=_notas_do_form())


@app.route("/artigos")
def pagina_artigos():
    lista = []
    for slug in redator.listar_artigos():
        dados = redator.carregar_artigo(slug)
        conteudo, meta = dados if dados else ("", {})
        lista.append({
            "slug": slug,
            "titulo": meta.get("titulo", slug),
            "pendencias": (conteudo.count("{{LINK_")
                           + conteudo.count("X,X")
                           + conteudo.count("<!-- IMAGEM")),
            "eh_atualizacao": slug.endswith("_ATUALIZADO"),
        })
    return render_template("artigos.html", artigos=lista,
                           wp_ok=bool(config.WP_USER
                                      and config.WP_APP_PASSWORD))


@app.route("/artigos/<slug>/preview")
def preview_artigo(slug):
    dados = redator.carregar_artigo(slug)
    if not dados:
        abort(404)
    conteudo, meta = dados
    return render_template("artigo_preview.html", slug=slug,
                           conteudo=conteudo, meta=meta)


@app.route("/artigos/<slug>/download")
def download_artigo(slug):
    caminho = config.PASTA_ARTIGOS / f"{slug}.html"
    if not caminho.exists():
        abort(404)
    return send_file(caminho, as_attachment=True)


@app.route("/artigos/<slug>/publicar", methods=["POST"])
def publicar_artigo(slug):
    status = request.form.get("status", "draft")
    status = "publish" if status == "publish" else "draft"
    return _iniciar_ou_avisar("publicar", _job_publicar,
                              slug=slug, status=status)


# ----------------------------------------------------------------------
# Acompanhamento das tarefas
# ----------------------------------------------------------------------
@app.route("/jobs/<jid>")
def pagina_job(jid):
    job = JOBS.get(jid)
    if not job:
        abort(404)
    return render_template("job.html", job=job)


@app.route("/api/jobs/<jid>")
def api_job(jid):
    job = JOBS.get(jid)
    if not job:
        abort(404)
    resultado_html = ""
    if job["status"] == "ok":
        resultado_html = _resultado_html(job)
    elif job["status"] == "erro":
        resultado_html = ("<h3>❌ A tarefa encontrou um problema</h3>"
                          "<p>Leia o log acima — geralmente o motivo está "
                          "na última linha.</p>")
    return jsonify({"status": job["status"], "log": job["log"],
                    "resultado_html": resultado_html,
                    "voltar": _voltar_para(job["tipo"])})


def _voltar_para(tipo: str) -> str:
    mapa = {"analisar": "pagina_analisar", "pautas": pagina_pautas.__name__,
            "pesquisar": "pagina_escrever", "escrever": "pagina_artigos",
            "atualizar": "pagina_artigos", "publicar": "pagina_artigos"}
    return url_for(mapa.get(tipo, "index"))


# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Painel web do Atlas")
    parser.add_argument("--porta", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1",
                        help="mantenha 127.0.0.1: painel só na sua máquina")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    url = f"http://127.0.0.1:{args.porta}"
    print(f"\n  ATLAS — Painel web rodando em {url}")
    print("  (deixe esta janela aberta; Ctrl+C para encerrar)\n")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host=args.host, port=args.porta, threaded=True)


if __name__ == "__main__":
    main()
