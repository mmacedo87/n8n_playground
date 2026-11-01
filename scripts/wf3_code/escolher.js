// WF3 · "Escolher transportadoras" (valida a escolha do LLM e acrescenta os dados da carga e da versão do pedido)
const cfg = $('Configuração').first().json;
const base = $('Listar candidatas').first().json;
const todas = $('Ler transportadoras ativas').all().map(i => i.json).filter(t => t && t.id);
const p = $('Ler proposta').first().json;
const porId = Object.fromEntries(todas.map(t => [t.id, t]));
const candidatas = base.candidatas.map(c => porId[c.id]).filter(Boolean);
const min = Number(cfg.minimo_transportadoras) || 4;
const alvo = base.alvo;
const out = $json.output || {};
const ids = Array.isArray(out.ids) ? [...new Set(out.ids.filter(x => typeof x === 'string'))] : [];
const validos = ids.filter(id => candidatas.some(c => c.id === id));
const modosDe = (t) => (Array.isArray(t.modos) ? t.modos : []);
let sel; let por;
if (candidatas.length <= alvo) { sel = candidatas; por = 'todas'; }
else if (validos.slice(0, alvo).length >= Math.min(min, alvo)) { sel = validos.slice(0, alvo).map(id => porId[id]); por = 'llm'; }
else {
  por = 'regra';
  sel = [];
  for (const m of ['maritimo', 'rodoviario', 'aereo', 'ferroviario']) {
    if (sel.length >= alvo) break;
    if (sel.some(t => modosDe(t).includes(m))) continue;
    const c = candidatas.find(t => !sel.includes(t) && modosDe(t).includes(m));
    if (c) sel.push(c);
  }
  for (const t of candidatas) { if (sel.length >= alvo) break; if (!sel.includes(t)) sel.push(t); }
}
sel = sel.slice().sort((a, b) => a.nome.localeCompare(b.nome));
const total = base.ja_contactadas + sel.length;
const motivo = por === 'llm' ? String(out.motivo || '').slice(0, 300) : '';
const ver = (id) => base.candidatas.find(c => c.id === id) || {};
const n = (v) => (v === null || v === undefined || v === '' ? null : v);
return sel.map(t => ({ json: {
  proposta_id: p.id, codigo: p.codigo, produto: p.produto, densidade: p.densidade, granulometria: p.granulometria,
  quantidade: p.quantidade, unidade: p.unidade, embalagem: p.embalagem, incoterm: p.incoterm, destino_pais: p.destino_pais,
  tipo_carga: n(p.tipo_carga), n_camioes: n(p.n_camioes), n_paletes: n(p.n_paletes), peso_palete_kg: n(p.peso_palete_kg),
  palete_c_m: n(p.palete_c_m), palete_l_m: n(p.palete_l_m), palete_a_m: n(p.palete_a_m),
  morada_carga: n(p.morada_carga), morada_descarga: n(p.morada_descarga), cp_descarga: n(p.cp_descarga),
  transportadora_id: t.id, transportadora_nome: t.nome, transportadora_email: t.email, modos: modosDe(t).join(', '),
  abaixo_do_minimo: base.atualizar ? false : total < min, escolhido_por: por, motivo_escolha: motivo, tentativa: base.tentativa || 1,
  atualizar: !!base.atualizar, versao: ver(t.id).versao || 1, substitui_id: ver(t.id).substitui_id || null
} }));
