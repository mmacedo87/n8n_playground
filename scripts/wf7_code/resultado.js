const cfg = $('Configuração').first().json;
const r = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const fmt = (n, d = 2) => { const x = Number(n); if (n === null || n === undefined || n === '' || !isFinite(x)) return '-'; const p = Math.abs(x).toFixed(d).split('.'); return (x < 0 ? '-' : '') + p[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + (d ? ',' + p[1] : ''); };
const dataPt = (v) => /^\d{4}-\d{2}-\d{2}/.test(String(v || '')) ? String(v).slice(8, 10) + '/' + String(v).slice(5, 7) + '/' + String(v).slice(0, 4) : '-';
const httpDe = (e) => /expirou/.test(e) ? 410 : /permissão/.test(e) ? 403 : /não é válida/.test(e) ? 404 : /estado/.test(e) ? 409 : 400;
const CSS = 'body{font-family:Arial,Helvetica,sans-serif;background:#f7efe2;color:#2a1c11;max-width:640px;margin:24px auto;padding:0 16px;line-height:1.45}h1{font-size:24px}table{border-collapse:collapse;width:100%;background:#fff;border:2px solid #3e5b3a;border-radius:10px}td{padding:6px 12px;border-bottom:1px solid #e3d5bf}td.v{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.total td{font-size:20px;font-weight:bold}.aviso{background:#fff3cd;border-left:4px solid #c9a227;padding:8px 12px;margin:10px 0}.erro{background:#fde8e5;border-left:4px solid #a3261b;padding:8px 12px}.ok{background:#e6f1e4;border-left:4px solid #3e5b3a;padding:8px 12px}a{color:#3e5b3a;font-weight:bold}';
const moldura = (titulo, corpo) => '<!doctype html><html lang="pt-PT"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>' + esc(titulo) + '</title><style>' + CSS + '</style></head><body>' + corpo + '</body></html>';
const voltar = cfg.url_pagina + '?t=' + encodeURIComponent(cfg.token);
if (!r.ok) {
  const erro = String(r.erro || 'Não foi possível gravar o preço.');
  return [{ json: { gravado: false, http: httpDe(erro), html: moldura('Preço não gravado', '<h1>O preço não foi gravado</h1><p class="erro">' + esc(erro) + '</p><p><a href="' + esc(voltar) + '">Voltar à página do preço</a></p>') } }];
}
const REG = { pt_normal: 'IVA 23 %', ue_isento: 'Isento, UE (art. 14.º RITI)', exportacao_isento: 'Isento, exportação (art. 14.º CIVA)', outro: 'IVA ' + fmt(r.iva_pct) + ' %' };
const linha = (k, v, cls) => '<tr' + (cls ? ' class="' + cls + '"' : '') + '><td>' + esc(k) + '</td><td class="v">' + v + '</td></tr>';
const avisos = Array.isArray(r.avisos) ? r.avisos : [];
const corpo = '<h1>Preço gravado · ' + esc(r.codigo) + '</h1><p class="ok">' + (r.preco_alterado ? 'O preço foi alterado (antes: ' + fmt(r.preco_anterior) + ' €).' : 'O preço ficou definido.') + '</p>'
  + avisos.map(a => '<p class="aviso">' + esc(a) + '</p>').join('')
  + '<table>' + linha('Produto: ' + fmt(r.quantidade_kg, 0) + ' kg × ' + fmt(r.preco_kg, 4) + ' €/kg' + (Number(r.desconto_pct) ? ' − ' + fmt(r.desconto_pct) + ' %' : ''), fmt(r.valor_produto) + ' €')
  + linha('Frete' + (r.frete_corrigido ? ' (valor corrigido à mão)' : ''), fmt(r.valor_frete) + ' €') + linha('Valor líquido', fmt(r.valor_liquido) + ' €')
  + linha(REG[r.iva_regime] || 'IVA', fmt(r.valor_iva) + ' €') + linha('Total da proposta', fmt(r.preco_final) + ' €', 'total') + '</table>'
  + '<p>Validade da proposta: até <b>' + dataPt(r.validade_proposta) + '</b>.</p><p>Vai receber por email o resumo atualizado, com um <b>código de aprovação novo</b>. Para aprovar, responda a esse email com OK e o código. Os códigos anteriores deixam de valer.</p><p><a href="' + esc(voltar) + '">Alterar outra vez</a></p>';
const slack = '💶 Preço da *' + r.codigo + '* ' + (r.preco_alterado ? 'alterado' : 'definido') + ' por ' + r.utilizador + ': total ' + fmt(r.preco_final) + ' € (líquido ' + fmt(r.valor_liquido) + ' €, ' + (REG[r.iva_regime] || 'IVA') + ')' + (r.preco_alterado ? ' · antes ' + fmt(r.preco_anterior) + ' €' : '') + (avisos.length ? ' · ⚠️ ' + avisos.length + ' aviso(s)' : '');
return [{ json: { gravado: true, http: 200, codigo: r.codigo, slack_texto: slack, html: moldura('Preço gravado ' + r.codigo, corpo) } }];
