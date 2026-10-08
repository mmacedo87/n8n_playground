-- 1) Remove o índice duplicado criado por engano na 0003.
--    A restrição requisitos_pais_pais_iso_codigo_pautal_key (pais_iso, codigo_pautal) fica como único registo.
drop index if exists public.requisitos_pais_pais_nc_uq;

-- 2) Contagem de tentativas de envio por pedido de cotação.
--    O WF3 ignora as linhas 'falhou' e repete o envio até 5 tentativas; à 6.ª não envia e avisa por email.
alter table public.pedidos_cotacao
  add column if not exists tentativas smallint not null default 1;
