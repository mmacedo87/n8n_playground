# Bateria de testes

Fonte de verdade dos resultados: página "Bateria de testes" no Notion (checkbox, razão e resolução provável das falhas).
Este ficheiro descreve **o que** se testa. Regra: tudo o que se cria leva testes novos, e antes de dar algo por fechado corre-se a bateria completa.

Última execução completa: 2026-10-07 17:40 (Lisboa): todos os testes anteriores continuam a passar; novos C2, D5-D8, E2 e B7 passam; F1-F6 pendentes.

## A. Supabase (transação revertida, sem deixar dados)
| Id | Verifica |
| --- | --- |
| A1 | Existem as 7 tabelas |
| A2 | RLS ativa nas 7 tabelas |
| A3-A5 | Código `PRP-AAAA-NNNN`, sequência consecutiva, estado por omissão `pedido` |
| A6-A8 | Rejeita Incoterm inválido, quantidade 0 e estado inválido |
| A9 | Trigger atualiza `atualizado_em` |
| A10-A12 | Rejeita código duplicado, FK inexistente e modo de transporte inválido |
| A13 | `purgar_leads_antigos(12)` apaga leads antigos |
| A14 | Chave anónima não lê `propostas` |
| A15-A17 | Dados de teste presentes; o teste não deixou dados (contador 1, 1 proposta, 0 leads) |
| A18 | Advisors de segurança sem avisos WARN |

## B-E. n8n (dados fixados em nós com credenciais; Set, If e Stop and Error correm a sério)
| Id | Verifica |
| --- | --- |
| B1-B6 | Credenciais, workflows publicados, Error Workflow ligado, nó de chamada ao WF2 desativado |
| C1 | Mail Error Flow monta o aviso correto a partir de um erro simulado |
| C2 | Mail Error Flow escapa HTML na mensagem de erro (verificação estrutural da expressão) |
| D1 | WF2 com formulário válido: normaliza (fob→FOB, "ES - Espanha"→ES) e devolve ok/código/id/estado |
| D2 | WF2 chamado por outro workflow (entradas em minúsculas) |
| D3-D4 | WF2 falha em "Pedido inválido" com Incoterm inexistente e com quantidade 0 |
| D5 | Cliente com `<script>` e mais de 200 caracteres: fica truncado a 200 e o fluxo conclui |
| D6 | Email de confirmação escapa HTML (verificação estrutural; o nó de email está fixado nos testes) |
| D7 | 'Criar proposta no Supabase' sem retry |
| D8 | Saída de erro do email ligada a 'Email falhou depois de gravar' |
| B7 | WF2 e Read Outlook não guardam execuções bem-sucedidas |
| E1 | Read Outlook Messages corre a cadeia completa |
| E2 | 'Marcar original como lido' fica entre 'Mover draft' e a chamada ao WF2 |

## F. Pendentes (precisam de execução real)
F1 envio real do email de confirmação · F2 escrita real no Supabase pelo n8n · F3 submissão real no URL público · F4 aviso de erro real em produção · F5 leitura real da Folder 1 · F6 bloqueio de campos em falta no navegador.
