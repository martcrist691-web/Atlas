#!/usr/bin/env python3
"""Testes OFFLINE do Atlas (não precisam de internet nem das dependências).

Simula os módulos externos (requests, bs4, dotenv) só para importar o
projeto e testar a lógica pura: parsing de JSON da IA, slug, heurística de
desatualização, separação de META, calendário de pautas.

Rode:  python testes/teste_offline.py
Na sua máquina, com 'pip install -r requirements.txt' feito, tudo aqui
continua válido — só que com as bibliotecas reais.
"""
import sys
import types
from datetime import datetime
from unittest.mock import MagicMock

# ------------------------------------------------------------------
# 1. Módulos falsos para satisfazer os imports sem internet
# ------------------------------------------------------------------
requests_fake = types.ModuleType("requests")
requests_fake.Session = MagicMock
requests_fake.get = MagicMock()
requests_fake.post = MagicMock()


class _ReqExc(Exception):
    pass


exc_mod = types.ModuleType("requests.exceptions")
for nome in ("SSLError", "ConnectionError", "Timeout", "RequestException"):
    setattr(exc_mod, nome, type(nome, (_ReqExc,), {}))
requests_fake.exceptions = exc_mod
requests_fake.RequestException = exc_mod.RequestException
sys.modules["requests"] = requests_fake
sys.modules["requests.exceptions"] = exc_mod

bs4_fake = types.ModuleType("bs4")
bs4_fake.BeautifulSoup = MagicMock()
sys.modules["bs4"] = bs4_fake

dotenv_fake = types.ModuleType("dotenv")
dotenv_fake.load_dotenv = lambda *a, **k: True
sys.modules["dotenv"] = dotenv_fake

sys.path.insert(0, __file__.rsplit("/", 2)[0])  # raiz do projeto

# ------------------------------------------------------------------
# 2. Testes
# ------------------------------------------------------------------
OK = 0
FALHAS = 0


def testa(nome, condicao):
    global OK, FALHAS
    if condicao:
        OK += 1
        print(f"  ✅ {nome}")
    else:
        FALHAS += 1
        print(f"  ❌ {nome}")


print("\n== llm._extrair_bloco_json ==")
from agente import llm

t1 = '```json\n[{"titulo": "X", "tipo": "review"}]\n```'
r1 = llm._extrair_bloco_json(t1)
import json
testa("extrai JSON com cercas markdown", json.loads(r1)[0]["titulo"] == "X")

t2 = 'Claro! Aqui está: {"a": 1, "b": {"c": [2]}} espero que ajude'
testa("extrai objeto aninhado no meio do texto",
      json.loads(llm._extrair_bloco_json(t2))["b"]["c"] == [2])

t3 = '[1, [2, {"x": "a]b"}]]'
testa("balanceamento com string contendo ]",
      json.loads(llm._extrair_bloco_json(t3))[1][1]["x"] == "a]b")

print("\n== analisador._sinais_desatualizacao ==")
from agente import analisador

hoje = datetime(2026, 8, 6)
post_velho = {
    "texto_check": "moto g54 vale a pena em 2024? review completo",
    "ultima_modificacao": "2025-01-10",
}
sinais = analisador._sinais_desatualizacao(post_velho, hoje)
testa("detecta ano antigo (2024)", any("2024" in s for s in sinais))
testa("detecta post parado há muito tempo",
      any("sem atualização" in s for s in sinais))

post_sazonal = {
    "texto_check": "presentes dia dos pais tech",
    "ultima_modificacao": datetime.now().strftime("%Y-%m-%d"),
}
sinais2 = analisador._sinais_desatualizacao(post_sazonal, datetime(2026, 9, 20))
testa("detecta sazonal 'dia dos pais' que já passou fora de época",
      any("sazonal" in s for s in sinais2))
sinais3 = analisador._sinais_desatualizacao(post_sazonal, datetime(2026, 7, 20))
testa("não marca sazonal na véspera do evento (julho)",
      len(sinais3) == 0)

post_ok = {
    "texto_check": "redmi note 15 pro vale a pena em 2026? review",
    "ultima_modificacao": datetime.now().strftime("%Y-%m-%d"),
}
testa("post recente do ano corrente não gera sinais",
      analisador._sinais_desatualizacao(post_ok, hoje) == [])

print("\n== redator (slug, META, categoria) ==")
from agente import redator

testa("slug remove acentos e pontuação",
      redator._slug("Galaxy Buds FE: Vale a Pena? Áudio 2026!")
      == "galaxy-buds-fe-vale-a-pena-audio-2026")

resp = '<p>artigo…</p>\nMETA: {"slug": "teste-slug", "descricao": "desc"}'
html, meta = redator._separar_meta(resp)
testa("separa HTML do bloco META", html == "<p>artigo…</p>"
      and meta["slug"] == "teste-slug")
resp_sem = "<h2>só html</h2>"
html2, meta2 = redator._separar_meta(resp_sem)
testa("sem META devolve html integral + meta vazio",
      html2 == resp_sem and meta2 == {})
testa("mapeia categoria smartphone",
      redator._categoria_padrao("smartphone") == "Smartphones & Wearables")

print("\n== planejador (CSV de pautas) ==")
from agente import planejador

pautas_teste = [{
    "id": "1", "data_programada": "2026-08-07",
    "titulo": "Teste Vale a Pena em 2026?", "tipo": "review",
    "prioridade": "alta", "justificativa": "teste",
    "palavras_chave": "a, b", "produtos_alvo": "Produto X",
    "origem": "atlas", "status": "sugerida",
}]
planejador.salvar_pautas(pautas_teste)
lid = planejador.carregar_pautas()
testa("salva e relê CSV de pautas",
      len(lid) == 1 and lid[0]["titulo"].startswith("Teste"))
testa("pauta_por_id encontra", planejador.pauta_por_id("1") is not None)
planejador.marcar_status("1", "escrita")
testa("marcar_status atualiza",
      planejador.carregar_pautas()[0]["status"] == "escrita")
# limpa o arquivo de teste
planejador.ARQUIVO_CSV.unlink(missing_ok=True)
planejador.ARQUIVO_JSON.unlink(missing_ok=True)

print("\n== pesquisador.carregar_notas ==")
from agente import pesquisador

arq_notas = pesquisador.config.PASTA_PESQUISAS / "notas_produto-teste-x.txt"
arq_notas.write_text("AMAZON\nnota: 4,6\ntotal: +450", encoding="utf-8")
achado = pesquisador.carregar_notas("produto teste x")
testa("encontra notas_<produto>.txt pelo slug", achado and "4,6" in achado)
testa("produto sem arquivo devolve None",
      pesquisador.carregar_notas("outro produto qq") is None)
arq_notas.unlink()

print("\n== redator: notas das lojas entram no prompt ==")
capturado = {}


def gerar_falso(sistema, usuario, temperatura=0.7, max_tokens=8000):
    capturado["usuario"] = usuario
    return '<p>artigo fake</p>\nMETA: {"slug": "artigo-teste"}'


gerar_original = llm.gerar
llm.gerar = gerar_falso
try:
    res = redator.escrever_artigo({"nome": "Produto Teste", "resumo": "r"},
                                  notas_lojas="nota: 4,6 / total: +450")
    testa("com TXT, notas reais vão para o prompt",
          res is not None and "4,6" in capturado["usuario"]
          and "NOTAS REAIS" in capturado["usuario"])
    res2 = redator.escrever_artigo({"nome": "Produto Sem Nota"})
    testa("sem TXT, prompt mantém regra do placeholder X,X",
          res2 is not None and "X,X" in capturado["usuario"])
finally:
    llm.gerar = gerar_original
    from agente import config as _config_artigos
    for f in _config_artigos.PASTA_ARTIGOS.glob("artigo-teste*"):
        f.unlink()

print("\n== analisador: classificação DNS / link interno ==")
from agente import config

err_dns = Exception("Failed to establish a new connection: "
                    "[Errno -2] Name or service not known")
testa("detecta falha de DNS (domínio inexistente)",
      analisador._falha_dns(err_dns))
testa("conexão recusada NÃO é falha de DNS",
      not analisador._falha_dns(Exception("Connection refused")))
testa("link do próprio site é interno",
      analisador._eh_interno(config.SITE_URL + "/qualquer-post"))
testa("www.no domínio não confunde",
      analisador._eh_interno("https://www." +
                             config.SITE_URL.split("://")[1] + "/post"))
testa("link externo não é interno",
      not analisador._eh_interno("https://www.amazon.com.br/dp/X"))
testa("encurtador de afiliado não é interno",
      not analisador._eh_interno("https://link.amazon/B0abc"))

print("\n== config ==")
from agente import config

testa("pastas de dados criadas",
      config.PASTA_ANALISES.exists() and config.PASTA_ARTIGOS.exists())
testa("SITE_URL sem barra final",
      not config.SITE_URL.endswith("/"))

print("\n" + "=" * 50)
print(f"RESULTADO: {OK} passaram, {FALHAS} falharam")
print("=" * 50)
sys.exit(1 if FALHAS else 0)
