# Estado e tarefas (2026-10-08)

Mapa das 10 fases do briefing (Sports Unified Europe, infill natural, ~2 pedidos/mês, humano sempre no loop).

| Fase | Estado | O que existe |
| --- | --- | --- |
| 1. Prospeção | Parcial | Tabela `leads` e "Read Outlook Messages" (inativo, não testado a sério com a caixa real). Falta a extração a partir dos emails (WF1) |
| 2. Definição comercial | Feito | WF2: formulário e sub-workflow, grava em `propostas` (PRP-AAAA-NNNN) e confirma por email. Avisa no Slack (#novas-propostas) |
| 3. Cotação de transporte | Parcial | WF3: 1 email único a até 5 transportadoras (BCC), reenvio até 5 tentativas, aviso Slack (#pedidos-cotacao). WF6 lê as respostas em texto e grava em `cotacoes_frete` (testado com dados fixados). Faltam PDFs/anexos (OCR) e o teste real |
| 4. Enriquecimento | Feito (dados por validar, lista em `docs/validacao-despachante.md`) | WF4: código pautal, taxa (UE regra, EUA via USITC, resto manual) e notas fitossanitárias em `proposta_compliance`. Códigos pautais por validar pelo despachante |
| 5. Geração de proposta (Moloni) | Bloqueado | API confirmada (`estimates/insert`), ver `docs/moloni-api.md`. Faltam Developer ID/Client Secret e decisão sobre o refresh token (14 dias) |
| 6. Validação (Bárbara) | Parcial | WF5: email e aviso Slack com o resumo (proposta, cotações, compliance). Falta o chamador e o mecanismo de aprovação |
| 7. Envio ao cliente | Por fazer | Email com Bárbara em CC, só depois da aprovação |
| 8. Confirmação | Por fazer | Detetar "SIM" (resposta livre vs. link/botão) |
| 9. Expedição | Por fazer | Tabela partilhada Bárbara + Madalena |
| 10. Follow-up | Por fazer | Proposta final com o modo de expedição |

## Transversal (feito)
Supabase com RLS (10 tabelas), Mail Error Flow e WF2 Error Flow, modo de teste (emails desviados), `ai_log` para uso de IA, Slack (Notificar Slack), repositório com export sanitizado e verificação de segredos, bateria de testes (`tests/BATERIA.md`).

## Pendentes
1. ~~Convidar a app do Slack e repetir S1/S2~~ (feito, passam).
2. Validar códigos pautais (despachante) e regras do Reino Unido, Brasil, China, Japão e Marrocos.
3. WF6: teste real com uma resposta de transportadora e leitura de PDFs/anexos (OCR); comparar cotações.
4. Moloni (fase 5, bloqueado), chamador e aprovação da Bárbara (WF5, fase 6), envio e confirmação (fases 7-8), tabela de expedição (fase 9).
5. Proteger o formulário manual do WF3: precisa de uma credencial Basic Auth criada pelo utilizador (ou desativar o trigger em produção).
6. O briefing refere granulado de caroço de azeitona e misturas, que ainda não existem em `produtos`.
5. WF1: extração de leads a partir de emails; ligar o "Read Outlook Messages" ao WF2.
6. Testes reais por fazer: F5 (leitura real do Outlook), F6 (campos em falta no formulário), G9.
7. Dados de teste (PRP-2026-0001 a 0015): decisão do utilizador, manter por agora (`supabase/limpar_dados_de_teste.sql` disponível).
8. Passagem a produção: ver `docs/passagem-producao.md` (destinatários, transportadoras reais, créditos OpenRouter, proteger o formulário manual do WF3).
