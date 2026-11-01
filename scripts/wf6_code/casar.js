// WF6 · "Casar email com proposta e transportadora"
// Associa cada email por ordem: (1) código PRP no assunto ou corpo; (2) conversa de um pedido enviado;
// (3) referência da transportadora; (4) remetente com um único pedido aberto. Em dúvida: por_associar (nunca grava).
const msgs = $('Ler emails não lidos da caixa').all().map(i => i.json).filter(m => m && m.id);
const transp = $('Ler transportadoras').all().map(i => i.json).filter(t => t && t.id);
const props = $('Ler propostas a cotar').all().map(i => i.json).filter(p => p && p.id);
const vistos = new Set($('Ler cotações já registadas').all().map(i => i.json.email_origem_id).filter(Boolean));
const pedidos = $('Ler pedidos já enviados').all().map(i => i.json).filter(p => p && p.id && p.proposta_id);

const htmlParaTexto = (h, tipo) => tipo !== 'html' ? String(h || '').replace(/[ \t\u00a0]+/g, ' ').replace(/ *\n */g, '\n').replace(/\n{3,}/g, '\n\n').trim() : String(h || '')
  .replace(/<style[\s\S]*?<\/style>/gi, ' ').replace(/<script[\s\S]*?<\/script>/gi, ' ')
  .replace(/<br\s*\/?>|<\/(p|div|tr|li|h\d)>/gi, '\n').replace(/<\/t[dh]>/gi, ' | ')
  .replace(/<[^>]+>/g, ' ')
  .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#43;/g, '+')
  .replace(/[ \t ]+/g, ' ').replace(/ *\n */g, '\n').replace(/\n{3,}/g, '\n\n').trim();

// Tira histórico citado, assinatura e avisos legais; devolve só o que a transportadora escreveu agora.
const limpar = (t) => {
  const linhas = String(t).split('\n');
  const cab = /^(enviad[oa]|sent|data|date|para|to|assunto|subject)\s*:/i;
  let fim = linhas.length;
  for (let i = 0; i < linhas.length; i++) {
    const l = linhas[i].trim();
    const antes = linhas.slice(0, i).join('\n').trim().length;
    const marca = /^-{2,}\s*(original message|mensagem original)/i.test(l) || /^_{5,}$/.test(l) || /^>/.test(l)
      || /^(em|on) .{5,200}(escreveu|wrote)\s*:?$/i.test(l)
      || (/^(de|from)\s*:\s*\S/i.test(l) && linhas.slice(i + 1, i + 5).some(x => cab.test(x.trim())));
    const aviso = /^(aviso legal|disclaimer|this (e-?mail|message) (is|and any)|este (e-?mail|email|mensagem)|a informação contida|confidential)/i.test(l);
    const despedida = /^(com os melhores cumprimentos|melhores cumprimentos|atenciosamente|cumprimentos|best regards|kind regards|regards|obrigad[oa],?)\b/i.test(l);
    if ((marca || aviso) && antes >= 10) { fim = i; break; }
    if (despedida && antes >= 40) { fim = i; break; }
  }
  return linhas.slice(0, fim).join('\n').trim();
};

const emailDe = (m) => String(((m.from || {}).emailAddress || {}).address || '').toLowerCase();
const dominioDe = (e) => e.includes('@') ? e.split('@').pop() : '';
const ignoradas = [];
const out = [];
for (const m of msgs) {
  const assunto = String(m.subject || '');
  const de = emailDe(m);
  if (/^\s*\[teste\]/i.test(assunto) || /^\s*(\[teste\]\s*)?\[?PRP-\d{4}-\d{4}\]?\s*pedido de cota/i.test(assunto)
      || (/^\s*cota[cç][aã]o\s+portugal\//i.test(assunto))) { ignoradas.push({ id: m.id, motivo: 'é o nosso pedido' }); continue; }
  if (vistos.has(m.id)) { ignoradas.push({ id: m.id, motivo: 'já registada' }); continue; }

  const bruto = htmlParaTexto((m.body && m.body.content) || m.bodyPreview || '', (m.body && m.body.content) ? String((m.body.contentType || '')).toLowerCase() : 'text');
  const texto = limpar(bruto).replace(/\n/g, ' \n').replace(/ +/g, ' ').slice(0, 6000).trim();

  // remetente: email exato; ou domínio aceite (caixas partilhadas); pode haver mais do que uma transportadora
  let cands = transp.filter(t => String(t.email || '').toLowerCase() === de);
  if (!cands.length) {
    const dom = dominioDe(de);
    cands = dom ? transp.filter(t => (t.dominios_aceites || []).map(x => String(x).toLowerCase()).includes(dom)) : [];
  }
  if (!cands.length) { ignoradas.push({ id: m.id, motivo: 'remetente não é transportadora conhecida' }); continue; }

  const abertas = new Set(props.map(p => p.id));
  const pedidosAbertos = pedidos.filter(p => abertas.has(p.proposta_id) && cands.some(c => c.id === p.transportadora_id));
  let p = null, t = null, via = null;

  // 1) código PRP: assunto primeiro; no corpo só o texto novo (sem histórico) e só se for um único código.
  // A conversa do Outlook (2) vale mais do que o código citado no histórico (2b).
  const codAss = (assunto.match(/PRP-\d{4}-\d{4}/gi) || []).map(x => x.toUpperCase());
  const codCorpo = [...new Set((bruto.match(/PRP-\d{4}-\d{4}/gi) || []).map(x => x.toUpperCase()))];
  const codNovo = [...new Set((texto.match(/PRP-\d{4}-\d{4}/gi) || []).map(x => x.toUpperCase()))];
  const cod = codAss[0] || (codNovo.length === 1 ? codNovo[0] : null);
  if (cod) { p = props.find(x => x.codigo === cod) || null; via = 'codigo'; if (!p) { ignoradas.push({ id: m.id, motivo: 'proposta não está a_cotar nem em_validacao' }); continue; } }
  // 2) conversa de um pedido enviado
  if (!p && m.conversationId) {
    const ped = pedidosAbertos.filter(x => x.conversation_id && x.conversation_id === m.conversationId);
    const ps = [...new Set(ped.map(x => x.proposta_id))];
    if (ps.length === 1) { p = props.find(x => x.id === ps[0]); via = 'conversa'; }
  }
  // 2b) único código no histórico citado (a resposta cita o nosso pedido)
  if (!p && codNovo.length === 0 && codCorpo.length === 1) { p = props.find(x => x.codigo === codCorpo[0]) || null; via = 'codigo_citado'; }
  // 3) referência da transportadora no texto
  if (!p) {
    const ped = pedidosAbertos.filter(x => x.ref_transportadora && texto.toLowerCase().includes(String(x.ref_transportadora).toLowerCase()));
    const ps = [...new Set(ped.map(x => x.proposta_id))];
    if (ps.length === 1) { p = props.find(x => x.id === ps[0]); via = 'referencia'; }
  }
  // 4) remetente conhecido com um único pedido aberto
  if (!p) {
    const ps = [...new Set(pedidosAbertos.map(x => x.proposta_id))];
    if (ps.length === 1) { p = props.find(x => x.id === ps[0]); via = 'remetente'; }
  }
  if (!p) {
    out.push({ json: { associado: false, email_id: m.id, assunto, remetente: de, motivo: pedidosAbertos.length > 1 ? 'vários pedidos abertos desta transportadora' : 'sem código nem conversa que identifique a proposta' } });
    continue;
  }

  // transportadora: se vários candidatos (domínio partilhado), usa o pedido da proposta; senão fica por associar
  const tc = cands.length === 1 ? cands : cands.filter(c => pedidos.some(x => x.proposta_id === p.id && x.transportadora_id === c.id));
  if (tc.length !== 1) { out.push({ json: { associado: false, email_id: m.id, assunto, remetente: de, motivo: 'não foi possível saber qual das transportadoras do domínio respondeu' } }); continue; }
  t = tc[0];
  const ped = pedidos.filter(x => x.proposta_id === p.id && x.transportadora_id === t.id).sort((a, b) => (b.versao || 1) - (a.versao || 1))[0] || null;
  out.push({ json: { associado: true, via, email_id: m.id, conversation_id: m.conversationId || null, codigo: p.codigo, proposta_id: p.id, transportadora_id: t.id, transportadora_nome: t.nome, pedido_cotacao_id: ped ? ped.id : null, assunto, texto, tem_anexos: !!m.hasAttachments, recebida_em: m.receivedDateTime || null } });
}
return out;
