#!/usr/bin/env bash
# Falha se encontrar segredos ou dados pessoais nos ficheiros versionados.
# Uso: bash scripts/check_no_secrets.sh
set -u
cd "$(dirname "$0")/.."
fail=0

check() {
  local label="$1" pattern="$2"
  if grep -rInE --exclude-dir=.git --exclude-dir=scripts -e "$pattern" . ; then
    echo "!! $label"
    fail=1
  fi
}

check "email real (só são permitidos @example.invalid)" '[A-Za-z0-9._%+-]+@(outlook|live|gmail|hotmail)\.[a-z.]+'
check "chave JWT / service_role" 'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}'
check "chave sk-" 'sk-[A-Za-z0-9_-]{20,}'
check "id de credencial n8n" '"id": "(QjXLZW5OedzLKe4O|iOkVb3a5z2vvQzvW|kO4TRc6Glme6Yyyi)"'
check "webhookId no JSON" '"webhookId"'

if [ "$fail" -eq 0 ]; then echo "OK: nada suspeito encontrado."; fi
exit "$fail"
