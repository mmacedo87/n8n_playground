# Estado e tarefas (2026-10-08, fim do dia)

Mapa das 10 fases do briefing (Sports Unified Europe, infill natural, ~2 pedidos/mês, humano sempre no loop).

| Fase | Estado | O que existe |
| --- | --- | --- |
| 1. Prospeção | Parcial | WF1 (`t7cjKbq4VKfx44Fv`): o LLM extrai o pedido do email e o código valida cada campo. O "Read Outlook Messages" grava o pedido como lead **rascunho** (`leads`, com campos em falta e confiança), avisa no Slack e cria o draft de resposta (nunca envia, nunca cria a proposta). Teste real do LLM passa (X7); falta o teste com um email real na Folder 1 (X6) e a decisão de ligar o lead ao WF2 |
| 2. Definição comercial | Feito | WF2: formulário e sub-workflow, grava em `propostas` (PRP-AAAA-NNNN) e confirma por email. Avisa no Slack (#novas-propostas) |
| 3. Cotação de transporte | Parcial | WF3: 1 email único a até 5 transportadoras (BCC), reenvio até 5 tentativas, aviso Slack (#pedidos-cotacao). WF6 lê as respostas (texto e PDFs anexos) e grava em `cotacoes_frete`; quando há cotações suficientes (regra a confirmar: mínimo de 3 ou todas as pedidas) chama o WF5. Testado com dados fixados; falta o teste real com uma resposta de transportadora |
| 4. Enriquecimento | Feito (dados por validar, lista em `docs/validacao-despachante.md`) | WF4: código pautal, taxa (UE regra, EUA via USITC, resto manual) e notas fitossanitárias em `proposta_compliance`. Códigos pautais por validar pelo despachante |
| 5. Geração de proposta (Moloni) | Bloqueado | API confirmada (`estimates/insert`), ver `docs/moloni-api.md`. Faltam Developer ID/Client Secret e decisão sobre o refresh token (14 dias) |
| 6. Validação (Bárbara) | Parcial | WF5: email e aviso Slack com o resumo; marca a proposta `em_validacao`. WF8 (`4dU064sO0xcxkPTc`, por publicar): a resposta da Bárbara com "OK" na primeira linha aprova; qualquer outro texto é só aviso no Slack. Falta o teste real (precisa de uma proposta em `em_validacao`) e confirmar o email da Bárbara |
| 7. Envio ao cliente | Por fazer | Email com Bárbara em CC, só depois da aprovação |
| 8. Confirmação | Por fazer | Detetar "SIM" (resposta livre vs. link/botão) |
| 9. Expedição | Por fazer | Tabela partilhada Bárbara + Madalena |
| 10. Follow-up | Por fazer | Proposta final com o modo de expedição |

## Transversal (feito)
Supabase com RLS (10 tabelas), Mail Error Flow e WF2 Error Flow, modo de teste (emails desviados), `ai_log` para uso de IA, Slack (Notificar Slack), repositório com export sanitizado e verificação de segredos, bateria de testes (`tests/BATERIA.md`).

## Pendentes
**Dependem de si**
1. Confirmar a regra WF6 → WF5 (enviar o resumo à Bárbara com 3 cotações, ou todas as pedidas se forem menos).
2. Proteger o formulário manual do WF3: precisa de uma credencial Basic Auth criada por si (ou desativar o trigger em produção).
3. Teste real do WF1/Read Outlook: pôr um email de teste na Folder 1 (X6).
4. Teste real do WF8: publicar quando houver uma proposta real em `em_validacao`; definir o email da Bárbara no WF5 e no WF8.
5. Teste real do WF6 com uma resposta verdadeira de transportadora.
6. Validar códigos pautais (despachante) e regras do Reino Unido, Brasil, China, Japão e Marrocos.
7. Moloni (fase 5, bloqueado): Developer ID/Client Secret e decisão sobre o refresh token.
8. Dados de teste (PRP-2026-0001 a 0015): decisão sua, manter por agora (`supabase/limpar_dados_de_teste.sql` disponível).

**Por construir**
9. Fases 7 a 10: envio ao cliente (só depois da aprovação), confirmação, tabela de expedição e follow-up.
10. O briefing refere granulado de caroço de azeitona e misturas, que ainda não existem em `produtos`.
11. Passagem a produção: ver `docs/passagem-producao.md`.
12. Testes reais por fazer: F5 (agora X6), F6 (campos em falta no formulário), G9 (402 do OpenRouter já visto em execução real: o WF1 falhou em segurança).
