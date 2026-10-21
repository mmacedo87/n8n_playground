-- 0008: reforço de segurança e rastreio (AI Act / avaliação 2026-10-21).
-- 1) Retira as permissões de anon e authenticated (o n8n usa service_role/ligação própria). A RLS continua ativa.
-- 2) Funções deixam de ser executáveis por PUBLIC/anon/authenticated.
-- 3) Validação do despachante passa a exigir quem validou e quando (restrição NOT VALID: não falha por linhas antigas).
-- 4) Código de aprovação por proposta (6 caracteres), exigido na resposta "OK <código>" do WF8.
-- Reversão: supabase/rollbacks/0008_rollback.sql.

revoke all on all tables    in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke execute on all functions in schema public from public, anon, authenticated;
grant  execute on all functions in schema public to service_role;
alter default privileges in schema public revoke all on tables    from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;
alter default privileges in schema public revoke execute on functions from public, anon, authenticated;

alter table produtos
  add constraint produtos_validado_auditado
  check (validado = false or (validado_por is not null and validado_em is not null)) not valid;

alter table propostas
  add column codigo_aprovacao text not null
  default upper(substr(md5(gen_random_uuid()::text), 1, 6));
