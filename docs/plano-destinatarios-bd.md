# Plano: emails dos workflows na base de dados

Estado: **proposta, por aprovar** · 2026-10-28 · Inclui avaliação de segurança e de AI Act (a seguir às secções 1-4).

## 1. Objetivo e âmbito

Tirar os emails dos workflows e do código e guardá-los na tabela `configuracao` do Supabase, que já existe (migração 0009, hoje só com `modo_envio`), para:
- alternar entre teste e produção mudando linhas, sem republicar workflows nem reenviar valores `REDACTED@example.invalid` do export (armadilha já vivida no WF2);
- simplificar a passagem a produção (o deploy deixa de pedir quase todos os emails);
- manter o repositório sem emails.

**Onde estão hoje** (levantamento dos exports): Set do WF2 (`destinatario_confirmacao`), WF3 (`destinatario_principal`), WF5 (`destinatario_validacao`), WF9 e WF12 (`cc_barbara`), WF10 (`email_madalena`, `email_barbara`), `destinatario_teste` em WF3, WF5, WF9, WF10, WF12, WF13; constantes no código do WF11 («Decidir plano») e do WF13 («Plano para a Madalena»); lista `AUTORIZADOS` no código do WF8; destinatário dos dois error flows. As transportadoras e os clientes já estão na BD (`transportadoras.email`, `propostas.contacto_email`).

**Fora do âmbito:** WF1, WF6, prompts e qualquer nó com LLM; emails de clientes e transportadoras.

## 2. Desenho

**Tabela:** estender `configuracao` (chave/valor), o padrão que o WF3 já usa (lê `modo_envio` e, se falhar, assume `revisao`).

| Chave | Valor | Usada por |
| --- | --- | --- |
| `email.erros` | email | Mail Error Flow, WF2 Error Flow (com recurso, ver S6) |
| `email.confirmacao_pedido` | email | WF2 |
| `email.cotacoes` | email | WF3 |
| `email.validacao_barbara` | email | WF5 |
| `email.barbara` / `email.cc_barbara` | email | WF9, WF10, WF11, WF12 |
| `email.madalena` | email | WF10, WF11, WF13 |
| `modo_teste` | `ligado` / `desligado` | todos os que enviam |
| `email.teste` | email | quando `modo_teste = ligado`, **todos** os envios (internos, ao cliente e às transportadoras) vão para este endereço, com `[TESTE]` no assunto |

**Resolução num único sítio:** um sub-workflow «Ler configuração» (ou, se preferirmos, um nó Supabase + Code em cada workflow; ver D1) lê a tabela, valida e devolve um objeto `{email_barbara, email_madalena, ..., modo_teste}`. A regra do modo de teste vive aí, não repetida em 10 workflows.

**Regra de falha (fail-closed):** chave em falta ou inválida = o workflow pára com erro claro e o error flow avisa. Nunca se envia para um endereço vazio nem se recorre a um valor antigo. Única exceção: os error flows mantêm um endereço de recurso, para o aviso não depender do Supabase.

**WF8 `AUTORIZADOS`:** fica no código (ver D4).

## 3. Passos

| # | Passo | Entregável |
| --- | --- | --- |
| 0 | Decidir D1-D5 (secção 7) | decisões registadas |
| 1 | Migração 0010 + rollback + `schema.sql`: chaves, restrições, histórico de alterações, testes SQL | `supabase/migrations/0010_*.sql`, `supabase/rollbacks/0010_rollback.sql` |
| 2 | «Ler configuração» + testes offline do resolvedor | sub-workflow, `scripts/config_code/`, `tests/test_config_code.py` |
| 3 | Migrar WF10, WF11, WF13 (os últimos alterados); depois WF2, WF3, WF5, WF9, WF12; error flows com recurso | um commit por workflow, versionId e bateria no corpo |
| 4 | Deploy e assistente: tirar `BINDINGS`/`CODE_BINDINGS` dos emails migrados; `config.example.json` passa a pedir só recurso de erros e aprovadores; o instalador preenche a tabela | `scripts/deploy_workflows.py`, `app/`, kit, `docs/passagem-producao.md`, `resumo-cliente.html` |
| 5 | Testes reais comedidos (secção 6), PR `dev` → `main` | registo em `tests/BATERIA.md` |

Cada passo corre a bateria completa e fica em commit próprio em `dev`.

## 4. Avaliação de segurança

| # | Ameaça | Risco | Mitigação |
| --- | --- | --- | --- |
| S1 | Quem lê ou altera a tabela | Médio | RLS ativa sem políticas e `revoke` a `anon`/`authenticated` (já assim na 0009): só `service_role`. A credencial do n8n é `service_role`, logo quem edita workflows pode alterar a tabela: limitar o acesso ao projeto n8n e ao painel Supabase, MFA. |
| S2 | Redirecionar emails para fora da empresa (fuga de propostas e dados de clientes) | **Alto** | Restrição na BD: formato de um único endereço (sem espaços, vírgulas, `;`, CR/LF), e **lista de domínios permitidos** para chaves `email.*` (ver D3). Histórico imutável de alterações (S3). |
| S3 | Alteração sem rasto | Médio | Tabela `configuracao_historico` preenchida por trigger (chave, valor antigo/novo, quando, utilizador da BD), sem `update`/`delete` para `service_role`. Cobre também `modo_envio` e `modo_teste`. |
| S4 | Injeção em cabeçalhos (BCC escondido) | Médio | Os valores não vêm de utilizadores, mas a validação de S2 bloqueia vírgulas e quebras de linha; o resolvedor repete a validação antes de enviar. |
| S5 | `modo_teste` errado: ligado em produção (nada chega) ou desligado em desenvolvimento (envios reais) | Médio | Valor em falta ou inválido = erro (fail-closed); `[TESTE]` no assunto; verificação do valor na checklist de passagem a produção e no início de cada bateria. |
| S6 | Supabase em baixo | Baixo | Os workflows já dependem dele. Só os error flows têm endereço de recurso fixo, preenchido pelo deploy e nunca no Git. |
| S7 | Segredos no repositório (público) | Positivo | Menos emails em `workflows/` e em `config.json`; `check_no_secrets.sh` continua obrigatório. |
| S8 | Reversão | Baixo | Rollback SQL e `restore_workflow_version` do n8n; commits independentes por workflow. |
| S9 | RGPD | Baixo | Só emails profissionais de 2-3 pessoas, finalidade e prazo definidos (histórico: 12 meses), tabela fora da API pública. Acrescentar ao registo de tratamentos. |

## 5. Avaliação AI Act

Seguindo o procedimento de `docs/ai-act/05-gestao-de-mudanca.md`:

| Pergunta | Resposta |
| --- | --- |
| (a) Cai no Art. 5? | Não. |
| (b) Cai no Anexo III? | Não. |
| (c) A IA passa a decidir algo? | Não. Nenhum nó com LLM é alterado (WF1, WF6 e o texto do WF3 ficam como estão). |
| (d) Novos dados pessoais? | Emails profissionais de pessoal interno ficam na BD. **Não vão ao LLM**: confirmar por teste que nenhum prompt lê `configuracao`. |

**Conclusão:** não dispara reavaliação formal (classificação mantém-se: risco limitado/mínimo); regista-se na secção 3 de `05-gestao-de-mudanca.md`. Pontos a vigiar:

| Artigo / boa prática | Impacto | Ação |
| --- | --- | --- |
| Art. 14 (supervisão humana, boa prática) | A tabela guarda `modo_envio`, que pode passar o WF3 a envio sem revisão humana; o aviso de transparência do Art. 50 (frase fixa no WF3) tem de se manter. | Histórico (S3) cobre `modo_envio`; teste de que, com `modo_envio = revisao`, nada é enviado; manter a lista de aprovadores do WF8 no código (D4). |
| Art. 50 (transparência) | Sem alteração: o modo de teste só desvia destinatários, não altera o texto. | Teste: a frase de IA continua no email do WF3 com `modo_teste` ligado e desligado. |
| Art. 4 (literacia) | Quem edita a configuração passa a ser administrador do sistema. | Incluir essas pessoas no registo de formação (`04-formacao-literacia-ia.md`). |
| Registo/rastreabilidade (Art. 12, boa prática) | Melhora: alterações de configuração ficam auditáveis. | Referir `configuracao_historico` em `03-fichas-uso-ia.md` e `06-retencao-rgpd-e-incidentes.md` (retenção). |

Esta avaliação é técnica e de apoio, **não é aconselhamento jurídico** (mesma ressalva da `avaliacao-ai-act.md`).

## 6. Testes

| Tipo | O quê |
| --- | --- |
| SQL (transação revertida, `tests/supabase_bateria.sql`) | Rejeita email com espaço, vírgula, `;`, quebra de linha, sem `@`, domínio fora da lista; `modo_teste` fora de `ligado`/`desligado`; `anon`/`authenticated` sem acesso; trigger grava histórico em inserção e alteração; histórico não se apaga. |
| Offline (`tests/test_config_code.py`) | Resolvedor: chave em falta ou inválida dá erro; `modo_teste` ligado desvia todos os destinos; desligado usa os reais; nunca devolve vazio. |
| Estrutural | Nenhum export de `workflows/` tem email (`REDACTED`) fora dos recursos de erro e do WF8; todos os workflows que enviam usam o resolvedor; deploy sem `BINDINGS` dos emails migrados. |
| n8n com dados fixados | Cada workflow migrado: caminho feliz e chave em falta (pára com erro). |
| Real, comedido | (1) WF11 «Não» e «Sim» com `modo_teste = ligado` (tudo chega ao `email.teste`); (2) uma cadeia completa nova por email, com `modo_teste` ligado, antes da passagem a produção; (3) um envio com `modo_teste = desligado` só quando a lista de domínios estiver preenchida e for aprovado. Sem apagar dados de teste (regra 7). |
| Regressão | Bateria completa existente (unittest, e2e do assistente, Supabase A1-A27+). |

## 7. Decisões que preciso de ti

| # | Decisão | Recomendação |
| --- | --- | --- |
| D1 | Sub-workflow «Ler configuração» (lógica num só sítio) ou nó Supabase + Code em cada workflow (sem chamada extra) | Sub-workflow, desde que as chamadas não pesem nas execuções do plano n8n Cloud (a confirmar antes de implementar). |
| D2 | Uma só `modo_teste` global ou por ambiente | Global na BD de desenvolvimento; em produção a tabela parte com `desligado` e o instalador preenche. |
| D3 | Lista de domínios permitidos para `email.*` | Sim; em desenvolvimento inclui os aliases de teste, em produção só o domínio da empresa. |
| D4 | `AUTORIZADOS` do WF8 na tabela ou no código | No código: mudar quem pode aprovar exige commit e revisão (rasto no Git). Rever na fase seguinte. |
| D5 | Falha de leitura: parar (recomendado) ou usar um valor de recurso | Parar, exceto nos error flows. |
