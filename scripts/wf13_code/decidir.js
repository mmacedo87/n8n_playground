// WF13 · «Decidir»: valida o pedido da Bárbara/Madalena e prepara o RASCUNHO de confirmação de reserva (nunca envia).
const cfg = $('Normalizar pedido').first().json;
const p = $('Ler proposta').first().json;
if (!p || !p.id) throw new Error('Confirmação de reserva: proposta ' + cfg.codigo + ' não encontrada.');
const acao = cfg.acao;
if (!['rascunho', 'confirmada', 'cancelada'].includes(acao)) throw new Error('Confirmação de reserva: ação inválida.');
if (acao !== 'cancelada' && !['aprovada', 'enviada', 'aceite', 'em_expedicao'].includes(p.estado)) throw new Error('Confirmação de reserva: a proposta ' + cfg.codigo + ' está no estado ' + p.estado + '; só se confirma a reserva depois de aprovada.');
const cots = $('Ler cotações').all().map(i => i.json).filter(c => c && c.id);
const transps = {};
$('Ler transportadoras').all().forEach(i => { if (i.json && i.json.id) transps[i.json.id] = i.json; });
const norm = (s) => String(s == null ? '' : s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
const nome = norm(cfg.transportadora);
const ref = norm(cfg.ref_transportadora);
let cand = cots.filter(c => transps[c.transportadora_id] && norm(transps[c.transportadora_id].nome) === nome);
if (cand.length === 0) throw new Error('Confirmação de reserva: a transportadora «' + cfg.transportadora + '» não tem cotação na proposta ' + cfg.codigo + '. Use o nome exatamente como no resumo.');
if (ref) cand = cand.filter(c => norm(c.ref_transportadora) === ref);
if (cand.length === 0) throw new Error('Confirmação de reserva: nenhuma cotação de «' + cfg.transportadora + '» tem a referência «' + cfg.ref_transportadora + '».');
if (cand.length > 1) throw new Error('Confirmação de reserva: «' + cfg.transportadora + '» tem ' + cand.length + ' cotações na proposta ' + cfg.codigo + '; indique a referência da transportadora (' + cand.map(c => c.ref_transportadora || 'sem ref.').join(', ') + ').');
const c = cand[0];
const t = transps[c.transportadora_id];
const atual = c.estado_reserva || 'nenhuma';
const outraConfirmada = cots.find(x => x.id !== c.id && x.estado_reserva === 'confirmada');
if (acao !== 'cancelada') {
  if (c.revisao === 'a_rever') throw new Error('Confirmação de reserva: a cotação está marcada «a rever»; valide o preço e as condições antes de a escolher.');
  if (c.preco === null || c.preco === undefined || c.preco === '') throw new Error('Confirmação de reserva: a cotação não tem preço registado.');
  if (outraConfirmada) throw new Error('Confirmação de reserva: já existe outra cotação confirmada para a proposta ' + cfg.codigo + '. Cancele-a primeiro.');
  if (atual === 'confirmada') throw new Error('Confirmação de reserva: esta cotação já está confirmada.');
  if (acao === 'confirmada' && !['standby', 'rascunho'].includes(atual)) throw new Error('Confirmação de reserva: só se confirma uma reserva em standby ou com rascunho criado (estado atual: ' + atual + ').');
  if (acao === 'rascunho' && !['nenhuma', 'standby', 'rascunho', 'cancelada'].includes(atual)) throw new Error('Confirmação de reserva: estado de reserva inesperado (' + atual + ').');
} else if (!['standby', 'rascunho', 'confirmada'].includes(atual)) {
  throw new Error('Confirmação de reserva: não há reserva a cancelar (estado atual: ' + atual + ').');
}
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const tem = (v) => v !== null && v !== undefined && v !== '';
const dataPt = (d) => (/^\d{4}-\d{2}-\d{2}/.test(String(d || '')) ? String(d).slice(8, 10) + '/' + String(d).slice(5, 7) + '/' + String(d).slice(0, 4) : String(d || ''));
const ENTREGA = { fixa: 'entrega em data fixa', janela: 'entrega dentro do período indicado', sem_data: 'sem data de entrega fixada' };
const PRECO_POR = { camiao: 'por camião', total: 'valor total', palete: 'por palete' };
const linha = (k, v) => (tem(v) ? '<tr><td style="padding:4px 16px 4px 0"><b>' + k + '</b></td><td>' + esc(v) + '</td></tr>' : '');
const teste = !!cfg.destinatario_teste;
const refTxt = tem(c.ref_transportadora) ? c.ref_transportadora : null;
const assunto = (teste ? '[TESTE] ' : '') + 'Confirmação de reserva' + (refTxt ? ' ' + refTxt : '') + ' [' + p.codigo + ']';
const corpo = (teste ? '<p><i>Rascunho de teste. Destinatário real: ' + esc(t.email) + '.</i></p>' : '')
  + '<p>Exmos. Senhores, vimos por este meio confirmar a reserva do transporte referente ao pedido ' + esc(p.codigo) + (refTxt ? ' (vossa referência ' + esc(refTxt) + ')' : '') + ', nas condições da cotação recebida:</p>'
  + '<table>' + linha('Referência', p.codigo) + linha('Vossa referência', refTxt) + linha('Preço', c.preco + ' ' + (c.moeda || '') + (PRECO_POR[c.preco_por] ? ' (' + PRECO_POR[c.preco_por] + (tem(c.n_camioes_incluidos) ? ', ' + c.n_camioes_incluidos + ' camião(ões)' : '') + ')' : ''))
  + linha('Condição de entrega', (ENTREGA[c.tipo_entrega] || null) && ENTREGA[c.tipo_entrega] + (tem(c.data_entrega_pedida) ? ' (' + dataPt(c.data_entrega_pedida) + ')' : '')) + linha('Modo', c.modo) + linha('Trânsito', tem(c.transito_dias) ? c.transito_dias + ' dias' : null) + '</table>'
  + '<p>Agradecemos a confirmação de receção e a data de recolha.</p><p>Cumprimentos,<br>Equipa comercial (rascunho preparado pelo sistema de propostas)</p>';
const libertar = acao === 'confirmada' ? cots.filter(x => x.id !== c.id && ['standby', 'rascunho'].includes(x.estado_reserva)).map(x => x.id) : [];
return [{ json: {
  acao, proposta_id: p.id, codigo: p.codigo, cotacao_id: c.id, transportadora: t.nome,
  novo_estado: acao === 'cancelada' ? 'cancelada' : acao,
  frete_escolhido_id: acao === 'cancelada' ? null : c.id,
  limpar_frete: acao === 'cancelada' && p.frete_escolhido_id === c.id,
  atualizar_proposta: acao !== 'cancelada' || p.frete_escolhido_id === c.id,
  criar_rascunho: acao === 'rascunho',
  para: teste ? cfg.destinatario_teste : t.email, assunto, corpo_html: corpo, libertar_ids: libertar
} }];
