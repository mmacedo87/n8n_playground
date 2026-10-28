# Execução dos testes de compliance AI Act: resultados e resoluções

Data: 2026-10-21 · Base: `testes-ai-act.md` (72 testes) e `avaliacao-ai-act.md`
Nota: não substitui parecer jurídico.

## 0. Como foram executados (leia primeiro)

**Não executei nenhum workflow.** Executar formulários, webhooks ou o WF3 enviaria emails reais a transportadoras, e os workflows com `executeWorkflowTrigger` não podem ser lançados por MCP. O que fiz foi:

- **Inspeção estática** das definições dos 17 workflows n8n (nós, código, prompts, `onError`, credenciais, ativos/inativos).
- **Consultas só de leitura** ao Supabase (tabelas, RLS, políticas, grants, advisors, `ai_log`, `propostas`, `pedidos_cotacao`, `proposta_compliance`).
- Não consegui verificar a visibilidade do repositório GitHub (a API GraphQL está bloqueada nesta sessão) nem aceder ao domínio n8n pelo shell.

Legenda: ✅ passa (verificado por inspeção/SQL) · ❌ falha (gap confirmado) · ⚠️ parcial · ⏳ não executável por mim (precisa de execução real, dados reais, documento ou ação humana). Onde digo "inspeção" significa que o critério foi verificado no código, **não** por execução. Os testes que exigem execução ficam com a resolução e o procedimento exato para quem os correr.

**Resumo:** ❌ 14 · ⚠️ 18 · ✅ 13 · ⏳ 27 (os ⏳ são sobretudo documentais, formação, DPA e dados reais). Os ✅ e ⚠️ baseiam-se em inspeção, não em execução.

Dados de suporte (SQL, 2026-10-21): `ai_log` = 28 linhas (27 `modelo_fixo`, 1 `llm`); `pedidos_cotacao` = 44, todos `enviado`; `proposta_compliance` = 5, todas `automatico`; 0 linhas de `ai_log` com "@" nos resumos; `propostas.token_confirmacao` com default de 2 UUID concatenados (64 hex).

---

## 1. Classificação e âmbito

| ID | Resultado | Evidência | Resolução precisa |
| --- | --- | --- | --- |
| C1 | ⚠️ | Inspeção: prompts só extraem campos de pedidos/cotações e redigem texto de email; sem pontuação de pessoas, biometria nem inferência de emoções. Falta o documento assinado. | Criar `docs/ai-act/checklist-art5.md` com as 8 práticas do Art. 5(1) e "não aplicável" + justificação por prática; assinada e datada pela gestão. |
| C2 | ⏳ | Tecnicamente nenhum uso em emprego, crédito, educação, serviços essenciais ou aplicação da lei. Falta justificação escrita. | Escrever 1 página: "Sistema usado só em operações comerciais B2B de exportação; não consta do Anexo III (pontos 1–8)"; aprovada pela gestão. |
| C3 | ✅ | Inspeção WF1/WF3/WF6: saídas do LLM passam por código de validação ("Validar pedido", "Montar email", "Validar extração"); `preco_final`, `aprovada` e envio ao cliente só são definidos por Code/humano (WF8 "OK"). | Manter. Acrescentar este teste como verificação em cada alteração de workflow (V3). |
| C4 | ⚠️ | 3 workflows com LLM (WF1, WF3, WF6); a documentação refere números diferentes de usos (ver D1). | Atualizar `documentacao-tecnica.md` e `passagem-producao.md` para: 3 workflows, 4 tarefas (extração do pedido, redação do email WF3, escolha de transportadoras WF3, extração de cotações WF6). |
| C5 | ⏳ | Avaliação concluiu: deployer e provavelmente fornecedor do próprio sistema. Sem parecer arquivado. | Pedir parecer ao jurista sobre o papel; arquivar em `docs/ai-act/parecer-papel.pdf`. |
| C6 | ❌ | Não existe procedimento de reavaliação. | Criar `docs/ai-act/gestao-de-mudanca.md`: mudança de modelo (`anthropic/claude-haiku-4.5`), prompt, caso de uso ou categoria de dados exige repetir C1–C3 e registar em `ai_log` a nova versão. |

## 2. Literacia em IA (Art. 4)

| ID | Resultado | Evidência | Resolução precisa |
| --- | --- | --- | --- |
| L1 | ⏳ | Sem registo de formação nos documentos do projeto. | Sessão de 60 min com Bárbara, Madalena e administradores; folha de presença datada guardada em `docs/ai-act/formacao-2026-XX.pdf`. |
| L2 | ⏳ | Sem material. | Montar slides com: o que cada uma das 4 tarefas faz, limites, erros típicos (preço mal lido, país trocado), viés de automação, como corrigir (editar no Supabase) e a quem escalar. |
| L3 | ⏳ | Requer pessoas. | Caso de teste: cotação com preço "1.250" lido como 1,25; a Bárbara e a Madalena têm de o identificar e dizer a quem reportar. |
| L4 | ❌ | Sem procedimento de entrada. | Acrescentar ponto "formação em IA" à checklist de integração de novos colaboradores. |

## 3. Transparência (Art. 50)

| ID | Resultado | Evidência | Resolução precisa |
| --- | --- | --- | --- |
| T1 | ❌ | O Code "Montar email" do WF3 assina "Equipa comercial (mensagem enviada pelo sistema de propostas)". Não há frase explícita a dizer que o texto foi redigido com apoio de IA. | No nó "Montar email" acrescentar sempre, após a assinatura: "Esta mensagem foi redigida com apoio de um sistema de inteligência artificial e enviada pelo nosso sistema de propostas." Validar num envio de teste (`destinatario_teste`). |
| T2 | ❌ | Mesmo ponto: a frase só pode ser garantida se for acrescentada em código e não vier do LLM. | Acrescentar a frase em código **depois** do `limpo()` e fora do texto do LLM (como a assinatura). Teste: forçar saída do LLM vazia; o email deve continuar a ter a frase. |
| T3 | ⏳ | Sem parecer. | Jurista decide sobre Art. 50(1) (interação direta com pessoas) e 50(2) (marcação de conteúdo sintético); arquivar. Provável conclusão: aviso por boa prática, obrigação limitada. |
| T4 | ✅ | Inspeção WF1/WF13: criam rascunho em Outlook ("To Check") e nenhum nó de envio. | Se se quiser alinhar com T1, acrescentar a mesma frase nos rascunhos que contenham texto gerado por IA. |
| T5 | ❌ | WF9 e WF10 sem LLM (ok). **WF12** diz no rodapé "enviada com o apoio de um sistema automático, revista pela nossa equipa", mas é um modelo fixo, sem revisão humana por mensagem: a afirmação é incorreta. WF9 tem rodapé equivalente. | Corrigir o texto do rodapé em WF9 e WF12 para: "Mensagem enviada automaticamente pelo nosso sistema de propostas." (sem "revista" quando não há revisão). Manter sem nós LLM. |
| T6 | ✅ | `ai_log` tem 28 linhas, 27 `modelo_fixo` e 1 `llm`, com workflow, execução, modelo e versão de prompt. | Ver G1 sobre o rácio (indica que o LLM quase nunca é aceite). |

## 4. Supervisão humana (Art. 14)

| ID | Resultado | Evidência | Resolução precisa |
| --- | --- | --- | --- |
| H1 | ⚠️ | Inspeção: WF9 só trata propostas aprovadas. Mas WF8 (aprovação por email) está **inativo**, por isso hoje não há caminho de aprovação por email a funcionar. Não executado. | Ativar WF8 (depois de H3–H6), e correr em teste: WF9 com proposta `em_validacao` deve recusar e avisar no Slack. |
| H2 | ⚠️ | Inspeção: WF9 valida `preco_final`. Não executado. | Executar WF9 manualmente com proposta aprovada e `preco_final` nulo; esperado: recusa e aviso. Se enviar, adicionar IF `preco_final > 0` antes do envio. |
| H3 | ⚠️ | Regex de aprovação `/^(ok|aprovo|aprovado|aprovada)\s*[.!]?$/i` aplicada à primeira linha: "ok mas muda o frete" e "não aprovo OK" **não** passam. Correto por inspeção, não executado. | Correr os 4 emails de teste com WF8 em modo de teste; esperado: só "OK" e "Aprovo" aprovam. |
| H4 | ✅ | `AUTORIZADOS=['REDACTED@example.invalid']`; outros remetentes não aprovam (inspeção). | Confirmar que este é o endereço da Bárbara; se for um endereço de serviço, substituir pelo(s) dela(s) e dos administradores. |
| H5 | ✅ | WF8 só atualiza propostas em `em_validacao` (inspeção). | Executar com uma proposta noutro estado para confirmação. |
| H6 | ❌ | WF8 identifica o remetente pelo campo `from` do Outlook, sem validação de SPF/DKIM/DMARC nem de token. Um From forjado pode aprovar. | Opção A (recomendada): incluir no email de pedido de aprovação um código de 6 dígitos (ou o `token_confirmacao`) e exigir "OK <código>". Opção B: ler `internetMessageHeaders` e exigir `Authentication-Results: dkim=pass` e `dmarc=pass`. Verificar também SPF/DKIM/DMARC do domínio de destino. |
| H7 | ⚠️ | `aprovada_por` e `aprovada_em` existem na tabela e são preenchidos pelo WF8 (inspeção). Sem aprovações reais para validar. | Após o primeiro teste de H3, confirmar a linha em `propostas`. |
| H8 | ✅ | Inspeção WF13/Read Outlook: leads por email ficam `novo` (rascunho) e não criam proposta. | Confirmar com 1 email de teste. |
| H9 | ✅ | Inspeção: WF1 e WF13 só criam rascunhos (sem nó de envio). | Manter. |
| H10 | ⏳ | Requer pessoas. | Mostrar à Bárbara 5 resumos, 1 com cotação trocada; medir se deteta. Mostrar a fonte (excerto do email/PDF) ao lado do valor extraído. |
| H11 | ⏳ | Decisão não documentada: o texto do WF3 sai sem revisão. | Gestão decide e regista: (a) manter envio automático com validação por código e aviso de IA (T1), ou (b) rascunho para aprovação da Bárbara. Dado o risco baixo, (a) com T1/T2 é defensável. |

## 5. Exatidão e robustez (Art. 15)

| ID | Resultado | Evidência | Resolução precisa |
| --- | --- | --- | --- |
| R1 | ⏳ | Requer 20 emails reais. | Montar amostra anonimizada; medir campos corretos; meta ≥ 95% e 0 pedidos inventados. |
| R2 | ⏳ | Requer respostas reais. | Idem com 10 respostas de transportadoras. |
| R3 | ⏳ | Requer PDFs reais. | Idem com 10 PDFs (incluir digitalizados). |
| R4 | ⚠️ | WF6 "Validar extração" verifica se o preço aparece no texto e usa regras `a_rever`. Não executado. | Testar com resposta com dois preços e outra sem moeda. |
| R5 | ✅ | WF3: ambos os nós LLM têm `onError: continueRegularOutput`; WF1 define `falhou_llm`. `ai_log` mostra 27 usos de `modelo_fixo`, o que mostra que a reserva funciona. | Fazer simulação com chave inválida para confirmar o aviso. |
| R6 | ✅ | "Validar pedido" (WF1) valida Incoterms e países; WF3 valida IDs de transportadora. | Teste unitário em Code com JSON inválido. |
| R7 | ✅ | `limpo()` rejeita `/https?:|www[.]|[<>€$]|EUR|USD/i` e exige `intro.includes(d.codigo)`; caso contrário usa texto fixo. | Manter. |
| R8 | ⚠️ | Prompt e código não incluem o nome do cliente final (inspeção). Falta ver emails reais enviados. | Rever os 44 `pedidos_cotacao` enviados (conteúdo) com 5 amostras. |
| R9 | ⚠️ | WF5 associa respostas à proposta por código no assunto. WF5 e WF2 têm versão rascunho diferente da ativa. | Alinhar versão publicada (ver D1) e testar com assunto alterado. |
| R10 | ⏳ | Requer comparação em 5 destinos. | Correr WF3 em modo teste para 5 países e comparar com a regra. |
| R11 | ⏳ | Requer 5 repetições. | Repetir 5× a mesma extração; campos críticos idênticos. A temperatura é 0,3 e 0,2 no WF3: considerar 0 na extração. |
| R12 | ⚠️ | `ai_log` guarda modelo e versão de prompt. Modelo fixo: `anthropic/claude-haiku-4.5`. | Fixar versão datada do modelo, se disponível, e guardar o hash do prompt. |

## 6. Segurança e injeção de prompt

| ID | Resultado | Evidência | Resolução precisa |
| --- | --- | --- | --- |
| S1 | ⚠️ | LLM sem ferramentas nem acesso a envio; saída validada em código. Risco residual baixo. Não executado. | Enviar 3 emails de injeção para o WF1 em teste; esperado: sem ação, só rascunho. |
| S2 | ⚠️ | WF6 valida preço contra o texto e marca `a_rever`. Não executado. | Testar com PDF com texto oculto. |
| S3 | ⏳ | Requer teste. | Testar HTML com texto invisível e Unicode. |
| S4 | ✅ | Prompts por inspeção: só dados necessários; sem preços internos nem segredos. | Manter. |
| S5 | ⚠️ | Script `scripts/check_no_secrets.sh` não executado aqui (repositório não acessível). Credenciais n8n usam o gestor de credenciais. | Executar o script e `git log -p` com pesquisa de padrões; ativar secret scanning. |
| S6 | ❌ | Formulários WF3, WF11 e WF13 sem autenticação (inspeção). | Ativar autenticação básica nos Form Triggers (ou restringir por IP/proxy), ou desativar os triggers não usados. |
| S7 | ⚠️ | Token de 64 hex (2 UUID). Falta ver expiração e uso único no WF10. | Garantir que WF10 marca o token usado/expirado; testar reutilização. |
| S8 | ⚠️ | RLS ativa, sem políticas (nega por defeito), mas os grants a `anon`/`authenticated` mantêm-se por defeito e há uma view `security_invoker`. | `revoke all on all tables in schema public from anon, authenticated;` e testar com a chave anónima (esperado 401/vazio) nas 11 tabelas. |

## 7. Registo, rastreabilidade e retenção

| ID | Resultado | Evidência | Resolução precisa |
| --- | --- | --- | --- |
| G1 | ⚠️ | Existe `ai_log` com 28 linhas. Só 1 `llm` contra 27 `modelo_fixo`: ou o LLM falha, ou o texto é quase sempre rejeitado. | Investigar o motivo (ex.: `intro.includes(codigo)` rejeita texto); ajustar o prompt para incluir o código; registar o motivo da rejeição em `ai_log`. |
| G2 | ✅ | 0 linhas com "@" em `input_resumo`/`output_resumo`. | Manter. |
| G3 | ⏳ | Não percorri uma proposta de ponta a ponta. | Escolher 1 PRP e reconstruir cadeia a partir das tabelas. |
| G4 | ❌ | Sem prazo de retenção escrito para `ai_log`, `leads`, execuções n8n. | Definir: `ai_log` 24 meses, `leads` 12 meses, execuções n8n 30 dias; configurar em n8n e documentar. |
| G5 | ❌ | Não existe `pg_cron`, por isso `purgar_leads_antigos` não corre sozinha. | Instalar `pg_cron` ou criar um workflow n8n agendado que chame `select purgar_leads_antigos()`. Testar com lead de teste com +12 meses. |
| G6 | ⏳ | Backups são administração do Supabase. | Confirmar plano de backups e restaurar num projeto de teste. |
| G7 | ⚠️ | Existem Mail Error Flow e Notificar Slack. Execução 243 de um fluxo de erro terminou com sucesso. Não provoquei falhas por workflow. | Provocar falha em cada workflow ativo e confirmar que chega o email com o nó e o erro. |

## 8. Proteção de dados na cadeia de IA

| ID | Resultado | Evidência | Resolução precisa |
| --- | --- | --- | --- |
| P1 | ⏳ | Definição da conta OpenRouter, fora do meu alcance. | Ativar Zero Data Retention; bloquear modelos `:free`; guardar captura. |
| P2 | ⏳ | Documentos. | Arquivar DPA de n8n, Supabase, OpenRouter, Microsoft, Moloni e termos da Anthropic. |
| P3 | ⏳ | Região não verificada. | Confirmar a região do n8n Cloud e do projeto Supabase; documentar transferências se fora da UE. |
| P4 | ✅ | Texto enviado ao LLM limitado a 6000 caracteres e HTML limpo (inspeção WF1). | Manter. |
| P5 | ⏳ | Requer simulação. | Escolher contacto de teste e apagar em `leads`, `propostas`, `pedidos_cotacao` e nas execuções n8n; documentar o procedimento. |
| P6 | ⏳ | Não consegui consultar a visibilidade do repositório. | `gh api repos/<owner>/<repo> --jq .private` e ativar secret scanning. |
| P7 | ❌ | Há workflows com modo de teste (`destinatario_teste`) e dados de teste em transportadoras. | Antes de produção: limpar `destinatario_teste` em WF3, WF5, WF9, WF10, WF12, WF13 e substituir contactos de teste em `transportadoras`; verificar com uma proposta real. |

## 9. Conteúdo de negócio

| ID | Resultado | Evidência | Resolução precisa |
| --- | --- | --- | --- |
| Q1 | ❌ | Os códigos pautais em `produtos` não estão validados pelo despachante (`validado` sem `validado_por`/`validado_em`). | Seguir `validacao_despachante.md`; ao validar, preencher `validado=true`, `validado_por`, `validado_em`. |
| Q2 | ⚠️ | WF4 tem regra para países não automatizados (`a_verificar_manualmente`). Não executado. | Executar com UK, BR, CN, JP, MA. |
| Q3 | ⚠️ | Produtos como caroço de azeitona/mistura não constam de `produtos`. | Inserir os produtos ou garantir que o WF1 rejeita pedidos sem produto reconhecido. |

## 10. Documentação

| ID | Resultado | Evidência | Resolução precisa |
| --- | --- | --- | --- |
| D1 | ❌ | 7 inconsistências identificadas na avaliação (nº de workflows com IA, WF13 não documentado, regra WF6→WF5, versões rascunho≠ativa de WF2 e WF5, WF6 e WF8 inativos). | Corrigir as 7 em `documentacao-tecnica.md`/`passagem-producao.md`; publicar as versões de WF2 e WF5; ativar WF6 e WF8 ou documentar porque estão inativos. |
| D2 | ❌ | Não existem fichas. | Criar 4 fichas (finalidade, dados, modelo, prompt, validações, supervisão, limitações). |
| D3 | ❌ | Sem política de uso de IA. | Documento de 1 página aprovado pela gestão. |
| D4 | ⏳ | Não simulei desativação nem restauro. | Registar o tempo para desativar todos os workflows e restaurar uma versão anterior (`restore_workflow_version`); meta < 15 min. |

## 11. Revisão periódica

| ID | Resultado | Evidência | Resolução precisa |
| --- | --- | --- | --- |
| V1 | ⏳ | Ainda sem produção. | Mensal nos primeiros 3 meses: 10 linhas de `ai_log` revistas pela Bárbara. |
| V2 | ⏳ | Idem. | Registo trimestral de incidentes. |
| V3 | ⏳ | Idem. | Reavaliação semestral (esta avaliação serve de base). |
| V4 | ⏳ | Idem. | Confirmar prazos e eventuais adiamentos com o jurista. |

---

## Prioridade das correções (antes de produção)

1. **S8** revogar grants `anon`/`authenticated`.
2. **S6** autenticar os formulários.
3. **H6** proteger a aprovação por email (código ou verificação DKIM).
4. **T1/T2/T5** frase de IA em código e corrigir rodapés WF9/WF12.
5. **P7** limpar modo de teste e dados de teste.
6. **Q1** validação do despachante.
7. **G1** perceber porque o texto do LLM é rejeitado quase sempre.
8. **G4/G5** retenção e purga agendada.
9. Ativar WF8 (e WF6, se aplicável) e corrigir D1.
10. Documentos: C1, C2, C5, T3, H11, P1–P3.

---

## Atualização 2026-10-21 (2.ª passagem): testes executados e documentação criada

Executado só em leitura (nada escrito na base de dados; uma tentativa de teste com escrita revertida foi cancelada e não correu). Workflows continuam sem execuções minhas.

| ID | Novo resultado | Evidência |
| --- | --- | --- |
| S8 | ✅ funcional, ⚠️ hardening | Como `anon`, `select count(*)` devolveu 0 em todas as 12 tabelas/vistas (RLS efetiva). Mas `anon` mantém grants SIUD e pode executar `purgar_leads_antigos` e `proximo_codigo_proposta`. Proposta em `docs-ai-act/08-migracao-proposta-0005-hardening.sql` (não aplicada). |
| G5 | ⚠️ | Lógica da função verificada por leitura (`estado <> 'convertido'` e mais antigo que N meses). Não corri a purga (o teste com escrita foi cancelado). Sem `pg_cron`, não é automática. |
| Q1 | ❌ confirmado | Os 3 produtos têm `validado=false`, sem `validado_por`/`validado_em`. |
| Q2 | ✅ dados | GB, BR, CN, JP, MA estão em `requisitos_pais` com `metodo=tabela_manual`. A reação do WF4 não foi executada. |
| Q3 | ❌ | Só existem granulado, pó e aglomerado; faltam caroço de azeitona e mistura. |
| P7 | ❌ confirmado | 8 transportadoras `TESTE - ...` ativas com `@example.invalid`; 2 com emails pessoais de teste; todos os 28 registos de `ai_log` têm `teste=true`. |
| G1/T6 | ⚠️ | `ai_log` regista `modelo=claude-haiku-4.5` mesmo quando o texto foi `modelo_fixo`, o que induz em erro; 27 de 28 são texto fixo. Só 1 está ligado a uma proposta (PRP-2026-0017). |
| G3 | ⚠️ | PRP-2026-0017: 5 pedidos, 2 cotações, 1 compliance, 1 `ai_log`, aprovada por `REDACTED@example.invalid`, enviada; mas `frete_escolhido_id` vazio. Cadeia incompleta no frete. |
| H7 | ✅ | `aprovada_por` e `aprovada_em` preenchidos em PRP-0017 e PRP-0016 (esta com `aprovada_por='teste'`, dado de teste). |
| S7 | ⚠️ | Existem `token_expira_em` e `confirmada_em`; PRP-0016 foi confirmada uma vez. Falta testar reutilização/expiração no WF10. |
| G2 | ✅ | 0 registos com "@" em `ai_log`. |
| R5 | ✅ inspeção | Ambos os nós LLM do WF3 têm `onError: continueRegularOutput`. |

### Documentação criada (pasta `docs-ai-act/`)

| Ficheiro | Cobre |
| --- | --- |
| `01-checklist-art5-e-enquadramento.md` | C1, C2, C3, C5 |
| `02-politica-uso-ia-e-supervisao.md` | D3, H11, T3 |
| `03-fichas-uso-ia.md` | C4, D2, T6, R12 |
| `04-formacao-literacia-ia.md` | L1–L4, H10 |
| `05-gestao-de-mudanca.md` | C6, V3, V4 |
| `06-retencao-rgpd-e-incidentes.md` | G4, G6, P1–P3, P5, V2 |
| `07-runbook-reversao.md` | D4 |
| `08-migracao-proposta-0005-hardening.sql` | S8, G5, Q1 (proposta, não aplicada) |

Estes documentos passam de "não existe" a "existe, em rascunho". Os testes documentais só ficam ✅ depois de preenchidos e assinados (aprovação da gestão, parecer do jurista, DPA, folha de presença, exercício do runbook). Os campos a preencher estão marcados com `____` ou `[ ]`.
