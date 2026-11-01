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
