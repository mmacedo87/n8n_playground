// Corre o código de um nó Code do n8n fora do n8n: node wf6_harness.js <ficheiro.js> <entrada.json>
// entrada.json: { "nodes": { "Nome do nó": [json,...] }, "input": [json,...] }
const fs = require('fs');
const [,, ficheiro, entrada] = process.argv;
const dados = JSON.parse(fs.readFileSync(entrada, 'utf8'));
const items = (arr) => (arr || []).map(j => ({ json: j }));
const $ = (nome) => {
  if (!(dados.nodes || {})[nome]) throw new Error('Nó não simulado: ' + nome);
  // itemMatching(i): no n8n segue o pairedItem; aqui o item i do nó simulado corresponde ao item i da entrada.
  return { all: () => items(dados.nodes[nome]), first: () => items(dados.nodes[nome])[0], itemMatching: (i) => items(dados.nodes[nome])[i] };
};
const $input = { all: () => items(dados.input), first: () => items(dados.input)[0] };
const $json = (dados.input || [{}])[0] || {};
const fn = new Function('$', '$input', '$json', '"use strict";' + fs.readFileSync(ficheiro, 'utf8'));
try {
  const r = fn($, $input, $json);
  process.stdout.write(JSON.stringify(r.map(x => x.json)));
} catch (e) {
  process.stdout.write(JSON.stringify({ __erro: String(e.message) }));
}
