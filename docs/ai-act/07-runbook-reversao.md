# Runbook: desativar a IA e reverter

Estado: versão 1.0 · 2026-10-21 · Cobre o teste D4

Objetivo: parar o uso de IA e/ou reverter uma alteração em menos de **15 minutos** (meta a validar no exercício).

## 1. Desativação de emergência

1. Desativar (unpublish) os workflows com LLM: **WF1, WF3, WF6**.
2. Se houver risco de envio indevido ao cliente, desativar também **WF8, WF9, WF10 e WF12**.
3. Confirmar no n8n que não há execuções a decorrer e que os triggers (Outlook, webhooks, formulários) estão inativos.
4. Avisar a Bárbara e a gestão; continuar o processo manualmente (cotações por email normal).
5. Registar o incidente (`06-retencao-rgpd-e-incidentes.md`).

## 2. Reversão de uma versão

1. Identificar o workflow e a última versão boa (histórico de versões do n8n e commits no branch `dev`).
2. Restaurar a versão anterior no n8n; confirmar nós, credenciais e `onError`.
3. Voltar a publicar e executar um teste em modo de teste (`destinatario_teste` preenchido).
4. Repor o modo de produção só após o teste passar.

## 3. Retorno ao funcionamento normal

Correr a bateria 🔴 (`testes-ai-act.md`) e os testes de regressão; registar em `05-gestao-de-mudanca.md`.

## 4. Registo do exercício

| Data | Executor | Passo | Tempo | Observações |
| --- | --- | --- | --- | --- |
| | | Desativar WF1, WF3, WF6 | | |
| | | Restaurar versão de um workflow | | |
| | | Total (meta < 15 min) | | |
