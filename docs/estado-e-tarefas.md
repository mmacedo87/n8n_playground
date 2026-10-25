# Estado e tarefas (2026-10-17)

Mapa das 10 fases do briefing (Sports Unified Europe, infill natural, até 30 propostas/mês, humano sempre no loop).

| Fase | Estado | O que existe |
| --- | --- | --- |
| 1. Prospeção | Parcial | WF1 (`t7cjKbq4VKfx44Fv`): o LLM extrai o pedido do email e o código valida cada campo. O "Read Outlook Messages" grava o pedido como lead **rascunho** (`leads`, com campos em falta e confiança), avisa no Slack e cria o draft de resposta (nunca envia, nunca cria a proposta). Teste real do LLM passa (X7); falta o teste com um email real na Folder 1 (X6) e a decisão de ligar o lead ao WF2 |
| 2. Definição comercial | Feito | WF2: formulário e sub-workflow, grava em `propostas` (PRP-AAAA-NNNN) e confirma por email. Avisa no Slack (#novas-propostas) |
| 3. Cotação de transporte | Parcial | WF3: 1 email único a até 5 transportadoras (BCC), reenvio até 5 tentativas, aviso Slack (#pedidos-cotacao). WF6 lê as respostas (texto e PDFs anexos) e grava em `cotacoes_frete`; sempre que há cotações novas chama o WF5, que envia à Bárbara o resumo atualizado com assunto fixo por proposta (aceita propostas `a_cotar` e `em_validacao`). Testado com dados fixados e com uma resposta real com PDF (L3, PRP-2026-0017). **2026-10-17** (rascunhos por publicar): WF2 com dados de carga e moradas (opcionais); WF3 com tabela de carga, assunto «Cotação Portugal/CP – País [PRP]» e modo «Atualizar cotação» (versao+1); WF6 associa por conversa/referência/domínio e extrai condições (fixa/período, por camião/total, `a_rever`); WF5 mostra condições, referência e reserva; WF13 (`9C7Wfvim8cAIsgZ6`, rascunho, `publish:false`) cria só o rascunho de confirmação de reserva. Migração 0007 aplicada |
| 4. Enriquecimento | Feito (dados por validar, lista em `docs/validacao-despachante.md`) | WF4: código pautal, taxa (UE regra, EUA via USITC, resto manual) e notas fitossanitárias em `proposta_compliance`. Códigos pautais por validar pelo despachante |
| 5. Geração de proposta (Moloni) | Bloqueado | API confirmada (`estimates/insert`), ver `docs/moloni-api.md`. Faltam Developer ID/Client Secret e decisão sobre o refresh token (14 dias) |
| 6. Validação (Bárbara) | Parcial | WF5: email e aviso Slack com o resumo; marca a proposta `em_validacao`. WF8 (`4dU064sO0xcxkPTc`, testado a sério a 2026-10-16 e despublicado a seguir): a resposta da Bárbara com "OK" na primeira linha aprova; qualquer outro texto é só aviso no Slack. Falta o teste real (precisa de uma proposta em `em_validacao`) e confirmar o email da Bárbara |
| 7. Envio ao cliente | Feito (depende do Moloni para o preço) | WF9 (`UrGBkXG37To7RYMR`): email com a Bárbara em CC, chamado pelo WF8 após aprovação; recusa se não houver `preco_final` |
| 8. Confirmação | Feito | WF10 (`30Z4Nnge3BRZbU8G`): link no email, página de resumo e botão (2 passos); token de 30 dias; avisa expedição e Slack |
| 9. Expedição | Feito | Tabela `expedicoes` + vista `v_expedicoes`; WF11 (`P4FDjLoaiGl3XP01`): formulário do plano |
| 10. Follow-up | Feito | WF12 (`ETUqp17gsET6Vc5A`): proposta final com modo e chegada estimada; marca `concluida` |

## Transversal (feito)
Supabase com RLS (11 tabelas), Mail Error Flow e WF2 Error Flow, modo de teste (emails desviados), `ai_log` para uso de IA, Slack (Notificar Slack), repositório com export sanitizado e verificação de segredos, bateria de testes (`tests/BATERIA.md`).

## Pendentes
**Dependem de si**
1. ~~Regra WF6 → WF5~~ Decidido a 2026-10-16: a Bárbara recebe sempre o resumo atualizado quando há cotações novas (sem mínimo), com assunto fixo por proposta; o WF6 aceita também propostas `em_validacao`.
2. Proteger o formulário manual do WF3: precisa de uma credencial Basic Auth criada por si (ou desativar o trigger em produção).
3. Teste real do WF1/Read Outlook: pôr um email de teste na Folder 1 (X6).
4. Teste real do WF8: publicar quando houver uma proposta real em `em_validacao`; definir o email da Bárbara no WF5 e no WF8.
6. Validar códigos pautais (despachante) e regras do Reino Unido, Brasil, China, Japão e Marrocos.
7. Moloni (fase 5, bloqueado): Developer ID/Client Secret e decisão sobre o refresh token.
8. Dados de teste (PRP-2026-0001 a 0015): decisão sua, manter por agora (`supabase/limpar_dados_de_teste.sql` disponível).

**Novos (2026-10-17)**
**Novos (2026-10-25)**
- WF3: modo de envio `automatico`/`revisao` lido de `configuracao` (migração 0009, aplicada no desenvolvimento); rascunho em Inbox/To Check; testado a sério (exec. 272, 274, 276). Rascunho n8n bbc0fc46, **por publicar**. Interruptor no assistente («Updates ao fluxo») e em `scripts/atualizar_config.py`.
- Decidido: n8n Cloud (região UE e DPA por confirmar com o suporte do n8n); o repositório de desenvolvimento pode ficar público, o de produção será privado.
- Publicar os rascunhos do WF2, WF3, WF5 (a versão publicada difere do rascunho) e testar o WF13 com uma proposta aprovada real; o WF6 continua inativo por desenho.
- Bateria Supabase A1-A35/B1-B8 por correr (foi cancelada); migração 0007 aplicada na instância de desenvolvimento.
- Limitação: o envio Outlook não devolve `conversationId`, por isso a associação por conversa só funciona depois de o WF6 preencher `pedidos_cotacao.conversation_id`; PRP no assunto/corpo e referência da transportadora funcionam já.
- Dependem do cliente: fio completo da DSV, respostas de outras transportadoras (uma com PDF), preço por camião ou total, domínios das transportadoras, se a morada exata de descarga pode ir no pedido, quem escolhe e confirma a reserva.
- WhatsApp/SMS: decisão do cliente e conta Meta.

**Por construir**
9. Fases 7 a 10 construídas e testadas. Falta: preço final (Moloni) para o WF9 funcionar, publicar o WF8, e na passagem a produção esvaziar `destinatario_teste` e preencher `cc_barbara`, `email_madalena`, `email_barbara`, `url_base`, `url_form`.
10. O briefing refere granulado de caroço de azeitona e misturas, que ainda não existem em `produtos`.
11. Passagem a produção: ver `docs/passagem-producao.md`.
12. Testes reais por fazer: F5 (agora X6), F6 (campos em falta no formulário), G9 (402 do OpenRouter já visto em execução real: o WF1 falhou em segurança).
