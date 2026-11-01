-- ============================================================
-- Automação de propostas (cortiça) v0.1 — esquema Supabase
-- Executar no SQL Editor do Supabase (projeto na região UE).
-- Tabelas: leads, transportadoras, propostas, cotacoes_frete,
--          requisitos_pais, ai_log (+ contadores_proposta para o ID PRP).
-- ============================================================

-- ---------- Funções auxiliares ----------

-- Mantém atualizado_em sempre que uma linha muda.
create or replace function set_atualizado_em()
returns trigger
language plpgsql
as $$
begin
  new.atualizado_em := now();
  return new;
end;
$$;

-- Contador anual para o ID de proposta (PRP-2026-0001, PRP-2026-0002, ...).
-- O upsert bloqueia a linha do ano, por isso duas submissões em simultâneo
-- nunca recebem o mesmo número.
create table contadores_proposta (
  ano    int primary key,
  ultimo int not null default 0
);

create or replace function proximo_codigo_proposta()
returns text
language plpgsql
as $$
declare
  v_ano int := extract(year from (now() at time zone 'Europe/Lisbon'))::int;
  v_n   int;
begin
  insert into contadores_proposta (ano, ultimo)
  values (v_ano, 1)
  on conflict (ano) do update set ultimo = contadores_proposta.ultimo + 1
  returning ultimo into v_n;

  return format('PRP-%s-%s', v_ano, lpad(v_n::text, 4, '0'));
end;
$$;

-- ---------- leads (WF1) ----------
create table leads (
  id                 uuid primary key default gen_random_uuid(),
  empresa            text not null,
  contacto_nome      text,
  contacto_email     text,
  produto_interesse  text,
  pais               text,
  quantidade_texto   text,              -- como veio no email, antes de normalizar
  origem_email_id    text unique,       -- ID da mensagem no Outlook (evita duplicados)
  assunto            text,              -- WF1 (migração 0005): assunto do email
  dados_extraidos    jsonb,             -- WF1: pedido extraído pelo LLM e validado em código (rascunho)
  confianca          numeric(3,2) check (confianca is null or confianca between 0 and 1),
  campos_em_falta    text[] not null default '{}',
  estado             text not null default 'novo'
                     check (estado in ('novo','contactado','convertido','descartado')),
  criado_em          timestamptz not null default now(),
  atualizado_em      timestamptz not null default now()
);

create index leads_estado_idx on leads (estado);
create index leads_criado_em_idx on leads (criado_em);

-- ---------- transportadoras (WF3) ----------
create table transportadoras (
  id             uuid primary key default gen_random_uuid(),
  nome           text not null,
  email          text not null,
  modos          text[] not null default '{}'
                 check (modos <@ array['rodoviario','maritimo','aereo','ferroviario']),
  rotas          text[] not null default '{}',   -- países de destino que servem (ex. 'DE','US')
  ativa          boolean not null default true,
  dominios_aceites text[] not null default '{}'   -- migração 0007: domínios das respostas (minúsculas, sem @)
                 check (array_to_string(dominios_aceites, ',') !~ '[@A-Z ]'),
  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now()
);

-- ---------- propostas (WF2 em diante) ----------
create table propostas (
  id                   uuid primary key default gen_random_uuid(),
  codigo               text not null unique default proximo_codigo_proposta(),  -- PRP-AAAA-NNNN
  lead_id              uuid references leads (id) on delete set null,

  -- pedido (formulário do WF2)
  cliente              text not null,
  contacto_email       text,
  produto              text not null,
  densidade            text not null,    -- texto até a Bárbara fechar as listas; depois pode passar a lista fixa
  granulometria        text not null,
  quantidade           numeric(12,2) not null check (quantidade > 0),
  unidade              text not null default 'kg',
  embalagem            text not null,
  incoterm             text not null
                       check (incoterm in ('EXW','FCA','FAS','FOB','CFR','CIF','CPT','CIP','DAP','DPU','DDP')),
  destino_pais         text not null,
  destino_local        text,

  -- carga e moradas (migração 0007)
  tipo_carga           text check (tipo_carga is null or tipo_carga in ('completa','grupagem')),
  n_camioes            smallint check (n_camioes is null or n_camioes > 0),
  n_paletes            int check (n_paletes is null or n_paletes > 0),
  peso_palete_kg       numeric(8,2) check (peso_palete_kg is null or peso_palete_kg > 0),
  palete_c_m           numeric(4,2) check (palete_c_m is null or palete_c_m > 0),
  palete_l_m           numeric(4,2) check (palete_l_m is null or palete_l_m > 0),
  palete_a_m           numeric(4,2) check (palete_a_m is null or palete_a_m > 0),
  morada_carga         text,
  morada_descarga      text,
  cp_descarga          text,

  -- valores calculados em código (WF5), nunca pelo modelo
  moeda                text not null default 'EUR',
  preco_tabela         numeric(12,4),
  desconto_pct         numeric(5,2) not null default 0 check (desconto_pct between 0 and 100),
  frete_escolhido_id   uuid,             -- liga a cotacoes_frete (chave estrangeira adicionada abaixo)
  preco_final          numeric(14,2),

  -- ligação ao Moloni
  moloni_orcamento_id  text,

  -- percurso
  estado               text not null default 'pedido'
                       check (estado in ('pedido','a_cotar','cotado','em_validacao','aprovada',
                                         'enviada','aceite','recusada','em_expedicao','concluida','cancelada')),
  aprovada_por         text,
  aprovada_em          timestamptz,
  foi_editada          boolean not null default false,  -- métrica: % aprovadas sem edição
  enviada_em           timestamptz,                      -- métrica: tempo pedido -> enviada

  criado_em            timestamptz not null default now(),
  atualizado_em        timestamptz not null default now()
);

create index propostas_estado_idx on propostas (estado);
create index propostas_cliente_idx on propostas (cliente);
create index propostas_lead_idx on propostas (lead_id);

-- ---------- cotacoes_frete (WF3) ----------
create table cotacoes_frete (
  id                 uuid primary key default gen_random_uuid(),
  proposta_id        uuid not null references propostas (id) on delete cascade,
  transportadora_id  uuid references transportadoras (id) on delete set null,
  modo               text check (modo in ('rodoviario','maritimo','aereo','ferroviario')),
  preco              numeric(12,2),
  moeda              text not null default 'EUR',
  transito_dias      int check (transito_dias >= 0),
  validade           date,
  condicoes          text,
  ficheiro_origem    text,                 -- nome do PDF/anexo de onde saiu a extração
  email_origem_id    text,                 -- ID da mensagem de resposta no Outlook
  confianca          numeric(3,2) check (confianca between 0 and 1),
  revisao            text not null default 'automatica'
                     check (revisao in ('automatica','a_rever','revista')),
  corrigida_a_mao    boolean not null default false,  -- métrica: % extrações corrigidas
  recebida_em        timestamptz not null default now()
);

create index cotacoes_frete_proposta_idx on cotacoes_frete (proposta_id);

-- Fecha a ligação circular propostas -> cotacoes_frete.
alter table propostas
  add constraint propostas_frete_escolhido_fk
  foreign key (frete_escolhido_id) references cotacoes_frete (id) on delete set null;

-- ---------- requisitos_pais (WF4 simplificado) ----------
create table requisitos_pais (
  id                        uuid primary key default gen_random_uuid(),
  pais_iso                  text not null,          -- código de 2 letras (ex. 'DE')
  pais_nome                 text not null,
  codigo_pautal             text not null default '4501.90',  -- validar com despachante
  taxa_direitos_pct         numeric(5,2),
  notas_taxas               text,
  requisitos_fitossanitarios text,
  fonte                     text not null,          -- de onde veio a informação
  verificado_em             date not null,          -- data da última verificação
  atualizado_em             timestamptz not null default now(),
  metodo                    text not null default 'tabela_manual'
                            check (metodo in ('regra_ue','api_usitc','tabela_manual')),
  unique (pais_iso, codigo_pautal)
);

-- ---------- ai_log (registo de uso de IA) ----------
create table ai_log (
  id              bigint generated always as identity primary key,
  criado_em       timestamptz not null default now(),
  workflow        text not null,                   -- ex. 'WF3 extracao frete'
  execucao_n8n_id text,
  proposta_id     uuid references propostas (id) on delete set null,
  modelo          text not null,
  versao_prompt   text,
  input_resumo    text,                            -- resumo mínimo, sem dados desnecessários
  output_resumo   text,
  tokens_in       int,
  tokens_out      int,
  custo_eur       numeric(10,6),                   -- métrica: custo LLM por proposta
  aprovado_por    text,
  aprovado_em     timestamptz
);

create index ai_log_proposta_idx on ai_log (proposta_id);
create index ai_log_criado_em_idx on ai_log (criado_em);

-- ---------- Triggers de atualizado_em ----------
create trigger leads_atualizado_em before update on leads
  for each row execute function set_atualizado_em();
create trigger transportadoras_atualizado_em before update on transportadoras
  for each row execute function set_atualizado_em();
create trigger propostas_atualizado_em before update on propostas
  for each row execute function set_atualizado_em();
create trigger requisitos_pais_atualizado_em before update on requisitos_pais
  for each row execute function set_atualizado_em();

-- ---------- Retenção (RGPD) ----------
-- Apaga leads não convertidos com mais de N meses (por defeito, 12).
-- Corre-se à mão ou a partir de um workflow agendado no n8n.
create or replace function purgar_leads_antigos(meses int default 12)
returns int
language plpgsql
as $$
declare
  v_apagados int;
begin
  delete from leads
  where estado <> 'convertido'
    and criado_em < now() - make_interval(months => meses);
  get diagnostics v_apagados = row_count;
  return v_apagados;
end;
$$;

-- ---------- Pedidos de cotação de frete (WF3) ----------
create table pedidos_cotacao (
  id uuid primary key default gen_random_uuid(),
  proposta_id uuid not null references propostas(id) on delete cascade,
  transportadora_id uuid not null references transportadoras(id) on delete cascade,
  assunto text not null,
  corpo_html text not null,
  redirecionado_teste boolean not null default false,
  estado text not null default 'a_enviar' check (estado in ('a_enviar','rascunho','enviado','falhou','respondido')),  -- 'rascunho': migração 0009
  gerado_por text not null default 'llm' check (gerado_por in ('llm','modelo_fixo')),
  modelo text,
  tentativas smallint not null default 1,
  versao smallint not null default 1 check (versao >= 1),          -- migração 0007: atualizações de cotação
  substitui_id uuid references pedidos_cotacao (id) on delete set null,
  conversation_id text,                                             -- conversa do Outlook
  ref_transportadora text,                                          -- referência da transportadora
  criado_em timestamptz not null default now(),
  enviado_em timestamptz,
  atualizado_em timestamptz not null default now(),
  constraint pedidos_cotacao_proposta_transp_versao_key unique (proposta_id, transportadora_id, versao)
);
create index pedidos_cotacao_proposta_idx on pedidos_cotacao (proposta_id);
create index pedidos_cotacao_conversation_idx on pedidos_cotacao (conversation_id) where conversation_id is not null;
alter table pedidos_cotacao enable row level security;
create trigger pedidos_cotacao_atualizado_em before update on pedidos_cotacao
  for each row execute function set_atualizado_em();

-- Condições de cada cotação e estado da reserva (migração 0007; fica aqui porque refere pedidos_cotacao).
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

-- ---------- Produtos e enriquecimento de proposta (WF4) ----------
-- Códigos pautais por produto (a validar pelo despachante).
create table produtos (
  produto        text primary key,
  codigo_nc      text not null,
  hts_us         text,                    -- código HTS de 10 dígitos para os EUA
  descricao      text,
  validado       boolean not null default false,
  validado_por   text,
  validado_em    date,
  atualizado_em  timestamptz not null default now()
);
alter table produtos enable row level security;

-- Resultado do enriquecimento por proposta (histórico; vale a linha mais recente).
create table proposta_compliance (
  id                         uuid primary key default gen_random_uuid(),
  proposta_id                uuid not null references propostas(id),
  destino_pais               text not null,
  codigo_nc                  text,
  hts_us                     text,
  taxa_direitos_pct          numeric,
  taxa_texto                 text,
  notas_taxas                text,
  requisitos_fitossanitarios text,
  custos_adicionais_nota     text not null default 'Custos de inland e taxas portuárias: constam das cotações das transportadoras (pedir discriminação).',
  fonte                      text,
  metodo                     text not null check (metodo in ('regra_ue','api_usitc','tabela_manual')),
  estado                     text not null check (estado in ('automatico','a_verificar_manualmente')),
  validado_por               text,
  validado_em                timestamptz,
  criado_em                  timestamptz not null default now()
);
create index proposta_compliance_proposta_idx on proposta_compliance (proposta_id, criado_em desc);
alter table proposta_compliance enable row level security;
-- Dados iniciais (produtos e regras por país): ver supabase/migrations/0003_wf4_enriquecimento.sql

-- ---------- Fases 7 a 10 (migração 0006) ----------
-- Confirmação por link (WF10): token aleatório por proposta, com validade.
alter table propostas
  add column token_confirmacao text not null
    default (replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '')),
  add column token_expira_em timestamptz not null default (now() + interval '30 days'),
  add column confirmada_em timestamptz,
  add column followup_enviado_em timestamptz;

-- Código de aprovação (migração 0008): o WF5 envia-o à Bárbara e o WF8 só aprova com «OK <código>».
alter table propostas
  add column codigo_aprovacao text not null default upper(substr(md5(gen_random_uuid()::text), 1, 6));

create unique index propostas_token_confirmacao_idx on propostas (token_confirmacao);

-- Expedição (WF10 cria a linha, WF11 preenche, WF12 envia o follow-up).
create table expedicoes (
  id                    uuid primary key default gen_random_uuid(),
  proposta_id           uuid not null unique references propostas (id) on delete cascade,
  estado                text not null default 'por_planear'
                        check (estado in ('por_planear','planeada','concluida')),
  tempo_producao_dias   int check (tempo_producao_dias is null or tempo_producao_dias >= 0),
  stock_ok              boolean,
  data_recolha          date,
  modo                  text check (modo is null or modo in ('rodoviario','maritimo','aereo','ferroviario')),
  transportadora        text,
  notas                 text,
  planeada_por          text,
  planeada_em           timestamptz,
  criado_em             timestamptz not null default now(),
  atualizado_em         timestamptz not null default now()
);

alter table expedicoes enable row level security;
create trigger expedicoes_atualizado_em before update on expedicoes
  for each row execute function set_atualizado_em();

-- Vista de leitura para a Bárbara e a Madalena (corre com os direitos de quem consulta).
create view v_expedicoes with (security_invoker = true) as
select p.codigo, p.cliente, p.produto, p.quantidade, p.unidade, p.incoterm, p.destino_pais,
       e.estado, e.tempo_producao_dias, e.stock_ok, e.data_recolha, e.modo, e.transportadora,
       e.notas, e.planeada_por, e.planeada_em, e.criado_em
from expedicoes e
join propostas p on p.id = e.proposta_id;

-- ---------- Segurança ----------
-- RLS ativa e sem políticas: a chave anónima não lê nem escreve nada.
-- O n8n usa a chave de serviço (service_role), que ignora o RLS.
alter table contadores_proposta enable row level security;
alter table leads               enable row level security;
alter table transportadoras     enable row level security;
alter table propostas           enable row level security;
alter table cotacoes_frete      enable row level security;
alter table requisitos_pais     enable row level security;
alter table ai_log              enable row level security;

-- Reforço (migração 0008): anon e authenticated sem permissões; funções só para service_role.
revoke all on all tables    in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke execute on all functions in schema public from public, anon, authenticated;
grant  execute on all functions in schema public to service_role;
alter default privileges in schema public revoke all on tables    from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;
alter default privileges in schema public revoke execute on functions from public, anon, authenticated;

-- A validação do despachante exige quem validou e quando.
alter table produtos
  add constraint produtos_validado_auditado
  check (validado = false or (validado_por is not null and validado_em is not null)) not valid;

-- Configuração (migração 0009): definições que se mudam sem tocar nos workflows.
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
   'schema');

-- Lead convertido (migração 0010): proposta ligada a um lead marca o lead como 'convertido'
-- (assim purgar_leads_antigos() não o apaga e a ligação ao email de origem fica).
create or replace function marcar_lead_convertido()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.lead_id is not null then
    update leads set estado = 'convertido'
     where id = new.lead_id and estado <> 'convertido';
  end if;
  return new;
end;
$$;
revoke execute on function marcar_lead_convertido() from public, anon, authenticated;
create trigger propostas_lead_convertido
  after insert or update of lead_id on propostas
  for each row execute function marcar_lead_convertido();

-- Código secreto do link do plano de expedição (migração 0011): vai no link do WF10/WF13 (&t=) e o WF11 compara-o.
alter table propostas
  add column token_plano text not null
  default (replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', ''));
alter table propostas add constraint propostas_token_plano_key unique (token_plano);
alter table propostas add constraint propostas_token_plano_formato check (token_plano ~ '^[0-9a-f]{64}$');

-- ============================================================
-- OPCIONAL: dados de teste (descomentar para usar).
-- Nomes e emails são fictícios; trocar pelas transportadoras reais.
-- ============================================================
-- insert into transportadoras (nome, email, modos, rotas) values
--   ('Transportadora Teste A', 'a@example.invalid', array['rodoviario'],  array['ES','FR','DE']),
--   ('Transportadora Teste B', 'b@example.invalid', array['maritimo'],   array['US','BR']),
--   ('Transportadora Teste C', 'c@example.invalid', array['rodoviario','maritimo'], array['DE','IT','US']);

-- ============================================================
-- Migração 0012 (2026-11-01): preço final por formulário (WF7). Cópia de supabase/migrations/0012_preco_manual.sql.
-- ============================================================
-- 0012: preço final por formulário (WF7, fase 5 sem Moloni). Plano: docs/plano-wf7-preco-manual.md.
-- 1) utilizadores (pessoas e permissões; hoje só a Bárbara com pode_definir_preco) + histórico imutável de alterações.
-- 2) acessos_preco: uma ligação pessoal por proposta e por pessoa (token 64 hex, 14 dias).
-- 3) historico_precos: uma linha por cada preço gravado (auditoria).
-- 4) Colunas de preço em propostas (preco_tabela passa a ser o €/kg; desconto_pct, frete_escolhido_id e preco_final reaproveitados).
-- 5) Limites em configuracao: preco.max_eur_kg, preco.max_desconto_pct, preco.validade_dias.
-- 6) Funções (só service_role): preparar_acessos_preco (WF5), contexto_preco (WF7 GET), gravar_preco_proposta (WF7 POST).
--    O cálculo é feito aqui, em numeric (sem erros de vírgula flutuante), numa só transação, com a proposta bloqueada.
-- Sem LLM. Reversão: supabase/rollbacks/0012_rollback.sql.

-- ---------- 1. utilizadores ----------
create table utilizadores (
  id                  uuid primary key default gen_random_uuid(),
  nome                text not null check (length(trim(nome)) between 2 and 80),
  email               text not null unique
                      check (email = lower(email) and email ~ '^[^@[:space:],;<>]+@[^@[:space:],;<>]+\.[a-z]{2,}$'),
  pode_definir_preco  boolean not null default false,
  pode_aprovar        boolean not null default false,   -- reservado: o WF8 continua com a lista no código (D4 do plano de destinatários)
  ativo               boolean not null default true,
  criado_em           timestamptz not null default now(),
  atualizado_em       timestamptz not null default now()
);
create trigger utilizadores_atualizado_em before update on utilizadores
  for each row execute function set_atualizado_em();

create table utilizadores_historico (
  id             bigint generated always as identity primary key,
  utilizador_id  uuid not null,
  operacao       text not null check (operacao in ('INSERT','UPDATE','DELETE')),
  antes          jsonb,
  depois         jsonb,
  alterado_em    timestamptz not null default now(),
  alterado_por   text not null default current_user
);

create or replace function registar_historico_utilizadores()
returns trigger language plpgsql set search_path = public as $$
begin
  insert into utilizadores_historico (utilizador_id, operacao, antes, depois)
  values (coalesce(new.id, old.id), tg_op,
          case when tg_op in ('UPDATE','DELETE') then to_jsonb(old) end,
          case when tg_op in ('INSERT','UPDATE') then to_jsonb(new) end);
  return coalesce(new, old);
end;
$$;
create trigger utilizadores_historico_trg after insert or update or delete on utilizadores
  for each row execute function registar_historico_utilizadores();

-- O histórico não se altera nem se apaga (nem pela service_role).
create or replace function bloquear_alteracao_historico()
returns trigger language plpgsql set search_path = public as $$
begin
  raise exception 'histórico imutável: % não é permitido em %', tg_op, tg_table_name;
end;
$$;
create trigger utilizadores_historico_imutavel before update or delete on utilizadores_historico
  for each row execute function bloquear_alteracao_historico();

-- ---------- 2. acessos_preco ----------
create table acessos_preco (
  id             uuid primary key default gen_random_uuid(),
  proposta_id    uuid not null references propostas (id) on delete cascade,
  utilizador_id  uuid not null references utilizadores (id) on delete cascade,
  token          text not null unique
                 default (replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', ''))
                 check (token ~ '^[0-9a-f]{64}$'),
  expira_em      timestamptz not null default now() + interval '14 days',
  criado_em      timestamptz not null default now(),
  unique (proposta_id, utilizador_id)
);

-- ---------- 3. colunas de preço em propostas ----------
alter table propostas
  add column valor_produto       numeric(14,2),
  add column valor_frete         numeric(14,2),
  add column frete_corrigido     boolean not null default false,
  add column valor_liquido       numeric(14,2),
  add column iva_regime          text check (iva_regime in ('pt_normal','ue_isento','exportacao_isento','outro')),
  add column iva_pct             numeric(5,2) check (iva_pct between 0 and 30),
  add column valor_iva           numeric(14,2),
  add column cliente_nif         text check (cliente_nif ~ '^[A-Z]{2}[A-Z0-9]{2,13}$'),
  add column validade_proposta   date,
  add column preco_origem        text check (preco_origem in ('manual','moloni')),
  add column preco_definido_por  uuid references utilizadores (id),
  add column preco_definido_em   timestamptz,
  add column preco_notas         text check (length(preco_notas) <= 1000);

comment on column propostas.preco_tabela is 'Preço do produto em EUR/kg (definido no WF7)';
comment on column propostas.preco_final is 'Total da proposta com IVA (valor_liquido + valor_iva)';

-- ---------- 4. historico_precos ----------
create table historico_precos (
  id                 bigint generated always as identity primary key,
  proposta_id        uuid not null references propostas (id) on delete cascade,
  utilizador_id      uuid not null references utilizadores (id),
  preco_kg           numeric(12,4) not null,
  desconto_pct       numeric(5,2) not null,
  quantidade_kg      numeric(14,2) not null,
  cotacao_id         uuid references cotacoes_frete (id) on delete set null,
  valor_produto      numeric(14,2) not null,
  valor_frete        numeric(14,2) not null,
  frete_corrigido    boolean not null,
  valor_liquido      numeric(14,2) not null,
  iva_regime         text not null,
  iva_pct            numeric(5,2) not null,
  valor_iva          numeric(14,2) not null,
  preco_final        numeric(14,2) not null,
  validade_proposta  date not null,
  notas              text,
  criado_em          timestamptz not null default now()
);
create index historico_precos_proposta_idx on historico_precos (proposta_id, criado_em);
create trigger historico_precos_imutavel before update or delete on historico_precos
  for each row when (pg_trigger_depth() = 0) execute function bloquear_alteracao_historico();

-- ---------- 5. limites em configuracao ----------
insert into configuracao (chave, valor, descricao, atualizado_por) values
  ('preco.max_eur_kg', '50', 'WF7: preço máximo aceite por kg (proteção contra enganos de escrita)', 'migracao 0012'),
  ('preco.max_desconto_pct', '50', 'WF7: desconto máximo aceite em %', 'migracao 0012'),
  ('preco.validade_dias', '30', 'WF7: validade por omissão da proposta, em dias', 'migracao 0012');

-- ---------- 6. funções ----------
-- Regime de IVA sugerido pelo país de destino (menções a confirmar com a contabilidade).
create or replace function iva_sugerido(p_pais text)
returns text language sql immutable set search_path = public as $$
  select case
    when upper(p_pais) = 'PT' then 'pt_normal'
    when upper(p_pais) in ('AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','EL','HU','IE','IT','LV','LT',
                           'LU','MT','NL','PL','RO','SK','SI','ES','SE') then 'ue_isento'
    else 'exportacao_isento'
  end;
$$;

-- Frete proposto para uma cotação: total, por camião (× n.º de camiões) ou por palete (× n.º de paletes).
-- Devolve null quando não dá para calcular com segurança (âmbito não claro, cotação a rever, dados em falta).
create or replace function frete_proposto(c cotacoes_frete, p propostas)
returns numeric language sql stable set search_path = public as $$
  select case
    when c.preco is null or c.revisao = 'a_rever' or coalesce(c.moeda, 'EUR') <> 'EUR' then null
    when c.preco_por = 'total' then round(c.preco, 2)
    when c.preco_por = 'camiao' then round(c.preco * coalesce(p.n_camioes, c.n_camioes_incluidos, 1), 2)
    when c.preco_por = 'palete' and p.n_paletes is not null then round(c.preco * p.n_paletes, 2)
    else null
  end;
$$;

-- WF5: cria (ou reutiliza, se ainda válida) a ligação pessoal de cada utilizador com permissão para a proposta.
create or replace function preparar_acessos_preco(p_proposta_id uuid)
returns table (nome text, email text, token text, expira_em timestamptz)
language plpgsql set search_path = public as $$
#variable_conflict use_column
begin
  insert into acessos_preco (proposta_id, utilizador_id)
  select p_proposta_id, u.id from utilizadores u where u.ativo and u.pode_definir_preco
  on conflict (proposta_id, utilizador_id) do update
    set token = case when acessos_preco.expira_em < now() + interval '1 day'
                     then excluded.token else acessos_preco.token end,
        expira_em = case when acessos_preco.expira_em < now() + interval '1 day'
                         then excluded.expira_em else acessos_preco.expira_em end;
  return query
    select u.nome, u.email, a.token, a.expira_em
    from acessos_preco a join utilizadores u on u.id = a.utilizador_id
    where a.proposta_id = p_proposta_id and u.ativo and u.pode_definir_preco;
end;
$$;

-- Verifica uma ligação e devolve o erro (ou null) e os registos associados.
create or replace function verificar_acesso_preco(p_token text, out erro text, out a acessos_preco, out u utilizadores, out p propostas)
language plpgsql set search_path = public as $$
begin
  if p_token is null or p_token !~ '^[0-9a-f]{64}$' then erro := 'A ligação não é válida. Use o botão do email de resumo mais recente.'; return; end if;
  select * into a from acessos_preco where token = p_token;
  if a.id is null then erro := 'A ligação não é válida. Use o botão do email de resumo mais recente.'; return; end if;
  if a.expira_em < now() then erro := 'A ligação expirou. Use o botão do email de resumo mais recente.'; return; end if;
  select * into u from utilizadores where id = a.utilizador_id;
  if not (u.ativo and u.pode_definir_preco) then erro := 'Não tem permissão para definir preços.'; return; end if;
  select * into p from propostas where id = a.proposta_id;
  if p.estado not in ('pedido','a_cotar','cotado','em_validacao') then
    erro := 'A proposta ' || p.codigo || ' está no estado «' || p.estado || '»: o preço já não pode ser alterado.'; return;
  end if;
end;
$$;

-- WF7 (GET): tudo o que a página do preço precisa, ou {ok:false, erro}.
create or replace function contexto_preco(p_token text)
returns jsonb language plpgsql set search_path = public as $$
declare v record; v_cot jsonb; v_cfg jsonb;
begin
  select * into v from verificar_acesso_preco(p_token);
  if v.erro is not null then return jsonb_build_object('ok', false, 'erro', v.erro); end if;
  select coalesce(jsonb_agg(jsonb_build_object(
           'id', c.id, 'transportadora', coalesce(t.nome, 'transportadora'), 'modo', c.modo, 'preco', c.preco,
           'moeda', c.moeda, 'preco_por', c.preco_por, 'transito_dias', c.transito_dias, 'validade', c.validade,
           'revisao', c.revisao, 'ref', c.ref_transportadora, 'frete_proposto', frete_proposto(c, (v.p)))
           order by c.preco nulls last), '[]'::jsonb)
    into v_cot
    from cotacoes_frete c left join transportadoras t on t.id = c.transportadora_id
    where c.proposta_id = (v.p).id;
  select jsonb_object_agg(chave, valor) into v_cfg from configuracao where chave like 'preco.%';
  return jsonb_build_object(
    'ok', true,
    'utilizador', (v.u).nome,
    'proposta', jsonb_build_object(
      'codigo', (v.p).codigo, 'cliente', (v.p).cliente, 'produto', (v.p).produto, 'densidade', (v.p).densidade,
      'granulometria', (v.p).granulometria, 'quantidade', (v.p).quantidade, 'unidade', (v.p).unidade,
      'quantidade_kg', (v.p).quantidade * case when (v.p).unidade = 't' then 1000 else 1 end,
      'embalagem', (v.p).embalagem, 'incoterm', (v.p).incoterm, 'destino_pais', (v.p).destino_pais,
      'destino_local', (v.p).destino_local, 'estado', (v.p).estado, 'n_camioes', (v.p).n_camioes, 'n_paletes', (v.p).n_paletes,
      'preco_kg', (v.p).preco_tabela, 'desconto_pct', (v.p).desconto_pct, 'cotacao_id', (v.p).frete_escolhido_id,
      'valor_frete', (v.p).valor_frete, 'iva_regime', (v.p).iva_regime, 'iva_pct', (v.p).iva_pct,
      'cliente_nif', (v.p).cliente_nif, 'preco_final', (v.p).preco_final, 'validade_proposta', (v.p).validade_proposta,
      'preco_notas', (v.p).preco_notas),
    'frete_obrigatorio', upper((v.p).incoterm) in ('CFR','CIF','CPT','CIP','DAP','DPU','DDP'),
    'iva_sugerido', iva_sugerido((v.p).destino_pais),
    'cotacoes', v_cot,
    'limites', coalesce(v_cfg, '{}'::jsonb));
end;
$$;

-- WF7 (POST): valida, calcula e grava o preço numa só transação. Devolve {ok:true, ...valores} ou {ok:false, erro}.
create or replace function gravar_preco_proposta(
  p_token text, p_preco_kg numeric, p_desconto_pct numeric, p_cotacao_id uuid, p_valor_frete numeric,
  p_iva_regime text, p_iva_pct numeric, p_cliente_nif text, p_validade_dias int, p_notas text)
returns jsonb language plpgsql set search_path = public as $$
declare
  v record; p propostas; c cotacoes_frete;
  v_max_kg numeric; v_max_desc numeric; v_val_def int;
  v_kg numeric; v_frete numeric; v_frete_prop numeric; v_corrigido boolean := false; v_cot_id uuid;
  v_sug text; v_regime text; v_pct numeric; v_nif text; v_notas text; v_dias int;
  v_prod numeric; v_liq numeric; v_iva numeric; v_total numeric; v_cod text; v_avisos text[] := '{}';
begin
  select * into v from verificar_acesso_preco(p_token);
  if v.erro is not null then return jsonb_build_object('ok', false, 'erro', v.erro); end if;
  select * into p from propostas where id = (v.p).id for update;           -- bloqueia a proposta até ao fim
  if p.estado not in ('pedido','a_cotar','cotado','em_validacao') then
    return jsonb_build_object('ok', false, 'erro', 'A proposta ' || p.codigo || ' mudou de estado entretanto («' || p.estado || '»).');
  end if;
  if coalesce(p.moeda, 'EUR') <> 'EUR' then return jsonb_build_object('ok', false, 'erro', 'Só são suportadas propostas em EUR.'); end if;

  select coalesce((select valor::numeric from configuracao where chave = 'preco.max_eur_kg'), 50),
         coalesce((select valor::numeric from configuracao where chave = 'preco.max_desconto_pct'), 50),
         coalesce((select valor::int from configuracao where chave = 'preco.validade_dias'), 30)
    into v_max_kg, v_max_desc, v_val_def;

  -- Produto
  if p_preco_kg is null or p_preco_kg <= 0 or p_preco_kg > v_max_kg then
    return jsonb_build_object('ok', false, 'erro', 'O preço por kg tem de estar entre 0,01 e ' || v_max_kg || ' €.');
  end if;
  if coalesce(p_desconto_pct, 0) < 0 or coalesce(p_desconto_pct, 0) > v_max_desc then
    return jsonb_build_object('ok', false, 'erro', 'O desconto tem de estar entre 0 e ' || v_max_desc || ' %.');
  end if;
  v_kg := p.quantidade * case when p.unidade = 't' then 1000 else 1 end;
  if v_kg is null or v_kg <= 0 then return jsonb_build_object('ok', false, 'erro', 'A proposta não tem quantidade válida.'); end if;
  v_prod := round(v_kg * p_preco_kg * (1 - coalesce(p_desconto_pct, 0) / 100), 2);

  -- Frete, conforme o Incoterm
  if upper(p.incoterm) in ('CFR','CIF','CPT','CIP','DAP','DPU','DDP') then
    if p_cotacao_id is null then
      return jsonb_build_object('ok', false, 'erro', 'Com o Incoterm ' || p.incoterm || ' o frete entra no preço: escolha uma cotação de frete.');
    end if;
    select * into c from cotacoes_frete where id = p_cotacao_id and proposta_id = p.id;
    if c.id is null then return jsonb_build_object('ok', false, 'erro', 'A cotação escolhida não pertence a esta proposta.'); end if;
    if coalesce(c.moeda, 'EUR') <> 'EUR' then return jsonb_build_object('ok', false, 'erro', 'A cotação escolhida não está em EUR.'); end if;
    v_frete_prop := frete_proposto(c, p);
    if p_valor_frete is not null then
      if p_valor_frete < 0 or p_valor_frete > 1000000 then return jsonb_build_object('ok', false, 'erro', 'O valor do frete não é válido.'); end if;
      v_frete := round(p_valor_frete, 2);
      v_corrigido := v_frete_prop is null or v_frete <> v_frete_prop;
    elsif v_frete_prop is null then
      return jsonb_build_object('ok', false, 'erro', 'Não é possível calcular o frete desta cotação (âmbito não claro ou a rever): escreva o valor do frete.');
    else
      v_frete := v_frete_prop;
    end if;
    v_cot_id := c.id;
    if c.validade is not null and c.validade < current_date + coalesce(p_validade_dias, v_val_def) then
      v_avisos := v_avisos || ('A cotação de frete é válida só até ' || to_char(c.validade, 'DD/MM/YYYY') || ', antes do fim da validade da proposta.');
    end if;
  else
    v_frete := 0; v_cot_id := null;
    if p_cotacao_id is not null then v_avisos := v_avisos || ('Com o Incoterm ' || p.incoterm || ' o frete não entra no preço: a cotação escolhida foi ignorada.'); end if;
  end if;

  -- IVA
  v_sug := iva_sugerido(p.destino_pais);
  v_regime := coalesce(nullif(p_iva_regime, ''), v_sug);
  v_notas := nullif(trim(coalesce(p_notas, '')), '');
  if v_regime not in ('pt_normal','ue_isento','exportacao_isento','outro') then
    return jsonb_build_object('ok', false, 'erro', 'Regime de IVA desconhecido.');
  end if;
  if v_regime <> v_sug and length(coalesce(v_notas, '')) < 5 then
    return jsonb_build_object('ok', false, 'erro', 'Escolheu um regime de IVA diferente do sugerido: explique porquê nas notas.');
  end if;
  v_pct := case v_regime when 'pt_normal' then 23 when 'ue_isento' then 0 when 'exportacao_isento' then 0 else p_iva_pct end;
  if v_pct is null or v_pct < 0 or v_pct > 30 then return jsonb_build_object('ok', false, 'erro', 'Indique a taxa de IVA (0 a 30 %).'); end if;
  v_nif := nullif(upper(regexp_replace(coalesce(p_cliente_nif, p.cliente_nif, ''), '[^A-Za-z0-9]', '', 'g')), '');
  if v_regime = 'ue_isento' and (v_nif is null or v_nif !~ '^[A-Z]{2}[A-Z0-9]{2,13}$') then
    return jsonb_build_object('ok', false, 'erro', 'A isenção intracomunitária exige o NIF europeu do cliente (ex.: NL123456789B01).');
  end if;
  if v_nif is not null and v_nif !~ '^[A-Z]{2}[A-Z0-9]{2,13}$' then
    return jsonb_build_object('ok', false, 'erro', 'O NIF tem de começar pelo código do país (ex.: ES, NL, PT).');
  end if;

  v_dias := coalesce(p_validade_dias, v_val_def);
  if v_dias < 1 or v_dias > 90 then return jsonb_build_object('ok', false, 'erro', 'A validade tem de estar entre 1 e 90 dias.'); end if;
  if length(coalesce(v_notas, '')) > 1000 then return jsonb_build_object('ok', false, 'erro', 'As notas têm no máximo 1000 caracteres.'); end if;

  v_liq := v_prod + v_frete;
  v_iva := round(v_liq * v_pct / 100, 2);
  v_total := v_liq + v_iva;
  if v_total <= 0 then return jsonb_build_object('ok', false, 'erro', 'O total tem de ser maior do que zero.'); end if;
  v_cod := upper(substr(md5(gen_random_uuid()::text), 1, 6));                -- novo código de aprovação

  update propostas set
    preco_tabela = p_preco_kg, desconto_pct = coalesce(p_desconto_pct, 0),
    frete_escolhido_id = case when v_cot_id is not null then v_cot_id else frete_escolhido_id end,
    valor_produto = v_prod, valor_frete = v_frete, frete_corrigido = v_corrigido, valor_liquido = v_liq,
    iva_regime = v_regime, iva_pct = v_pct, valor_iva = v_iva, preco_final = v_total, cliente_nif = v_nif,
    validade_proposta = current_date + v_dias, preco_origem = 'manual', preco_definido_por = (v.u).id,
    preco_definido_em = now(), preco_notas = v_notas, codigo_aprovacao = v_cod
  where id = p.id;

  insert into historico_precos (proposta_id, utilizador_id, preco_kg, desconto_pct, quantidade_kg, cotacao_id,
    valor_produto, valor_frete, frete_corrigido, valor_liquido, iva_regime, iva_pct, valor_iva, preco_final,
    validade_proposta, notas)
  values (p.id, (v.u).id, p_preco_kg, coalesce(p_desconto_pct, 0), v_kg, v_cot_id, v_prod, v_frete, v_corrigido,
    v_liq, v_regime, v_pct, v_iva, v_total, current_date + v_dias, v_notas);

  return jsonb_build_object('ok', true, 'codigo', p.codigo, 'proposta_id', p.id, 'utilizador', (v.u).nome,
    'quantidade_kg', v_kg, 'preco_kg', p_preco_kg, 'desconto_pct', coalesce(p_desconto_pct, 0),
    'valor_produto', v_prod, 'valor_frete', v_frete, 'frete_corrigido', v_corrigido, 'valor_liquido', v_liq,
    'iva_regime', v_regime, 'iva_pct', v_pct, 'valor_iva', v_iva, 'preco_final', v_total,
    'validade_proposta', current_date + v_dias, 'preco_alterado', p.preco_final is not null,
    'preco_anterior', p.preco_final, 'avisos', to_jsonb(v_avisos));
end;
$$;

-- ---------- 7. segurança ----------
alter table utilizadores enable row level security;
alter table utilizadores_historico enable row level security;
alter table acessos_preco enable row level security;
alter table historico_precos enable row level security;
revoke all on utilizadores, utilizadores_historico, acessos_preco, historico_precos from anon, authenticated;
revoke execute on function iva_sugerido(text), frete_proposto(cotacoes_frete, propostas), preparar_acessos_preco(uuid),
  verificar_acesso_preco(text), contexto_preco(text),
  gravar_preco_proposta(text, numeric, numeric, uuid, numeric, text, numeric, text, int, text),
  registar_historico_utilizadores(), bloquear_alteracao_historico()
  from public, anon, authenticated;
grant execute on function iva_sugerido(text), frete_proposto(cotacoes_frete, propostas), preparar_acessos_preco(uuid),
  verificar_acesso_preco(text), contexto_preco(text),
  gravar_preco_proposta(text, numeric, numeric, uuid, numeric, text, numeric, text, int, text) to service_role;
