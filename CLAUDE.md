# Contexto do projeto (ler primeiro)

Automação de propostas comerciais de uma empresa de cortiça. Stack: n8n Cloud (`mmacedo87.app.n8n.cloud`), Supabase (projeto `ahisuvnooplmiczjytfp`), Outlook, OpenRouter, Slack; Moloni previsto. Humano sempre no loop, RGPD e AI Act. Idioma de trabalho: português europeu, respostas curtas. Briefing e documentos vivos estão no Project "FMacedo" (Briefing_Automacao_Processo_Comercial.docx, resumo-cliente.html, documentacao-tecnica.md, passagem-producao.md, claude/estado_do_projeto.md, claude/validacao_despachante.md, claude/moloni_api.md).

## Regras permanentes do utilizador
1. Tudo o que se cria leva testes; antes de dar por fechado, corre-se a bateria completa (`tests/BATERIA.md`), que inclui testes de execução real, mas comedidos (poupar créditos e runs).
2. Cada alteração a um workflow é um commit em `dev` (um commit por workflow), formato `tipo(âmbito): resumo`, corpo com versionId do n8n e resultado da bateria, terminando com as linhas `Co-Authored-By` e `Claude-Session` do sistema. `main` só por PR (branches: `dev` trabalho, `stable` cópia estável, `main` produção; Action `.github/workflows/main-so-por-pr.yml`, ver `docs/versionamento.md`).
3. Se o utilizador disser "não memorizes", não guardar em memória.
4. Notificações: **só fora do horário de expediente do utilizador (das 19h00 às 08h00 do dia seguinte, hora de Portugal; confirmar a hora com a ferramenta de hora atual). Dentro do expediente (08h00-19h00) não enviar nada para o Slack: o resultado vai só na resposta do chat.** Fora do expediente, no fim de cada tarefa, e sempre que ficar bloqueada, enviar para #claude-tasks-status **só pelo workflow n8n "Claude → Slack | Estado das tarefas" (id `xbLMBhTje4dFEof9`, `execute_workflow`, trigger "Receber estado do Claude", body {task, status completed|blocked|failed, summary, changes[], checks[], next_steps[], links[]})**. Mensagens diretas pelo Slack MCP aparecem como do utilizador e não geram push. Se falhar, dizer ao utilizador, nunca afirmar que foi enviado.
5. Tarefa bloqueada: guardar tudo o que foi feito, notificar, passar à seguinte.
6. "Documento do cliente" = `resumo-cliente.html` (no Project e em `docs/`): atualizar esse ficheiro, não criar docs novos.
7. Não repetir escritas no Supabase que o utilizador cancelou; não apagar dados de teste sem ele pedir (PRP-2026-0001 a 0015 ficam).

## Mapa dos workflows (n8n)
| Workflow | Id | Notas |
| --- | --- | --- |
| WF2 Pedido de proposta | `8pRJJuN094Mp9iuu` | formulário com Basic Auth (credencial `httpBasicAuth`); chama WF3, WF4 e Slack sem esperar; error flow próprio (WF2 Error Flow) |
| WF3 Pedido de cotação de frete | `x9RhWxZfJ0apbhlc` | UM email (BCC), reenvio até 5 tentativas, 6.ª avisa |
| WF4 Enriquecimento | `ya6mCmn3qi4YE3CG` | compliance, sem IA |
| WF5 Resumo para validação | `8xj41URokjCimmon` | email à Bárbara + Slack; marca `em_validacao`; chamado pelo WF6 |
| WF6 Ler cotações | `HErViy6cNVrTIH7A` | Outlook Trigger na Inbox (5 min, não lidos) + gatilho manual; texto e PDFs; regista cada extração em `ai_log`; chama o WF5 |
| Notificar Slack | `N7BZddGLl0WlSl9Q` | canais propostas `C0C7T8J8D54`, cotacoes `C0C7V2PU4PL`, estado `C0C7SN9MKQE` |
| Mail Error Flow / WF2 Error Flow | `fWXNAbhbQLuYeurE` / `Xs4ZlE9DSqNifiPk` | Error Workflows |
| WF8 Aprovação da Bárbara | `4dU064sO0xcxkPTc` | publicado (desde 2026-10-26); Outlook Trigger a cada 2 min; só aprova «OK <código de aprovação>» na 1.ª linha, de remetente em `AUTORIZADOS`, com a proposta em `em_validacao` |
| WF9 Envio ao cliente | `UrGBkXG37To7RYMR` | sub-workflow, chamado pelo WF8; precisa de `preco_final` |
| WF10 Confirmação da encomenda | `30Z4Nnge3BRZbU8G` | webhook GET `confirmar-proposta`, link com token |
| WF11 Plano de expedição | `P4FDjLoaiGl3XP01` | formulário `plano-expedicao`, só com o código secreto do link (`t` = `propostas.token_plano`, migração 0011) (pergunta «Os dados da reserva estão corretos?»: Não avisa a Bárbara e não grava); chama o WF12 |
| WF12 Follow-up ao cliente | `ETUqp17gsET6Vc5A` | sub-workflow; marca `concluida` |
| WF13 Confirmação de reserva de frete | `9C7Wfvim8cAIsgZ6` | formulário `confirmar-reserva` (path em `options.path`, Basic Auth); ao confirmar a reserva envia à Madalena o link do WF11 (só se a proposta já está `aceite`); ao transportador e ao cliente só cria RASCUNHO (nunca envia); atualiza `estado_reserva` e `frete_escolhido_id` |
| WF1 Extrair pedido do email | `t7cjKbq4VKfx44Fv` | sub-workflow, LLM + validação em código; nunca cria propostas |
| Read Outlook Messages | `39zlpRbdQvI7dHGe` | Outlook Trigger na Folder 1 (5 min, não lidos) + gatilho manual; chama o WF1, grava o lead; rascunho de resposta só para pedidos (ou falha do LLM), o resto só fica lido; se o pedido mapeia com confiança ≥ 0.8, chama o WF2 com `lead_id` (a proposta fica ligada ao lead e o lead passa a `convertido` por trigger, migração 0010) |
| Teste - Cenários reais (só dev) | `iD9ACaK1TSwHZgP8` | inativo de propósito; cria mensagens de teste na caixa; não está no Git nem no manifest |

No n8n de desenvolvimento estão todos publicados (modo produção com aliases de teste desde 2026-10-27). O `publish` do `workflows/manifest.json` é a regra do deploy de produção, não o espelho do desenvolvimento: WF6, WF8, WF13 e Read Outlook ficam `false` e ativam-se à mão no arranque (`docs/passagem-producao.md`). Estado real e pendentes: `docs/estado-e-tarefas.md`.

## Armadilhas já encontradas
- `test_workflow` fixa gatilho, nós com credenciais e HTTP; Execute Workflow corre a sério se não for fixado. Execute Workflow Trigger não se executa por `execute_workflow`.
- Para ver erros de um sub-workflow chamado em teste, pôr `saveDataSuccessExecution=all` no sub-workflow e repor `none` no fim (o `onError` contínuo conta como sucesso).
- Execuções de sucesso não são guardadas (`saveDataSuccessExecution none`): verificar no Supabase.
- `addNode` ignora `alwaysOutputData`/`executeOnce`: usar `setNodeSettings`. Um nó com 0 itens pára o ramo em silêncio.
- Slack: a app (`status_notifications`) tem de ser membro de cada canal privado.
- Outlook "Forbidden" pontual = renovação do token; repetir.
- Em modo de teste o BCC fica vazio: o nó de envio usa o To como alternativa.
- **Nunca reenviar para o n8n valores vindos do export sanitizado** (`REDACTED@example.invalid`, ids, destinatários vazios): sobrescrevem a configuração viva (já aconteceu com `destinatario_confirmacao` do WF2). Ler a versão viva (`get_workflow_details`/`get_workflow_version`) e alterar só o necessário; `setNodeParameter` não acrescenta ao fim de arrays (reenviar o array completo, a partir do vivo).
- Código dos nós Code mantido em `scripts/wf3_code`, `wf5_code`, `wf6_code`, `wf13_code`, `read_outlook_code` e testado offline (`tests/harness_code_node.js`); os testes de deriva comparam o `jsCode` do export com esses ficheiros. Correr os testes com `python3 -m unittest tests.test_wf3_code` (ponto, não barra).
- Notificações Slack: o utilizador pediu a 2026-10-17 para não enviar nenhuma até voltar a pedir.
- **Deriva Git ↔ n8n** (aconteceu com WF3, WF5, WF6, WF8, WF9 e WF12, corrigida a 2026-10-29): qualquer alteração no n8n, mesmo de configuração, exige export e commit no mesmo dia. Verificação: `versionId` vivo (`get_workflow_details`, `detailLevel: execution`) = `meta.sourceVersionId` do ficheiro.
- O n8n vivo omite valores por omissão (ex. `operation` de um rascunho Outlook, `method: GET`, `pollTimes` de 2 min): os testes estruturais não devem exigir esses campos explícitos.
- Outlook Trigger: o primeiro poll depois de publicar só fixa a hora de referência; emails já por ler antes disso não o disparam. Execuções de sucesso não ficam guardadas: confirmar no Supabase.
- A migração 0004 foi aplicada sem ficar em `supabase_migrations.schema_migrations` (a coluna `tentativas` existe).

## Exportar um workflow para Git
`python3 -I scripts/sanitize_workflow.py <detalhes.json>`; `settings.errorWorkflow` = `<ID do Mail Error Flow na instância de destino>`; `destinatario_teste` vazio; `meta` com exportedFrom, sourceWorkflowId, sourceVersionId, exportedAt, sanitized; IDs de pastas do Outlook (`folderId`, `foldersToInclude`) à mão como `<ID da pasta ... no Outlook de destino>` (o sanitizer não os troca); correr `scripts/check_no_secrets.sh`. Referências a outros workflows ficam como `{{WF:Nome}}` (o sanitizer converte; novo workflow entra em `workflows/manifest.json`). Deploy para outra instância: `scripts/deploy_workflows.py` + `deploy/config.json` (ver `docs/passagem-producao.md`); testes: `python3 -m unittest tests/test_deploy.py tests/test_app.py tests/test_kit.py` e `python3 tests/e2e_app.py`. Assistente web local para quem instala: `app/` + kit com `scripts/build_kit.py`.

## Ficheiros
Ver `docs/estado-e-tarefas.md` (estado por fase e pendentes), `docs/passagem-producao.md`, `docs/versionamento.md`, `tests/BATERIA.md`, `supabase/` (schema, migrações 0001-0011 e rollbacks 0007-0011, script de limpeza não corrido).
