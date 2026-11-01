const cfg = $('Configuração').first().json;
const b = cfg.form || {};
// Números: aceita vírgula ou ponto. Vazio = null. Texto inválido = valor impossível, que a função na BD recusa com mensagem clara.
const num = (v, invalido) => { const s = String(v == null ? '' : v).trim().replace(/\s/g, '').replace(',', '.'); if (s === '') return null; const x = Number(s); return Number.isFinite(x) ? x : invalido; };
const uuid = (v) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(v || '').trim()) ? String(v).trim().toLowerCase() : null;
const txt = (v, n) => { const s = String(v == null ? '' : v).trim().slice(0, n); return s === '' ? null : s; };
const dias = num(b.validade_dias, 0);
return [{ json: { rpc: {
  p_token: cfg.token,
  p_preco_kg: num(b.preco_kg, null),
  p_desconto_pct: num(b.desconto_pct, -1),
  p_cotacao_id: uuid(b.cotacao_id),
  p_valor_frete: num(b.valor_frete, -1),
  p_iva_regime: txt(b.iva_regime, 30),
  p_iva_pct: num(b.iva_pct, -1),
  p_cliente_nif: txt(b.cliente_nif, 20),
  p_validade_dias: dias === null ? null : Math.round(dias),
  p_notas: txt(b.notas, 1000)
} } }];
