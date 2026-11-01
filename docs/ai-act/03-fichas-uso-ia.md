# Inventário e fichas dos usos de IA

Estado: versão 1.0 · 2026-10-21 · Cobre os testes C4, D2, T6, R12
Modelo em todos os usos: `anthropic/claude-haiku-4.5` via OpenRouter. Os workflows registam cada uso em `ai_log` (workflow, execução, modelo, `versao_prompt`).

## Inventário

| # | Workflow | Tarefa | Temperatura | Máx. tokens | Prompt (`ai_log.versao_prompt`) |
| --- | --- | --- | --- | --- | --- |
| 1 | WF1 | Extração dos campos do pedido (email) | a confirmar | a confirmar | a registar |
| 2 | WF3 | Redação do email único de pedido de cotação | 0,3 | 600 | v2 (v1 histórico) |
| 3 | WF3 | Escolha das melhores transportadoras | 0,2 | 500 | a registar |
| 4 | WF6 | Extração de cotações (texto/PDF) | a confirmar | a confirmar | a registar |

Os restantes workflows (WF2, WF4, WF5, WF8, WF9, WF10, WF11, WF12, WF13, Read Outlook, Notificar Slack, Error Flows) **não usam LLM**. Qualquer alteração a esta tabela segue `05-gestao-de-mudanca.md`.

## Ficha 1: WF1, extração do pedido

- **Finalidade:** transformar um email de pedido em campos estruturados (produto, quantidade, destino, Incoterm, etc.).
- **Dados enviados:** texto do email limpo de HTML, limitado a 6000 caracteres. Sem anexos.
- **Output:** JSON validado pelo nó "Validar pedido" (lista de Incoterms, países). Em falha: `falhou_llm=true`, sem dados inventados.
- **Supervisão:** o resultado fica como lead `novo` / rascunho em "To Check"; nada é enviado automaticamente; a Bárbara revê.
- **Limitações:** pode ler mal quantidades ou países; newsletters/spam devem ser ignoradas; vulnerável a injeção de prompt (mitigado: LLM sem ferramentas, validação em código).
- **Testes:** R1, R5, R6, S1, S3, S4, P4, H8, H9.

## Ficha 2: WF3, redação do email de pedido de cotação

- **Finalidade:** redigir a introdução do email único às transportadoras.
- **Dados enviados:** código da proposta, produto, quantidade, rota/destino. Sem nome do cliente final nem preços.
- **Validação (nó "Montar email"):** rejeita texto com links, HTML, símbolos de moeda ou "EUR/USD"; exige o código da proposta na introdução; caso contrário usa texto fixo. A assinatura e a frase de transparência são acrescentadas em código.
- **Supervisão:** envio automático às transportadoras; revisão amostral (V1). Decisão formal em `02-politica-uso-ia-e-supervisao.md`.
- **Limitações:** a maioria das execuções registadas caiu no texto fixo (27 de 28 em 2026-10-21), por isso o `ai_log` deve registar o motivo da rejeição.
- **Testes:** T1, T2, T6, R5, R7, R8, G1.

## Ficha 3: WF3, escolha de transportadoras

- **Finalidade:** escolher 4 ou 5 transportadoras adequadas ao destino e modo (marítimo/terrestre).
- **Dados enviados:** destino, modo, lista de transportadoras ativas e respetivas rotas.
- **Validação:** só transportadoras ativas que servem o destino; reserva por regra determinística; envio mesmo com menos de 4.
- **Supervisão:** o pedido de cotação é visível em `pedidos_cotacao` e no Slack.
- **Limitações:** pode excluir uma transportadora adequada; mitigado pela regra de reserva.
- **Testes:** R6, R10, R11.

## Ficha 4: WF6, extração de cotações

- **Finalidade:** extrair preço, moeda, modo, prazo e validade de respostas das transportadoras (texto e PDF).
- **Dados enviados:** texto da resposta/PDF.
- **Validação (nó "Validar extração"):** o preço tem de existir no texto original; ambiguidades ou ausência de moeda marcam `a_rever`; nunca se grava valor inventado.
- **Supervisão:** cotações em `a_rever` ficam para decisão humana; o preço final é decidido por pessoas.
- **Limitações:** PDFs digitalizados, múltiplos preços, condições por camião/total.
- **Testes:** R2, R3, R4, S2.
