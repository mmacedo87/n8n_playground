-- 0009: tabela de configuração e modo de envio do WF3.
-- 1) Tabela `configuracao` (chave/valor) para definições que se mudam sem tocar nos workflows.
-- 2) Primeira definição: `modo_envio` = 'automatico' (envia às transportadoras) ou 'revisao'
--    (o WF3 cria um rascunho no Outlook, na pasta "To Check", para uma pessoa rever e enviar).
-- 3) Novo estado 'rascunho' em pedidos_cotacao (pedido preparado mas ainda não enviado).
-- Reversão: supabase/rollbacks/0009_rollback.sql.

create table configuracao (
  chave          text primary key,
  valor          text not null,
  descricao      text,
  atualizado_em  timestamptz not null default now(),
  atualizado_por text,
  constraint configuracao_modo_envio_valido
    check (chave <> 'modo_envio' or valor in ('automatico','revisao'))
);
alter table configuracao enable row level security;
revoke all on configuracao from anon, authenticated;

create trigger configuracao_atualizado_em before update on configuracao
  for each row execute function set_atualizado_em();

insert into configuracao (chave, valor, descricao, atualizado_por) values
  ('modo_envio', 'automatico',
   'WF3: automatico = envia o pedido de cotação às transportadoras; revisao = cria rascunho no Outlook (pasta To Check) para uma pessoa enviar',
   'migracao 0009');

alter table pedidos_cotacao drop constraint pedidos_cotacao_estado_check;
alter table pedidos_cotacao add constraint pedidos_cotacao_estado_check
  check (estado in ('a_enviar','rascunho','enviado','falhou','respondido'));
