-- Reversão da 0008. Atenção: devolver permissões a anon só se for mesmo necessário (RLS continua a bloquear).
alter table propostas drop column if exists codigo_aprovacao;
alter table produtos drop constraint if exists produtos_validado_auditado;
grant select, insert, update, delete on all tables in schema public to anon, authenticated;
grant execute on all functions in schema public to public;
