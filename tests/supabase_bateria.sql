-- Bateria Supabase (A1-A27 e B1-B8). Corre numa única instrução e TERMINA SEMPRE com uma exceção que traz o relatório:
-- por isso a transação é revertida e não fica nenhum dado nem se apaga nenhum. A9 (trigger) verifica-se pelo catálogo,
-- porque dentro de uma transação now() é constante.
create or replace function pg_temp.falha(q text) returns boolean language plpgsql as $f$
begin
  execute q;
  return false;                       -- não falhou: o teste deve marcar erro
exception when others then
  return true;
end $f$;

do $t$
declare
  r text := '';
  n int;
  p1 uuid; p2 uuid; t1 uuid; c1 text; c2 text;
  base text := $b$insert into propostas (cliente,produto,densidade,granulometria,quantidade,embalagem,incoterm,destino_pais) values ('T','p','d','g',%s,'e','%s','ES')$b$;
  tabelas text[] := array['contadores_proposta','leads','transportadoras','propostas','cotacoes_frete','requisitos_pais','ai_log','pedidos_cotacao','produtos','proposta_compliance','expedicoes'];
  tb text;
  ok boolean;
begin
  -- A1/A2
  select count(*) into n from information_schema.tables where table_schema='public' and table_name = any(tabelas);
  r := r || format('A1 %s tabelas=%s' || E'\n', case when n=11 then 'OK' else 'FALHA' end, n);
  select count(*) into n from pg_class c join pg_namespace s on s.oid=c.relnamespace where s.nspname='public' and c.relname = any(tabelas) and c.relrowsecurity;
  r := r || format('A2 %s RLS ativa=%s' || E'\n', case when n=11 then 'OK' else 'FALHA' end, n);

  -- A3-A5
  insert into propostas (cliente,produto,densidade,granulometria,quantidade,embalagem,incoterm,destino_pais) values ('T1','p','d','g',10,'e','FOB','ES') returning id, codigo into p1, c1;
  insert into propostas (cliente,produto,densidade,granulometria,quantidade,embalagem,incoterm,destino_pais) values ('T2','p','d','g',10,'e','FOB','DE') returning id, codigo into p2, c2;
  r := r || format('A3 %s formato=%s' || E'\n', case when c1 ~ '^PRP-\d{4}-\d{4}$' then 'OK' else 'FALHA' end, c1);
  r := r || format('A4 %s consecutivo %s -> %s' || E'\n', case when right(c2,4)::int = right(c1,4)::int + 1 then 'OK' else 'FALHA' end, c1, c2);
  r := r || format('A5 %s estado por omissão' || E'\n', case when (select estado from propostas where id=p1)='pedido' then 'OK' else 'FALHA' end);

  -- A6-A8
  r := r || format('A6 %s' || E'\n', case when pg_temp.falha(format(base,'10','XXX')) then 'OK' else 'FALHA' end);
  r := r || format('A7 %s' || E'\n', case when pg_temp.falha(format(base,'0','FOB')) then 'OK' else 'FALHA' end);
  r := r || format('A8 %s' || E'\n', case when pg_temp.falha($q$update propostas set estado='xpto'$q$) then 'OK' else 'FALHA' end);

  -- A9 (catálogo)
  select count(*) into n from pg_trigger where tgname in ('propostas_atualizado_em','leads_atualizado_em','transportadoras_atualizado_em','requisitos_pais_atualizado_em','pedidos_cotacao_atualizado_em','expedicoes_atualizado_em') and not tgisinternal;
  r := r || format('A9 %s triggers atualizado_em=%s/6' || E'\n', case when n=6 then 'OK' else 'FALHA' end, n);

  -- A10-A12
  r := r || format('A10 %s' || E'\n', case when pg_temp.falha(format($q$update propostas set codigo=%L where id=%L$q$, c1, p2)) then 'OK' else 'FALHA' end);
  r := r || format('A11 %s' || E'\n', case when pg_temp.falha($q$insert into cotacoes_frete (proposta_id) values (gen_random_uuid())$q$) then 'OK' else 'FALHA' end);
  r := r || format('A12 %s' || E'\n', case when pg_temp.falha(format($q$insert into cotacoes_frete (proposta_id,modo) values (%L,'foguetao')$q$, p1)) then 'OK' else 'FALHA' end);

  -- A13
  insert into leads (empresa, estado, criado_em) values ('velho','novo', now() - interval '13 months'), ('velho conv','convertido', now() - interval '13 months'), ('novo','novo', now());
  select purgar_leads_antigos(12) into n;
  r := r || format('A13 %s apagados=%s (esperado 1), restantes=%s' || E'\n', case when n=1 and (select count(*) from leads)=2 then 'OK' else 'FALHA' end, n, (select count(*) from leads));

  -- A14 (anon)
  ok := true;
  begin
    set local role anon;
    perform 1 from propostas limit 1;
    get diagnostics n = row_count;
    ok := (n = 0);
  exception when insufficient_privilege then ok := true;
  end;
  reset role;
  r := r || format('A14 %s anon não lê propostas' || E'\n', case when ok then 'OK' else 'FALHA' end);

  -- A19-A24
  insert into transportadoras (nome,email) values ('Teste','x@example.invalid') returning id into t1;
  insert into pedidos_cotacao (proposta_id, transportadora_id, assunto, corpo_html) values (p1, t1, 'a', 'b');
  r := r || format('A19 %s pedidos_cotacao com RLS' || E'\n', case when (select relrowsecurity from pg_class where relname='pedidos_cotacao') then 'OK' else 'FALHA' end);
  r := r || format('A20 %s índice por proposta' || E'\n', case when exists (select 1 from pg_indexes where indexname='pedidos_cotacao_proposta_idx') then 'OK' else 'FALHA' end);
  r := r || format('A21 %s único proposta+transportadora' || E'\n', case when pg_temp.falha(format($q$insert into pedidos_cotacao (proposta_id, transportadora_id, assunto, corpo_html) values (%L,%L,'a','b')$q$, p1, t1)) then 'OK' else 'FALHA' end);
  r := r || format('A22 %s' || E'\n', case when pg_temp.falha(format($q$update pedidos_cotacao set estado='xx' where proposta_id=%L$q$, p1)) then 'OK' else 'FALHA' end);
  r := r || format('A23 %s' || E'\n', case when pg_temp.falha(format($q$update pedidos_cotacao set gerado_por='xx' where proposta_id=%L$q$, p1)) then 'OK' else 'FALHA' end);
  r := r || format('A24 %s FK, cascade e trigger' || E'\n', case when pg_temp.falha($q$insert into pedidos_cotacao (proposta_id, transportadora_id, assunto, corpo_html) values (gen_random_uuid(), gen_random_uuid(),'a','b')$q$)
     and exists (select 1 from pg_constraint where conrelid='pedidos_cotacao'::regclass and contype='f' and confdeltype='c')
     and exists (select 1 from pg_trigger where tgname='pedidos_cotacao_atualizado_em') then 'OK' else 'FALHA' end);

  -- A25-A27 (dados de referência)
  select count(*) into n from produtos;
  r := r || format('A25 %s produtos=%s (validados=%s) RLS=%s' || E'\n', case when n=3 then 'OK' else 'FALHA' end, n, (select count(*) from produtos where validado),
      (select bool_and(relrowsecurity) from pg_class where relname in ('produtos','proposta_compliance')));
  r := r || format('A26 %s regras "*" total=%s regra_ue=%s api_usitc=%s tabela_manual=%s' || E'\n',
      case when (select count(*) from requisitos_pais where codigo_pautal='*')=12
            and (select count(*) from requisitos_pais where codigo_pautal='*' and metodo='regra_ue')=6
            and (select count(*) from requisitos_pais where codigo_pautal='*' and metodo='api_usitc')=1
            and (select count(*) from requisitos_pais where codigo_pautal='*' and metodo='tabela_manual')=5 then 'OK' else 'FALHA' end,
      (select count(*) from requisitos_pais where codigo_pautal='*'), (select count(*) from requisitos_pais where codigo_pautal='*' and metodo='regra_ue'),
      (select count(*) from requisitos_pais where codigo_pautal='*' and metodo='api_usitc'), (select count(*) from requisitos_pais where codigo_pautal='*' and metodo='tabela_manual'));
  begin
    insert into proposta_compliance (proposta_id,destino_pais,metodo,estado) values (p1,'ES','tabela_manual','a_verificar_manualmente');
    r := r || 'A27 OK taxa nula aceite' || E'\n';
  exception when others then r := r || 'A27 FALHA ' || sqlerrm || E'\n';
  end;

  -- B1-B8
  r := r || format('B1 %s token de 64 caracteres=%s' || E'\n', case when (select length(token_confirmacao) from propostas where id=p1)=64 then 'OK' else 'FALHA' end, (select length(token_confirmacao) from propostas where id=p1));
  r := r || format('B2 %s token único' || E'\n', case when (select token_confirmacao from propostas where id=p1) <> (select token_confirmacao from propostas where id=p2)
        and pg_temp.falha(format($q$update propostas set token_confirmacao=(select token_confirmacao from propostas where id=%L) where id=%L$q$, p1, p2)) then 'OK' else 'FALHA' end);
  insert into expedicoes (proposta_id) values (p1);
  r := r || format('B3 %s expedição única por proposta' || E'\n', case when pg_temp.falha(format($q$insert into expedicoes (proposta_id) values (%L)$q$, p1)) then 'OK' else 'FALHA' end);
  r := r || format('B4 %s' || E'\n', case when pg_temp.falha(format($q$update expedicoes set estado='x' where proposta_id=%L$q$, p1)) then 'OK' else 'FALHA' end);
  r := r || format('B5 %s' || E'\n', case when pg_temp.falha(format($q$update expedicoes set modo='x' where proposta_id=%L$q$, p1)) then 'OK' else 'FALHA' end);
  r := r || format('B6 %s dias negativos' || E'\n', case when pg_temp.falha(format($q$update expedicoes set tempo_producao_dias=-1 where proposta_id=%L$q$, p1)) then 'OK' else 'FALHA' end);
  r := r || format('B7 %s FK' || E'\n', case when pg_temp.falha($q$insert into expedicoes (proposta_id) values (gen_random_uuid())$q$) then 'OK' else 'FALHA' end);
  ok := true;
  begin
    set local role anon;
    perform 1 from expedicoes limit 1; get diagnostics n = row_count; ok := (n=0);
  exception when insufficient_privilege then ok := true;
  end;
  reset role;
  r := r || format('B8 %s anon sem acesso; vista v_expedicoes=%s linha(s)' || E'\n', case when ok and exists (select 1 from pg_views where viewname='v_expedicoes') then 'OK' else 'FALHA' end, (select count(*) from v_expedicoes));

  raise exception E'BATERIA SUPABASE (revertida)\n%\nFALHAS: %', r, (length(r) - length(replace(r,'FALHA','')))/5;
end $t$;
