-- Bateria Supabase do preço por formulário (migração 0012, WF7): P1-P25. Corre numa única instrução e TERMINA SEMPRE
-- com uma exceção que traz o relatório: a transação é revertida e não fica nenhum dado. Utilizadores e propostas de teste
-- são criados aqui (emails @example.invalid); não depende dos dados do projeto.
do $t$
declare
  r text := ''; ok int := 0; falhas int := 0;
  u1 uuid; u2 uuid; p1 uuid; p2 uuid; p3 uuid; p4 uuid; p5 uuid; p6 uuid; c1 uuid; c3 uuid; c4 uuid; c5 uuid;
  t1 text; t2 text; t3 text; t4 text; t5 text; t6 text; tb text; tk text; j jsonb; cod1 text; cod2 text; n int; nperm int;
begin
  insert into utilizadores (nome, email, pode_definir_preco) values ('Teste com permissão', 'com.permissao@example.invalid', true) returning id into u1;
  insert into utilizadores (nome, email, pode_definir_preco) values ('Teste sem permissão', 'sem.permissao@example.invalid', false) returning id into u2;
  select count(*) into nperm from utilizadores where ativo and pode_definir_preco;

  insert into propostas (cliente, produto, densidade, granulometria, quantidade, unidade, embalagem, incoterm, destino_pais, estado)
    values ('P1 PT DAP','Granulado','130','1-2',8000,'kg','big bag','DAP','PT','em_validacao') returning id into p1;
  insert into propostas (cliente, produto, densidade, granulometria, quantidade, unidade, embalagem, incoterm, destino_pais, estado)
    values ('P2 ES FCA','Granulado','130','1-2',8,'t','big bag','FCA','ES','a_cotar') returning id into p2;
  insert into propostas (cliente, produto, densidade, granulometria, quantidade, unidade, embalagem, incoterm, destino_pais, estado)
    values ('P3 US CIF','Granulado','130','1-2',5000,'kg','big bag','CIF','US','a_cotar') returning id into p3;
  insert into propostas (cliente, produto, densidade, granulometria, quantidade, unidade, embalagem, incoterm, destino_pais, estado, n_camioes)
    values ('P4 FR DAP camiao','Granulado','130','1-2',20000,'kg','big bag','DAP','FR','a_cotar',2) returning id into p4;
  insert into propostas (cliente, produto, densidade, granulometria, quantidade, unidade, embalagem, incoterm, destino_pais, estado)
    values ('P5 DE DDP a rever','Granulado','130','1-2',1000,'kg','big bag','DDP','DE','a_cotar') returning id into p5;
  insert into propostas (cliente, produto, densidade, granulometria, quantidade, unidade, embalagem, incoterm, destino_pais, estado)
    values ('P6 aprovada','Granulado','130','1-2',1000,'kg','big bag','EXW','PT','aprovada') returning id into p6;
  insert into cotacoes_frete (proposta_id, preco, moeda, preco_por, validade) values (p1, 1850, 'EUR', 'total', current_date + 60) returning id into c1;
  insert into cotacoes_frete (proposta_id, preco, moeda, preco_por, validade) values (p3, 2400, 'EUR', 'total', current_date + 10) returning id into c3;
  insert into cotacoes_frete (proposta_id, preco, moeda, preco_por) values (p4, 900, 'EUR', 'camiao') returning id into c4;
  insert into cotacoes_frete (proposta_id, preco, moeda, preco_por, revisao) values (p5, 700, 'EUR', 'nao_claro', 'a_rever') returning id into c5;

  select token into t1 from preparar_acessos_preco(p1) where email = 'com.permissao@example.invalid';
  select token into tk from preparar_acessos_preco(p1) where email = 'com.permissao@example.invalid';
  if t1 = tk then ok := ok + 1; r := r || 'P1 OK reutiliza a ligação ainda válida' || E'\n'; else falhas := falhas + 1; r := r || 'P1 FALHA token mudou' || E'\n'; end if;
  select count(*) into n from preparar_acessos_preco(p1);
  if n = nperm then ok := ok + 1; r := r || 'P2 OK só utilizadores ativos com pode_definir_preco' || E'\n'; else falhas := falhas + 1; r := r || format('P2 FALHA n=%s esperado=%s', n, nperm) || E'\n'; end if;
  select token into t2 from preparar_acessos_preco(p2) where email = 'com.permissao@example.invalid';
  select token into t3 from preparar_acessos_preco(p3) where email = 'com.permissao@example.invalid';
  select token into t4 from preparar_acessos_preco(p4) where email = 'com.permissao@example.invalid';
  select token into t5 from preparar_acessos_preco(p5) where email = 'com.permissao@example.invalid';
  select token into t6 from preparar_acessos_preco(p6) where email = 'com.permissao@example.invalid';
  insert into acessos_preco (proposta_id, utilizador_id) values (p1, u2) returning token into tb;

  j := contexto_preco(t1);
  if (j->>'ok')::boolean and (j->>'frete_obrigatorio')::boolean and j->>'iva_sugerido' = 'pt_normal' and jsonb_array_length(j->'cotacoes') = 1 and (j->'cotacoes'->0->>'frete_proposto')::numeric = 1850
    then ok := ok + 1; r := r || 'P3 OK contexto: frete obrigatório, IVA PT, frete proposto 1850' || E'\n'; else falhas := falhas + 1; r := r || 'P3 FALHA ' || j::text || E'\n'; end if;
  j := gravar_preco_proposta(t1, 1.71, 5, c1, null, null, null, null, 30, null);
  if (j->>'ok')::boolean and (j->>'valor_produto')::numeric = 12996.00 and (j->>'valor_frete')::numeric = 1850 and (j->>'valor_iva')::numeric = 3414.58 and (j->>'preco_final')::numeric = 18260.58
    then ok := ok + 1; r := r || 'P4 OK DAP PT: 12996 + 1850 + IVA 3414,58 = 18260,58' || E'\n'; else falhas := falhas + 1; r := r || 'P4 FALHA ' || j::text || E'\n'; end if;
  select codigo_aprovacao into cod1 from propostas where id = p1;
  j := gravar_preco_proposta(t1, 1.80, 0, c1, 2000, null, null, null, 30, null);
  select codigo_aprovacao into cod2 from propostas where id = p1; select count(*) into n from historico_precos where proposta_id = p1;
  if (j->>'ok')::boolean and cod1 <> cod2 and n = 2 and (j->>'frete_corrigido')::boolean and (j->>'preco_alterado')::boolean
    then ok := ok + 1; r := r || 'P5 OK alterar o preço: código de aprovação novo, 2 no histórico, frete corrigido' || E'\n'; else falhas := falhas + 1; r := r || 'P5 FALHA ' || j::text || E'\n'; end if;
  j := gravar_preco_proposta(t2, 1.50, 0, null, null, null, null, null, 30, null);
  if not (j->>'ok')::boolean and j->>'erro' like '%NIF%' then ok := ok + 1; r := r || 'P6 OK isenção UE sem NIF recusada' || E'\n'; else falhas := falhas + 1; r := r || 'P6 FALHA ' || j::text || E'\n'; end if;
  j := gravar_preco_proposta(t2, 1.50, 0, c1, null, null, null, 'es b-12345678', 30, null);
  if (j->>'ok')::boolean and (j->>'quantidade_kg')::numeric = 8000 and (j->>'valor_frete')::numeric = 0 and j->>'iva_regime' = 'ue_isento' and (j->>'preco_final')::numeric = 12000 and jsonb_array_length(j->'avisos') = 1
    then ok := ok + 1; r := r || 'P7 OK FCA ES: 8 t = 8000 kg, sem frete, isento UE, cotação ignorada com aviso' || E'\n'; else falhas := falhas + 1; r := r || 'P7 FALHA ' || j::text || E'\n'; end if;
  j := gravar_preco_proposta(t3, 2, 0, c3, null, null, null, null, 30, null);
  if (j->>'ok')::boolean and j->>'iva_regime' = 'exportacao_isento' and (j->>'preco_final')::numeric = 12400 and jsonb_array_length(j->'avisos') = 1
    then ok := ok + 1; r := r || 'P8 OK CIF US: exportação isenta, aviso de validade da cotação' || E'\n'; else falhas := falhas + 1; r := r || 'P8 FALHA ' || j::text || E'\n'; end if;
  j := gravar_preco_proposta(t4, 1, 0, c4, null, null, null, 'FR12345678901', 30, null);
  if (j->>'ok')::boolean and (j->>'valor_frete')::numeric = 1800 then ok := ok + 1; r := r || 'P9 OK por camião: 900 × 2 = 1800' || E'\n'; else falhas := falhas + 1; r := r || 'P9 FALHA ' || j::text || E'\n'; end if;
  j := gravar_preco_proposta(t5, 1, 0, c5, null, null, null, 'DE123456789', 30, null);
  if not (j->>'ok')::boolean and j->>'erro' like '%escreva o valor do frete%' then ok := ok + 1; r := r || 'P10 OK cotação a rever obriga a escrever o frete' || E'\n'; else falhas := falhas + 1; r := r || 'P10 FALHA ' || j::text || E'\n'; end if;
  j := gravar_preco_proposta(t5, 1, 0, c5, 650, null, null, 'DE123456789', 30, null);
  if (j->>'ok')::boolean and (j->>'valor_frete')::numeric = 650 and (j->>'frete_corrigido')::boolean then ok := ok + 1; r := r || 'P11 OK frete escrito à mão aceite' || E'\n'; else falhas := falhas + 1; r := r || 'P11 FALHA ' || j::text || E'\n'; end if;
  j := gravar_preco_proposta(t4, 1, 0, null, null, null, null, 'FR12345678901', 30, null);
  if not (j->>'ok')::boolean and j->>'erro' like '%escolha uma cotação%' then ok := ok + 1; r := r || 'P12 OK DAP sem cotação recusado' || E'\n'; else falhas := falhas + 1; r := r || 'P12 FALHA ' || j::text || E'\n'; end if;
  j := gravar_preco_proposta(t1, 0, 0, c1, null, null, null, null, 30, null);
  if not (j->>'ok')::boolean then ok := ok + 1; r := r || 'P13 OK €/kg = 0 recusado' || E'\n'; else falhas := falhas + 1; r := r || 'P13 FALHA' || E'\n'; end if;
  j := gravar_preco_proposta(t1, 1, 80, c1, null, null, null, null, 30, null);
  if not (j->>'ok')::boolean and j->>'erro' like '%desconto%' then ok := ok + 1; r := r || 'P14 OK desconto 80 % recusado' || E'\n'; else falhas := falhas + 1; r := r || 'P14 FALHA' || E'\n'; end if;
  j := gravar_preco_proposta(t1, 60, 0, c1, null, null, null, null, 30, null);
  if not (j->>'ok')::boolean then ok := ok + 1; r := r || 'P15 OK €/kg acima do limite recusado' || E'\n'; else falhas := falhas + 1; r := r || 'P15 FALHA' || E'\n'; end if;
  j := gravar_preco_proposta(t1, 1, 0, c1, null, 'exportacao_isento', null, null, 30, null);
  if not (j->>'ok')::boolean and j->>'erro' like '%explique%' then ok := ok + 1; r := r || 'P16 OK regime diferente do sugerido exige nota' || E'\n'; else falhas := falhas + 1; r := r || 'P16 FALHA ' || j::text || E'\n'; end if;
  j := gravar_preco_proposta('abc', 1, 0, c1, null, null, null, null, 30, null);
  if not (j->>'ok')::boolean then ok := ok + 1; r := r || 'P17 OK código de ligação inválido recusado' || E'\n'; else falhas := falhas + 1; r := r || 'P17 FALHA' || E'\n'; end if;
  update acessos_preco set expira_em = now() - interval '1 minute' where token = t5;
  j := contexto_preco(t5);
  if not (j->>'ok')::boolean and j->>'erro' like '%expirou%' then ok := ok + 1; r := r || 'P18 OK ligação expirada recusada' || E'\n'; else falhas := falhas + 1; r := r || 'P18 FALHA ' || j::text || E'\n'; end if;
  j := gravar_preco_proposta(tb, 1.71, 0, c1, null, null, null, null, 30, null);
  if not (j->>'ok')::boolean and j->>'erro' like '%permissão%' then ok := ok + 1; r := r || 'P19 OK utilizador sem permissão recusado' || E'\n'; else falhas := falhas + 1; r := r || 'P19 FALHA ' || j::text || E'\n'; end if;
  update utilizadores set pode_definir_preco = false where id = u1;
  j := contexto_preco(t1);
  if not (j->>'ok')::boolean then ok := ok + 1; r := r || 'P20 OK retirar a permissão bloqueia logo a ligação' || E'\n'; else falhas := falhas + 1; r := r || 'P20 FALHA' || E'\n'; end if;
  update utilizadores set pode_definir_preco = true where id = u1;
  j := contexto_preco(t6);
  if not (j->>'ok')::boolean and j->>'erro' like '%aprovada%' then ok := ok + 1; r := r || 'P21 OK proposta aprovada já não muda de preço' || E'\n'; else falhas := falhas + 1; r := r || 'P21 FALHA ' || j::text || E'\n'; end if;
  select count(*) into n from utilizadores_historico where utilizador_id = u1 and operacao = 'UPDATE';
  if n >= 2 then ok := ok + 1; r := r || 'P22 OK alterações de permissão ficam no histórico' || E'\n'; else falhas := falhas + 1; r := r || format('P22 FALHA n=%s', n) || E'\n'; end if;
  begin delete from historico_precos where proposta_id = p1; falhas := falhas + 1; r := r || 'P23 FALHA histórico de preços apagável' || E'\n';
  exception when others then ok := ok + 1; r := r || 'P23 OK histórico de preços imutável' || E'\n'; end;
  begin delete from utilizadores_historico where utilizador_id = u1; falhas := falhas + 1; r := r || 'P24 FALHA histórico de utilizadores apagável' || E'\n';
  exception when others then ok := ok + 1; r := r || 'P24 OK histórico de utilizadores imutável' || E'\n'; end;
  if not has_function_privilege('anon', 'gravar_preco_proposta(text,numeric,numeric,uuid,numeric,text,numeric,text,integer,text)', 'execute')
     and not has_function_privilege('authenticated', 'contexto_preco(text)', 'execute')
     and has_function_privilege('service_role', 'gravar_preco_proposta(text,numeric,numeric,uuid,numeric,text,numeric,text,integer,text)', 'execute')
     and not has_table_privilege('anon', 'utilizadores', 'select') and not has_table_privilege('authenticated', 'acessos_preco', 'select')
    then ok := ok + 1; r := r || 'P25 OK anon/authenticated sem acesso; service_role executa' || E'\n'; else falhas := falhas + 1; r := r || 'P25 FALHA permissões' || E'\n'; end if;
  raise exception E'BATERIA PREÇO (revertida)\n%\nOK: %  FALHAS: %', r, ok, falhas;
end $t$;
