#!/usr/bin/env bash
# ============================================================
#  ATLAS - Instalação automática (Linux: Zorin OS / Ubuntu / Debian)
#
#  Como usar:
#    - Dois cliques no arquivo (escolha "Executar no terminal"), ou
#    - No terminal:  ./instalar-atlas.sh
# ============================================================
set -u
cd "$(dirname "$0")" || exit 1

echo
echo "  =========================================================="
echo "    ATLAS - Instalação automática (Linux)"
echo "  =========================================================="
echo

fechar() { read -r -p "Enter para fechar..."; exit "${1:-0}"; }

# ---------- 1. Localizar o Python ----------
if command -v python3 >/dev/null 2>&1; then
  PYCMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYCMD="python"
else
  echo "  [ERRO] Python não encontrado."
  echo
  echo "  Instale com:"
  echo "    sudo apt update && sudo apt install python3 python3-venv python3-pip"
  echo
  fechar 1
fi
echo "  [OK] $($PYCMD --version 2>&1) encontrado."

# ---------- 2. Criar o ambiente virtual ----------
if [ -x .venv/bin/python ]; then
  echo "  [OK] Ambiente virtual já existe (.venv) — pulando criação."
else
  echo "  Criando ambiente virtual (.venv)..."
  if ! $PYCMD -m venv .venv; then
    echo
    echo "  [ERRO] Não consegui criar o ambiente virtual."
    echo "  No Zorin/Ubuntu geralmente falta o pacote python3-venv."
    echo "  Rode:"
    echo "    sudo apt update && sudo apt install python3-venv python3-pip"
    echo "  Depois execute este arquivo de novo."
    echo
    fechar 1
  fi
  echo "  [OK] Ambiente virtual criado."
fi
echo

# ---------- 3. Instalar dependências ----------
echo "  Instalando dependências (pode levar 1-2 minutos)..."
echo
.venv/bin/python -m pip install --upgrade pip --quiet
if ! .venv/bin/python -m pip install -r requirements.txt; then
  echo
  echo "  [ERRO] Falha ao instalar dependências."
  echo "  Confira sua conexão com a internet e rode de novo."
  echo
  fechar 1
fi
echo
echo "  [OK] Dependências instaladas."
echo

# ---------- 4. Criar o .env ----------
if [ -f .env ]; then
  echo "  [OK] Arquivo .env já existe — mantido como está."
else
  cp .env.example .env
  echo "  [OK] Arquivo .env criado (a partir do .env.example)."
fi
echo

echo "  =========================================================="
echo "    INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
echo "  =========================================================="
echo
echo "  Próximos passos (uma só vez):"
echo
echo "  1. ESCOLHA A IA:"
echo "     a) GRÁTIS E LOCAL (Ollama) — no terminal:"
echo "          curl -fsSL https://ollama.com/install.sh | sh"
echo "          ollama pull llama3.1"
echo "     b) API PAGA — abra o arquivo .env e cole sua chave"
echo "        (instruções dentro do próprio arquivo)."
echo
echo "  2. PUBLICAR NO WORDPRESS (opcional): preencha WP_USER e"
echo "     WP_APP_PASSWORD no .env com a 'Senha de Aplicação' do WP"
echo "     (Painel do WP -> Usuários -> Perfil -> Senhas de Aplicação)."
echo
echo "  3. Para usar o agente: dois cliques em 'abrir-painel.sh'."
echo

read -r -p "  Quer abrir o painel agora? (s/n): " RESP
case "$RESP" in
  s | S | y | Y)
    echo
    echo "  Abrindo http://127.0.0.1:5000 ..."
    echo "  (esta janela precisa ficar aberta enquanto você usa o painel)"
    echo
    xdg-open "http://127.0.0.1:5000" >/dev/null 2>&1 &
    exec .venv/bin/python painel.py --no-browser
    ;;
esac

echo
echo "  Instalador encerrado. Até mais!"
fechar 0
