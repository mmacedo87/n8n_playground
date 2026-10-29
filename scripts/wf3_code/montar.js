// WF3 · "Montar email": UM email para todas as transportadoras (BCC), tabela montada por código com os dados da carga.
// O LLM só escreve a introdução e o fecho (pedido novo); numa atualização o texto é fixo.
const itens = $('Escolher transportadoras').all().map(i => i.json);
const d = itens[0];
const cfg = $('Configuração').first().json;
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const out = ($input.first() && $input.first().json && $input.first().json.output) || {};
const intro = typeof out.introducao === 'string' ? out.introducao.trim() : '';
const fecho = typeof out.fecho === 'string' ? out.fecho.trim() : '';
const limpo = (t, max) => t.length > 0 && t.length <= max && !/https?:|www[.]|[<>€$]|EUR|USD/i.test(t);
const atualizar = !!d.atualizar;
const llmOk = !atualizar && limpo(intro, 700) && intro.includes(d.codigo) && limpo(fecho, 400);
const introFinal = atualizar
  ? 'Exmos. Senhores, solicitamos que atualizem a cotação do pedido com a referência ' + d.codigo + ', cujos dados atuais constam da tabela abaixo.'
  : (llmOk ? intro : 'Exmos. Senhores, solicitamos uma cotação de frete para o pedido com a referência ' + d.codigo + ', cujos dados constam da tabela abaixo.');
const fechoFinal = llmOk ? fecho : 'Agradecemos a vossa resposta com a cotação e as respetivas condições.';
const PAISES = { ES: 'Espanha', FR: 'França', DE: 'Alemanha', IT: 'Itália', NL: 'Países Baixos', BE: 'Bélgica', GB: 'Reino Unido', US: 'Estados Unidos', BR: 'Brasil', CN: 'China', JP: 'Japão', MA: 'Marrocos' };
const pais = PAISES[d.destino_pais] || d.destino_pais;
const tem = (v) => v !== null && v !== undefined && v !== '';
const linha = (k, v) => '<tr><td style="padding:4px 16px 4px 0"><b>' + k + '</b></td><td>' + esc(v) + '</td></tr>';
const opc = (k, v) => (tem(v) ? linha(k, v) : '');
const tipo = d.tipo_carga === 'completa' ? 'Camião completo' : d.tipo_carga === 'grupagem' ? 'Grupagem' : null;
const dims = [d.palete_c_m, d.palete_l_m, d.palete_a_m].every(tem) ? [d.palete_c_m, d.palete_l_m, d.palete_a_m].map(Number).join(' × ') + ' m' : null;
const redirecionado = !!cfg.destinatario_teste;
const nomes = itens.map(t => t.transportadora_nome).join(', ');
const emails = itens.map(t => t.transportadora_email).join(', ');
const destinatarioTo = redirecionado ? cfg.destinatario_teste : cfg.destinatario_principal;
const destinatariosBcc = redirecionado ? '' : emails;
const base = d.cp_descarga
  ? 'Cotação Portugal/' + d.cp_descarga + ' – ' + pais + ' [' + d.codigo + ']'
  : '[' + d.codigo + '] Pedido de cotação de frete - ' + d.produto + ' - destino ' + d.destino_pais;
const assunto = (redirecionado ? '[TESTE] ' : '') + (atualizar ? 'Atualização: ' : '') + base;
// Aviso de transparência (AI Act, Art. 50 / boa prática): fixo em código, nunca vindo do LLM.
const AVISO_IA = 'Esta mensagem foi redigida com apoio de um sistema de inteligência artificial e enviada pelo nosso sistema de propostas.';
const corpo = (redirecionado ? '<p><i>Email de teste. Destinatários reais (em BCC): ' + esc(nomes) + '.</i></p>' : '')
  + '<p>' + esc(introFinal) + '</p>'
  + '<table>' + linha('Referência', d.codigo) + linha('Produto', d.produto) + linha('Densidade', d.densidade) + linha('Granulometria', d.granulometria)
  + linha('Quantidade', d.quantidade + ' ' + d.unidade) + linha('Embalagem', d.embalagem) + linha('Incoterm', d.incoterm) + linha('País de destino', pais)
  + opc('Tipo de carga', tipo) + opc('Nº de camiões', d.n_camioes) + opc('Nº de paletes', d.n_paletes)
  + opc('Peso por palete', tem(d.peso_palete_kg) ? d.peso_palete_kg + ' kg' : null) + opc('Dimensões da palete (C × L × A)', dims)
  + opc('Morada de carga', d.morada_carga) + opc('Morada de descarga', d.morada_descarga) + opc('Código postal de descarga', d.cp_descarga) + '</table>'
  + '<p><b>Pedimos que a resposta inclua:</b></p><ul><li>preço (indicar a moeda e se é por camião ou o total do transporte)</li><li>modo de transporte e prazo de trânsito em dias</li><li>se a entrega é em data fixa ou dentro de um período, com o preço de cada condição</li><li>validade da cotação</li><li>condições e eventuais custos adicionais (inland, taxas portuárias, outros)</li></ul>'
  + '<p><b>Importante:</b> mantenha a referência ' + esc(d.codigo) + ' no assunto da resposta.</p>'
  + '<p>' + esc(fechoFinal) + '</p><p>Cumprimentos,<br>Equipa comercial (mensagem enviada pelo sistema de propostas)</p>'
  + '<p><i>' + AVISO_IA + '</i></p>';
return itens.map(t => ({ json: Object.assign({}, t, { assunto: assunto, corpo_html: corpo, destinatario_to: destinatarioTo, destinatarios_bcc: destinatariosBcc, redirecionado_teste: redirecionado, gerado_por: llmOk ? 'llm' : 'modelo_fixo', modelo: cfg.modelo, total_transportadoras: itens.length, nomes_transportadoras: nomes }) }));
