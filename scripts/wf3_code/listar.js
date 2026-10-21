// WF3 · "Listar candidatas"
// Pedido novo: transportadoras do país ainda não contactadas (até ao máximo). Atualização: as já contactadas (último pedido enviado),
// cada uma com versao+1 e o id do pedido que substitui.
const p = $('Ler proposta').first().json;
const cfg = $('Configuração').first().json;
const atualizar = $('Normalizar código').first().json.atualizar === true;
const MAX_TENTATIVAS = 5;
const todas = $('Ler transportadoras ativas').all().map(i => i.json).filter(t => t && t.id);
const pedidos = $('Ler pedidos já feitos').all().map(i => i.json).filter(r => r && r.transportadora_id);
// 'falhou' não conta como contactada: pode ser repetida até MAX_TENTATIVAS
const feitasIds = pedidos.filter(r => r.estado !== 'falhou').map(r => r.transportadora_id);
const falhadas = pedidos.filter(r => r.estado === 'falhou');
const anteriores = falhadas.reduce((m, r) => Math.max(m, Number(r.tentativas) || 1), 0);
const max = Number(cfg.maximo_transportadoras) || 5;
const doPais = todas.filter(t => Array.isArray(t.rotas) && t.rotas.includes(p.destino_pais));
if (doPais.length === 0) throw new Error('Não há transportadoras ativas para o destino ' + p.destino_pais + ' (proposta ' + p.codigo + '): nada foi enviado. Acrescente transportadoras ou rotas.');
if (anteriores >= MAX_TENTATIVAS) throw new Error('Proposta ' + p.codigo + ': o envio do pedido de cotação falhou ' + anteriores + ' vezes (máximo ' + MAX_TENTATIVAS + ') e NÃO foi tentado de novo. Verifique a ligação ao Outlook e envie o pedido manualmente.');
let candidatas; let jaContactadas; let vagas;
if (atualizar) {
  // último pedido enviado de cada transportadora ativa do país
  const ultimo = {};
  for (const r of pedidos.filter(x => x.estado === 'enviado')) { if (!ultimo[r.transportadora_id] || (Number(r.versao) || 1) > (Number(ultimo[r.transportadora_id].versao) || 1)) ultimo[r.transportadora_id] = r; }
  candidatas = doPais.filter(t => ultimo[t.id]).sort((a, b) => a.nome.localeCompare(b.nome))
    .map(t => Object.assign({}, t, { _versao: (Number(ultimo[t.id].versao) || 1) + 1, _substitui_id: ultimo[t.id].id }));
  if (candidatas.length === 0) throw new Error('Proposta ' + p.codigo + ': não há pedidos de cotação enviados para atualizar.');
  jaContactadas = 0; vagas = candidatas.length;
} else {
  jaContactadas = doPais.filter(t => feitasIds.includes(t.id)).length;
  candidatas = doPais.filter(t => !feitasIds.includes(t.id)).sort((a, b) => a.nome.localeCompare(b.nome)).map(t => Object.assign({}, t, { _versao: 1, _substitui_id: null }));
  vagas = max - jaContactadas;
  if (candidatas.length === 0 || vagas <= 0) throw new Error('Todas as transportadoras já foram contactadas para a proposta ' + p.codigo);
}
return [{ json: {
  codigo: p.codigo, produto: p.produto, quantidade: p.quantidade, unidade: p.unidade, incoterm: p.incoterm, destino_pais: p.destino_pais,
  alvo: Math.min(vagas, candidatas.length), vagas: vagas, ja_contactadas: jaContactadas, tentativa: anteriores + 1, atualizar: atualizar,
  candidatas: candidatas.map(t => ({ id: t.id, nome: t.nome, modos: t.modos || [], paises_servidos: t.rotas, versao: t._versao, substitui_id: t._substitui_id }))
} }];
