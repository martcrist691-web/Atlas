#!/usr/bin/env bash
# ============================================================
#  ATLAS - Abrir o painel no navegador (Linux)
#
#  Como usar:
#    - Dois cliques no arquivo (escolha "Executar no terminal"), ou
#    - No terminal:  ./abrir-painel.sh
# ============================================================
cd "$(dirname "$0")" || exit 1

if [ ! -x .venv/bin/python ]; then
  echo
  echo "  O Atlas ainda não foi instalado nesta pasta."
  echo "  Rode primeiro:  ./instalar-atlas.sh"
  echo
  read -r -p "Enter para fechar..."
  exit 1
fi

echo
echo "  Iniciando o painel do Atlas em http://127.0.0.1:5000"
echo "  O navegador vai abrir sozinho."
echo "  NÃO FECHE esta janela enquanto estiver usando o painel."
echo "  (Para encerrar: aperte Ctrl+C ou feche a janela)"
echo

exec .venv/bin/python painel.py
