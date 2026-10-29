-- Reversão da 0011. Os links do plano de expedição deixam de levar código (o WF11 tem de voltar à versão anterior).
alter table propostas drop constraint if exists propostas_token_plano_formato;
alter table propostas drop constraint if exists propostas_token_plano_key;
alter table propostas drop column if exists token_plano;
