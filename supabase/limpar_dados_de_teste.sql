-- Limpa TODOS os dados de teste (propostas, pedidos de cotação, compliance, logs de IA)
-- e repõe o contador para a primeira proposta real ser PRP-<ano>-0001.
-- Correr uma vez, antes de ir para produção. NÃO tocar em transportadoras, produtos nem requisitos_pais.
begin;
delete from proposta_compliance;
delete from ai_log;
delete from propostas;                       -- apaga em cascata pedidos_cotacao e cotacoes_frete
update contadores_proposta set ultimo = 0;
commit;
