# Plano de versionamento no GitHub

Estado: aprovado para arrancar (2026-10-06). Aplica-se a workflows n8n, SQL do Supabase, testes e documentação.

## Princípios

1. O n8n continua a ser a fonte de verdade do que está a correr; o Git é a fonte de verdade do histórico e da recuperação.
2. Nada secreto no repositório: sem chaves, tokens, passwords, IDs de credenciais, emails reais nem o caminho (`webhookId`) de formulários públicos.
3. Cada alteração a um workflow fica num commit próprio em `dev`, com mensagem que diz o que mudou, e a bateria de testes corrida antes.
4. Nada chega a `main` sem passar pelo `dev` e por um Pull Request.

## Branches

| Branch | Uso |
| --- | --- |
| `dev` | Trabalho corrente, ligado ao ambiente de desenvolvimento/testes do n8n |
| `stable` | Cópia de `dev` num ponto estável (mesmo commit); serve de referência para instalar em produção |
| `main` | Só o que foi validado e pode ir para produção. Atualizado por Pull Request vindo de `dev` |
| `feat/<nome>` | Opcional, para trabalho maior (ex. `feat/wf1-extracao`); entra em `dev` por PR |

O branch no GitHub chama-se `dev` (minúsculas).

## Estrutura do repositório

```
workflows/            um JSON por workflow, sanitizado
supabase/schema.sql   esquema completo atual
supabase/migrations/  alterações incrementais, numeradas (0001_..., 0002_...)
tests/                bateria de testes (descrição e dados de teste)
docs/                 documentação e planos
scripts/              sanitização e verificação de segredos
README.md
```

## Convenções

- **Ficheiros de workflow:** nome em minúsculas com hífens (`wf2-pedido-proposta.json`). O `meta` de cada JSON guarda o ID do workflow de origem, a `versionId` do n8n e a data de exportação.
- **Commits:** `tipo(âmbito): resumo`. Tipos: `feat`, `fix`, `test`, `docs`, `chore`, `db`. Exemplo: `feat(wf2): validar quantidade > 0`. O corpo indica a `versionId` do n8n e o resultado da bateria (ex. "bateria: 25/25").
- **Migrações SQL:** nunca editar uma migração já aplicada; criar a seguinte. `schema.sql` é atualizado em conjunto para refletir o estado atual.
- **Tags de versão:** `v0.1.0`, `v0.2.0`... em `main`, quando a bateria completa passa e o conjunto é aprovado.

## Fluxo de trabalho

1. Alterar o workflow no n8n (ambiente DEV).
2. Correr a bateria de testes (Notion: "Bateria de testes"); acrescentar testes novos para o que mudou.
3. Exportar o workflow, sanitizar com `scripts/sanitize_workflow.py` e substituir o ficheiro em `workflows/`.
4. Correr `scripts/check_no_secrets.sh` (falha se encontrar emails reais, chaves ou IDs sensíveis).
5. Commit em `dev` e push.
6. Quando um conjunto está estável: Pull Request `dev` → `main`, revisão, merge e tag.

## Segurança do repositório

- O repositório `mmacedo87/n8n_playground` está **público**. Antes de entrarem dados ou lógica de negócio reais, passá-lo a **privado**.
- Ativar secret scanning e push protection no GitHub.
- Proteger `main`: exigir Pull Request, sem push direto, sem force-push.
- O destinatário dos emails e os IDs de pastas/credenciais/workflows aparecem como marcadores (`REDACTED@example.invalid`, `<ID ...>`); ao importar noutra instância, preenchê-los.

## Recuperação (restore)

1. Importar o JSON em n8n (Workflows → Import from file) ou via API.
2. Ligar as credenciais pelo nome (os IDs não vão no Git).
3. Preencher os marcadores: destinatários, IDs de pastas Outlook, ID do Mail Error Flow como Error Workflow, ID do WF2 no nó de chamada.
4. Publicar e correr a bateria de testes.

## Evolução prevista

- **Curto prazo (manual):** exportar e sanitizar a cada alteração, como acima.
- **Médio prazo:** exportação noturna automática com GitHub Action que chama a API do n8n (chave guardada como secret do GitHub) e abre um PR em `dev` se houver diferenças.
- **Produção:** se o plano n8n incluir Source Control (Environments), usar a ligação Git nativa com um branch por ambiente e deixar de exportar à mão.
- **Detalhe a decidir:** manter o webhookId fora do Git obriga a que o URL do formulário mude quando se reimporta; em produção, fixar o caminho do formulário (campo `path`) e guardá-lo.

## Proteção do `main` (GitHub Actions)
- Ficheiro `.github/workflows/main-so-por-pr.yml`.
- **Em PR para `main`:** só aceita PRs de `dev` ou `stable`, corre os testes unitários (`test_deploy`, `test_app`, `test_kit`) e a verificação de segredos.
- **Em push para `main`:** falha se o commit não vier de um PR fundido (deteta pushes diretos; uma Action não os consegue impedir).
- O bloqueio efetivo é a regra de proteção do branch `main` (exigir PR e o check «PR para main (origem dev + testes)»).
- Depois de um merge em `main`, avançar `dev` e `stable` (fast-forward) para o mesmo commit.
