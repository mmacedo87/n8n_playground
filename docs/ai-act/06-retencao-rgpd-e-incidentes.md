# Retenção, proteção de dados e incidentes

Estado: **rascunho para aprovação** · Versão 1.0 · 2026-10-21 · Cobre os testes G4, G6, P1, P2, P3, P5, V2

## 1. Retenção (G4)

| Dados | Onde | Prazo proposto | Mecanismo |
| --- | --- | --- | --- |
| Leads não convertidos | Supabase `leads` | 12 meses | `purgar_leads_antigos(12)`, agendado (workflow n8n semanal ou pg_cron) |
| Leads convertidos / propostas | `leads`, `propostas`, `cotacoes_frete`, `pedidos_cotacao` | Obrigações contabilísticas/comerciais (a confirmar com contabilista) | Manual |
| Registo de uso de IA | `ai_log` | 24 meses | Eliminação manual anual |
| Execuções n8n | n8n Cloud | 30 dias (a confirmar na configuração) | Definição do n8n |
| Rascunhos e emails | Outlook | Política de email da empresa | Manual |

A configuração real tem de coincidir com esta tabela. Estado a 2026-10-21: o `pg_cron` não está instalado, por isso a purga ainda não corre sozinha.

## 2. Cadeia de IA e subcontratantes (P1, P2, P3)

| Fornecedor | Função | DPA arquivado | Região | Notas |
| --- | --- | --- | --- | --- |
| n8n Cloud | Orquestração | [ ] | `____` | |
| Supabase | Base de dados | [ ] | `____` | Backups: ver secção 4 |
| OpenRouter | Gateway do LLM | [ ] | `____` | Zero Data Retention ativo [ ]; modelos `:free` bloqueados [ ] |
| Anthropic (via OpenRouter) | Modelo | [ ] termos | `____` | |
| Microsoft (Outlook/365) | Email | [ ] | `____` | |
| Moloni | Faturação/orçamentos | [ ] | `____` | |

Arquivo dos DPA: `________________`. Capturas de ecrã das definições: `________________`.

## 3. Pedidos de acesso e apagamento (P5)

1. Receber o pedido e confirmar a identidade.
2. Localizar o contacto (por email) em `leads`, `propostas`, `pedidos_cotacao`, `cotacoes_frete`, Outlook e nas execuções n8n.
3. Exportar os dados (acesso) ou apagar/anonimizar (apagamento), respeitando obrigações legais de conservação.
4. Responder em 30 dias e registar no registo de incidentes e pedidos (secção 5).

`ai_log` não guarda emails nem corpo de mensagens (verificado em 2026-10-21: 0 registos com "@").

## 4. Backups e restauro (G6)

- Confirmar o plano de backups do Supabase e a frequência.
- Teste: restaurar num projeto de teste e comparar contagens de `propostas` e `ai_log`.
- Último teste: `__________` · Resultado: `__________`

## 5. Registo de incidentes e pedidos (V2)

| Data | Tipo (erro de IA, fuga, pedido RGPD) | Descrição | Impacto | Correção | Responsável |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

Contacto para reporte de erros de IA: `__________`
