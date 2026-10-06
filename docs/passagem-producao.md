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
