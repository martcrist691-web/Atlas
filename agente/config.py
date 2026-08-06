"""Configuração central do Atlas.

Lê o arquivo .env na raiz do projeto e expõe os valores para os demais
módulos. Para criar o .env a partir do modelo, rode no terminal do VS Code:

    cp .env.example .env      (Linux/Mac)
    copy .env.example .env    (Windows)
"""
from pathlib import Path

from dotenv import load_dotenv

# Raiz do projeto = pasta onde ficam atlas.py, .env, modelo/ etc.
RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

import os


def _pega(chave: str, padrao: str = "") -> str:
    valor = os.getenv(chave, padrao).strip()
    return valor if valor else padrao


# --- Site ---------------------------------------------------------------
SITE_URL = _pega("SITE_URL", "https://curadoriaprime.com").rstrip("/")

# --- IA -----------------------------------------------------------------
LLM_PROVIDER = _pega("LLM_PROVIDER", "ollama").lower()  # "ollama" | "openai"

OLLAMA_URL = _pega("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = _pega("OLLAMA_MODEL", "llama3.1")

LLM_API_KEY = _pega("LLM_API_KEY")
LLM_BASE_URL = _pega("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_MODEL = _pega("LLM_MODEL", "gpt-4o-mini")

# --- WordPress ----------------------------------------------------------
WP_USER = _pega("WP_USER")
WP_APP_PASSWORD = _pega("WP_APP_PASSWORD")

# --- Pesquisa web (opcional) --------------------------------------------
TAVILY_API_KEY = _pega("TAVILY_API_KEY")

# --- Pastas de trabalho ---------------------------------------------------
DADOS = RAIZ / "dados"
PASTA_ANALISES = DADOS / "analises"
PASTA_PAUTAS = DADOS / "pautas"
PASTA_PESQUISAS = DADOS / "pesquisas"
PASTA_ARTIGOS = DADOS / "artigos"
MODELO_PADRAO = RAIZ / "modelo" / "padrao_artigo.md"

for pasta in (PASTA_ANALISES, PASTA_PAUTAS, PASTA_PESQUISAS, PASTA_ARTIGOS):
    pasta.mkdir(parents=True, exist_ok=True)

# --- Comportamento do crawler -------------------------------------------
USER_AGENT = (
    "AtlasBot/1.0 (+agente editorial interno da Curadoria Prime; "
    "verificacao de links e conteudo)"
)
# Navegador de verdade: usado ao TESTAR links de terceiros, pois muitos
# sites (Amazon, fabricantes, portais) bloqueiam requisições com cara de
# robô e devolvem 403/503/404 falso para crawlers.
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
PAUSA_ENTRE_POSTS = 1.0      # segundos (educação com o próprio servidor)
PAUSA_ENTRE_LINKS = 0.2      # segundos
TIMEOUT_HTTP = 12            # segundos por requisição
DIAS_DESATUALIZADO = 120     # post sem update há mais que isso => suspeito
