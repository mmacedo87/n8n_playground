# Bateria de testes

Fonte de verdade dos resultados: página "Bateria de testes" no Notion (checkbox, razão e resolução provável das falhas).
Este ficheiro descreve **o que** se testa. Regra: tudo o que se cria leva testes novos, e antes de dar algo por fechado corre-se a bateria completa.

Última execução: 2026-10-08 (Lisboa), depois de o WF3 passar a enviar UM único email às transportadoras. Supabase (A1-A27) todos passam; n8n: B1-B3 (credenciais, Error Workflow, callerPolicy) verificados; WF3 testado com dados fixados em modo de teste e em modo de produção (exec. 70 e 71), WF2 (exec. 72, 73) e WF4 (exec. 74) passam. Não re-corridos nesta data: C, E, restantes G, H e I (o código dos respetivos workflows não mudou). G9 e F1-F6 (execução real) continuam pendentes.

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
| R2 | Repetir uma proposta cujo envio falhou | **Conhecido, por corrigir**: as linhas `falhou` contam como "já contactadas" e o WF3 recusa (exec. 83) |

## F. Pendentes (precisam de execução real)
~~F1 envio real do email · F2 escrita real no Supabase · F3 submissão real~~ (feitos em 2026-10-07: PRP-2026-0002 gravada; email enviado para o destinatário de teste, sem erro registado; receção a confirmar pelo utilizador) · F4 aviso de erro real em produção · F5 leitura real da Folder 1 · F6 bloqueio de campos em falta no navegador.
