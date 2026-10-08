# Bateria de testes

Fonte de verdade dos resultados: página "Bateria de testes" no Notion (checkbox, razão e resolução provável das falhas).
Este ficheiro descreve **o que** se testa. Regra: tudo o que se cria leva testes novos, e antes de dar algo por fechado corre-se a bateria completa.

Última execução: 2026-10-08 (Lisboa, 23:20, bateria final da T7). Supabase A1-A27 e os testes novos de `leads` (migração 0005) passam numa transação revertida (nada deixado; contador 15, 15 propostas, 0 leads); advisors de segurança só com INFO. n8n com dados fixados nesta corrida: WF4 (exec. 168), WF2 válido (exec. 169) e inválido (exec. 170). WF3, Notificar Slack e Mail Error Flow não mudaram desde a última corrida real com sucesso (exec. 108, 142-167 para o aviso de estado). Testados nas alterações de hoje: WF5 W1-W7 (exec. 125-127), WF6 L4-L10 (exec. 128-135), WF8 M1-M4 (exec. 121-124), WF1 X1-X4 (exec. 137-140), Read Outlook X5 (exec. 141). Real com LLM: X7 (exec. 164). Pendentes: G9 (402 já visto em execução real, ver X7), F1-F6, X6 (email real na Folder 1), M5 (resposta real da Bárbara), L real com resposta de transportadora.

## A. Supabase (transação revertida, sem deixar dados)
| Id | Verifica |
| --- | --- |
| A1 | Existem as 10 tabelas |
| A2 | RLS ativa nas 10 tabelas |
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
| A25 | `produtos` e `proposta_compliance` existem com RLS ativa; `produtos` tem os 3 produtos com `validado=false` |
| A26 | `requisitos_pais` tem 12 regras com `codigo_pautal='*'` (6 `regra_ue`, 1 `api_usitc`, 5 `tabela_manual`) e a restrição `metodo` |
| A27 | `proposta_compliance` aceita linha com taxa nula e `metodo=tabela_manual` (transação revertida; tabela fica a 0 linhas) |

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
| G1 | Caminho feliz: código normalizado (" prp-2026-0099 " → PRP-2026-0099), só transportadoras do país de destino, ordem por nome, assunto com o código PRP, destinatário desviado para o email de teste. **UM único email** (o nó de envio corre uma vez), com um registo em `pedidos_cotacao` por transportadora (exec. 70) |
| G13 | Modo de produção (`destinatario_teste` vazio): um só email com To = `destinatario_principal` e todas as transportadoras em BCC, sem prefixo [TESTE] (exec. 71) |
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

| H7 | WF2 válido (WF3 e WF4 fixados): chama o WF3 e o WF4 em paralelo a partir de "Devolver proposta" e conclui sem erro (exec. 65) |
| H8 | WF2 inválido (cliente vazio, quantidade 0): falha em "Pedido inválido" e nem o WF3 nem o WF4 correm (exec. 66) |

## I. WF4 Enriquecimento de proposta (dados fixados em nós com credenciais e no HTTP; Set, If e Code correm a sério)
| Id | Verifica |
| --- | --- |
| I1 | EUA, Granulado (HTS 4501.90.40.00): lê "Free" no USITC → `taxa_direitos_pct=0`, `metodo=api_usitc`, `estado=automatico`; a nota diz que não inclui direitos adicionais (exec. 60) |
| I2 | UE (ES): regra intra-UE, não chama o USITC → `taxa_direitos_pct=0`, `metodo=regra_ue`, `estado=automatico` (exec. 61) |
| I3 | EUA com Aglomerado (sem HTS): não consulta o USITC → `metodo=tabela_manual`, `estado=a_verificar_manualmente`, nota "Produto sem código HTS" (exec. 62) |
| I4 | Falha do USITC (resposta sem dados): o fluxo não pára; passa a `tabela_manual` / `a_verificar_manualmente` (exec. 63) |
| I5 | Código inexistente → erro "proposta não encontrada" (exec. 64) |
| I6 | Produto com código pautal não validado: a nota acrescenta "ainda não validado pelo despachante" (exec. 60-61) |
| I7 | Estrutura: sem nós de IA; Error Workflow = Mail Error Flow; só chamado por outro workflow (`workflowsFromSameOwner`) |
| I8 | Gravação na BD: o INSERT com o formato de saída de "Montar compliance" (valores nulos incluídos) respeita as restrições (A27) |

Limite conhecido: o nó "Gravar compliance" e o trigger só correm a sério na primeira proposta real; o Execute Workflow Trigger não se executa pelo MCP.

## R. Testes reais (comedidos)
Regra: no máximo 1 execução real do encadeamento completo por alteração relevante (WF2 → WF3 + WF4, destino ES, modo de teste: 1 email para o destinatário de teste, 1 chamada ao LLM de redação). Não repetir em cada bateria; os restantes testes usam dados fixados. Apagar a proposta de teste depois.

| # | Teste | Resultado |
|---|---|---|
| R1 | WF2 real pelo formulário (cliente "TESTE REAL", ES): proposta gravada, email de confirmação, WF3 e WF4 arrancam | 2026-10-08. Exec. 75 e 77: falharam com "Forbidden" do Outlook (token a renovar; credencial OK à 3.ª tentativa). Exec. 79/80: o WF3 falhou porque o BCC ia vazio em modo de teste (bug corrigido, WF3 versão da43bd61). Exec. 85 (PRP-2026-0013): **passou**: proposta a `a_cotar`, 4 pedidos `enviado` com `redirecionado_teste`, 1 linha em `ai_log`, `proposta_compliance` automatico/regra_ue |
| R2 | Repetir uma proposta cujo envio falhou (real, PRP-2026-0012 com 4 linhas `falhou`, exec. 90) | **Passa** (2026-10-08): as linhas `falhou` são substituídas, 4 pedidos `enviado` com `tentativas=2`, proposta a `a_cotar`, 1 email |
| R3 | Limite de tentativas (fixado, exec. 88): 5 falhas anteriores → o WF3 não envia e falha com "falhou 5 vezes (máximo 5) e NÃO foi tentado de novo" (o Mail Error Flow envia o aviso) | Passa |
| R4 | Com 4 falhas anteriores (fixado, exec. 89): tenta a 5.ª, `tentativa=5`, os itens do email repostos após o apagar | Passa |
| R5 | Proposta nova sem linhas `falhou` (real, PRP-2026-0014, exec. 104 e 105): o nó "Limpar tentativas falhadas" não devolvia itens e o WF3 parava em silêncio sem gravar nada (o teste fixado R4 escondia o problema). Corrigido com `alwaysOutputData` e `executeOnce` no nó | Exec. 105 **passa**: 4 pedidos `enviado`, proposta a `a_cotar` |
| R6 | Mail Error Flow real (exec. 103 e 107): erro do Slack chega ao Error Workflow e envia o email de aviso | Passa |

## S. Slack (Notificar Slack, WF2 e WF3)
| Id | Verifica | Resultado |
| --- | --- | --- |
| S1 | Sub-workflow "Notificar Slack" real: publica no canal certo com o texto escapado | **Passa** (2026-10-08, exec. 108): mensagens publicadas em #novas-propostas e #pedidos-cotacao depois de a app ser convidada (antes falhava com `channel_not_found`, exec. 102 e 106) |
| S2 | WF2 chama o aviso "nova proposta" e o WF3 o aviso "cotação enviada", em paralelo e sem esperar | **Passa** (exec. 108, PRP-2026-0015): "🆕 Nova proposta ..." às 19:56:39 e "📦 Pedido de cotação enviado ... 4 transportadoras · (teste)" às 19:56:40 |

## W. WF5 Resumo para validação (dados fixados; Set e Code correm a sério)
| Id | Verifica | Resultado |
| --- | --- | --- |
| W1 | Com 2 cotações e compliance automático: assunto `[TESTE] [código] Proposta para validação...`, tabela de cotações (modo, preço, trânsito, validade), compliance e texto Slack com contagens (exec. 113) | Passa |
| W2 | Sem cotações nem compliance: "Ainda não há cotações", "compliance ainda não disponível"; HTML do cliente escapado (exec. 114) | Passa |
| W3 | Código inexistente → erro claro "proposta ... não encontrada" (exec. 115) | Passa |
| W5 | Com os dados completos (exec. 125): o email tem a coluna «Revisão» (automática / a rever) e a instrução «responda apenas com OK» | Passa |
| W6 | Proposta já `aprovada` → erro «não pode voltar a ser enviada para validação» (exec. 126); código inexistente continua a dar erro claro (exec. 127) | Passa |
| W7 | Depois do email, o nó «Marcar proposta em validação» passa a proposta a `em_validacao` (nó fixado nos testes; confirmar na primeira execução real) | Estrutural |
| W4 | Execução real (email + Slack + estado) | Pendente: precisa de uma proposta com cotações e do WF6 a chamar o WF5 |

## L. WF6 Ler cotações das transportadoras (dados fixados; Code corre a sério)
| Id | Verifica | Resultado |
| --- | --- | --- |
| L1 | 3 emails: resposta de transportadora conhecida com PRP a_cotar é aceite; o nosso pedido (`[TESTE] ...`) e remetente desconhecido são ignorados; extração válida → `revisao=automatica`, moeda em maiúsculas (exec. 116) | Passa |
| L2 | Validação do LLM: sem preço, modo ou prazo, confiança < 0,8 ou anexos → `a_rever` (verificação estrutural do código) | Passa (estrutural) |
| L3 | Execução real (Outlook, OpenRouter, Supabase, download do anexo) | Pendente: precisa de uma resposta real de transportadora, de preferência com PDF (os emails das transportadoras de teste são `@example.invalid`) |
| L4 | Passagem ao WF5: 1 cotação nova + 1 já registada, 2 pedidos enviados → a proposta segue (cotações 2, pedidos 2) (exec. 130) | Passa |
| L6 | Estrutural: «Ler pedidos de cotação enviados» com `executeOnce` e `alwaysOutputData` (o `addNode` ignorava-os; corrigido com `setNodeSettings`). O nó é fixado nos testes, por isso só a primeira execução real confirma | Estrutural |
| L7 | PDF com texto anexo (exec. 132): «Escolher o PDF» + «Extrair texto do PDF» (a sério, PDF real de teste) leem «frete maritimo 950 EUR, 8 dias»; texto do email + PDF vai ao LLM; confiança 0,95 → `automatica` com a nota «dados também lidos do PDF anexo» | Passa |
| L8 | Anexo que não é PDF (exec. 133): `anexo_lido=false`, sem dados → `a_rever` com «Há anexos que não foi possível ler» | Passa |
| L9 | Email sem anexos (exec. 134): o nó do PDF falha sem binário, o fluxo segue e a cotação mantém o comportamento anterior (`automatica`) | Passa |
| L10 | Regressão do L1 com a nova cadeia (exec. 135): só o email da transportadora conhecida é aceite; o nosso pedido e o remetente desconhecido são ignorados | Passa |
| L11 | Estrutural: cotação lida de PDF exige confiança ≥ 0,9 para ficar `automatica` (senão `a_rever`) | Estrutural |
| L5 | Poucas cotações: 1 cotação para 2 pedidos (exec. 128) e 1 para 4 pedidos, exige 3 (exec. 129) → nada é enviado ao WF5 | Passa |

## M. WF8 Aprovação da Bárbara por email (dados fixados; Code e If correm a sério)
| Id | Verifica | Resultado |
| --- | --- | --- |
| M1 | Resposta «OK» da Bárbara a proposta `em_validacao` → `aplicar=true`, `aprovada_por`/`aprovada_em` preenchidos, nó de gravação chamado, aviso Slack «aprovada» (exec. 121) | Passa |
| M2 | «OK mas muda o frete» → comentário: NÃO aprova, aviso Slack com o comentário (exec. 122) | Passa |
| M3 | Remetente desconhecido → ignorado, nada acontece (exec. 123) | Passa |
| M4 | Proposta já `aprovada` → aprovação ignorada, aviso Slack (exec. 124) | Passa |
| M5 | Trigger real do Outlook (resposta verdadeira) e gravação real no Supabase | Pendente: o workflow está por publicar; precisa de uma proposta real em `em_validacao` (W4) |

## X. WF1 Extração do pedido e «Read Outlook Messages» (dados fixados; Code e If correm a sério)
| Id | Verifica | Resultado |
| --- | --- | --- |
| X1 | WF1: pedido completo → `e_pedido=true`, campos validados, sem campos em falta, rascunho PT «a preparar a proposta» (exec. 137) | Passa |
| X2 | WF1: campos em falta e valores inválidos (incoterm/país/quantidade) → ficam a null e entram em `campos_em_falta`; rascunho lista o que falta (exec. 138) | Passa |
| X3 | WF1: email que não é pedido → `e_pedido=false`, sem rascunho (exec. 139) | Passa |
| X4 | WF1: falha do LLM → `falhou_llm=true`, confiança 0, sem inventar dados (exec. 140) | Passa |
| X5 | Read Outlook Messages: HTML limpo (style, `&nbsp;`), remetente em minúsculas, pedido segue para o ramo «sim» e newsletter para o «não» (exec. 141) | Passa |
| X6 | Real: email de teste na Folder 1 → lead gravado (jsonb `dados_extraidos`, `campos_em_falta`), draft em To Check, original lido, aviso Slack | Pendente: precisa de um email de teste na Folder 1 e créditos OpenRouter |
| X7 | Real (LLM a sério, OpenRouter haiku 4.5): pedido em inglês → empresa, 4-8 mm, 60 kg/m3, 2 t, big bags, FOB, ES/Valencia, confiança 0.95, rascunho em inglês; newsletter → `e_pedido=false`, sem rascunho (exec. 164, sub-exec. 165-166; antes falhou com 402 por chave sem créditos, o fallback funcionou) | Passa |

## F. Pendentes (precisam de execução real)
~~F1 envio real do email · F2 escrita real no Supabase · F3 submissão real~~ (feitos em 2026-10-07: PRP-2026-0002 gravada; email enviado para o destinatário de teste, sem erro registado; receção a confirmar pelo utilizador) · F4 aviso de erro real em produção · F5 leitura real da Folder 1 · F6 bloqueio de campos em falta no navegador.
