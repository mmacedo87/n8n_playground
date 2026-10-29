// WF6 · "Validar extração"
// O LLM só extrai. Aqui valida-se tudo em código: tipos, valores, preço presente no texto do email e dúvidas -> a_rever.
// Uma cotação com várias condições (ex. entrega fixa vs. dentro da semana) gera uma linha por condição.
const base = $('Juntar texto do anexo').all().map(i => i.json);
const MODOS = ['rodoviario', 'maritimo', 'aereo', 'ferroviario'];
const ENTREGAS = ['fixa', 'janela', 'sem_data', 'nao_claro'];
const PRECO_POR = ['camiao', 'total', 'palete', 'nao_claro'];
const data = (s) => { const v = String(s || ''); if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return null; const d = new Date(v + 'T00:00:00Z'); return isNaN(d) || d.toISOString().slice(0, 10) !== v ? null : v; };
// o preço tem de aparecer no texto (formatos 1702.50, 1702,50, 1.702,50, 1,702.50, 1 702,50)
const precoNoTexto = (preco, texto) => {
  const t = String(texto).replace(/[ \s]+/g, ' ');
  const sem = t.replace(/(?<=\d) (?=\d{3}\b)/g, '');
  const [int, dec] = preco.toFixed(2).split('.');
  const milhar = int.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const milharEn = int.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  const cands = [`${int}.${dec}`, `${int},${dec}`, `${milhar},${dec}`, `${milharEn}.${dec}`];
  if (dec === '00') cands.push(int, milhar, milharEn);
  return cands.some(c => new RegExp('(?<![\\d.,])' + c.replace(/[.,]/g, m => '\\' + m) + '(?![\\d]|[.,]\\d)').test(sem) || new RegExp('(?<![\\d.,])' + c.replace(/[.,]/g, m => '\\' + m) + '(?![\\d]|[.,]\\d)').test(t));
};
const out = [];
$input.all().forEach((it, idx) => {
  const b = base[idx];
  if (!b) return;
  const o = (it.json && it.json.output) || {};
  const modo = MODOS.includes(o.modo) ? o.modo : null;
  const dias = typeof o.transito_dias === 'number' && o.transito_dias >= 0 ? Math.round(o.transito_dias) : null;
  const validade = data(o.validade);
  const moeda = String(o.moeda || '').slice(0, 3).toUpperCase();
  const ref = o.ref_transportadora ? String(o.ref_transportadora).replace(/\s+/g, ' ').trim().slice(0, 60) : null;
  let conf = typeof o.confianca === 'number' ? Math.min(1, Math.max(0, o.confianca)) : 0;
  const anexoPendente = !!b.tem_anexos && !b.anexo_lido;
  const minConf = b.anexo_lido ? 0.9 : 0.8;
  const avisos = [];
  if (anexoPendente) avisos.push('Há anexos que não foi possível ler (PDF digitalizado ou outro tipo): rever manualmente');

  // opções: aceita as novas (opcoes[]) ou o formato antigo (preco único)
  let brutas = Array.isArray(o.opcoes) ? o.opcoes.slice(0, 5) : [];
  if (!brutas.length && typeof o.preco === 'number') brutas = [{ preco: o.preco, tipo_entrega: 'nao_claro', preco_por: 'nao_claro' }];
  const opcoes = [];
  for (const x of brutas) {
    if (!x || typeof x.preco !== 'number' || !(x.preco > 0) || x.preco > 1e7) continue;
    const preco = Math.round(x.preco * 100) / 100;
    const noTexto = precoNoTexto(preco, b.texto);
    if (!noTexto) avisos.push(`O preço ${preco} não aparece no texto do email`);
    opcoes.push({
      preco, noTexto,
      tipo_entrega: ENTREGAS.includes(x.tipo_entrega) ? x.tipo_entrega : 'nao_claro',
      data_entrega_pedida: data(x.data_entrega_pedida),
      preco_por: PRECO_POR.includes(x.preco_por) ? x.preco_por : 'nao_claro',
      n_camioes_incluidos: Number.isInteger(x.n_camioes_incluidos) && x.n_camioes_incluidos > 0 && x.n_camioes_incluidos < 100 ? x.n_camioes_incluidos : null,
      descricao: x.descricao ? String(x.descricao).replace(/\s+/g, ' ').slice(0, 160) : null,
    });
  }
  const gerais = o.condicoes ? String(o.condicoes).replace(/\s+/g, ' ').slice(0, 300) : '';
  const standby = o.reserva_standby === true;
  const base1 = { proposta_id: b.proposta_id, transportadora_id: b.transportadora_id, transportadora_nome: b.transportadora_nome, codigo: b.codigo, email_id: b.email_id, conversation_id: b.conversation_id || null, pedido_cotacao_id: b.pedido_cotacao_id || null, ref_transportadora: ref, recebida_em: b.recebida_em, modo, transito_dias: dias, validade };
  if (!opcoes.length) {
    out.push({ json: { ...base1, opcao: 0, opcoes_total: 0, preco: null, moeda: null, tipo_entrega: null, data_entrega_pedida: null, preco_por: null, n_camioes_incluidos: null, estado_reserva: standby ? 'standby' : 'nenhuma', condicoes: (avisos.concat(gerais ? [gerais] : [])).join(' · ').slice(0, 460) || 'Sem preço no email: rever manualmente', confianca: Math.min(conf, 0.5), revisao: 'a_rever' } });
    return;
  }
  opcoes.forEach((x, k) => {
    const duvida = x.preco_por === 'nao_claro' || x.tipo_entrega === 'nao_claro';
    const completa = modo !== null && dias !== null && moeda.length === 3;
    const rever = !completa || conf < minConf || anexoPendente || !x.noTexto || duvida;
    const partes = [];
    if (x.descricao) partes.push(x.descricao);
    if (x.preco_por === 'nao_claro') partes.push('Preço: não é claro se é por camião ou total');
    if (x.tipo_entrega === 'nao_claro' && opcoes.length > 1) partes.push('Condição de entrega pouco clara');
    if (standby) partes.push('Reserva em standby: aguarda confirmação nossa');
    if (gerais) partes.push(gerais);
    if (k === 0) avisos.forEach(a => partes.push(a));
    if (b.anexo_lido) partes.push('[dados também lidos do PDF anexo]');
    out.push({ json: { ...base1, opcao: k + 1, opcoes_total: opcoes.length, preco: x.preco, moeda: moeda.length === 3 ? moeda : null, tipo_entrega: x.tipo_entrega, data_entrega_pedida: x.data_entrega_pedida, preco_por: x.preco_por, n_camioes_incluidos: x.n_camioes_incluidos, estado_reserva: standby ? 'standby' : 'nenhuma', condicoes: partes.join(' · ').slice(0, 460) || null, confianca: completa ? conf : Math.min(conf, 0.5), revisao: rever ? 'a_rever' : 'automatica' } });
  });
});
return out;
