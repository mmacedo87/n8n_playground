# Avaliação AI Act: Automação de propostas comerciais (Sports Unified Europe / Soteria)

Data: 2026-10-21 · Âmbito: todos os workflows, dados, integrações e documentos do projeto (briefing, documentação técnica, estado do projeto, passagem a produção, resumo ao cliente, Moloni, validação do despachante, pedidos ao cliente).
Referência: Regulamento (UE) 2024/1689 (AI Act). Esta avaliação é técnica e de apoio; **não é aconselhamento jurídico**. Confirmar as conclusões com um jurista, incluindo o estado atual de eventuais adiamentos de prazos (pacote "Digital Omnibus").

## 1. Conclusão geral

| Pergunta | Conclusão | Justificação |
| --- | --- | --- |
| Práticas proibidas (Art. 5)? | **Não** | Sem manipulação, pontuação social, biometria ou exploração de vulnerabilidades. |
| Sistema de risco elevado (Art. 6 + Anexo III)? | **Não** (probabilidade baixa) | Casos de uso B2B comerciais/logísticos; não toca em emprego, crédito, serviços essenciais, educação, biometria, aplicação da lei. A IA não decide preços, nem aprova, nem envia propostas. |
| Classificação | **Risco limitado / mínimo**, com obrigações de transparência (Art. 50) a ponderar | Texto gerado por IA e enviado automaticamente (WF3) e extração de dados de emails externos. |
| Papel da empresa | **Deployer** (Art. 3(4)) e, provavelmente, **fornecedor** de um sistema de IA próprio (Art. 3(3)) | O sistema foi desenvolvido e é posto em serviço sob responsabilidade da empresa, com modelos de terceiros (Claude Haiku 4.5 via OpenRouter). O fornecedor do modelo é Anthropic (GPAI, Cap. V). |
| Obrigação já aplicável com lacuna | **Literacia em IA (Art. 4)** | Não há registo de formação da Bárbara, Madalena e administradores. |
| Nível de maturidade | **Bom desenho, documentação e passagem a produção por fechar** | Supervisão humana, validação em código, registo de IA e fallback já existem. Faltam classificação formal, transparência, formação e vários itens de RGPD/segurança. |

## 2. Inventário e avaliação por componente

Legenda de risco residual: 🟢 baixo · 🟡 médio · 🔴 alto (a tratar antes de produção).

| Componente | Usa IA? | Função da IA | Controlos existentes | Enquadramento AI Act | Lacunas / observações | Risco | Ação recomendada |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Read Outlook Messages** | Indireto (chama WF1) | Lê emails da Folder 1, limpa HTML, limita a 6000 caracteres | Cria só rascunhos; não envia; marca como lido; manual/inativo | Risco mínimo; Art. 4 | O texto integral do email externo (dados pessoais de contactos) segue para o LLM. Teste real X6 por fazer | 🟡 | Teste X6; confirmar zero retenção no OpenRouter; DPA |
| **WF1: Extrair pedido do email** | **Sim** (extração) | Extrai campos do pedido; devolve `e_pedido` e `confianca` | Código valida cada campo (Incoterm, país ISO, listas); `falhou_llm` em vez de inventar; lead sempre rascunho; nunca cria proposta; `ai_log` só com domínio do remetente | Risco mínimo / limitado. Art. 4, 14 (boa prática), 15 (boa prática) | **Injeção de prompt** via email externo: sem teste documentado de resistência. Sem métrica de exatidão em volume. Teste real do LLM passou (X7, 1 pedido + 1 newsletter) | 🟡 | Testes adversariais (emails com instruções ocultas); amostra de exatidão; manter rascunho obrigatório |
| **WF2: Pedido de proposta** | Não | Validação e gravação em código; email de confirmação por modelo | Validação, número PRP, Error Flow próprio | Fora do âmbito de IA | Dispara o WF3 automaticamente | 🟢 | Nenhuma específica |
| **WF3: Pedido de cotação de frete** | **Sim** (escolha de transportadoras e redação de introdução/fecho) | Escolhe 4-5 transportadoras entre as ativas; redige texto do email | Escolha validada contra lista existente e regra de reserva; texto recusado se tiver links, preços ou HTML (usa texto fixo); nome do cliente final nunca incluído; BCC; reenvio limitado; modo de teste | **Art. 50(1)/(2)** a ponderar: texto de IA enviado **sem revisão humana** a pessoas (contactos das transportadoras) | O email **sai automaticamente** logo após o WF2, antes de qualquer validação humana. Não há indicação de que o texto foi gerado por IA. Formulário manual sem autenticação (pendente) | 🟡 | Acrescentar frase fixa de transparência ("texto parcialmente gerado com apoio de IA"); decidir se a introdução gerada por IA fica sujeita a revisão; proteger o formulário (Basic Auth) |
| **WF4: Enriquecimento (compliance)** | Não | Código pautal, taxa e fitossanitário por regras e consultas (USITC) | Sem LLM; `validado=false` até o despachante validar | Fora do âmbito de IA; relevante para qualidade de dados | Códigos pautais **não validados**; países fora de UE/EUA "a verificar manualmente"; direitos adicionais EUA por confirmar | 🟡 | Validação pelo despachante antes de produção; Bárbara vê `a_verificar_manualmente` antes de aprovar |
| **WF6: Ler cotações** | **Sim** (extração de PDF/texto livre) | Extrai preço, modo, prazo, validade, condições | Código valida tipos e valores; marca `a_rever` com dúvidas; não grava se não consegue associar com segurança; remetentes por email/domínio autorizados | Risco mínimo/limitado; Art. 4, 15 (boa prática) | **Erro de extração de preço é o risco mais relevante** (afeta o preço final). **Injeção de prompt** em PDFs de terceiros. Sem teste com resposta real de transportadora. Workflow inativo/manual | 🔴 | Teste real com respostas verdadeiras (texto e PDF); conferência humana de preço/prazo na etapa WF5 (mostrar excerto da fonte); testes adversariais |
| **WF5: Resumo para validação** | Não (resumo montado em código) | Reúne dados, cotações e compliance; marca `em_validacao` | Ponto de revisão humana; cotações `a_rever` em destaque | Supervisão humana (boa prática Art. 14) | **Risco de viés de automação**: a Bárbara pode confiar nos valores extraídos sem verificar a fonte. Email da Bárbara por definir | 🟡 | Incluir excerto/link do email ou PDF original; formação (Art. 4) |
| **WF8: Aprovação da Bárbara** | Não | Lê resposta; só "OK" na 1.ª linha de remetente autorizado | Lista `AUTORIZADOS`; só em `em_validacao`; regista quem aprovou e quando; outro texto só gera aviso | Supervisão humana efetiva | A autenticidade do remetente depende do email (**risco de falsificação** se SPF/DKIM/DMARC não estiverem corretos). Teste real M5 por fazer; por publicar | 🟡 | Verificar autenticação do remetente (cabeçalhos) ou confirmar por link com token; SPF/DKIM/DMARC; teste real |
| **WF9: Envio da proposta ao cliente** | Não (segundo a documentação) | Email PT/EN com Bárbara em CC; link de confirmação | Só após aprovação; recusa sem `preco_final` | Fora do âmbito de IA (a confirmar que o texto é modelo fixo) | Depende do Moloni; confirmar que nenhum campo é gerado por LLM | 🟢 | Confirmar ausência de LLM; revisão dos textos |
| **WF10: Confirmação da encomenda** | Não | Link, página de resumo, botão em 2 passos, token de 30 dias | Token com validade; não confirma duas vezes | Fora do âmbito de IA | Segurança do token/URL (não é matéria de IA) | 🟢 | Nenhuma específica |
| **WF11: Plano de expedição** | Não | Formulário; grava em `expedicoes` | RLS | Fora do âmbito de IA | Formulário sem autenticação a confirmar | 🟢 | Proteger formulário |
| **WF12: Follow-up ao cliente** | Não | Proposta final com modo e chegada estimada | Sub-workflow; modo de teste | Fora do âmbito de IA | Sem observações | 🟢 | Nenhuma |
| **WF13: Confirmação de reserva de frete** | Não | Cria só rascunho no Outlook; liberta reservas em standby | Nunca envia; pessoa revê | Fora do âmbito de IA | Não consta da documentação técnica (só no resumo e na checklist 13b) | 🟢 | Atualizar a documentação técnica |
| **Notificar Slack / Error Flows** | Não | Avisos | Só o essencial nas mensagens | Fora do âmbito de IA | Nenhuma | 🟢 | Nenhuma |
| **Moloni (fase 5)** | Não | Geração de orçamento via API | Preço final calculado em código | Fora do âmbito de IA | Bloqueado (credenciais e refresh token de 14 dias) | 🟢 | Manter regra: preço nunca decidido por LLM |
| **Supabase / `ai_log`** | Suporte | Registo de uso de IA (workflow, execução, modelo, versão do prompt, resumo) | RLS em 11 tabelas; purga de `leads` aos 12 meses | Registo e rastreabilidade (boa prática Art. 12) | Free sem backups; `ai_log` guarda resumo de entrada/saída: definir retenção; execuções bem-sucedidas não guardadas (bom para RGPD, mas limita auditoria) | 🟡 | Supabase Pro; definir retenção do `ai_log`; testar restauro |
| **OpenRouter / Claude Haiku 4.5** | **Sim** | Modelo GPAI de terceiros | Modelo fixado; `:free` proibido; limite de gasto previsto | Cap. V (obrigações do fornecedor do modelo); deployer deve usar conforme instruções | Zero retenção **por ativar**; DPA por assinar; intermediário adicional na cadeia de dados | 🔴 | Ativar zero retenção, assinar DPA (OpenRouter e Anthropic), confirmar transferências fora da UE |
| **n8n Cloud** | Suporte | Orquestração | 2FA a configurar; sem segredos nos workflows | n/a | Região UE por confirmar; DPA por assinar; ambiente de teste e produção | 🟡 | Confirmar região UE e DPA; instância de produção separada |
| **GitHub** | Suporte | Versionamento | Exportação sanitizada; verificação de segredos | n/a | **Repositório público**; passar a privado antes de dados reais | 🟡 | Privado, secret scanning, proteção de `main` |
| **Documentação** | n/a | n/a | Documentação técnica, estado, checklist de produção | Art. 11 (boa prática); Art. 4 | Falta classificação formal, registo de risco e política de uso de IA. Inconsistências entre documentos (secção 5) | 🟡 | Adotar esta avaliação como base e manter atualizada |

## 3. Requisitos do AI Act por artigo

| Artigo | Requisito | Aplica-se? | Estado atual | Gap | Prioridade |
| --- | --- | --- | --- | --- | --- |
| Art. 4 | Literacia em IA do pessoal | **Sim** (deployer e fornecedor; em vigor desde 02/02/2025) | Princípios de desenho documentados; sem formação registada | Formação curta e registo para Bárbara, Madalena e quem administra o sistema | Alta |
| Art. 5 | Práticas proibidas | Verificado: não aplicável | n/a | n/a | n/a |
| Art. 6 / Anexo III | Classificação de risco elevado | Não aplicável (análise acima) | Classificação não documentada formalmente (checklist 7) | Guardar a justificação (este documento) | Média |
| Arts. 8-15 | Requisitos de risco elevado (gestão de risco, dados, documentação, registo, supervisão, exatidão, cibersegurança) | Não obrigatórios | Boa parte cumprida por desenho (validação em código, registo, supervisão humana) | Usar como boa prática; ver testes de robustez | Baixa |
| Art. 14 (boa prática) | Supervisão humana | Não obrigatório, mas bem implementado | Aprovação obrigatória antes do cliente; rascunhos; `a_rever` | Mitigar viés de automação; WF3 sai sem revisão | Média |
| Art. 26 | Obrigações do deployer de alto risco | Não aplicável | n/a | n/a | n/a |
| **Art. 50(1)** | Informar pessoas que interagem diretamente com um sistema de IA | **A ponderar** | Emails de WF3 com texto gerado por IA, sem aviso | Acrescentar aviso fixo ou documentar porque a interação é considerada óbvia/não direta | Média |
| **Art. 50(2)** | Marcar conteúdo sintético (texto) em formato legível por máquina | Recai sobretudo no **fornecedor do modelo**; se a empresa é fornecedora do sistema, avaliar | Não documentado | Confirmar com o jurista o papel e a eventual obrigação; registo em `ai_log` ajuda | Média |
| Art. 50(4) | Divulgar texto gerado por IA publicado para informar o público | Não aplicável (comunicações privadas B2B) | n/a | n/a | n/a |
| Cap. V (Arts. 51-55) | Modelos GPAI | Obrigações do fornecedor do modelo (Anthropic) | Modelo e versão fixados e registados | Guardar documentação do fornecedor e os termos de uso | Baixa |
| Art. 99 | Sanções | Relevante para Art. 4 e 50 | n/a | Reduzir risco com os itens acima | Baixa |

## 4. Riscos transversais e plano de ação

| # | Risco / lacuna | Componentes | Impacto | Ação | Responsável sugerido | Prioridade |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Erro de extração de preço/prazo de cotações | WF6, WF5 | Proposta com preço errado | Teste real com respostas verdadeiras; mostrar a fonte na revisão; manter `a_rever` | Técnico + Bárbara | 🔴 Alta |
| 2 | Zero retenção e DPA por concluir com fornecedores de IA | OpenRouter, Anthropic, n8n, Supabase | RGPD: dados pessoais de contactos enviados ao LLM | Ativar zero retenção; assinar DPA; confirmar região UE | Gestão + técnico | 🔴 Alta |
| 3 | Injeção de prompt em emails e PDFs de terceiros | WF1, WF6 | Dados falsos nos rascunhos ou cotações | Testes adversariais; manter o LLM sem ações (só extrai); validação em código | Técnico | 🟡 Média |
| 4 | Aprovação por email dependente da autenticidade do remetente | WF8 | Aprovação indevida | SPF/DKIM/DMARC; verificar cabeçalhos ou usar link com token | Técnico | 🟡 Média |
| 5 | Texto de IA enviado sem revisão e sem aviso | WF3 | Transparência (Art. 50) | Frase fixa de transparência; decidir revisão humana da introdução | Gestão + técnico | 🟡 Média |
| 6 | Sem formação documentada (Art. 4) | Equipa | Incumprimento de obrigação em vigor | Sessão curta + registo (o que a IA faz, limites, viés de automação, como corrigir) | Gestão | 🟡 Média |
| 7 | Viés de automação na validação | WF5, WF8 | Aprovações sem verificar | Checklist de validação; mostrar fonte original | Bárbara | 🟡 Média |
| 8 | Classificação de risco e política de IA não formalizadas | Documentação | Falta de evidência | Aprovar este documento como registo; rever a cada alteração relevante (novo uso de IA, novo modelo, novos dados) | Gestão | 🟡 Média |
| 9 | Retenção do `ai_log`, backups e restauro | Supabase | Auditoria e RGPD | Definir prazo; Supabase Pro; testar restauro | Técnico | 🟡 Média |
| 10 | Formulários sem autenticação; repositório público | WF3, WF11, WF13, GitHub | Acesso indevido | Basic Auth ou desativar; repositório privado | Técnico | 🟡 Média |
| 11 | Códigos pautais e regras por país não validados | WF4 | Informação de compliance incorreta na proposta | Validação do despachante | Despachante | 🟡 Média |
| 12 | Documentação desatualizada ou inconsistente | Documentos | Perda de rastreabilidade | Corrigir pontos da secção 5 | Técnico | 🟢 Baixa |

## 5. Inconsistências encontradas na documentação

| Documento | Observação | Correção sugerida |
| --- | --- | --- |
| `documentacao-tecnica.md` vs `resumo-cliente.html` | A documentação diz que o LLM do WF3 "só redige introdução e fecho"; o resumo diz que a IA também **escolhe as transportadoras** (4 tarefas de IA). | Alinhar: 3 workflows usam LLM (WF1, WF3, WF6) e 4 tarefas (extrair pedido, escolher transportadoras, redigir email, extrair cotações). |
| `documentacao-tecnica.md` | Não lista o WF13 nem a migração 0007; só constam no resumo e na checklist 13b. | Acrescentar WF13 e 0007 à tabela de workflows. |
| `resumo-cliente.html` (secção AI Act) | "A equipa comercial revê o pedido antes de qualquer proposta seguir para o cliente" é exato para clientes, mas o WF3 envia emails às transportadoras **antes** de qualquer revisão. | Esclarecer que a supervisão humana cobre propostas ao cliente, não os pedidos de cotação às transportadoras. |
| `resumo-cliente.html` | A afirmação "100% rastreável" e o `ai_log` guardam só resumo; execuções bem-sucedidas não são guardadas. | Reformular para "rastreável por registo em base de dados" ou ajustar a retenção. |
| `passagem-producao.md` e `estado_do_projeto.md` | Regra WF6→WF5: a checklist diz "sem mínimo" (decidido a 16/10), o estado de projeto e o `pedidos-ao-cliente` ainda dizem "3 cotações". | Atualizar os documentos para a regra em vigor. |
| `pedidos-ao-cliente.html` e `estado_do_projeto.md` | Datados de 09/10 (versão 0.4 do pedido); entretanto há WF13 e cotações reais. | Atualizar. |
| Briefing | Prevê 2 pedidos/mês; o resumo e custos assumem 30-35 encomendas/mês. | Registar o volume esperado na avaliação de risco (impacto em execuções e supervisão humana). |

## 6. Pontos que a empresa deve decidir ou confirmar

| Ponto | Pergunta |
| --- | --- |
| Papel | A empresa será considerada fornecedora do sistema ou apenas utilizadora? Confirmar com o jurista (impacta o Art. 50). |
| Transparência | Aceita incluir uma frase de transparência nos emails às transportadoras e nos rascunhos? |
| Revisão do WF3 | A introdução gerada por IA pode sair sem revisão, ou deve passar por aprovação? |
| Formação | Quem dá a formação (Art. 4) e como fica registada? |
| Revisão da avaliação | Rever sempre que: mudar o modelo ou o prompt, entrar um novo uso de IA, passar a produção, ou mudar o tipo de dados tratados. |

## 7. Fontes consideradas

- Briefing de automação, documentação técnica, estado do projeto, checklist de passagem a produção, resumo ao cliente, pedidos ao cliente, validação do despachante e nota da API Moloni (documentos do projeto).
- Regulamento (UE) 2024/1689: Arts. 3, 4, 5, 6, 14, 26, 50, 99 e Cap. V (conhecimento do utilizador; não foi feita pesquisa online nesta avaliação).
- **Não foram inspecionados** os workflows no n8n, o schema do Supabase nem o conteúdo dos prompts: as constatações baseiam-se na documentação. Recomenda-se uma verificação direta antes de produção.
