"""Testes offline do nó «Decidir» do WF13 (scripts/wf13_code/decidir.js), casos anonimizados."""
import json, subprocess, tempfile, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
JS = RAIZ / 'scripts' / 'wf13_code' / 'decidir.js'


def correr(c):
    nodes = {
        'Normalizar pedido': [{'codigo': c['proposta']['codigo'], 'acao': c['acao'], 'transportadora': c['transportadora'], 'ref_transportadora': c['ref'], 'destinatario_teste': c['teste']}],
        'Ler proposta': [c['proposta']], 'Ler cotações': c['cots'],
        'Ler transportadoras': [{'id': 't1', 'nome': 'Transp A', 'email': 'a@exemplo.invalid'}, {'id': 't2', 'nome': 'Transp B', 'email': 'b@exemplo.invalid'}, {'id': 't3', 'nome': 'Transp C', 'email': 'c@exemplo.invalid'}]}
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({'nodes': nodes, 'input': []}, f, ensure_ascii=False)
    r = subprocess.run(['node', str(RAIZ / 'tests' / 'harness_code_node.js'), str(JS), f.name], capture_output=True, text=True)
    Path(f.name).unlink()
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


class Casos(unittest.TestCase):
    def test_casos(self):
        for c in json.load(open(RAIZ / 'tests' / 'fixtures' / 'wf13' / 'casos.json', encoding='utf-8')):
            with self.subTest(c['id'], desc=c['desc']):
                out = correr(c)
                if c.get('erro'):
                    self.assertIn(c['erro'], out['__erro'])
                    continue
                self.assertNotIn('__erro', out if isinstance(out, dict) else {}, out)
                r = out[0]
                for k, v in c['expect'].items():
                    self.assertEqual(r[k], v, k)
                for s in c.get('corpo_contem', []):
                    self.assertIn(s, r['corpo_html'])
                for s in c.get('assunto_contem', []):
                    self.assertIn(s, r['assunto'])

    def test_nunca_envia(self):
        self.assertNotIn('send', JS.read_text(encoding='utf-8').lower().replace('resend', ''))


class Exportacao(unittest.TestCase):
    def test_codigo_igual_ao_exportado(self):
        wf = json.load(open(RAIZ / 'workflows' / 'wf13-confirmacao-reserva.json', encoding='utf-8'))
        no = {n['name']: n for n in wf['nodes']}['Decidir']
        self.assertEqual(no['parameters']['jsCode'].strip(), JS.read_text(encoding='utf-8').strip())

    def test_so_rascunho_no_outlook(self):
        wf = json.load(open(RAIZ / 'workflows' / 'wf13-confirmacao-reserva.json', encoding='utf-8'))
        for n in wf['nodes']:
            if n['type'] == 'n8n-nodes-base.microsoftOutlook':
                self.assertEqual(n['parameters'].get('resource'), 'draft', n['name'])
                self.assertEqual(n['parameters'].get('operation'), 'create', n['name'])


if __name__ == '__main__':
    unittest.main()
