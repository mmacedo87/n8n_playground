-- WF1: rascunho do pedido extraído do email (a rever por um humano antes de criar a proposta)
alter table leads
  add column if not exists assunto text,
  add column if not exists dados_extraidos jsonb,
  add column if not exists confianca numeric(3,2) check (confianca is null or confianca between 0 and 1),
  add column if not exists campos_em_falta text[] not null default '{}';

comment on column leads.dados_extraidos is 'Campos do pedido extraidos do email pelo LLM e validados em codigo; rascunho a rever, nunca cria proposta sozinho';
comment on column leads.campos_em_falta is 'Campos obrigatorios do pedido de proposta que o email nao trazia';
