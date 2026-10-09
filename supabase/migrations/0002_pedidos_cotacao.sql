-- Pedidos de cotação de frete enviados às transportadoras (WF3).
-- Aplicada em DEV a 2026-10-07.
create table public.pedidos_cotacao (
  id uuid primary key default gen_random_uuid(),
  proposta_id uuid not null references public.propostas(id) on delete cascade,
  transportadora_id uuid not null references public.transportadoras(id) on delete cascade,
  assunto text not null,
  corpo_html text not null,
  redirecionado_teste boolean not null default false,
  estado text not null default 'a_enviar' check (estado in ('a_enviar','enviado','falhou','respondido')),
  gerado_por text not null default 'llm' check (gerado_por in ('llm','modelo_fixo')),
  modelo text,
  criado_em timestamptz not null default now(),
  enviado_em timestamptz,
  atualizado_em timestamptz not null default now(),
  unique (proposta_id, transportadora_id)
);
create index pedidos_cotacao_proposta_idx on public.pedidos_cotacao (proposta_id);
alter table public.pedidos_cotacao enable row level security;
create trigger pedidos_cotacao_atualizado_em before update on public.pedidos_cotacao
  for each row execute function public.set_atualizado_em();
