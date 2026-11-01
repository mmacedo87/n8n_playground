-- Reversão da migração 0007. ATENÇÃO: apaga os dados guardados nas colunas novas.
-- Se já houver pedidos com versao > 1 para a mesma proposta e transportadora, apagar primeiro as versões antigas,
-- senão a restrição única original não pode ser recriada.

alter table transportadoras drop column if exists dominios_aceites;

alter table cotacoes_frete
  drop column if exists estado_reserva,
  drop column if exists conversation_id,
  drop column if exists n_camioes_incluidos,
  drop column if exists preco_por,
  drop column if exists data_entrega_pedida,
  drop column if exists tipo_entrega,
  drop column if exists ref_transportadora,
  drop column if exists pedido_cotacao_id;

drop index if exists pedidos_cotacao_conversation_idx;
alter table pedidos_cotacao drop constraint if exists pedidos_cotacao_proposta_transp_versao_key;
alter table pedidos_cotacao
  drop column if exists ref_transportadora,
  drop column if exists conversation_id,
  drop column if exists substitui_id,
  drop column if exists versao;
alter table pedidos_cotacao add constraint pedidos_cotacao_unico
  unique (proposta_id, transportadora_id);

alter table propostas
  drop column if exists cp_descarga,
  drop column if exists morada_descarga,
  drop column if exists morada_carga,
  drop column if exists palete_a_m,
  drop column if exists palete_l_m,
  drop column if exists palete_c_m,
  drop column if exists peso_palete_kg,
  drop column if exists n_paletes,
  drop column if exists n_camioes,
  drop column if exists tipo_carga;
