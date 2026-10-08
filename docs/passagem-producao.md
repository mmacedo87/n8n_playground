# Passagem a produção: checklist

Tudo o que falta fazer para sair do ambiente de desenvolvimento/testes. Marcar cada ponto quando concluído.

## 1. Decisões que bloqueiam
- [ ] Decidir n8n Cloud vs VPS na UE. Se Cloud: confirmar a região UE da instância (suporte/DPA) e os limites de execuções do plano.
- [ ] Decidir se produção é uma instância/projeto separado do desenvolvimento (recomendado) e como se promove: exportar do Git (`main`) ou Source Control nativo do n8n.
- [ ] Definir responsáveis: quem aprova propostas, quem recebe erros, quem administra n8n, Supabase e Microsoft 365.

## 2. n8n
- [ ] Criar a instância/projeto de produção com 2FA e utilizadores nominais, sem contas partilhadas.
- [ ] Importar os workflows a partir de `main` e ligar credenciais de produção pelo nome.
- [ ] Preencher marcadores: destinatários, IDs das pastas Outlook, Mail Error Flow como Error Workflow de **todos** os workflows, ID do WF2 no nó de chamada.
- [ ] Fixar o caminho (`path`) do formulário e decidir o URL final (domínio próprio, se possível).
- [ ] Proteger o formulário: autenticação (Basic Auth) ou ligação só a partir de um sítio controlado; avaliar captcha e limite de pedidos.
- [ ] Definir retenção de execuções: guardar execuções falhadas, não guardar dados de execuções bem-sucedidas com dados pessoais, ou prune curto.
- [ ] Ativar notificações de erro para mais do que um destinatário (equipa) e testar com uma falha real em produção.
- [ ] Publicar os workflows e confirmar que os triggers estão ativos.
- [ ] Ativar o nó de chamada ao WF2 no workflow principal apenas quando houver extração de dados (WF1) a preencher os campos.

## 3. Supabase
- [ ] Criar projeto de produção em região UE (ou migrar o atual) com plano que inclua backups diários e, idealmente, point-in-time recovery.
- [ ] Aplicar `supabase/schema.sql` e todas as migrações por ordem.
- [ ] Remover dados de teste (proposta PRP-2026-0001, transportadoras TESTE) e reiniciar o contador `contadores_proposta` do ano.
- [ ] Manter RLS ativa; chave `service_role` só no n8n; nunca em clientes, Git ou documentos.
- [ ] Restringir acesso à base de dados (rede/IPs, se aplicável) e ativar alertas de uso.
- [ ] Inserir transportadoras reais e requisitos por país com fonte e data de verificação.
- [ ] Agendar a purga RGPD (`purgar_leads_antigos`) e definir o prazo de retenção definitivo.
- [ ] Testar um restauro de backup antes de entrar em produção.

## 4. Microsoft 365 / Outlook
- [ ] Usar a caixa real (ou caixa partilhada dedicada) e registar a app no Microsoft Entra com permissões mínimas (ler, escrever e enviar email).
- [ ] Confirmar se o tenant exige consentimento de administrador e obtê-lo.
- [ ] Criar as pastas reais (entrada, To Check, etc.) e atualizar os IDs nos workflows.
- [ ] Substituir o destinatário fixo da confirmação pelo email do pedido (ou da equipa) e rever o texto do email.
- [ ] Verificar SPF/DKIM/DMARC do domínio de envio e limites de envio do Microsoft 365.
- [ ] Planear a renovação/expiração das credenciais OAuth e quem a monitoriza.

## 5. OpenRouter / IA
- [ ] Criar chave de produção separada, com limite de gasto mensal e alertas.
- [ ] Ativar exclusão de fornecedores que guardam ou treinam com dados (zero retenção); proibir modelos `:free`.
- [ ] Fixar o modelo e a versão do prompt por workflow e registar tudo em `ai_log`.
- [ ] Garantir que nenhuma decisão de preço ou envio ao cliente é tomada pelo modelo: valores calculados em código, envio só após aprovação humana.

## 6. Moloni
- [ ] Confirmar que o plano inclui API e criar credenciais de produção.
- [ ] Testar a criação de orçamento em rascunho antes de qualquer envio.

## 7. RGPD e AI Act
- [ ] Assinar/arquivar acordos de tratamento de dados (DPA) com n8n, Supabase, OpenRouter, Microsoft e Moloni; confirmar transferências fora da UE.
- [ ] Atualizar o registo de atividades de tratamento e a informação dada aos titulares.
- [ ] Documentar a classificação de risco do sistema de IA, o papel da supervisão humana e a transparência perante o cliente.
- [ ] Definir pedidos de acesso/apagamento: como localizar e apagar dados de uma pessoa em `leads`, `propostas` e execuções do n8n.

## 8. Dados e conteúdo
- [ ] Obter da Bárbara as listas definitivas (produtos, densidades, granulometrias, embalagens, países) e atualizar o formulário e as validações.
- [ ] Rever o código pautal e as taxas por país com o despachante.
- [ ] Rever os textos dos emails e do formulário.

## 9. Testes e arranque
- [ ] Fechar os testes pendentes F1 a F6 da bateria com execução real.
- [ ] Correr a bateria completa na instância de produção (sem dados reais) e guardar o resultado.
- [ ] Fazer um teste ponta a ponta com dados fictícios e depois com um pedido real acompanhado.
- [ ] Preparar plano de reversão: desativar workflows, restaurar versão anterior do Git, restaurar backup.
- [ ] Escrever o runbook: como correr, o que fazer quando há erro, quem contactar.

## 10. GitHub
- [ ] Passar o repositório a privado e ativar secret scanning e push protection.
- [ ] Proteger `main` (Pull Request obrigatório, sem force-push) e etiquetar a versão de arranque (`v1.0.0`).
- [ ] Confirmar que nada sensível está no histórico (`scripts/check_no_secrets.sh`).

## 11. Entregabilidade do email (evitar spam)
- [ ] Enviar a partir de uma caixa do domínio da empresa (por exemplo propostas@empresa.pt ou caixa partilhada), não de uma conta @outlook.com. Nos testes, os emails da conta pessoal foram para o spam do Gmail.
- [ ] Configurar SPF, DKIM e DMARC do domínio no Microsoft 365 e verificar com uma ferramenta de teste (por exemplo mail-tester).
- [ ] Manter os destinatários das confirmações dentro da organização; para clientes externos, subir o DMARC para quarentena/rejeitar e aumentar o volume gradualmente.
- [ ] Rever assunto, texto e assinatura do email com a equipa comercial.

## 12. WF3 (pedido de cotações) e encadeamento com o WF2
- [ ] No nó "Configuração" do WF3, **esvaziar `destinatario_teste`** e preencher `destinatario_principal` (o endereço da empresa, que fica em Para). Enquanto `destinatario_teste` estiver preenchido, nenhum email chega às transportadoras. Em produção é enviado um único email, com as transportadoras todas em BCC (não veem os endereços umas das outras).
- [ ] Carregar as transportadoras reais em `transportadoras` (email, modos, países em `rotas`) e apagar as `TESTE - Transportadora ...`. Para cada destino convém haver 4 a 5 transportadoras ativas; com menos, o WF3 envia a todas e assinala `abaixo_do_minimo_4`; sem nenhuma para o destino, falha e avisa.
- [ ] Comprar créditos na OpenRouter e ativar zero data retention; sem créditos o WF3 usa a regra de reserva e o texto fixo (funciona, mas sem o LLM).
- [ ] O WF2 arranca o WF3 no fim (nó "Pedir cotações de frete (WF3)"): confirmar o ID do WF3 nesse nó na instância de destino.
- [ ] Definir o Error Workflow do WF2 como o "WF2 Error Flow" e o do WF3 como o "Mail Error Flow"; preencher o destinatário em "Preparar aviso do WF2".
- [ ] O formulário "Pedir cotações de frete" do WF3 não tem autenticação: proteger ou desativar o trigger manual em produção.
- [ ] Reenvio após falha: o WF3 repete o envio até 5 tentativas (coluna `pedidos_cotacao.tentativas`, migração 0004) e à 6.ª não envia e avisa por email (via Mail Error Flow). Confirmar que o Mail Error Flow está definido como Error Workflow do WF3.
- [ ] Apagar os dados de teste com um só comando: `supabase/limpar_dados_de_teste.sql` (propostas PRP-2026-0001 a 0015, pedidos_cotacao, ai_log) antes de começar.

## 13. WF4 (enriquecimento) e compliance
- [ ] Validar com o despachante o código pautal de cada produto em `produtos` (hoje `validado=false`) e marcar `validado`, `validado_por` e `validado_em`.
- [ ] Rever as regras de `requisitos_pais`: confirmar a taxa e os requisitos fitossanitários do Reino Unido, Brasil, China, Japão e Marrocos (hoje `a_verificar_manualmente`) e os requisitos do USDA APHIS para os EUA.
- [ ] EUA: o USITC devolve a taxa base (coluna geral); confirmar com o transitário os direitos adicionais em vigor para a origem antes de enviar propostas.
- [ ] Decidir se o Reino Unido passa a consulta automática (UK Trade Tariff) depois de verificar a resposta da API.
- [ ] Confirmar o ID do WF4 no nó "Enriquecer proposta (WF4)" do WF2 na instância de destino e o Mail Error Flow como Error Workflow do WF4.
- [ ] Garantir que a Bárbara vê `proposta_compliance` (linhas `a_verificar_manualmente`) antes de validar a proposta (passo 6).
- [ ] Apagar os dados de teste de `proposta_compliance` antes de começar. (O índice duplicado `requisitos_pais_pais_nc_uq` já foi removido pela migração 0004; aplicar a 0004 também em produção.)

## 14. Slack (avisos de propostas e cotações)
- [ ] Criar (ou reutilizar) os canais de produção e **convidar a app do Slack** (`/invite @status_notifications`) para cada um; sem isso o aviso falha com `channel_not_found`.
- [ ] Substituir os IDs dos canais no código do nó "Escolher canal e texto" do workflow "Notificar Slack" (`propostas`, `cotacoes`, `estado`).
- [ ] Confirmar o ID do "Notificar Slack" nos nós "Avisar Slack: nova proposta" (WF2) e "Avisar Slack: cotação enviada" (WF3) na instância de destino.
- [ ] Credencial "Slack API" criada na instância de destino com permissão `chat:write`; o Mail Error Flow é o Error Workflow do "Notificar Slack".
- [ ] As mensagens só levam o essencial (código, cliente, produto, quantidade, destino); não incluir preços, moradas nem dados pessoais de contactos.
- [ ] O workflow próprio do utilizador "Claude → Slack | Estado das tarefas" é independente e fica fora do repositório.

## 15. WF5, WF6, WF8 (validação e leitura de cotações)
- [ ] Definir o email da Bárbara no WF5 (destinatário do resumo) e a lista `AUTORIZADOS` no código do WF8 (hoje só o email de teste). O WF8 só aprova com "OK"/"aprovo" na primeira linha, de um remetente autorizado, numa proposta em `em_validacao`.
- [ ] Confirmar a regra de arranque do WF5 no WF6 (`MAX_EXIGIDAS=3`: com 3 cotações, ou todas as pedidas se forem menos).
- [ ] Publicar o WF8 (poll de 2 minutos ao Outlook) só quando houver uma proposta real em `em_validacao`; ativar o WF6 com o trigger de produção.
- [ ] Testes reais por fazer: M5 (resposta real da Bárbara), uma resposta real de transportadora para o WF6 (texto e PDF).
- [ ] Confirmar os IDs do WF5 (no WF6) e do Mail Error Flow como Error Workflow do WF5, WF6 e WF8 na instância de destino.

## 16. WF1 e Read Outlook Messages (pedidos por email)
- [ ] Aplicar a migração `0005_leads_rascunho_pedido.sql` (colunas `assunto`, `dados_extraidos`, `confianca`, `campos_em_falta` em `leads`).
- [ ] Credencial OpenRouter com créditos na conta da chave usada (o erro 402 fez o WF1 falhar em segurança: `falhou_llm=true`, sem dados inventados).
- [ ] Teste real X6: um email na Folder 1 gera lead rascunho, draft em To Check, original lido e aviso Slack.
- [ ] Os leads são rascunhos para um humano rever; ninguém cria a proposta sozinho. O nó de chamada ao WF2 fica desativado até haver decisão.
- [ ] RGPD: o `ai_log` só leva o domínio do remetente; o texto do email vai ao LLM (confirmar zero retenção no OpenRouter) e `leads` entra na purga (`purgar_leads_antigos`).
