# Plano: Fase 5 – Preço final via Moloni (fluxo n8n)

Criado em 2026-10-17. Estado: **por implementar**. Nada foi criado no n8n.

## 1. Contexto

O **WF9 – Envio da proposta ao cliente** (`UrGBkXG37To7RYMR`) só envia se `propostas.preco_final > 0` e `estado = 'aprovada'`. Caso contrário falha com *"ainda não tem preço final (depende da fase 5, Moloni)"*.

Nenhum fluxo tem hoje nós ou credenciais Moloni. A fase 5 é um fluxo novo (não é adaptação de um existente) que, para uma proposta, obtém o preço no Moloni e grava `preco_final`.

Fluxos relacionados (todos com a etiqueta `propostas`):

| WF | ID | Papel |
|---|---|---|
| WF2 | `8pRJJuN094Mp9iuu` | Regista o pedido (cliente, produto, densidade, granulometria, quantidade kg, embalagem, incoterm, destino) |
| WF3 / WF6 | `x9RhWxZfJ0apbhlc` / `HErViy6cNVrTIH7A` | Pedem / leem cotações de frete |
| WF5 | `8xj41URokjCimmon` | Resumo para validação da Bárbara (estado `em_validacao`) |
| WF8 | `4dU064sO0xcxkPTc` | Aprovação por mensagem (estado `aprovada`) |
| WF9 | `UrGBkXG37To7RYMR` | Envio ao cliente (exige `preco_final`) |
| WF10–12 | – | Confirmação, expedição, follow-up |

Padrões a seguir (vistos nos WFs existentes): subfluxo com arranque `executeWorkflowTrigger` e entrada `codigo`; nó Set "Normalizar código" (`trim().toUpperCase().slice(0,20)`); Supabase `getAll` na tabela `propostas`; erros com mensagem clara em nó Code; `errorWorkflow: fWXNAbhbQLuYeurE` (Mail Error Flow); aviso Slack via subfluxo `N7BZddGLl0WlSl9Q` (canal `propostas`, `waitForSubWorkflow: false`); etiquetas `subworkflow` + `propostas`; destinatário de teste no nó Set com nota DEV.

## 2. Decisões em aberto (resolver antes de construir)

1. **Onde encaixa na cadeia?** Recomendado: chamar a fase 5 **antes do WF5**, para a Bárbara ver o preço ao validar. Alternativa: depois da aprovação (WF8) e antes do WF9. Se for a segunda, o preço não é validado por humano.
2. **O preço inclui frete?** Hoje há cotações de frete (`cotacoes_frete`) e incoterm. Definir se `preco_final` = produto + frete escolhido + margem, ou só produto. (Impacta o cálculo e quem escolhe a cotação.)
3. **Criar o orçamento no Moloni (`estimates/insert`) ou só ler preços?** Recomendado: criar o orçamento, para ficar rasto contabilístico e `our_reference = PRP-...`.
4. **Cliente:** a tabela `propostas` só tem o nome (`cliente`). É preciso mapear para um `customer_id` do Moloni (pesquisa por nome/NIF) e daí obter `price_class_id`. Confirmar se o NIF/mensagem do cliente existe em `propostas` ou se se adiciona uma coluna `moloni_customer_id`.
5. **Mapeamento produto → referência Moloni:** convenção sugerida (a confirmar com o catálogo real): `GRA-80-100-2-4`, `PO-60-80-0-1`, `AGL-120-150-8-15` (produto-densidade-granulometria). Se o Moloni não tiver estas referências, é preciso uma tabela de mapeamento.
6. **IVA:** regra para isenção (UE com NIF válido vs. Portugal 23% vs. países terceiros). Definir quem decide (regra em código por `destino_pais` ou o Moloni a aplicar a partir do cliente). O motivo de isenção (`M16` no simulação) tem de ser confirmado.
7. **Autenticação Moloni:** a API v1 usa OAuth2 (access_token por query/param, refresh_token). Verificar se existe nó/credencial nativa na instância (`search_nodes "moloni"`); senão, HTTP Request com credencial OAuth2 genérica. Segredos só no sistema de credenciais do n8n.

## 3. Desenho proposto

Novo fluxo: **"WF7 - Preço final (Moloni)"** (nome a confirmar; evitar colidir com a numeração existente). Subfluxo, entrada `codigo`.

```
Chamado por outro fluxo
 → Normalizar código
 → Ler proposta (Supabase, propostas)
 → Validar proposta (Code: existe, estado permitido, quantidade > 0)
 → Moloni: procurar cliente (customers/getBySearch)
 → Moloni: tabelas de preços (priceClasses/getAll)
 → Moloni: procurar produto (products/getBySearch por reference)
 → Calcular preço (Code: preço da tabela do cliente × kg, desconto, IVA)
 → [opcional] Moloni: criar orçamento (estimates/insert)
 → Gravar preco_final (Supabase update propostas: preco_final, moeda, moloni_document_id, preco_calculado_em)
 → Avisar Slack (subfluxo N7BZddGLl0WlSl9Q)
```

Regras de código (nó de código, sem LLM):
- Preço da linha = preço do produto para a `price_class_id` do cliente; se não existir preço na tabela, usar `price` base e marcar aviso.
- Preço especial por tabela (valor fixo) tem prioridade sobre percentagem.
- Arredondar a 2 casas só no total de cada linha; totais = soma das linhas; IVA sobre o líquido.
- Erro explícito se: cliente não encontrado ou ambíguo, produto sem referência, moeda ≠ EUR, resultado ≤ 0. Nunca gravar `preco_final` em dúvida.
- Idempotência: se `moloni_document_id` já existe, não criar outro orçamento (reutilizar/atualizar).

### Alterações a fluxos existentes
- **Cadeia (WF2/WF6 ou WF5):** acrescentar nó `executeWorkflow` para a fase 5, sem esperar (ou a esperar, se o WF5 precisar do preço no resumo). Depende da decisão 1.
- **WF5:** se a fase 5 correr antes, acrescentar linha "Preço" ao mensagem de resumo.
- **Supabase `propostas`:** colunas novas prováveis: `moloni_customer_id`, `moloni_document_id`, `moeda` (já usada pelo WF9), `preco_calculado_em`. Confirmar o esquema atual antes (ver `list_tables`).
- **WF9:** sem alterações (já valida `preco_final`).

## 4. Testes (usar os simulações)

Dados de teste já criadas em `/Users/mmacedo/claude_work/maclipe/`:
- `moloni_estimate_simulação.json` – cenário com IVA 23%: líquido 6 388,75, IVA 1 469,41, bruto **7 858,16**.
- `moloni_estimate_simulação_isento_iva.json` – cenário isento (`M16`): bruto **6 388,75**.

Cada ficheiro tem `priceClasses_getAll`, `products_getAll`, `estimates_getOne` e `n8n_items` (dados fixos de teste).

Plano de teste:
1. Dados fixos nos nós Moloni, com as secções correspondentes das simulações (`prepare_workflow_pin_data` / `test_workflow`), com os nós Supabase/Slack também fixados ou apontados a uma proposta de teste.
2. Casos: IVA 23% → `preco_final = 7858.16`; isento → `6388.75`; preço especial (Pó, Exportação 1,05 €/kg); desconto 5% na linha.
3. Casos de erro: cliente não encontrado, produto sem referência, tabela de preços sem o produto, estado inválido, repetir a chamada (idempotência).
4. Só depois, execução real contra o Moloni com um cliente de teste, antes de ligar à cadeia.
5. Confirmar que o WF9 já envia (com destinatário de teste) quando `preco_final` está preenchido.

## 5. Passos de implementação

1. Resolver as decisões da secção 2.
2. Obter uma resposta real de `estimates/getOne`, `priceClasses/getAll` e `products/getAll` da conta Moloni; ajustar os simulações e os nomes de campos (os atuais são baseados na API v1 e não foram confirmados).
3. Criar a credencial Moloni no n8n.
4. Ler as skills n8n antes de escrever (`n8n-workflow-lifecycle-official`, `n8n-node-configuration-official`, `n8n-code-nodes-official`, `n8n-credentials-and-security-official`, `n8n-error-handling-official`) e usar `get_workflow_sdk_reference`, `search_nodes`, `validate_workflow`.
5. Criar o fluxo (`create_workflow_from_code`), validar, verificar `connections` com `get_workflow_details`, testar com dados fixos de teste.
6. Ligar à cadeia, testar ponta a ponta com destinatários de teste, e só então publicar.

## 6. Riscos
- Campos Moloni dos simulações não confirmados.
- Cliente mal associado → preço de tabela errada. Atenuação: falhar em caso de ambiguidade.
- Duplicar orçamentos no Moloni. Atenuação: idempotência por `moloni_document_id`.
- Preço enviado ao cliente sem validação humana (se a fase 5 correr depois do WF8).
