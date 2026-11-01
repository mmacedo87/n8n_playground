-- Bateria Supabase (A1-A46 e B1-B8). Corre numa única instrução e TERMINA SEMPRE com uma exceção que traz o relatório:
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
  n0 int;
  p1 uuid; p2 uuid; t1 uuid; c1 text; c2 text; v1 uuid; v2 uuid; cf uuid;
  base text := $b$insert into propostas (cliente,produto,densidade,granulometria,quantidade,embalagem,incoterm,destino_pais) values ('T','p','d','g',%s,'e','%s','ES')$b$;
  tabelas text[] := array['contadores_proposta','leads','transportadoras','propostas','cotacoes_frete','requisitos_pais','ai_log','pedidos_cotacao','produtos','proposta_compliance','expedicoes','configuracao'];
  tb text;
  ok boolean;
begin
  -- A1/A2
  select count(*) into n from information_schema.tables where table_schema='public' and table_name = any(tabelas);
  r := r || format('A1 %s tabelas=%s' || E'\n', case when n=12 then 'OK' else 'FALHA' end, n);
  select count(*) into n from pg_class c join pg_namespace s on s.oid=c.relnamespace where s.nspname='public' and c.relname = any(tabelas) and c.relrowsecurity;
  r := r || format('A2 %s RLS ativa=%s' || E'\n', case when n=12 then 'OK' else 'FALHA' end, n);

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
  -- conta em relação aos leads que já existem (a base de desenvolvimento tem leads de teste recentes)
  select count(*) into n0 from leads where criado_em >= now() - interval '12 months' or estado = 'convertido';
  insert into leads (empresa, estado, criado_em) values ('velho','novo', now() - interval '13 months'), ('velho conv','convertido', now() - interval '13 months'), ('novo','novo', now());
  select purgar_leads_antigos(12) into n;
  r := r || format('A13 %s apagados=%s (esperado 1), restantes=%s (esperado %s)' || E'\n', case when n=1 and (select count(*) from leads)=n0+2 then 'OK' else 'FALHA' end, n, (select count(*) from leads), n0+2);

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

  -- A28-A34 (migração 0007: cotações reais)
  select count(*) into n from information_schema.columns where table_schema='public' and (
    (table_name='propostas' and column_name in ('tipo_carga','n_camioes','n_paletes','peso_palete_kg','palete_c_m','palete_l_m','palete_a_m','morada_carga','morada_descarga','cp_descarga')) or
    (table_name='pedidos_cotacao' and column_name in ('versao','substitui_id','conversation_id','ref_transportadora')) or
    (table_name='cotacoes_frete' and column_name in ('pedido_cotacao_id','ref_transportadora','tipo_entrega','data_entrega_pedida','preco_por','n_camioes_incluidos','conversation_id','estado_reserva')) or
    (table_name='transportadoras' and column_name='dominios_aceites'));
  r := r || format('A28 %s colunas novas=%s/23' || E'\n', case when n=23 then 'OK' else 'FALHA' end, n);
  update propostas set tipo_carga='completa', n_camioes=2, n_paletes=66, peso_palete_kg=375, palete_c_m=1.1, palete_l_m=1.1, palete_a_m=2.6, morada_carga='X', morada_descarga='Y', cp_descarga='74350' where id=p1;
  r := r || format('A29 %s propostas: valores válidos aceites; tipo_carga/n_paletes/peso/altura inválidos rejeitados' || E'\n',
    case when (select tipo_carga from propostas where id=p1)='completa'
          and pg_temp.falha(format($q$update propostas set tipo_carga='xx' where id=%L$q$, p1))
          and pg_temp.falha(format($q$update propostas set n_paletes=0 where id=%L$q$, p1))
          and pg_temp.falha(format($q$update propostas set peso_palete_kg=-1 where id=%L$q$, p1))
          and pg_temp.falha(format($q$update propostas set palete_a_m=0 where id=%L$q$, p1)) then 'OK' else 'FALHA' end);
  select id into v1 from pedidos_cotacao where proposta_id=p1 and transportadora_id=t1 and versao=1;
  insert into pedidos_cotacao (proposta_id, transportadora_id, assunto, corpo_html, versao, substitui_id, conversation_id, ref_transportadora) values (p1, t1, 'a2', 'b2', 2, v1, 'conv-1', 'Q-1') returning id into v2;
  r := r || format('A30 %s pedido versao 2 aceite; mesma versão repetida e versao 0 rejeitadas' || E'\n',
    case when v2 is not null
          and pg_temp.falha(format($q$insert into pedidos_cotacao (proposta_id, transportadora_id, assunto, corpo_html, versao) values (%L,%L,'a','b',2)$q$, p1, t1))
          and pg_temp.falha(format($q$insert into pedidos_cotacao (proposta_id, transportadora_id, assunto, corpo_html, versao) values (%L,%L,'a','b',0)$q$, p1, t1)) then 'OK' else 'FALHA' end);
  r := r || format('A31 %s substitui_id com FK e índice por conversa' || E'\n',
    case when pg_temp.falha(format($q$update pedidos_cotacao set substitui_id=gen_random_uuid() where id=%L$q$, v2))
          and exists (select 1 from pg_indexes where indexname='pedidos_cotacao_conversation_idx') then 'OK' else 'FALHA' end);
  insert into cotacoes_frete (proposta_id, transportadora_id, pedido_cotacao_id, preco, tipo_entrega, data_entrega_pedida, preco_por, n_camioes_incluidos, ref_transportadora, conversation_id, condicoes)
    values (p1, t1, v2, 1702.50, 'janela', '2026-07-02', 'nao_claro', 2, 'Q-1', 'conv-1', 'na semana, não fixo') returning id into cf;
  r := r || format('A32 %s cotação com condições aceite; estado_reserva por omissão=%s' || E'\n',
    case when (select estado_reserva from cotacoes_frete where id=cf)='nenhuma' then 'OK' else 'FALHA' end, (select estado_reserva from cotacoes_frete where id=cf));
  r := r || format('A33 %s tipo_entrega, preco_por, estado_reserva e n_camioes inválidos rejeitados' || E'\n',
    case when pg_temp.falha(format($q$update cotacoes_frete set tipo_entrega='xx' where id=%L$q$, cf))
          and pg_temp.falha(format($q$update cotacoes_frete set preco_por='xx' where id=%L$q$, cf))
          and pg_temp.falha(format($q$update cotacoes_frete set estado_reserva='xx' where id=%L$q$, cf))
          and pg_temp.falha(format($q$update cotacoes_frete set n_camioes_incluidos=0 where id=%L$q$, cf)) then 'OK' else 'FALHA' end);
  update transportadoras set dominios_aceites = array['pt.dsv.com','dsv.com'] where id=t1;
  r := r || format('A34 %s dominios_aceites: minúsculas sem @ aceites; com @ ou maiúsculas rejeitados' || E'\n',
    case when (select dominios_aceites from transportadoras where id=t1) = array['pt.dsv.com','dsv.com']
          and pg_temp.falha(format($q$update transportadoras set dominios_aceites=array['x@dsv.com'] where id=%L$q$, t1))
          and pg_temp.falha(format($q$update transportadoras set dominios_aceites=array['DSV.com'] where id=%L$q$, t1)) then 'OK' else 'FALHA' end);
  delete from pedidos_cotacao where id=v2;
  r := r || format('A35 %s apagar o pedido deixa cotacoes_frete.pedido_cotacao_id a nulo' || E'\n',
    case when (select pedido_cotacao_id from cotacoes_frete where id=cf) is null then 'OK' else 'FALHA' end);

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

  -- A36-A39 (migração 0008, AI Act)
  r := r || format('A36 %s anon/authenticated sem permissões nas tabelas' || E'\n', case when not exists (select 1 from information_schema.role_table_grants where table_schema='public' and grantee in ('anon','authenticated')) then 'OK' else 'FALHA' end);
  r := r || format('A37 %s anon sem execução das funções (purgar_leads_antigos, proximo_codigo_proposta)' || E'\n', case when not exists (select 1 from pg_proc pr join pg_namespace ns on ns.oid=pr.pronamespace where ns.nspname='public' and has_function_privilege('anon', pr.oid, 'execute')) then 'OK' else 'FALHA' end);
  r := r || format('A38 %s código de aprovação com 6 caracteres e distinto entre propostas' || E'\n', case when (select length(codigo_aprovacao) from propostas where id=p1)=6 and (select codigo_aprovacao from propostas where id=p1) <> (select codigo_aprovacao from propostas where id=p2) then 'OK' else 'FALHA' end);
  r := r || format('A39 %s produto só fica validado com validado_por e validado_em' || E'\n', case when pg_temp.falha($q$update produtos set validado=true where produto=(select produto from produtos limit 1)$q$) then 'OK' else 'FALHA' end);

  -- A40-A43 (migração 0009: configuracao e estado rascunho)
  r := r || format('A40 %s modo_envio existe com valor válido; RLS ativa; anon sem acesso' || E'\n', case when (select valor from configuracao where chave='modo_envio') in ('automatico','revisao') and (select relrowsecurity from pg_class where oid='public.configuracao'::regclass) and not has_table_privilege('anon','public.configuracao','select') and not has_table_privilege('authenticated','public.configuracao','select') then 'OK' else 'FALHA' end);
  r := r || format('A41 %s rejeita modo_envio inválido; aceita automatico e revisao' || E'\n', case when pg_temp.falha($q$update configuracao set valor='talvez' where chave='modo_envio'$q$) and not pg_temp.falha($q$update configuracao set valor='revisao' where chave='modo_envio'$q$) and not pg_temp.falha($q$update configuracao set valor='automatico' where chave='modo_envio'$q$) then 'OK' else 'FALHA' end);
  r := r || format('A42 %s trigger atualizado_em presente em configuracao' || E'\n', case when exists (select 1 from pg_trigger where tgrelid='public.configuracao'::regclass and tgname='configuracao_atualizado_em') then 'OK' else 'FALHA' end);
  r := r || format('A43 %s pedidos_cotacao aceita estado rascunho e rejeita estado inválido' || E'\n', case when not pg_temp.falha(format($q$insert into pedidos_cotacao (proposta_id, transportadora_id, assunto, corpo_html, estado, versao) values (%L, %L, 'a', 'b', 'rascunho', 98)$q$, p1, t1)) and pg_temp.falha(format($q$insert into pedidos_cotacao (proposta_id, transportadora_id, assunto, corpo_html, estado, versao) values (%L, %L, 'a', 'b', 'quase', 97)$q$, p1, t1)) then 'OK' else 'FALHA' end);

  -- A44-A45 (migração 0010: lead convertido quando fica ligado a uma proposta)
  insert into leads (empresa, origem_email_id) values ('Lead teste A44', 'bateria-a44') returning id into v1;
  insert into propostas (cliente,produto,densidade,granulometria,quantidade,embalagem,incoterm,destino_pais,lead_id) values ('T44','p','d','g',10,'e','FOB','ES',v1) returning id into v2;
  r := r || format('A44 %s proposta criada com lead_id marca o lead como convertido' || E'\n', case when (select estado from leads where id=v1)='convertido' then 'OK' else 'FALHA' end);
  insert into leads (empresa, origem_email_id) values ('Lead teste A45', 'bateria-a45') returning id into cf;
  update propostas set lead_id=cf where id=p1;
  r := r || format('A45 %s ligar uma proposta existente a um lead também o converte; anon sem execução da função' || E'\n', case when (select estado from leads where id=cf)='convertido' and not has_function_privilege('anon','public.marcar_lead_convertido()','execute') then 'OK' else 'FALHA' end);

  -- A46 (migração 0011: código secreto do link do plano)
  r := r || format('A46 %s token_plano com 64 hex, distinto entre propostas e do token do cliente; formato inválido rejeitado' || E'\n', case when (select token_plano from propostas where id=p1) ~ '^[0-9a-f]{64}$' and (select token_plano from propostas where id=p1) <> (select token_plano from propostas where id=p2) and (select token_plano <> token_confirmacao from propostas where id=p1) and pg_temp.falha(format($q$update propostas set token_plano='abc' where id=%L$q$, p1)) and pg_temp.falha(format($q$update propostas set token_plano=(select token_plano from propostas where id=%L) where id=%L$q$, p1, p2)) then 'OK' else 'FALHA' end);

  raise exception E'BATERIA SUPABASE (revertida)\n%\nFALHAS: %', r, (length(r) - length(replace(r,'FALHA','')))/5;
end $t$;
