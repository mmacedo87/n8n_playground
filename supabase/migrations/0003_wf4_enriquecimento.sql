-- WF4 Enriquecimento de proposta: códigos pautais por produto, regras por país e resultado por proposta.
-- Aplicada em DEV a 2026-10-08.

-- Códigos pautais por produto (a validar pelo despachante antes de produção).
create table if not exists public.produtos (
  produto text primary key,
  codigo_nc text not null,
  hts_us text,
  descricao text,
  validado boolean not null default false,
  validado_por text,
  validado_em date,
  atualizado_em timestamptz not null default now()
);
alter table public.produtos enable row level security;

insert into public.produtos (produto, codigo_nc, hts_us, descricao) values
  ('Granulado de cortiça', '4501.90', '4501.90.40.00', 'Cortiça triturada, granulada ou moída'),
  ('Pó de cortiça', '4501.90', '4501.90.40.00', 'Cortiça triturada, granulada ou moída (pó)'),
  ('Aglomerado de cortiça', '4504', null, 'Cortiça aglomerada e obras de cortiça aglomerada')
on conflict (produto) do nothing;

-- requisitos_pais passa a dizer como cada país é tratado.
-- NOTA: a unicidade (pais_iso, codigo_pautal) já existia (requisitos_pais_pais_iso_codigo_pautal_key);
-- o índice abaixo ficou duplicado em DEV e pode ser apagado (drop index requisitos_pais_pais_nc_uq).
create unique index if not exists requisitos_pais_pais_nc_uq on public.requisitos_pais (pais_iso, codigo_pautal);
alter table public.requisitos_pais add column if not exists metodo text not null default 'tabela_manual';
alter table public.requisitos_pais drop constraint if exists requisitos_pais_metodo_chk;
alter table public.requisitos_pais add constraint requisitos_pais_metodo_chk
  check (metodo in ('regra_ue','api_usitc','tabela_manual'));

-- Regras iniciais. codigo_pautal '*' = vale para qualquer código pautal do país.
-- UE: circulação intra-UE (sem direitos). EUA: taxa lida no USITC. Restantes: verificação manual.
insert into public.requisitos_pais (pais_iso, pais_nome, codigo_pautal, taxa_direitos_pct, notas_taxas, requisitos_fitossanitarios, fonte, verificado_em, metodo) values
  ('ES','Espanha','*',0,'Circulação intra-UE: sem direitos aduaneiros. IVA/regras de faturação aplicam-se.','Sem controlos aduaneiros nem fitossanitários na fronteira em circulação intra-UE.','Mercado interno da UE (livre circulação de mercadorias)', current_date,'regra_ue'),
  ('FR','França','*',0,'Circulação intra-UE: sem direitos aduaneiros. IVA/regras de faturação aplicam-se.','Sem controlos aduaneiros nem fitossanitários na fronteira em circulação intra-UE.','Mercado interno da UE (livre circulação de mercadorias)', current_date,'regra_ue'),
  ('DE','Alemanha','*',0,'Circulação intra-UE: sem direitos aduaneiros. IVA/regras de faturação aplicam-se.','Sem controlos aduaneiros nem fitossanitários na fronteira em circulação intra-UE.','Mercado interno da UE (livre circulação de mercadorias)', current_date,'regra_ue'),
  ('IT','Itália','*',0,'Circulação intra-UE: sem direitos aduaneiros. IVA/regras de faturação aplicam-se.','Sem controlos aduaneiros nem fitossanitários na fronteira em circulação intra-UE.','Mercado interno da UE (livre circulação de mercadorias)', current_date,'regra_ue'),
  ('NL','Países Baixos','*',0,'Circulação intra-UE: sem direitos aduaneiros. IVA/regras de faturação aplicam-se.','Sem controlos aduaneiros nem fitossanitários na fronteira em circulação intra-UE.','Mercado interno da UE (livre circulação de mercadorias)', current_date,'regra_ue'),
  ('BE','Bélgica','*',0,'Circulação intra-UE: sem direitos aduaneiros. IVA/regras de faturação aplicam-se.','Sem controlos aduaneiros nem fitossanitários na fronteira em circulação intra-UE.','Mercado interno da UE (livre circulação de mercadorias)', current_date,'regra_ue'),
  ('US','Estados Unidos','*',null,'Taxa base consultada na tabela HTS do USITC (coluna geral). Não inclui direitos adicionais em vigor para a origem; confirmar com o transitário.','A confirmar manualmente no USDA APHIS antes de enviar a proposta.','USITC HTS (hts.usitc.gov); USDA APHIS (aphis.usda.gov)', current_date,'api_usitc'),
  ('GB','Reino Unido','*',null,'Taxa de importação a confirmar no UK Global Tariff para o código pautal do produto.','A confirmar manualmente (UK Plant Health / GOV.UK) antes de enviar a proposta.','UK Trade Tariff (trade-tariff.service.gov.uk); GOV.UK', current_date,'tabela_manual'),
  ('BR','Brasil','*',null,'A confirmar manualmente (Siscomex / despachante).','A confirmar manualmente com o MAPA/despachante.','EU Access2Markets (trade.ec.europa.eu/access-to-markets)', current_date,'tabela_manual'),
  ('CN','China','*',null,'A confirmar manualmente (alfândega chinesa / despachante).','A confirmar manualmente antes de enviar a proposta.','EU Access2Markets (trade.ec.europa.eu/access-to-markets)', current_date,'tabela_manual'),
  ('JP','Japão','*',null,'A confirmar manualmente (alfândega japonesa / despachante).','A confirmar manualmente antes de enviar a proposta.','EU Access2Markets (trade.ec.europa.eu/access-to-markets)', current_date,'tabela_manual'),
  ('MA','Marrocos','*',null,'A confirmar manualmente (alfândega marroquina / despachante).','A confirmar manualmente antes de enviar a proposta.','EU Access2Markets (trade.ec.europa.eu/access-to-markets)', current_date,'tabela_manual')
on conflict (pais_iso, codigo_pautal) do nothing;

-- Resultado do enriquecimento por proposta (histórico; vale a linha mais recente).
create table if not exists public.proposta_compliance (
  id uuid primary key default gen_random_uuid(),
  proposta_id uuid not null references public.propostas(id),
  destino_pais text not null,
  codigo_nc text,
  hts_us text,
  taxa_direitos_pct numeric,
  taxa_texto text,
  notas_taxas text,
  requisitos_fitossanitarios text,
  custos_adicionais_nota text not null default 'Custos de inland e taxas portuárias: constam das cotações das transportadoras (pedir discriminação).',
  fonte text,
  metodo text not null check (metodo in ('regra_ue','api_usitc','tabela_manual')),
  estado text not null check (estado in ('automatico','a_verificar_manualmente')),
  validado_por text,
  validado_em timestamptz,
  criado_em timestamptz not null default now()
);
create index if not exists proposta_compliance_proposta_idx on public.proposta_compliance (proposta_id, criado_em desc);
alter table public.proposta_compliance enable row level security;

-- Correção posterior ao primeiro INSERT: a Bélgica ficou com taxa nula e passou a 0 (intra-UE).
update public.requisitos_pais set taxa_direitos_pct = 0 where pais_iso = 'BE' and codigo_pautal = '*';
