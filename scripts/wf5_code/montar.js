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
const aRever = (c) => c.revisao === 'a_rever';
const revisao = (c) => aRever(c) ? 'a rever' : 'automática' + (tem(c.confianca) && !isNaN(Number(c.confianca)) ? ' (confiança ' + Math.round(Number(c.confianca) * 100) + ' %)' : '');
const dataPt = (d) => (/^\d{4}-\d{2}-\d{2}/.test(String(d || '')) ? String(d).slice(8, 10) + '/' + String(d).slice(5, 7) + '/' + String(d).slice(0, 4) : String(d || ''));
const ENTREGA = { fixa: 'data fixa', janela: 'dentro de um período', sem_data: 'sem data indicada', nao_claro: 'não claro' };
const entrega = (c) => (ENTREGA[c.tipo_entrega] || '-') + (tem(c.data_entrega_pedida) ? ' (' + dataPt(c.data_entrega_pedida) + ')' : '');
const PRECO_POR = { camiao: 'por camião', total: 'total', palete: 'por palete', nao_claro: 'âmbito não claro' };
const precoTxt = (c) => (tem(c.preco) ? c.preco + ' ' + (c.moeda || '') : '-') + (PRECO_POR[c.preco_por] ? ' (' + PRECO_POR[c.preco_por] + (tem(c.n_camioes_incluidos) ? ', ' + c.n_camioes_incluidos + ' camião(ões)' : '') + ')' : '');
const RESERVA = { nenhuma: '-', standby: 'em standby', rascunho: 'rascunho de confirmação', confirmada: 'confirmada', cancelada: 'cancelada' };
const td = (v) => '<td style="padding:2px 12px 2px 0">' + esc(v) + '</td>';
const linhasCot = cots.map(c => '<tr' + (aRever(c) ? ' style="background:#fff3cd"' : '') + '>'
  + '<td style="padding:2px 12px 2px 0">' + esc(nomes[c.transportadora_id] || 'transportadora desconhecida') + (tem(c.ref_transportadora) ? '<br><small>ref. ' + esc(c.ref_transportadora) + '</small>' : '') + (c.id === p.frete_escolhido_id ? '<br><small><b>usada no preço</b></small>' : '') + '</td>'
  + td(c.modo || '-') + td(precoTxt(c)) + td(entrega(c)) + td(c.transito_dias != null ? c.transito_dias + ' dias' : '-') + td(c.validade || '-') + td(RESERVA[c.estado_reserva] || '-')
  + '<td>' + (aRever(c) ? '<b style="color:#b00020">' + esc(revisao(c)) + '</b>' : esc(revisao(c))) + '</td></tr>').join('');
const nRever = cots.filter(aRever).length;
const avisoRever = nRever ? '<p style="color:#b00020"><b>Atenção: ' + nRever + ' cotação(ões) marcada(s) «a rever».</b> Confirme o preço, o âmbito (por camião ou total) e as condições de entrega antes de aprovar.</p>' : '';
const cotHtml = cots.length ? avisoRever + '<table><tr><th align="left">Transportadora</th><th align="left">Modo</th><th align="left">Preço</th><th align="left">Entrega</th><th align="left">Trânsito</th><th align="left">Validade</th><th align="left">Reserva</th><th align="left">Revisão</th></tr>' + linhasCot + '</table>' : '<p>Ainda não há cotações de frete registadas.</p>';
const compHtml = temComp ? '<table>' + linha('Código NC', comp.codigo_nc) + linha('Taxa de direitos', comp.taxa_direitos_pct != null ? comp.taxa_direitos_pct + ' %' : (comp.taxa_texto || 'por confirmar')) + linha('Estado', compEstado) + '</table>' + (comp.requisitos_fitossanitarios ? '<p><b>Requisitos fitossanitários:</b> ' + esc(comp.requisitos_fitossanitarios) + '</p>' : '') + (comp.notas_taxas ? '<p><b>Notas:</b> ' + esc(comp.notas_taxas) + '</p>' : '') : '<p>As notas de compliance ainda não estão disponíveis.</p>';
// Preço (WF7): ligação pessoal de quem recebe este email, se tiver permissão (tabela utilizadores, migração 0012).
const destino = String(teste ? cfg.destinatario_teste : cfg.destinatario_validacao).trim().toLowerCase();
const acessos = $('Preparar ligação do preço (BD)').all().map(i => i.json).filter(a => a && a.token);
const meu = acessos.find(a => String(a.email || '').toLowerCase() === destino) || (teste ? acessos[0] : null);
const linkPreco = meu ? cfg.url_preco + '?t=' + encodeURIComponent(meu.token) : null;
const eur = (n) => { const x = Number(n); if (!isFinite(x)) return '-'; const q = Math.abs(x).toFixed(2).split('.'); return (x < 0 ? '-' : '') + q[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ',' + q[1] + ' €'; };
const REG = { pt_normal: 'IVA 23 %', ue_isento: 'Isento, UE (art. 14.º RITI)', exportacao_isento: 'Isento, exportação (art. 14.º CIVA)', outro: 'IVA ' + p.iva_pct + ' %' };
const temPreco = Number(p.preco_final) > 0;
const botao = (txt) => linkPreco ? '<p><a href="' + esc(linkPreco) + '" style="display:inline-block;background:#3e5b3a;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:bold">' + txt + '</a></p><p style="color:#666;font-size:12px">Ligação pessoal, válida até ' + dataPt(meu.expira_em) + '. Não a reencaminhe.</p>' : '<p style="color:#b00020">Não há nenhum utilizador com permissão para definir preços associado a este email.</p>';
const precoHtml = temPreco
  ? '<table>' + linha('Produto', eur(p.valor_produto) + ' (' + p.preco_tabela + ' €/kg' + (Number(p.desconto_pct) ? ', desconto ' + p.desconto_pct + ' %' : '') + ')') + linha('Frete', eur(p.valor_frete) + (p.frete_corrigido ? ' (corrigido à mão)' : '')) + linha('Valor líquido', eur(p.valor_liquido)) + linha(REG[p.iva_regime] || 'IVA', eur(p.valor_iva)) + '<tr><td style="padding:4px 16px 4px 0"><b>Total da proposta</b></td><td><b>' + eur(p.preco_final) + '</b></td></tr>' + linha('Validade', dataPt(p.validade_proposta)) + '</table>' + (p.preco_notas ? '<p><b>Notas do preço:</b> ' + esc(p.preco_notas) + '</p>' : '') + botao('Alterar o preço')
  : '<p><b>Preço por definir.</b> A proposta só pode ser aprovada depois de o preço estar definido.</p>' + botao('Definir o preço');
const assunto = (teste ? '[TESTE] ' : '') + '[' + p.codigo + '] Proposta para validação - ' + p.produto + ' - destino ' + p.destino_pais + (temPreco ? ' - ' + eur(p.preco_final) : ' - preço por definir') + (nRever ? ' - ' + nRever + ' cotação(ões) a rever' : '');
// AI Act (H6): a aprovação exige o código desta proposta (codigo_aprovacao). Só se mostra com preço definido; o código muda sempre que o preço muda (WF7).
const codAprov = tem(p.codigo_aprovacao) ? esc(p.codigo_aprovacao) : null;
const aprovar = !temPreco
  ? '<p><b>Ainda não pode aprovar:</b> defina primeiro o preço. Depois de o gravar, recebe um resumo novo com o código de aprovação.</p>'
  : '<p><b>' + (codAprov ? 'Para aprovar, responda a este email com OK e o código <span style="font-family:monospace">' + codAprov + '</span> na primeira linha (por exemplo: OK ' + codAprov + ').' : 'Código de aprovação indisponível: contacte o responsável técnico antes de aprovar.') + '</b> Se o preço mudar, os códigos anteriores deixam de valer. Se quiser alterações, responda com o comentário: a proposta continua em validação e a equipa é avisada. Por favor não altere o assunto.</p>';
const corpo = (teste ? '<p><i>Email de teste.</i></p>' : '') + '<p>A proposta <b>' + esc(p.codigo) + '</b> está pronta para a sua revisão. Nada é enviado ao cliente sem a sua validação.</p><table>' + linha('Cliente', p.cliente) + linha('Produto', p.produto) + linha('Densidade', p.densidade) + linha('Granulometria', p.granulometria) + linha('Quantidade', p.quantidade + ' ' + (p.unidade || 'kg')) + linha('Embalagem', p.embalagem) + linha('Incoterm', p.incoterm) + linha('Destino', p.destino_pais) + '</table><h3>Preço</h3>' + precoHtml + '<h3>Cotações de frete (' + cots.length + ')</h3>' + cotHtml + '<h3>Compliance</h3>' + compHtml + aprovar + '<p>Cumprimentos,<br>Sistema de propostas (mensagem automática)</p>';
const slack = '📝 Proposta *' + p.codigo + '* para validação · ' + p.produto + ' · destino ' + p.destino_pais + ' · ' + (temPreco ? 'preço ' + eur(p.preco_final) : 'preço por definir') + ' · cotações: ' + cots.length + (nRever ? ' (' + nRever + ' a rever)' : '') + ' · compliance: ' + compEstado + (teste ? ' · (teste)' : '');
return [{ json: { codigo: p.codigo, assunto, corpo_html: corpo, slack_texto: slack, para: teste ? cfg.destinatario_teste : cfg.destinatario_validacao, cotacoes: cots.length, a_rever: nRever, compliance: compEstado, tem_preco: temPreco, link_preco: !!linkPreco } }];
