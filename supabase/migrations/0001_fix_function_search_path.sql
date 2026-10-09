-- Fixa o search_path das funções (aviso function_search_path_mutable do Supabase).
-- Aplicada em DEV a 2026-10-06. Sem alteração de comportamento.
alter function public.set_atualizado_em() set search_path = public;
alter function public.proximo_codigo_proposta() set search_path = public;
alter function public.purgar_leads_antigos(int) set search_path = public;
