-- Reversão da 0010. Os leads já marcados 'convertido' ficam como estão (são dados, não estrutura).
drop trigger if exists propostas_lead_convertido on propostas;
drop function if exists marcar_lead_convertido();
