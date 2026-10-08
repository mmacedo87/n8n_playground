# Estado e tarefas (2026-10-08)

Mapa das 10 fases do briefing (Sports Unified Europe, infill natural, ~2 pedidos/mês, humano sempre no loop).

| Fase | Estado | O que existe |
| --- | --- | --- |
| 1. Prospeção | Parcial | Tabela `leads` e "Read Outlook Messages" (inativo, não testado a sério com a caixa real). Falta a extração a partir dos emails (WF1) |
| 2. Definição comercial | Feito | WF2: formulário e sub-workflow, grava em `propostas` (PRP-AAAA-NNNN) e confirma por email. Avisa no Slack (#novas-propostas) |
| 3. Cotação de transporte | Parcial | WF3: 1 email único a até 5 transportadoras (BCC), reenvio até 5 tentativas, aviso Slack (#pedidos-cotacao). Falta ler as respostas (PDF/texto livre) e comparar cotações |
| 4. Enriquecimento | Feito (dados por validar) | WF4: código pautal, taxa (UE regra, EUA via USITC, resto manual) e notas fitossanitárias em `proposta_compliance`. Códigos pautais por validar pelo despachante |
| 5. Geração de proposta (Moloni) | Por fazer | Depende de confirmar âmbito da API Moloni (OAuth, módulo Documentos) |
| 6. Validação (Bárbara) | Por fazer | Passo humano; falta o ecrã/aviso para aprovar |
| 7. Envio ao cliente | Por fazer | Email com Bárbara em CC, só depois da aprovação |
| 8. Confirmação | Por fazer | Detetar "SIM" (resposta livre vs. link/botão) |
| 9. Expedição | Por fazer | Tabela partilhada Bárbara + Madalena |
| 10. Follow-up | Por fazer | Proposta final com o modo de expedição |

## Transversal (feito)
Supabase com RLS (10 tabelas), Mail Error Flow e WF2 Error Flow, modo de teste (emails desviados), `ai_log` para uso de IA, Slack (Notificar Slack), repositório com export sanitizado e verificação de segredos, bateria de testes (`tests/BATERIA.md`).

## Pendentes
1. Convidar a app do Slack para #novas-propostas e #pedidos-cotacao e repetir S1/S2 (bloqueio atual).
2. Validar códigos pautais (despachante) e regras do Reino Unido, Brasil, China, Japão e Marrocos.
3. Ler respostas das transportadoras (OCR/extração) e comparar cotações.
4. Moloni (fase 5), validação da Bárbara (fase 6), envio e confirmação (fases 7-8), tabela de expedição (fase 9).
5. WF1: extração de leads a partir de emails; ligar o "Read Outlook Messages" ao WF2.
6. Testes reais por fazer: F5 (leitura real do Outlook), F6 (campos em falta no formulário), G9.
7. Dados de teste (PRP-2026-0001 a 0014): decisão do utilizador, manter por agora (`supabase/limpar_dados_de_teste.sql` disponível).
8. Passagem a produção: ver `docs/passagem-producao.md` (destinatários, transportadoras reais, créditos OpenRouter, proteger o formulário manual do WF3).
