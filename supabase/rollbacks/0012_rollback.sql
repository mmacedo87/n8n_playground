-- Reversão da 0012 (preço por formulário). O WF7 deixa de funcionar e o WF5/WF8/WF9/WF13 têm de voltar à versão anterior.
-- Atenção: apaga os preços gravados pelo WF7 (colunas novas e historico_precos). preco_final, preco_tabela,
-- desconto_pct e frete_escolhido_id ficam (já existiam antes da 0012).
drop function if exists gravar_preco_proposta(text, numeric, numeric, uuid, numeric, text, numeric, text, int, text);
drop function if exists contexto_preco(text);
drop function if exists verificar_acesso_preco(text);
drop function if exists preparar_acessos_preco(uuid);
drop function if exists frete_proposto(cotacoes_frete, propostas);
drop function if exists iva_sugerido(text);
drop table if exists historico_precos;
drop table if exists acessos_preco;
alter table propostas
  drop column if exists valor_produto, drop column if exists valor_frete, drop column if exists frete_corrigido,
  drop column if exists valor_liquido, drop column if exists iva_regime, drop column if exists iva_pct,
  drop column if exists valor_iva, drop column if exists cliente_nif, drop column if exists validade_proposta,
  drop column if exists preco_origem, drop column if exists preco_definido_por, drop column if exists preco_definido_em,
  drop column if exists preco_notas;
drop table if exists utilizadores_historico;
drop table if exists utilizadores;
drop function if exists registar_historico_utilizadores();
drop function if exists bloquear_alteracao_historico();
delete from configuracao where chave in ('preco.max_eur_kg', 'preco.max_desconto_pct', 'preco.validade_dias');
comment on column propostas.preco_tabela is null;
comment on column propostas.preco_final is null;
