const cfg = $('Normalizar código').first().json;
const p = $('Ler proposta').first().json;
if (!p || !p.id) throw new Error('Envio ao cliente: proposta ' + cfg.codigo + ' não encontrada.');
if (p.estado !== 'aprovada') throw new Error('Envio ao cliente: a proposta ' + p.codigo + ' está no estado ' + p.estado + ' e só se envia no estado aprovada.');
const emailCliente = String(p.contacto_email || '').trim();
if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(emailCliente)) throw new Error('Envio ao cliente: a proposta ' + p.codigo + ' não tem um email de cliente válido.');
const preco = Number(p.preco_final);
if (!(preco > 0)) throw new Error('Envio ao cliente: a proposta ' + p.codigo + ' ainda não tem preço final (definir no WF7). Nada foi enviado.');
if (!p.token_confirmacao || new Date(p.token_expira_em) < new Date()) throw new Error('Envio ao cliente: a ligação de confirmação da proposta ' + p.codigo + ' expirou ou não existe.');
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const teste = !!cfg.destinatario_teste;
const pt = ['PT', 'BR', 'AO', 'MZ'].includes(String(p.destino_pais || '').toUpperCase());
const link = cfg.url_confirmacao + '?t=' + encodeURIComponent(p.token_confirmacao);
const moeda = p.moeda || 'EUR';
// Números no formato de cada idioma: 1 234,56 (PT) ou 1,234.56 (EN).
const num = (n, d) => { const x = Number(n); const q = Math.abs(x).toFixed(d).split('.'); const inteiro = q[0].replace(/\B(?=(\d{3})+(?!\d))/g, pt ? ' ' : ','); return (x < 0 ? '-' : '') + inteiro + (d ? (pt ? ',' : '.') + q[1] : ''); };
const eur = (n) => num(n, 2) + ' ' + moeda;
const dataL = (v) => { const s = String(v || ''); return /^\d{4}-\d{2}-\d{2}/.test(s) ? (pt ? s.slice(8, 10) + '/' + s.slice(5, 7) + '/' + s.slice(0, 4) : s.slice(0, 10)) : ''; };
const linha = (k, v, forte) => '<tr><td style="padding:4px 16px 4px 0">' + (forte ? '<b>' + k + '</b>' : k) + '</td><td style="text-align:right">' + (forte ? '<b>' + esc(v) + '</b>' : esc(v)) + '</td></tr>';
const kg = Number(p.quantidade) * (p.unidade === 't' ? 1000 : 1);
const qtd = p.quantidade + ' ' + (p.unidade || 'kg');
const destino = p.destino_pais + (p.destino_local ? ' - ' + p.destino_local : '');
const T = pt
  ? { assunto: 'Proposta comercial - ' + p.produto, ola: 'Exmos. Senhores,', intro: 'Segue a nossa proposta comercial, com a referência <b>' + esc(p.codigo) + '</b>.', prod: 'Produto', den: 'Densidade', gra: 'Granulometria', q: 'Quantidade', emb: 'Embalagem', inc: 'Incoterm', dest: 'Destino', precoTit: 'Preço', unit: 'Preço unitário', desc: 'Desconto', vprod: 'Produto', frete: 'Transporte até ao destino', liq: 'Valor líquido', iva: 'IVA', tot: 'Valor total', val: 'Proposta válida até', ISEN: { ue_isento: 'IVA: isento ao abrigo do art. 14.º do RITI (transmissão intracomunitária)', exportacao_isento: 'IVA: isento ao abrigo do art. 14.º do CIVA (exportação)' }, nif: 'NIF do cliente', conf: 'Para confirmar a encomenda, clique na ligação abaixo:', btn: 'Confirmar encomenda', fim: 'Ficamos ao dispor para qualquer esclarecimento.', cump: 'Com os melhores cumprimentos,', sist: 'Equipa comercial (mensagem enviada com o apoio de um sistema automático, revista pela nossa equipa)', teste: 'Email de teste.' }
  : { assunto: 'Commercial proposal - ' + p.produto, ola: 'Dear Sir or Madam,', intro: 'Please find our commercial proposal, reference <b>' + esc(p.codigo) + '</b>.', prod: 'Product', den: 'Density', gra: 'Granulometry', q: 'Quantity', emb: 'Packaging', inc: 'Incoterm', dest: 'Destination', precoTit: 'Price', unit: 'Unit price', desc: 'Discount', vprod: 'Goods', frete: 'Freight to destination', liq: 'Net amount', iva: 'VAT', tot: 'Total amount', val: 'Offer valid until', ISEN: { ue_isento: 'VAT: exempt under article 14 of RITI (intra-Community supply, reverse charge)', exportacao_isento: 'VAT: exempt under article 14 of CIVA (export)' }, nif: 'Customer VAT number', conf: 'To confirm the order, please click the link below:', btn: 'Confirm order', fim: 'Please do not hesitate to contact us if you need any clarification.', cump: 'Best regards,', sist: 'Sales team (sent with the support of an automated system, reviewed by our team)', teste: 'Test email.' };
const temDecomp = p.valor_produto != null && p.valor_liquido != null && p.preco_tabela != null;
let precoHtml = '<table>';
if (temDecomp) {
  precoHtml += linha(T.unit, num(p.preco_tabela, 4) + ' ' + moeda + '/kg × ' + num(kg, 0) + ' kg');
  if (Number(p.desconto_pct) > 0) precoHtml += linha(T.desc, num(p.desconto_pct, 2) + ' %');
  precoHtml += linha(T.vprod, eur(p.valor_produto));
  if (Number(p.valor_frete) > 0) precoHtml += linha(T.frete + ' (' + esc(p.incoterm) + ')', eur(p.valor_frete));
  precoHtml += linha(T.liq, eur(p.valor_liquido));
  precoHtml += linha(T.iva + (p.iva_pct != null ? ' (' + num(p.iva_pct, 0) + ' %)' : ''), eur(p.valor_iva || 0));
}
precoHtml += linha(T.tot, eur(preco), true);
if (p.validade_proposta) precoHtml += linha(T.val, dataL(p.validade_proposta));
precoHtml += '</table>';
if (T.ISEN[p.iva_regime]) precoHtml += '<p style="font-size:13px">' + T.ISEN[p.iva_regime] + (p.cliente_nif ? ' · ' + T.nif + ': ' + esc(p.cliente_nif) : '') + '.</p>';
const assunto = (teste ? '[TESTE] ' : '') + '[' + p.codigo + '] ' + T.assunto;
const corpo = (teste ? '<p><i>' + T.teste + '</i></p>' : '') + '<p>' + T.ola + '</p><p>' + T.intro + '</p><table>' + linha(T.prod, p.produto) + linha(T.den, p.densidade) + linha(T.gra, p.granulometria) + linha(T.q, qtd) + linha(T.emb, p.embalagem) + linha(T.inc, p.incoterm) + linha(T.dest, destino) + '</table><h3>' + T.precoTit + '</h3>' + precoHtml + '<p>' + T.conf + '</p><p><a href="' + link + '" style="background:#2f6b4f;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none">' + T.btn + '</a></p><p>' + T.fim + '</p><p>' + T.cump + '<br>' + T.sist + '</p>';
const slack = '📤 Proposta *' + p.codigo + '* enviada ao cliente · ' + p.produto + ' · ' + num(preco, 2) + ' ' + moeda + (teste ? ' · (teste, redirecionada)' : '');
return [{ json: { codigo: p.codigo, assunto, corpo_html: corpo, para: teste ? cfg.destinatario_teste : emailCliente, cc: cfg.cc_barbara, slack_texto: slack, idioma: pt ? 'pt' : 'en' } }];
