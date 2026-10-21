const cfg = $('Normalizar código').first().json;
const p = $('Ler proposta').first().json;
if (!p || !p.id) throw new Error('Resumo de validação: proposta ' + cfg.codigo + ' não encontrada.');
if (!['pedido', 'a_cotar', 'cotado', 'em_validacao'].includes(p.estado)) throw new Error('Resumo de validação: a proposta ' + cfg.codigo + ' está no estado ' + p.estado + ' e não pode voltar a ser enviada para validação.');
const comp = $('Ler compliance').first().json || {};
const cots = $('Ler cotações').all().map(i => i.json).filter(c => c && c.id);
const nomes = {};
$('Ler transportadoras').all().forEach(i => { if (i.json && i.json.id) nomes[i.json.id] = i.json.nome; });
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const teste = !!cfg.destinatario_teste;
const temComp = !!comp.id;
const compEstado = temComp ? (comp.estado === 'automatico' ? 'automático' : 'a verificar manualmente') : 'ainda não disponível';
const linha = (k, v) => '<tr><td style="padding:4px 16px 4px 0"><b>' + k + '</b></td><td>' + esc(v) + '</td></tr>';
const tem = (v) => v !== null && v !== undefined && v !== '';
// Revisão: «a rever» (em destaque) ou «automática (confiança X %)», com a confiança do LLM em percentagem
const aRever = (c) => c.revisao === 'a_rever';
const revisao = (c) => aRever(c) ? 'a rever' : 'automática' + (tem(c.confianca) && !isNaN(Number(c.confianca)) ? ' (confiança ' + Math.round(Number(c.confianca) * 100) + ' %)' : '');
// Condições da cotação: entrega fixa vs. dentro de uma janela, e preço por camião vs. total
const dataPt = (d) => (/^\d{4}-\d{2}-\d{2}/.test(String(d || '')) ? String(d).slice(8, 10) + '/' + String(d).slice(5, 7) + '/' + String(d).slice(0, 4) : String(d || ''));
const ENTREGA = { fixa: 'data fixa', janela: 'dentro de um período', sem_data: 'sem data indicada', nao_claro: 'não claro' };
const entrega = (c) => (ENTREGA[c.tipo_entrega] || '-') + (tem(c.data_entrega_pedida) ? ' (' + dataPt(c.data_entrega_pedida) + ')' : '');
const PRECO_POR = { camiao: 'por camião', total: 'total', palete: 'por palete', nao_claro: 'âmbito não claro' };
const precoTxt = (c) => (tem(c.preco) ? c.preco + ' ' + (c.moeda || '') : '-') + (PRECO_POR[c.preco_por] ? ' (' + PRECO_POR[c.preco_por] + (tem(c.n_camioes_incluidos) ? ', ' + c.n_camioes_incluidos + ' camião(ões)' : '') + ')' : '');
const RESERVA = { nenhuma: '-', standby: 'em standby', rascunho: 'rascunho de confirmação', confirmada: 'confirmada', cancelada: 'cancelada' };
const td = (v) => '<td style="padding:2px 12px 2px 0">' + esc(v) + '</td>';
const linhasCot = cots.map(c => '<tr' + (aRever(c) ? ' style="background:#fff3cd"' : '') + '>'
  + '<td style="padding:2px 12px 2px 0">' + esc(nomes[c.transportadora_id] || 'transportadora desconhecida') + (tem(c.ref_transportadora) ? '<br><small>ref. ' + esc(c.ref_transportadora) + '</small>' : '') + '</td>'
  + td(c.modo || '-') + td(precoTxt(c)) + td(entrega(c)) + td(c.transito_dias != null ? c.transito_dias + ' dias' : '-') + td(c.validade || '-') + td(RESERVA[c.estado_reserva] || '-')
  + '<td>' + (aRever(c) ? '<b style="color:#b00020">' + esc(revisao(c)) + '</b>' : esc(revisao(c))) + '</td></tr>').join('');
const nRever = cots.filter(aRever).length;
const avisoRever = nRever ? '<p style="color:#b00020"><b>Atenção: ' + nRever + ' cotação(ões) marcada(s) «a rever».</b> Confirme o preço, o âmbito (por camião ou total) e as condições de entrega antes de aprovar.</p>' : '';
const cotHtml = cots.length ? avisoRever + '<table><tr><th align="left">Transportadora</th><th align="left">Modo</th><th align="left">Preço</th><th align="left">Entrega</th><th align="left">Trânsito</th><th align="left">Validade</th><th align="left">Reserva</th><th align="left">Revisão</th></tr>' + linhasCot + '</table>' : '<p>Ainda não há cotações de frete registadas.</p>';
const compHtml = temComp ? '<table>' + linha('Código NC', comp.codigo_nc) + linha('Taxa de direitos', comp.taxa_direitos_pct != null ? comp.taxa_direitos_pct + ' %' : (comp.taxa_texto || 'por confirmar')) + linha('Estado', compEstado) + '</table>' + (comp.requisitos_fitossanitarios ? '<p><b>Requisitos fitossanitários:</b> ' + esc(comp.requisitos_fitossanitarios) + '</p>' : '') + (comp.notas_taxas ? '<p><b>Notas:</b> ' + esc(comp.notas_taxas) + '</p>' : '') : '<p>As notas de compliance ainda não estão disponíveis.</p>';
const assunto = (teste ? '[TESTE] ' : '') + '[' + p.codigo + '] Proposta para validação - ' + p.produto + ' - destino ' + p.destino_pais + (nRever ? ' - ' + nRever + ' cotação(ões) a rever' : '');
// AI Act (H6): a aprovação exige o código desta proposta (coluna codigo_aprovacao), para que um remetente forjado não aprove só com «OK».
const codAprov = tem(p.codigo_aprovacao) ? esc(p.codigo_aprovacao) : null;
const aprovar = '<p><b>' + (codAprov ? 'Para aprovar, responda a este email com OK e o código <span style="font-family:monospace">' + codAprov + '</span> na primeira linha (por exemplo: OK ' + codAprov + ').' : 'Código de aprovação indisponível: contacte o responsável técnico antes de aprovar.') + '</b> Se quiser alterações, responda com o comentário: a proposta continua em validação e a equipa é avisada. Por favor não altere o assunto.</p>';
const corpo = (teste ? '<p><i>Email de teste.</i></p>' : '') + '<p>A proposta <b>' + esc(p.codigo) + '</b> está pronta para a sua revisão. Nada é enviado ao cliente sem a sua validação.</p><table>' + linha('Cliente', p.cliente) + linha('Produto', p.produto) + linha('Densidade', p.densidade) + linha('Granulometria', p.granulometria) + linha('Quantidade', p.quantidade + ' ' + (p.unidade || 'kg')) + linha('Embalagem', p.embalagem) + linha('Incoterm', p.incoterm) + linha('Destino', p.destino_pais) + '</table><h3>Cotações de frete (' + cots.length + ')</h3>' + cotHtml + '<h3>Compliance</h3>' + compHtml + aprovar + '<p>Cumprimentos,<br>Sistema de propostas (mensagem automática)</p>';
const slack = '📝 Proposta *' + p.codigo + '* para validação · ' + p.produto + ' · destino ' + p.destino_pais + ' · cotações: ' + cots.length + (nRever ? ' (' + nRever + ' a rever)' : '') + ' · compliance: ' + compEstado + (teste ? ' · (teste)' : '');
return [{ json: { codigo: p.codigo, assunto, corpo_html: corpo, slack_texto: slack, para: teste ? cfg.destinatario_teste : cfg.destinatario_validacao, cotacoes: cots.length, a_rever: nRever, compliance: compEstado } }];
