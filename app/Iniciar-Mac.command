#!/bin/bash
cd "$(dirname "$0")"
APP=app/deploy_app.py; [ -f "$APP" ] || APP=deploy_app.py
if command -v python3 >/dev/null 2>&1; then
  python3 "$APP"
else
  echo "Falta instalar o Python (só se faz uma vez). Vai abrir a página de transferência."
  open https://www.python.org/downloads/
  read -p "Depois de instalar, volte a abrir este ficheiro. Carregue em Enter para fechar."
fi
