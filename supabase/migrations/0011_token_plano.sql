-- 0011: código secreto do link do plano de expedição (WF11).
-- Porquê: o formulário do WF11 é aberto pela Madalena a partir de um link no email (WF10/WF13), por isso não leva
-- palavra-passe; sem este código, quem soubesse o URL e um código PRP podia gravar um plano e disparar o follow-up
-- ao cliente (WF12). O link passa a levar ?codigo=PRP-...&t=<token_plano> e o WF11 compara o t com esta coluna.
-- É diferente de token_confirmacao (que vai no email do cliente). Reversão: supabase/rollbacks/0011_rollback.sql.

alter table propostas
  add column token_plano text not null
  default (replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', ''));

alter table propostas add constraint propostas_token_plano_key unique (token_plano);
alter table propostas add constraint propostas_token_plano_formato check (token_plano ~ '^[0-9a-f]{64}$');
