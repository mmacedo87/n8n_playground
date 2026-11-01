// Read Outlook · "Preparar pedido para WF2"
// Converte o texto livre do WF1 nos valores exatos que o WF2 aceita, um item por email.
// Só marca pronto=true se o WF1 tem confiança >= 0.8, não falta nenhum campo e todos os valores mapeiam.
// lead_id: o lead gravado para este email (procura por origem_email_id), para a proposta ficar ligada ao lead.
const txt = (v) => String(v ?? '').toLowerCase();
let leads = [];
try { leads = $('Gravar lead (rascunho)').all().map(i => i.json).filter(l => l && l.id && l.origem_email_id); } catch (e) { leads = []; }

return $input.all().map((_, idx) => {
  const w = $('Extrair pedido (WF1)').itemMatching(idx).json;
  const motivos = [];

  const p = txt(w.produto);
  let produto = '';
  if (/p[óo]\b|powder|dust/.test(p)) produto = 'Pó de cortiça';
  else if (/aglom|agglom|block|board/.test(p)) produto = 'Aglomerado de cortiça';
  else if (/granul|infill|grit/.test(p)) produto = 'Granulado de cortiça';
  if (!produto) motivos.push('produto');

  const dn = parseFloat(String(w.densidade ?? '').replace(',', '.').match(/\d+(?:\.\d+)?/)?.[0]);
  let densidade = '';
  if (Number.isFinite(dn)) {
    if (dn >= 60 && dn < 80) densidade = '60-80 kg/m3';
    else if (dn >= 80 && dn < 100) densidade = '80-100 kg/m3';
    else if (dn >= 100 && dn < 120) densidade = '100-120 kg/m3';
    else if (dn >= 120 && dn <= 150) densidade = '120-150 kg/m3';
  }
  if (!densidade) motivos.push('densidade');

  const gm = String(w.granulometria ?? '').replace(/,/g, '.').match(/(\d+(?:\.\d+)?)\s*(?:-|–|\/|a|to)\s*(\d+(?:\.\d+)?)/i);
  const gran = gm ? `${parseFloat(gm[1])}-${parseFloat(gm[2])} mm` : '';
  const granulometria = ['0-1 mm', '1-2 mm', '2-4 mm', '4-8 mm', '8-15 mm'].includes(gran) ? gran : '';
  if (!granulometria) motivos.push('granulometria');

  const e = txt(w.embalagem);
  let embalagem = '';
  if (/big\s*-?\s*bag/.test(e)) embalagem = 'Big bag 1 m3';
  else if (/granel|bulk/.test(e)) embalagem = 'A granel';
  else if (/saco|sack|bag|palet|pallet/.test(e)) embalagem = 'Sacos 25 kg em palete';
  if (!embalagem) motivos.push('embalagem');

  const incoterm = String(w.incoterm ?? '').trim().toUpperCase();
  if (!['EXW', 'FCA', 'FAS', 'FOB', 'CFR', 'CIF', 'CPT', 'CIP', 'DAP', 'DPU', 'DDP'].includes(incoterm)) motivos.push('incoterm');

  const destino = String(w.destino_pais ?? '').trim().toUpperCase();
  if (!['ES', 'FR', 'DE', 'IT', 'NL', 'BE', 'GB', 'US', 'BR', 'CN', 'JP', 'MA'].includes(destino)) motivos.push('destino');

  let quantidade = Number(w.quantidade);
  const un = txt(w.unidade);
  if (/^(t|ton|tons|tonne|tonnes|tonelada|toneladas)$/.test(un.trim())) quantidade *= 1000;
  if (!(quantidade > 0)) motivos.push('quantidade');

  const cliente = String(w.empresa || w.remetente_nome || '').trim();
  if (!cliente) motivos.push('cliente');

  if (w.falhou_llm) motivos.push('falhou_llm');
  if (!w.e_pedido) motivos.push('nao_e_pedido');
  if (Number(w.confianca) < 0.8) motivos.push('confianca_baixa');
  if (Array.isArray(w.campos_em_falta) && w.campos_em_falta.length) motivos.push('campos_em_falta');

  const contacto_email = String(w.contacto_email || w.remetente_email || '').trim().toLowerCase();
  const lead = leads.find(l => l.origem_email_id === w.email_id);

  return { json: { pronto: motivos.length === 0, motivos: motivos.join(','), cliente, produto, densidade, granulometria, quantidade, embalagem, incoterm, destino, contacto_email, email_id: w.email_id, lead_id: lead ? lead.id : '' } };
});
