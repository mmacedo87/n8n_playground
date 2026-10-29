# Estado e tarefas (2026-10-29)

Mapa das 10 fases do briefing (Sports Unified Europe, infill natural, 30 a 35 encomendas/mês, humano sempre no loop). Instância de desenvolvimento: n8n Cloud `mmacedo87.app.n8n.cloud`, Supabase `ahisuvnooplmiczjytfp`. Cópia deste ficheiro no Project: `claude/estado_do_projeto.md` (a fonte é o repositório).

**2026-10-29:** WF6 e Read Outlook correm sozinhos (Outlook Trigger), formulários internos com Basic Auth e link do plano com código secreto.

**Marco (2026-10-27):** a PRP-2026-0022 percorreu as 10 fases com emails reais (aliases Gmail a fazer de cliente, Bárbara, Madalena e duas transportadoras): pedido por email → proposta → 2 cotações → validação e «OK código» → envio ao cliente → confirmação → reserva (WF13) → plano (WF11) → follow-up (WF12), estado final `concluida`. Guião: Project `claude/testes_cenarios_reais.md` (parte A passou; parte B por fazer).

| Fase | Estado | O que existe |
| --- | --- | --- |
| 1. Prospeção | Feito, automático | WF1 (LLM extrai, código valida). Read Outlook (Outlook Trigger na Folder 1, 5 em 5 min) grava o lead, cria rascunho de resposta só para pedidos e, com confiança ≥ 0,8 e todos os campos mapeados, chama o WF2 com o `lead_id` (lead passa a `convertido`) |
| 2. Definição comercial | Feito | WF2: formulário (Basic Auth) ou chamada do Read Outlook, grava `propostas` (com `contacto_email`), confirma por email, chama WF3 + WF4 + Slack |
| 3. Cotação de transporte | Feito, automático | WF3: um email (BCC) a até 5 transportadoras, `modo_envio` automático/revisão lido de `configuracao`, aviso de IA fixo. WF6 (Outlook Trigger na Inbox, 5 em 5 min): associa por código/conversa/referência/remetente, lê PDFs, grava várias condições, regista em `ai_log` e chama o WF5 |
| 4. Enriquecimento | Feito, dados por validar | WF4: código pautal, taxa, notas fitossanitárias. 0 produtos validados pelo despachante |
| 5. Proposta no Moloni | **Bloqueado** | API estudada (`docs/moloni-api.md`); faltam credenciais. O `preco_final` é posto à mão (SQL) nos testes |
| 6. Validação (Bárbara) | Feito | WF5 (resumo com cotações, condições e código de aprovação) e WF8 publicado (só «OK <código>» de remetente autorizado aprova) |
| 7. Envio ao cliente | Feito (preço depende do Moloni) | WF9: email PT/EN com link de confirmação, Bárbara em CC |
| 8. Confirmação | Feito | WF10: link com token (30 dias), 2 passos, cria `expedicoes`, avisa a Madalena |
| 9. Expedição | Feito | WF13 (formulário com Basic Auth; escolha e confirmação da reserva; só rascunhos para fora) e WF11 (plano; link com código secreto por proposta `token_plano`; dados da reserva lidos da BD, «reserva correta?») |
| 10. Follow-up | Feito | WF12: proposta final com recolha e chegada estimada; `concluida` |

## Transversal
- 16 workflows no Git (`workflows/`), todos publicados no n8n de desenvolvimento e iguais à versão viva (sincronizados a 2026-10-29). No deploy de produção, WF6, WF8, WF13 e Read Outlook ficam inativos até ao arranque (`publish:false` no manifest). Mais 2 só no n8n: «Claude → Slack | Estado das tarefas» e «Teste - Cenários reais (só dev)» (inativo).
- Supabase: 11 migrações (0004 aplicada sem registo no histórico; 0011 = `token_plano`), RLS ativo, `anon`/`authenticated` sem permissões, `configuracao.modo_envio = automatico`.
- Modo produção desde 27/10: `destinatario_teste` vazio; emails internos = aliases de teste; só 2 transportadoras ativas (`TESTE - Transp1/2 (Gmail)`).
- AI Act: avaliação, 72 testes e 7 documentos em rascunho (`docs/ai-act/`).
- Deploy automático, assistente de instalação e kit; GitHub Action que só aceita `main` por PR.
- Bateria offline: 127 testes (`python3 -m unittest tests.test_…`), `scripts/check_no_secrets.sh`.

## Pendentes
**Técnicos (próximos)**
1. ~~Autenticação nos formulários~~: feita a 2026-10-29. WF2, WF3 (manual) e WF13 com Basic Auth (credencial `httpBasicAuth`); WF11 protegido pelo código secreto no link (`token_plano`). Falta o utilizador confirmar o login com a sua palavra-passe.
2. ~~`lead_id` na proposta vinda de email~~ e ~~rascunho só para pedidos~~: feitos a 2026-10-29 (migração 0010, WF2 d89f09a6, Read Outlook 78d6485a; teste real PRP-2026-0024).
3. Read Outlook: notas antigas em dois nós («Chamar WF2»: «DESATIVADO…»; «Gravar lead»: «Nunca cria a proposta») a corrigir no editor do n8n (o MCP não altera notas).
4. ~~Gatilhos automáticos~~: feitos a 2026-10-29 (WF6 1ec4243c na Inbox, Read Outlook 1e3179d8 na Folder 1; teste real às 19:15).
5. Simplificação da arquitetura (revisão de 2026-10-28): sub-workflow «Enviar email» + «Montar email», que absorve `docs/plano-destinatarios-bd.md`; fundir WF9/WF12 e o aviso à Madalena do WF10/WF13.
6. Parte B dos testes de cenários reais: feitos B1.1, B1.2, B2.1, B2.2 e B4.1 (2026-10-29); faltam os restantes.
7. Propostas de teste presas em `em_validacao` (PRP-2026-0018 a 0021): decidir se ficam.

**Decisões suas**
8. Read Outlook → WF2 sem humano: com confiança ≥ 0,8 a proposta é criada e o WF3 envia o pedido às transportadoras sem revisão. A política e as fichas de IA (`docs/ai-act/02`, `03`) ainda dizem que o pedido por email nunca cria a proposta; pela gestão de mudança (`05`) é preciso reavaliar e registar a decisão.
9. Retenção automática (`purgar_leads_antigos` sem `pg_cron`).
10. Moloni: credenciais e refresh token.
11. Despachante: validar códigos pautais; produtos em falta (caroço de azeitona, misturas).
12. AI Act: aprovação da política, pareceres do jurista, DPAs, formação, região do n8n Cloud.
13. Passagem a produção: emails reais (Bárbara, Madalena, erros), transportadoras reais, repositório privado (`docs/passagem-producao.md`).
