-- 0007: pedidos e respostas de cotação reais (prints do cliente, 2026-10-17).
-- Só acrescenta colunas e muda uma restrição única; todas as colunas novas aceitam nulo
-- ou têm valor por omissão, por isso as linhas existentes ficam válidas. Reversão: supabase/rollbacks/0007_rollback.sql.

-- Dados de carga e moradas (WF2 grava, WF3 usa no pedido à transportadora).
alter table propostas
  add column tipo_carga       text check (tipo_carga is null or tipo_carga in ('completa','grupagem')),
  add column n_camioes        smallint check (n_camioes is null or n_camioes > 0),
  add column n_paletes        int check (n_paletes is null or n_paletes > 0),
  add column peso_palete_kg   numeric(8,2) check (peso_palete_kg is null or peso_palete_kg > 0),
  add column palete_c_m       numeric(4,2) check (palete_c_m is null or palete_c_m > 0),
  add column palete_l_m       numeric(4,2) check (palete_l_m is null or palete_l_m > 0),
  add column palete_a_m       numeric(4,2) check (palete_a_m is null or palete_a_m > 0),
  add column morada_carga     text,
  add column morada_descarga  text,
  add column cp_descarga      text;

-- Versões do pedido de cotação (atualizações) e dados para associar as respostas.
alter table pedidos_cotacao
  add column versao            smallint not null default 1 check (versao >= 1),
  add column substitui_id      uuid references pedidos_cotacao (id) on delete set null,
  add column conversation_id   text,     -- conversa do Outlook, para associar respostas com outro assunto
  add column ref_transportadora text;    -- referência que a transportadora usa (ex. Q-123456)

-- Passa a haver um pedido por proposta, transportadora e versão (antes: um por proposta e transportadora).
do $m$
declare c text;
begin
  -- o nome da restrição antiga difere entre a instância de desenvolvimento (pedidos_cotacao_unico) e uma instalação nova a partir de schema.sql
  for c in select conname from pg_constraint
           where conrelid = 'public.pedidos_cotacao'::regclass and contype = 'u' and array_length(conkey, 1) = 2 loop
    execute format('alter table public.pedidos_cotacao drop constraint %I', c);
  end loop;
end $m$;
alter table pedidos_cotacao add constraint pedidos_cotacao_proposta_transp_versao_key
  unique (proposta_id, transportadora_id, versao);
create index pedidos_cotacao_conversation_idx on pedidos_cotacao (conversation_id) where conversation_id is not null;

-- Condições de cada cotação e estado da reserva.
alter table cotacoes_frete
  add column pedido_cotacao_id   uuid references pedidos_cotacao (id) on delete set null,
  add column ref_transportadora  text,
  add column tipo_entrega        text check (tipo_entrega is null or tipo_entrega in ('fixa','janela','sem_data','nao_claro')),
  add column data_entrega_pedida date,
  add column preco_por           text check (preco_por is null or preco_por in ('camiao','total','palete','nao_claro')),
  add column n_camioes_incluidos smallint check (n_camioes_incluidos is null or n_camioes_incluidos > 0),
  add column conversation_id     text,
  add column estado_reserva      text not null default 'nenhuma'
             check (estado_reserva in ('nenhuma','standby','rascunho','confirmada','cancelada'));

-- Domínios de email aceites por transportadora (caixas partilhadas, ex. pt.dsv.com), em minúsculas e sem @.
alter table transportadoras
  add column dominios_aceites text[] not null default '{}'
    check (array_to_string(dominios_aceites, ',') !~ '[@A-Z ]');
