"""Cliente de IA unificado do Atlas.

Funciona com dois provedores, escolhidos no .env (LLM_PROVIDER):

- "ollama": IA 100% local e grátis (https://ollama.com). Boa para começar
  sem custo. Recomendado: llama3.1, qwen2.5 ou gemma2.
- "openai": qualquer API compatível com o formato OpenAI
  (OpenAI, Groq, DeepSeek, Gemini, OpenRouter...). Melhor qualidade.

Uso:

    from agente import llm
    texto = llm.gerar("Você é um editor de tecnologia.", "Escreva...")
    dados = llm.gerar_json(sistema, usuario)   # devolve dict/list já parseado
"""
import json
import re

import requests

from . import config

TIMEOUT_LLM = 300  # geração de artigo longo pode demorar


class ErroLLM(RuntimeError):
    """Erro de comunicação/configuração com o provedor de IA."""


def verificar_disponibilidade() -> str:
    """Confere se o provedor configurado está acessível. Devolve mensagem."""
    if config.LLM_PROVIDER == "ollama":
        try:
            r = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=10)
            r.raise_for_status()
            modelos = [m["name"] for m in r.json().get("models", [])]
            if not modelos:
                return (
                    "Ollama está rodando, mas sem modelos. Rode: "
                    f"ollama pull {config.OLLAMA_MODEL}"
                )
            tem = any(m.split(":")[0] == config.OLLAMA_MODEL.split(":")[0]
                      for m in modelos)
            if not tem:
                return (
                    f"Modelo '{config.OLLAMA_MODEL}' não encontrado no Ollama. "
                    f"Disponíveis: {', '.join(modelos)}. "
                    f"Rode: ollama pull {config.OLLAMA_MODEL}"
                )
            return f"OK - Ollama local com o modelo {config.OLLAMA_MODEL}"
        except requests.RequestException:
            return (
                "Ollama não está respondendo em "
                f"{config.OLLAMA_URL}. Instale em https://ollama.com, "
                "abra o app e rode: ollama pull " + config.OLLAMA_MODEL
            )
    else:
        if not config.LLM_API_KEY:
            return (
                "LLM_API_KEY está vazia no .env. Preencha com a chave da sua "
                "API (OpenAI, Groq, DeepSeek, Gemini, OpenRouter...) ou troque "
                "LLM_PROVIDER para 'ollama'."
            )
        return (f"OK - API configurada ({config.LLM_BASE_URL}, "
                f"modelo {config.LLM_MODEL})")


def gerar(sistema: str, usuario: str, temperatura: float = 0.7,
          max_tokens: int = 8000) -> str:
    """Chama o provedor de IA configurado e devolve o texto gerado."""
    if config.LLM_PROVIDER == "ollama":
        return _gerar_ollama(sistema, usuario, temperatura)
    return _gerar_openai(sistema, usuario, temperatura, max_tokens)


def _gerar_ollama(sistema: str, usuario: str, temperatura: float) -> str:
    url = f"{config.OLLAMA_URL}/api/chat"
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": usuario},
        ],
        "stream": False,
        "options": {"temperature": temperatura},
    }
    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT_LLM)
        r.raise_for_status()
    except requests.ConnectionError as exc:
        raise ErroLLM(
            "Não consegui falar com o Ollama. Ele está aberto? "
            f"(tentei {url})"
        ) from exc
    except requests.RequestException as exc:
        raise ErroLLM(f"Erro na chamada ao Ollama: {exc}") from exc
    return r.json()["message"]["content"].strip()


def _gerar_openai(sistema: str, usuario: str, temperatura: float,
                  max_tokens: int) -> str:
    if not config.LLM_API_KEY:
        raise ErroLLM("LLM_API_KEY não configurada no .env.")
    url = f"{config.LLM_BASE_URL}/chat/completions"
    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": usuario},
        ],
        "temperature": temperatura,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {config.LLM_API_KEY}"}
    try:
        r = requests.post(url, json=payload, headers=headers,
                          timeout=TIMEOUT_LLM)
        if r.status_code in (401, 403):
            raise ErroLLM(
                "Chave de API recusada (401/403). Confira LLM_API_KEY no .env."
            )
        r.raise_for_status()
    except requests.ConnectionError as exc:
        raise ErroLLM(f"Sem conexão com {url}. Confira LLM_BASE_URL.") from exc
    except requests.RequestException as exc:
        raise ErroLLM(f"Erro na API de IA: {exc}") from exc
    return r.json()["choices"][0]["message"]["content"].strip()


def _extrair_bloco_json(texto: str) -> str:
    """Extrai o primeiro JSON válido de uma resposta (mesmo com markdown)."""
    texto = re.sub(r"```(?:json)?", "", texto).strip("` \n")
    inicio = None
    for i, ch in enumerate(texto):
        if ch in "[{":
            inicio = i
            break
    if inicio is None:
        raise ErroLLM("A IA não devolveu JSON. Resposta:\n" + texto[:500])
    trecho = texto[inicio:]
    # acha o fechamento do bloco balanceando chaves/colchetes
    pilha, pares = [], {"}": "{", "]": "["}
    for i, ch in enumerate(trecho):
        if ch in "[{":
            pilha.append(ch)
        elif ch in "]}":
            if pilha and pilha[-1] == pares[ch]:
                pilha.pop()
                if not pilha:
                    return trecho[: i + 1]
    return trecho


def gerar_json(sistema: str, usuario: str, temperatura: float = 0.5):
    """Gera conteúdo e interpreta como JSON (dict ou list). Faz 1 retry."""
    instrucao = (
        "\n\nIMPORTANTE: responda APENAS com o JSON válido solicitado, "
        "sem explicações, sem markdown, sem ```."
    )
    ultimo_erro = None
    for tentativa in range(2):
        resposta = gerar(sistema, usuario + instrucao, temperatura)
        try:
            return json.loads(_extrair_bloco_json(resposta))
        except (json.JSONDecodeError, ErroLLM) as exc:
            ultimo_erro = exc
            usuario += (
                "\n\nSua resposta anterior não era JSON válido. "
                "Reenvie SOMENTE o JSON corrigido."
            )
    raise ErroLLM(
        f"A IA não conseguiu gerar JSON válido após 2 tentativas: {ultimo_erro}"
    )
