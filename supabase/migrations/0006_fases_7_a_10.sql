-- Fases 7 a 10: envio ao cliente, confirmação, expedição e follow-up.

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
