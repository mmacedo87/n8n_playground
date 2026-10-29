-- 0010: quando uma proposta fica ligada a um lead (propostas.lead_id), o lead passa a 'convertido'.
-- Porquê: o Read Outlook passa a ligar a proposta ao lead de origem; um lead convertido não é apagado
-- por purgar_leads_antigos(), por isso a ligação proposta → email de origem não se perde ao fim de 12 meses.
-- Só mexe em leads que ainda não estão 'convertido'. Reversão: supabase/rollbacks/0010_rollback.sql.

create or replace function marcar_lead_convertido()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.lead_id is not null then
    update leads set estado = 'convertido'
     where id = new.lead_id and estado <> 'convertido';
  end if;
  return new;
end;
$$;

revoke execute on function marcar_lead_convertido() from public, anon, authenticated;

create trigger propostas_lead_convertido
  after insert or update of lead_id on propostas
  for each row execute function marcar_lead_convertido();
