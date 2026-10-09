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
  estado text not null default 'a_enviar' check (estado in ('a_enviar','enviado','falhou','respondido')),
  gerado_por text not null default 'llm' check (gerado_por in ('llm','modelo_fixo')),
  modelo text,
  tentativas smallint not null default 1,
  criado_em timestamptz not null default now(),
  enviado_em timestamptz,
  atualizado_em timestamptz not null default now(),
  unique (proposta_id, transportadora_id)
);
create index pedidos_cotacao_proposta_idx on pedidos_cotacao (proposta_id);
alter table pedidos_cotacao enable row level security;
create trigger pedidos_cotacao_atualizado_em before update on pedidos_cotacao
  for each row execute function set_atualizado_em();

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

-- ============================================================
-- OPCIONAL: dados de teste (descomentar para usar).
-- Nomes e emails são fictícios; trocar pelas transportadoras reais.
-- ============================================================
-- insert into transportadoras (nome, email, modos, rotas) values
--   ('Transportadora Teste A', 'a@example.invalid', array['rodoviario'],  array['ES','FR','DE']),
--   ('Transportadora Teste B', 'b@example.invalid', array['maritimo'],   array['US','BR']),
--   ('Transportadora Teste C', 'c@example.invalid', array['rodoviario','maritimo'], array['DE','IT','US']);
