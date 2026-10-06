# n8n_playground

Automação de propostas comerciais (cortiça): n8n + Supabase + Outlook + OpenRouter + Moloni, com humano no controlo (RGPD e AI Act).
Este repositório guarda o histórico dos workflows n8n, do SQL do Supabase, dos testes e da documentação.

> Ambiente atual: desenvolvimento/testes. Branch de trabalho: `dev`. Branch de produção: `main`.

## Conteúdo

| Pasta | O que tem |
| --- | --- |
| `workflows/` | Workflows n8n exportados e sanitizados (um JSON por workflow) |
| `supabase/` | `schema.sql` (estado atual) e `migrations/` (alterações numeradas) |
| `tests/` | Descrição da bateria de testes |
| `docs/` | Plano de versionamento e checklist de passagem a produção |
| `scripts/` | Sanitização de exportações e verificação de segredos |

## Workflows

| Ficheiro | Função | Estado em DEV |
| --- | --- | --- |
| `mail-error-flow.json` | Aviso por email quando outro workflow falha | Publicado |
| `wf2-pedido-proposta.json` | Formulário e sub-workflow que regista o pedido no Supabase e confirma por email | Publicado |
| `read-outlook-messages.json` | Workflow principal: lê emails, cria drafts, (futuro) chama o WF2 | Inativo, trigger manual |

## Antes de importar noutra instância

Os JSON não têm segredos. Preencher: credenciais (ligadas pelo nome), destinatários (`REDACTED@example.invalid`), IDs de pastas Outlook, ID do Mail Error Flow como Error Workflow e ID do WF2 no nó de chamada. Ver `docs/versionamento.md`.

## Regras de trabalho

1. Alterar em DEV, correr a bateria de testes, exportar com `scripts/sanitize_workflow.py`, correr `scripts/check_no_secrets.sh`, commit em `dev`.
2. Tudo o que é novo leva testes novos; correr sempre a bateria completa.
3. Para `main` só por Pull Request.
