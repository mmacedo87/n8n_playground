# Moloni: âmbito da API para gerar a proposta (2026-10-08)

Fontes: [Autenticação](https://www.moloni.pt/dev/autenticacao/), [Orçamentos (estimates)](https://www.moloni.pt/dev/documents/estimates/), [índice da API](https://www.moloni.pt/dev/).

## Conclusão
A API permite criar orçamentos (`estimates`) automaticamente, por isso a fase 5 é viável. Para a construir falta o acesso de programador (Developer ID e Client Secret) e uma decisão sobre como manter a autenticação.

## O que a API oferece para orçamentos
| Endpoint | Para quê |
| --- | --- |
| `estimates/insert` | Cria um orçamento (descontos em %, de 0 a 100: `financial_discount`, `special_discount`, `salesman_commission` e `discount` por produto) |
| `estimates/getAll`, `getOne`, `count` | Consultar orçamentos |
| `estimates/update`, `delete` | Alterar ou apagar |

Não há `getPDFLink` na lista de orçamentos: o PDF terá de ser obtido por outra via (a confirmar na documentação completa ou no suporte do Moloni). Os restantes parâmetros do `insert` (cliente, produtos, preços, notas) não constam da página consultada e têm de ser confirmados com a conta de programador.

## Autenticação (OAuth 2.0)
- Precisa de conta com acesso de programador: Developer ID (`client_id`), Redirect URI e Client Secret.
- Access token válido 1 hora; refresh token válido **14 dias**.
- Com cerca de 2 propostas por mês, o refresh token vai caducar entre utilizações. Opções: (a) um workflow agendado que renova o token de poucos em poucos dias e o guarda de forma segura; (b) fluxo de password (guardar utilizador e palavra-passe do Moloni, o que o Moloni desaconselha); (c) voltar a autorizar manualmente quando caducar.

## O que preciso de si
1. Developer ID, Client Secret e Redirect URI (criados na área de programador do Moloni), ou acesso para os criar.
2. Escolher entre as opções (a), (b) e (c) de autenticação (recomendo a).
3. Um exemplo de orçamento real (cliente, produtos, preço de tabela, desconto, termos) e a tabela de preços, para mapear os campos.
