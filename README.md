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
| `wf5-resumo-validacao.json` | Fase 6: envia à Bárbara o resumo da proposta (dados, cotações de frete, compliance) para validação e avisa no Slack. Chamado pelo WF6 quando há cotações suficientes; marca a proposta `em_validacao` | Publicado |
| `wf6-ler-cotacoes.json` | Fase 3: lê as respostas das transportadoras (assunto com PRP), extrai preço, modo, prazo e validade com LLM, valida em código e grava em `cotacoes_frete` (`a_rever` se houver dúvidas). Lê também o texto de PDFs anexos; chama o WF5 quando há cotações suficientes | Inativo, trigger manual |
| `wf1-extrair-pedido-email.json` | Sub-workflow: o LLM extrai o pedido de um email e o código valida os campos, calcula o que falta e escreve o rascunho de resposta. Nunca cria propostas | Publicado |
| `wf8-aprovacao-barbara.json` | Fase 6: lê a resposta da Bárbara ao email do WF5; só "OK"/"aprovo" na primeira linha, de remetente autorizado e com a proposta em `em_validacao`, a passa a `aprovada`. O resto é só aviso no Slack | Por publicar |
| `wf9-envio-cliente.json` | Fase 7: envia a proposta aprovada ao cliente (Bárbara em CC) com link de confirmação | Publicado |
| `wf10-confirmacao-encomenda.json` | Fase 8: webhook do link de confirmação; marca `aceite` e cria a linha de expedição | Publicado |
| `wf11-plano-expedicao.json` | Fase 9: formulário do plano de expedição (tabela `expedicoes`) | Publicado |
| `wf12-followup-cliente.json` | Fase 10: proposta final ao cliente com modo e chegada estimada; marca `concluida` | Publicado |
| `read-outlook-messages.json` | Fase 1: lê os emails da Folder 1, chama o WF1, grava o pedido como lead rascunho, avisa no Slack e cria o draft de resposta (não envia). A chamada ao WF2 fica desativada | Inativo, trigger manual |

## Slack
- `#novas-propostas`: uma linha por proposta nova (código, cliente, produto, quantidade, Incoterm, destino). Vem do WF2.
- `#pedidos-cotacao`: uma linha quando o pedido de cotação é enviado (código, produto, destino, nº de transportadoras, tentativa, marca "teste"). Vem do WF3.
- `#claude-tasks-status`: estado das tarefas (workflow próprio do utilizador, não alterado).
- Os avisos são best-effort: o WF2 e o WF3 não esperam e uma falha do Slack não os pára (o Mail Error Flow avisa por email). A app do Slack tem de ser membro de cada canal privado (`/invite @status_notifications`).

## Estado e tarefas
Ver `docs/estado-e-tarefas.md` (mapa das 10 fases do briefing e lista de pendentes).

## Antes de importar noutra instância

Os JSON não têm segredos. Preencher: credenciais (ligadas pelo nome), destinatários (`REDACTED@example.invalid`), IDs de pastas Outlook, ID do Mail Error Flow como Error Workflow e IDs do WF1, WF2, WF3, WF4, WF5 e Notificar Slack nos nós de chamada, e os IDs dos canais Slack no código do nó "Escolher canal e texto". Ver `docs/versionamento.md`.

## Regras de trabalho

0. **Cada alteração a um workflow fica num commit em `dev`, com mensagem a dizer o que mudou** (um commit por workflow alterado).
1. Alterar em DEV, correr a bateria de testes, exportar com `scripts/sanitize_workflow.py`, correr `scripts/check_no_secrets.sh`, commit em `dev`.
2. Tudo o que é novo leva testes novos; correr sempre a bateria completa.
3. Para `main` só por Pull Request.

## Deploy para outra instância
`scripts/deploy_workflows.py` instala os workflows de `workflows/` numa instância n8n, resolve as referências por nome e aplica `deploy/config.json` (modelo em `deploy/config.example.json`). Ver `docs/passagem-producao.md`. Testes: `python3 -m unittest tests/test_deploy.py`.
