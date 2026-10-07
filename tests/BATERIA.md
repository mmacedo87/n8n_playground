# Bateria de testes

Fonte de verdade dos resultados: página "Bateria de testes" no Notion (checkbox, razão e resolução provável das falhas).
Este ficheiro descreve **o que** se testa. Regra: tudo o que se cria leva testes novos, e antes de dar algo por fechado corre-se a bateria completa.

Última execução completa: 2026-10-07 18:35 (Lisboa): todos os testes anteriores continuam a passar; novos A19-A24 e G1-G12 e H1-H6 passam (G9 revelou que a conta OpenRouter não tem créditos); F1-F6 pendentes.

## A. Supabase (transação revertida, sem deixar dados)
| Id | Verifica |
| --- | --- |
| A1 | Existem as 8 tabelas |
| A2 | RLS ativa nas 8 tabelas |
| A3-A5 | Código `PRP-AAAA-NNNN`, sequência consecutiva, estado por omissão `pedido` |
| A6-A8 | Rejeita Incoterm inválido, quantidade 0 e estado inválido |
| A9 | Trigger atualiza `atualizado_em` |
| A10-A12 | Rejeita código duplicado, FK inexistente e modo de transporte inválido |
| A13 | `purgar_leads_antigos(12)` apaga leads antigos |
| A14 | Chave anónima não lê `propostas` |
| A15-A17 | Dados de teste presentes; o teste não deixou dados (contador 1, 1 proposta, 0 leads) |
| A18 | Advisors de segurança sem avisos WARN |
| A19-A20 | `pedidos_cotacao` existe com RLS ativa; índice por proposta (catálogo) |
| A21 | Rejeita segundo pedido para a mesma proposta+transportadora (único) |
| A22-A23 | Rejeita `estado` e `gerado_por` inválidos |
| A24 | Rejeita proposta inexistente (FK); FK com `on delete cascade` e trigger de `atualizado_em` presentes (catálogo) |

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
| D9 | Email de confirmação com assunto "Pedido de proposta registado – código – cliente", saudação, próximo passo e assinatura automática (estrutural + execução 29 sem erros) |
| D7 | 'Criar proposta no Supabase' sem retry |
| D8 | Saída de erro do email ligada a 'Email falhou depois de gravar' |
| B7 | WF2 e Read Outlook não guardam execuções bem-sucedidas |
| E1 | Read Outlook Messages corre a cadeia completa |
| E2 | 'Marcar original como lido' fica entre 'Mover draft' e a chamada ao WF2 |

## G. WF3 Pedido de cotação de frete (dados fixados em nós com credenciais; Set, If e Code correm a sério)
| Id | Verifica |
| --- | --- |
| G1 | Caminho feliz: código normalizado (" prp-2026-0099 " → PRP-2026-0099), só transportadoras do país de destino, ordem por nome, assunto com o código PRP, destinatário desviado para o email de teste |
| G2 | Texto do LLM válido → `gerado_por=llm`; texto com link → `modelo_fixo` |
| G3 | O email não contém o nome do cliente final |
| G4 | Menos de 4 transportadoras (3 para US): envia a todas, `abaixo_do_minimo_4=true`, `escolha_por=todas` (exec. 46) |
| G5 | Proposta em estado `cancelada` → Stop and Error com mensagem clara |
| G6 | Todas as transportadoras já contactadas → erro (idempotência) |
| G7 | Código inexistente → erro "proposta não encontrada" |
| G8 | Corrida real (exec. 34 e 35): 9 pedidos gravados e enviados, propostas a `a_cotar`, `ai_log` preenchido |
| G10 | Escolha pelo LLM (fixado): aceita só ids da lista (ignora id inventado), 5 de 6 candidatas, `escolha_por=llm` (exec. 45) |
| G11 | Escolha de reserva (LLM falha ou escolhe mal): mistura de modos, o marítimo entra mesmo sendo o último por nome (exec. 44) |
| G12 | Nenhuma transportadora para o destino (JP) → erro "nada foi enviado" (exec. 47) |
| G9 | Falha da OpenRouter (402 sem créditos): o fluxo usa o texto fixo e envia na mesma |

## H. Encadeamento WF2 → WF3 e WF2 Error Flow
| Id | Verifica |
| --- | --- |
| H1 | WF2 válido (dados fixados, WF3 fixado): conclui sem erro (exec. 56) |
| H2 | WF2 inválido (Incoterm XYZ): falha em "Pedido inválido" e o nó do WF3 não corre (exec. 57) |
| H3 | Real: pedido inválido em produção → WF2 falha, o WF2 Error Flow envia o aviso "falhou antes de gravar... WF3 NÃO foi chamado"; nenhuma proposta nova, nenhum pedido de cotação (exec. 48-49) |
| H4 | Real: pedido válido (PRP-2026-0009, US) → WF2 conclui, o WF3 arranca sozinho: 5 pedidos enviados (marítimos e mistos), proposta a `a_cotar`, sem erros |
| H5 | Real: com a OpenRouter sem créditos o WF3 não pára: usa a regra de reserva e o texto fixo (corrigido: 'Escolher melhores transportadoras (LLM)' passou a continuar em caso de erro) |
| H6 | O WF2 usa o WF2 Error Flow como workflow de erro; o WF3 mantém o Mail Error Flow |

## F. Pendentes (precisam de execução real)
~~F1 envio real do email · F2 escrita real no Supabase · F3 submissão real~~ (feitos em 2026-10-07: PRP-2026-0002 gravada; email enviado para o destinatário de teste, sem erro registado; receção a confirmar pelo utilizador) · F4 aviso de erro real em produção · F5 leitura real da Folder 1 · F6 bloqueio de campos em falta no navegador.
