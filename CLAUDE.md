# Contexto do projeto (ler primeiro)

Automação de propostas comerciais de uma empresa de cortiça. Stack: n8n Cloud (`mmacedo87.app.n8n.cloud`), Supabase (projeto `ahisuvnooplmiczjytfp`), Outlook, OpenRouter, Slack; Moloni previsto. Humano sempre no loop, RGPD e AI Act. Idioma de trabalho: português europeu, respostas curtas. Briefing e documentos vivos estão no Project "FMacedo" (Briefing_Automacao_Processo_Comercial.docx, resumo-cliente.html, documentacao-tecnica.md, passagem-producao.md, claude/estado_do_projeto.md, claude/validacao_despachante.md, claude/moloni_api.md).

## Regras permanentes do utilizador
1. Tudo o que se cria leva testes; antes de dar por fechado, corre-se a bateria completa (`tests/BATERIA.md`), que inclui testes de execução real, mas comedidos (poupar créditos e runs).
2. Cada alteração a um workflow é um commit em `dev` (um commit por workflow), formato `tipo(âmbito): resumo`, corpo com versionId do n8n e resultado da bateria, terminando com as linhas `Co-Authored-By` e `Claude-Session` do sistema. `main` só por PR.
3. Se o utilizador disser "não memorizes", não guardar em memória.
4. Notificações: no fim de cada tarefa, e sempre que ficar bloqueada, enviar para #claude-tasks-status **só pelo workflow n8n "Claude → Slack | Estado das tarefas" (id `xbLMBhTje4dFEof9`, `execute_workflow`, trigger "Receber estado do Claude", body {task, status completed|blocked|failed, summary, changes[], checks[], next_steps[], links[]})**. Mensagens diretas pelo Slack MCP aparecem como do utilizador e não geram push. Se falhar, dizer ao utilizador, nunca afirmar que foi enviado.
5. Tarefa bloqueada: guardar tudo o que foi feito, notificar, passar à seguinte.
6. "Documento do cliente" = `resumo-cliente.html` (no Project e em `docs/`): atualizar esse ficheiro, não criar docs novos.
7. Não repetir escritas no Supabase que o utilizador cancelou; não apagar dados de teste sem ele pedir (PRP-2026-0001 a 0015 ficam).

## Mapa dos workflows (n8n)
| Workflow | Id | Notas |
| --- | --- | --- |
| WF2 Pedido de proposta | `8pRJJuN094Mp9iuu` | formulário; chama WF3, WF4 e Slack sem esperar |
| WF3 Pedido de cotação de frete | `x9RhWxZfJ0apbhlc` | UM email (BCC), reenvio até 5 tentativas, 6.ª avisa |
| WF4 Enriquecimento | `ya6mCmn3qi4YE3CG` | compliance, sem IA |
| WF5 Resumo para validação | `8xj41URokjCimmon` | email à Bárbara + Slack; marca `em_validacao`; chamado pelo WF6 |
| WF6 Ler cotações | `HErViy6cNVrTIH7A` | inativo, manual; texto e PDFs; chama o WF5 |
| Notificar Slack | `N7BZddGLl0WlSl9Q` | canais propostas `C0C7T8J8D54`, cotacoes `C0C7V2PU4PL`, estado `C0C7SN9MKQE` |
| Mail Error Flow / WF2 Error Flow | `fWXNAbhbQLuYeurE` / `Xs4ZlE9DSqNifiPk` | Error Workflows |
| WF8 Aprovação da Bárbara | `4dU064sO0xcxkPTc` | por publicar; só "OK" na 1.ª linha aprova |
| WF1 Extrair pedido do email | `t7cjKbq4VKfx44Fv` | sub-workflow, LLM + validação em código; nunca cria propostas |
| Read Outlook Messages | `39zlpRbdQvI7dHGe` | inativo, manual; chama o WF1, grava lead rascunho |

## Armadilhas já encontradas
- `test_workflow` fixa gatilho, nós com credenciais e HTTP; Execute Workflow corre a sério se não for fixado. Execute Workflow Trigger não se executa por `execute_workflow`.
- Para ver erros de um sub-workflow chamado em teste, pôr `saveDataSuccessExecution=all` no sub-workflow e repor `none` no fim (o `onError` contínuo conta como sucesso).
- Execuções de sucesso não são guardadas (`saveDataSuccessExecution none`): verificar no Supabase.
- `addNode` ignora `alwaysOutputData`/`executeOnce`: usar `setNodeSettings`. Um nó com 0 itens pára o ramo em silêncio.
- Slack: a app (`status_notifications`) tem de ser membro de cada canal privado.
- Outlook "Forbidden" pontual = renovação do token; repetir.
- Em modo de teste o BCC fica vazio: o nó de envio usa o To como alternativa.

## Exportar um workflow para Git
`python3 -I scripts/sanitize_workflow.py <detalhes.json>`; `settings.errorWorkflow` = `<ID do Mail Error Flow na instância de destino>`; `destinatario_teste` vazio; `meta` com exportedFrom, sourceWorkflowId, sourceVersionId, exportedAt, sanitized; correr `scripts/check_no_secrets.sh`.

## Ficheiros
Ver `docs/estado-e-tarefas.md` (estado por fase e pendentes), `docs/passagem-producao.md`, `docs/versionamento.md`, `tests/BATERIA.md`, `supabase/` (schema, migrações 0001-0004, script de limpeza não corrido).
