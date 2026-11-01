const r = $('Interpretar resposta').first().json;
const p = $input.first().json || {};
const cod = r.codigo;
if (!p.id) return [{ json: { ...r, aplicar: false, slack_texto: '⚠️ Recebi uma resposta a ' + cod + ' mas a proposta não existe.' } }];
if (r.acao === 'comentario') return [{ json: { ...r, aplicar: false, slack_texto: '💬 A Bárbara respondeu a *' + cod + '* com um comentário (a proposta continua em validação): "' + r.comentario + '"' } }];
if (p.estado !== 'em_validacao') return [{ json: { ...r, aplicar: false, slack_texto: '⚠️ Aprovação ignorada: *' + cod + '* está no estado ' + p.estado + ' (e não em validação).' } }];
// WF7: sem preço definido não há aprovação (o código de aprovação muda sempre que o preço muda).
if (!(Number(p.preco_final) > 0)) return [{ json: { ...r, aplicar: false, slack_texto: '⚠️ Aprovação ignorada: *' + cod + '* ainda não tem preço. Definir o preço pela ligação do resumo e aprovar com o código do resumo novo.' } }];
if (!r.codigo_enviado) return [{ json: { ...r, aplicar: false, slack_texto: '⚠️ Aprovação ignorada: a resposta a *' + cod + '* não traz o código de aprovação (responder «OK <código>»).' } }];
if (!p.codigo_aprovacao || String(p.codigo_aprovacao).toUpperCase() !== r.codigo_enviado) return [{ json: { ...r, aplicar: false, slack_texto: '⚠️ Aprovação ignorada: o código de aprovação enviado para *' + cod + '* está incorreto ou é de um resumo anterior (o preço pode ter mudado).' } }];
const total = Number(p.preco_final).toFixed(2).replace('.', ',');
return [{ json: { ...r, aplicar: true, aprovada_por: r.remetente, aprovada_em: new Date().toISOString(), slack_texto: '✅ Proposta *' + cod + '* aprovada por ' + r.remetente + ' com o total de ' + total + ' ' + (p.moeda || 'EUR') + '. Segue para o cliente (WF9).' } }];
