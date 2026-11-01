-- Reversão da 0009. Pedidos em estado 'rascunho' passam a 'a_enviar' antes de repor a restrição.
update pedidos_cotacao set estado = 'a_enviar' where estado = 'rascunho';
alter table pedidos_cotacao drop constraint pedidos_cotacao_estado_check;
alter table pedidos_cotacao add constraint pedidos_cotacao_estado_check
  check (estado in ('a_enviar','enviado','falhou','respondido'));
drop trigger if exists configuracao_atualizado_em on configuracao;
drop table if exists configuracao;
