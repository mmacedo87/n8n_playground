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
| `wf2-pedido-proposta.json` | Formulário e sub-workflow que regista o pedido no Supabase, confirma por email e, no fim, arranca o WF3 e o WF4 em paralelo | Publicado |
| `wf2-error-flow.json` | Workflow de erro do WF2: avisa que o WF3 não foi chamado | Publicado |
| `wf3-pedido-cotacao-frete.json` | Pede cotação de frete com UM único email a até 5 transportadoras (em BCC), com o código PRP no assunto; LLM redige só introdução e fecho | Publicado (modo de teste: emails desviados) |
| `notificar-slack.json` | Sub-workflow reutilizável: publica uma mensagem curta num canal do Slack (`propostas`, `cotacoes`, `estado`). Chamado pelo WF2 (nova proposta) e pelo WF3 (cotação enviada), sem esperar pelo resultado | Publicado |
| `wf4-enriquecimento-proposta.json` | Enriquecimento: código pautal, taxa por destino (UE por regra, EUA via USITC, restantes manual) e notas fitossanitárias, gravados em `proposta_compliance`. Sem LLM | Publicado |
| `wf5-resumo-validacao.json` | Fase 6: envia à Bárbara o resumo da proposta (dados, cotações de frete, compliance) para validação e avisa no Slack. Ainda sem chamador | Publicado |
| `read-outlook-messages.json` | Workflow principal: lê emails, cria drafts, (futuro) chama o WF2 | Inativo, trigger manual |

## Slack
- `#novas-propostas`: uma linha por proposta nova (código, cliente, produto, quantidade, Incoterm, destino). Vem do WF2.
- `#pedidos-cotacao`: uma linha quando o pedido de cotação é enviado (código, produto, destino, nº de transportadoras, tentativa, marca "teste"). Vem do WF3.
- `#claude-tasks-status`: estado das tarefas (workflow próprio do utilizador, não alterado).
- Os avisos são best-effort: o WF2 e o WF3 não esperam e uma falha do Slack não os pára (o Mail Error Flow avisa por email). A app do Slack tem de ser membro de cada canal privado (`/invite @status_notifications`).

## Estado e tarefas
Ver `docs/estado-e-tarefas.md` (mapa das 10 fases do briefing e lista de pendentes).

## Antes de importar noutra instância

Os JSON não têm segredos. Preencher: credenciais (ligadas pelo nome), destinatários (`REDACTED@example.invalid`), IDs de pastas Outlook, ID do Mail Error Flow como Error Workflow e IDs do WF2, WF3, WF4 e Notificar Slack nos nós de chamada, e os IDs dos canais Slack no código do nó "Escolher canal e texto". Ver `docs/versionamento.md`.

## Regras de trabalho

0. **Cada alteração a um workflow fica num commit em `dev`, com mensagem a dizer o que mudou** (um commit por workflow alterado).
1. Alterar em DEV, correr a bateria de testes, exportar com `scripts/sanitize_workflow.py`, correr `scripts/check_no_secrets.sh`, commit em `dev`.
2. Tudo o que é novo leva testes novos; correr sempre a bateria completa.
3. Para `main` só por Pull Request.
