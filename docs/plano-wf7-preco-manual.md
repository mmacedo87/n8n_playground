# Plano: WF7 – Definir o preço final (opção A, formulário)

Criado em 2026-11-01. Estado: **por implementar**. Nada foi criado no n8n nem no Supabase.
Substitui, para já, a integração Moloni descrita em `plano_workflow_moloni_fase5.md`. Os campos gravados são os mesmos, por isso o Moloni pode entrar mais tarde sem mexer no resto do processo.

## 1. Decisões tomadas

| Tema | Decisão |
|---|---|
| Frete no preço | **Depende do Incoterm.** EXW, FCA, FAS e FOB: só o produto. CFR, CIF, CPT, CIP, DAP, DPU e DDP: produto mais frete. |
| IVA | **O sistema sugere o regime pelo destino e quem define o preço confirma.** O `preco_final` é o **total com IVA**, e o email ao cliente mostra a decomposição. |
| Unidade | **€/kg mais desconto em %.** O sistema calcula o total. |
| Quem define o preço | **Só a Bárbara para já.** A permissão fica na tabela `utilizadores` (`pode_definir_preco`). Cada pessoa recebe a sua ligação. |
| Aprovação | Continua no WF8 («OK código»). Passa a exigir que o preço esteja definido. |

## 2. Como funciona (visto pela Bárbara)

```
WF6 recebe cotação ──► WF5 envia o resumo à Bárbara
                         │  secção «Preço: por definir»
                         │  botão «Definir preço» (ligação pessoal)
                         ▼
             WF7 – página do preço (GET)
               resumo do pedido, cotações de frete para escolher,
               €/kg, desconto, regime de IVA sugerido, validade, notas,
               total calculado em direto na página
                         │ Gravar
                         ▼
             WF7 – gravar (POST)
               volta a validar tudo (ligação, permissão, estado)
               calcula no servidor, grava, gera um código de aprovação novo
                         │
                         ├─► página «Preço gravado» com a decomposição
                         ├─► Slack (#propostas)
                         └─► WF5 reenvia o resumo, já com o preço e o código novo
                                   │
                                   ▼
                    Bárbara responde «OK <código>» ──► WF8 ──► WF9 (cliente)
```

**Porque se gera um código de aprovação novo:** se o preço mudar depois do primeiro resumo, a Bárbara podia aprovar com o código antigo sem ter visto o preço atual. Com um código novo, só o último resumo, que mostra o preço em vigor, permite aprovar.

## 3. Base de dados (uma migração)

### 3.1 Tabela nova `utilizadores`
| Coluna | Tipo | Notas |
|---|---|---|
| id | uuid pk | |
| nome | text not null | |
| email | text unique not null | em minúsculas |
| pode_definir_preco | boolean not null default false | |
| pode_aprovar | boolean not null default false | para usar depois no WF8; nesta fase ainda não é usado |
| ativo | boolean not null default true | |
| criado_em, atualizado_em | timestamptz | trigger `set_atualizado_em` |

Dados iniciais: Bárbara, com o email de teste `REDACTED@example.invalid` em desenvolvimento, `pode_definir_preco = true`. RLS ativa e sem políticas, como nas outras tabelas.

### 3.2 Tabela nova `acessos_preco` (uma ligação por proposta e por pessoa)
| Coluna | Tipo | Notas |
|---|---|---|
| id | uuid pk | |
| proposta_id | uuid fk → propostas, on delete cascade | |
| utilizador_id | uuid fk → utilizadores | |
| token | text unique not null | 64 hex, gerado na BD (o mesmo padrão de `token_plano`) |
| expira_em | timestamptz not null default now() + 14 dias | |
| criado_em | timestamptz | |
| unique (proposta_id, utilizador_id) | | o WF5 reutiliza a ligação se ainda for válida e cria uma nova se tiver expirado |

### 3.3 Tabela nova `historico_precos` (registo de cada preço gravado)
Uma linha por cada gravação: proposta_id, utilizador_id, €/kg, desconto, cotação de frete, valor do frete, regime e taxa de IVA, valor líquido, IVA, total, notas e data. Serve de auditoria («quem mudou o preço, quando e de quanto para quanto»).

### 3.4 Colunas novas em `propostas`
Algumas colunas que já existem são reaproveitadas: `preco_tabela` passa a guardar o €/kg, e também se usam `desconto_pct`, `frete_escolhido_id`, `preco_final` e `moeda`.

| Coluna nova | Tipo |
|---|---|
| valor_produto | numeric(14,2) |
| valor_frete | numeric(14,2) default 0 |
| valor_liquido | numeric(14,2) |
| iva_regime | text check in ('pt_normal','ue_isento','exportacao_isento','outro') |
| iva_pct | numeric(5,2) |
| valor_iva | numeric(14,2) |
| cliente_nif | text (obrigatório quando o regime é `ue_isento`) |
| validade_proposta | date |
| preco_origem | text check in ('manual','moloni') |
| preco_definido_por | uuid fk → utilizadores |
| preco_definido_em | timestamptz |
| preco_notas | text |

### 3.5 Função `gravar_preco_proposta(...)` (Postgres)
Faz numa só transação:
1. confirma que o token existe, não expirou e que o utilizador está ativo e tem `pode_definir_preco`;
2. confirma que a proposta está em `pedido`, `a_cotar`, `cotado` ou `em_validacao`;
3. grava os valores, gera um `codigo_aprovacao` novo e insere a linha em `historico_precos`;
4. devolve o código da proposta e o código de aprovação novo.

Se alguma verificação falhar, não grava nada e devolve um erro claro. O n8n chama-a por HTTP (`/rest/v1/rpc/...`) com a credencial Supabase que já existe. Ficar tudo dentro da base de dados evita gravações a meio e situações em que duas gravações em simultâneo se atropelam.

## 4. Regras de cálculo (nó Code, sem LLM)

1. **Quantidade em kg:** se a unidade for `t`, multiplica-se por 1000.
2. **Produto:** `valor_produto = round2(kg × €/kg × (1 − desconto/100))`.
3. **Frete conforme o Incoterm:**
   - Grupo E/F (EXW, FCA, FAS, FOB): `valor_frete = 0`. Se for escolhida uma cotação, o sistema ignora-a e mostra um aviso.
   - Grupo C/D (CFR, CIF, CPT, CIP, DAP, DPU, DDP): é **obrigatório** escolher uma cotação. O valor é proposto automaticamente:
     - preço «total»: o preço da cotação;
     - preço «por camião»: preço × n.º de camiões (da cotação ou da proposta);
     - preço «por palete»: preço × n.º de paletes;
     - âmbito «não claro» ou «a rever»: a Bárbara tem de escrever o valor à mão.
   - O valor proposto pode ser corrigido no formulário. Fica registado se foi corrigido.
4. **Líquido:** `valor_liquido = valor_produto + valor_frete`.
5. **IVA sugerido pelo destino** (as menções legais estão **por confirmar com a contabilidade**):
   - PT: 23 % (`pt_normal`). Madeira e Açores ficam como `outro`, com a taxa escrita à mão.
   - País da UE: 0 %, `ue_isento`. Exige o NIF do cliente. Menção: isento ao abrigo do art. 14.º do RITI.
   - Fora da UE: 0 %, `exportacao_isento`. Menção: isento ao abrigo do art. 14.º do CIVA.
   - A Bárbara pode mudar o regime. Se escolher um regime diferente do sugerido, tem de escrever uma nota.
6. **IVA e total:** `valor_iva = round2(valor_liquido × iva_pct/100)` e `preco_final = valor_liquido + valor_iva`.
7. **Recusa com mensagem clara se:**
   - €/kg ≤ 0 ou > 50 (o limite é a confirmar);
   - desconto fora de 0 a 50 %;
   - grupo C/D sem frete;
   - moeda da cotação diferente de EUR;
   - total ≤ 0;
   - `ue_isento` sem NIF.
8. **Avisos que não bloqueiam:**
   - validade da proposta posterior à validade da cotação de frete;
   - cotação marcada «a rever».

O cálculo é feito duas vezes: na página, em JavaScript, para a Bárbara ver o total enquanto escreve, e no servidor, que é o que conta. O servidor nunca confia nos totais que chegam da página.

## 5. WF7 – Definir o preço final

- **Nome:** `WF7 - Definir o preço final (formulário)`. Etiquetas: `propostas`, `preco`.
- **Disparo:** Webhook com GET e POST no caminho `definir-preco`. É o mesmo padrão do WF10, que mostra uma página e grava num segundo passo.
- **Configuração:** Error workflow `fWXNAbhbQLuYeurE`, `saveDataSuccessExecution: none`, `saveDataErrorExecution: all`.

| Grupo | Nós |
|---|---|
| Mostrar a página (GET) | Validar o formato do token → Ler o acesso, a proposta, o utilizador, as cotações e as transportadoras (Supabase) → Verificar (expirado, sem permissão, estado inválido: página de erro amigável, sem exceção) → Montar a página HTML (HTML escapado, cálculo em direto, IVA sugerido) → Responder |
| Gravar (POST) | Ler o formulário → Calcular e validar (Code) → `gravar_preco_proposta` (HTTP RPC) → Responder com a página «Preço gravado» → Avisar Slack (subfluxo `N7BZddGLl0WlSl9Q`, sem esperar) → Chamar o WF5 (reenviar o resumo, sem esperar) |

Uma página de erro não é uma falha do fluxo: o utilizador vê uma mensagem e não chega nenhum email de erro. Só os erros inesperados vão para o Mail Error Flow.

## 6. Alterações aos fluxos existentes

| Fluxo | Alteração |
|---|---|
| **WF5** (resumo) | (a) Ler os utilizadores com `pode_definir_preco` e criar ou reutilizar o acesso de cada um (por agora só a Bárbara). (b) Nova secção «Preço»: «por definir» com botão, ou a decomposição com o botão «Alterar preço». (c) Instruções de aprovação: «só pode aprovar depois de definir o preço». (d) Aceitar ser chamado pelo WF7. |
| **WF8** (aprovação) | No nó «Decidir»: se `preco_final` estiver vazio ou for ≤ 0, ignora a aprovação e avisa no Slack: «defina primeiro o preço». O código de aprovação passa a mudar sempre que o preço muda, sem outra alteração no WF8. |
| **WF9** (envio ao cliente) | O email passa a mostrar a decomposição: €/kg, quantidade, desconto, frete (se houver), regime e menção de IVA, total e validade da proposta. Sai a mensagem «depende da fase 5, Moloni». |
| **WF13** (reserva de frete) | Se a transportadora escolhida for diferente da cotação usada no preço (`frete_escolhido_id`), dá erro com explicação: o preço foi calculado com outra cotação e tem de ser alterado primeiro. |
| **WF10** (confirmação) | Verificar se a página de confirmação mostra o total e, se mostrar, se deve passar a mostrar a decomposição. |

Ficam para depois: usar `utilizadores.pode_aprovar` no WF8 em vez da lista `AUTORIZADOS` e tirar dos fluxos os emails escritos à mão.

## 7. Segurança

- Ligação pessoal com código de 64 hex, válida 14 dias. A permissão e o estado voltam a ser verificados quando se grava.
- Retirar a permissão (`pode_definir_preco = false` ou `ativo = false`) bloqueia logo a ligação.
- Todo o HTML é escapado. Os valores numéricos são validados no servidor.
- Não se pode alterar o preço depois da aprovação, porque a função recusa os estados `aprovada` e seguintes.
- Não há LLM em nenhum passo do preço.

## 8. Testes (com destinatários de teste)

| # | Caso | Esperado |
|---|---|---|
| T1 | DAP, PT, cotação «total» | frete incluído, IVA 23 %, total certo ao cêntimo |
| T2 | FCA, Espanha, com NIF | sem frete, `ue_isento`, total = líquido |
| T3 | CIF, EUA | frete incluído, `exportacao_isento` |
| T4 | Cotação «por camião» com 2 camiões | frete = preço × 2 |
| T5 | Cotação «a rever» ou âmbito não claro | obriga a escrever o valor do frete |
| T6 | Grupo C/D sem cotação | recusado com mensagem |
| T7 | `ue_isento` sem NIF | recusado |
| T8 | €/kg = 0, desconto de 80 % | recusado |
| T9 | Ligação expirada ou código inválido | página de erro, nada gravado |
| T10 | Utilizador com `pode_definir_preco = false` | página de erro, nada gravado |
| T11 | Proposta já aprovada | recusado |
| T12 | Preço alterado duas vezes | 2 linhas no histórico, código de aprovação novo, o «OK» com o código antigo é ignorado |
| T13 | «OK código» sem preço | WF8 ignora e avisa |
| T14 | Do princípio ao fim: pedido → cotação → preço → OK → envio ao cliente | o email ao cliente mostra a decomposição |
| T15 | WF13 com uma transportadora diferente da do preço | erro com explicação |
| T16 | Quantidade em toneladas | conversão para kg certa |

## 9. Passos de implementação

1. Confirmar com a contabilidade as menções de IVA e o limite máximo do €/kg.
2. Migração no Supabase (secção 3) e testes da função em transação revertida.
3. Construir o WF7 (lendo antes as skills n8n de configuração de nós, de código e de tratamento de erros), validar, verificar as ligações e testar com dados fixados.
4. Alterar o WF5, o WF8, o WF9 e o WF13. Cada alteração é validada e testada.
5. Teste completo com destinatários de teste (T14) e depois publicar.
6. Atualizar o Notion (bateria de testes e estado do processo) e a apresentação: o passo «Preço final» passa a pronto.

## 10. Riscos

- **Menções de IVA erradas:** atenuado por serem confirmadas com a contabilidade antes de publicar.
- **Frete mal interpretado** (por camião ou total): atenuado porque o valor é proposto, a Bárbara pode corrigi-lo e as cotações «a rever» obrigam a escrever o valor à mão.
- **Preço desatualizado** depois de chegar uma cotação nova: o resumo é reenviado e mostra o preço em vigor. O preço não muda sozinho, só pela mão da Bárbara.
- **Ligação reencaminhada a outra pessoa:** quem a receber pode definir o preço em nome da Bárbara até a ligação expirar. Atenuado pelo prazo de 14 dias, pelo registo no histórico e pela aprovação, que continua a exigir a resposta da Bárbara com o código.
