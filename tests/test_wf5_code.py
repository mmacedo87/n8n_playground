"""Testes offline do código do nó «Montar resumo» do WF5 (scripts/wf5_code/montar.js)."""
import json, subprocess, tempfile, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
JS = RAIZ / 'scripts' / 'wf5_code' / 'montar.js'


def correr(entrada):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(entrada, f, ensure_ascii=False)
    r = subprocess.run(['node', str(RAIZ / 'tests' / 'harness_code_node.js'), str(JS), f.name], capture_output=True, text=True)
    Path(f.name).unlink()
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


class Casos(unittest.TestCase):
    def test_casos(self):
        for c in json.load(open(RAIZ / 'tests' / 'fixtures' / 'wf5' / 'casos.json', encoding='utf-8')):
            with self.subTest(c['id'], desc=c['desc']):
                out = correr({'nodes': c['nodes'], 'input': []})
                if c.get('erro'):
                    self.assertIn(c['erro'], out['__erro'])
                    continue
                self.assertNotIn('__erro', out if isinstance(out, dict) else {}, out)
                r = out[0]
                for k, v in c['expect'].items():
                    self.assertEqual(r[k], v, k)
                for s in c['assunto_contem']:
                    self.assertIn(s, r['assunto'])
                for s in c['corpo_contem']:
                    self.assertIn(s, r['corpo_html'])
                for s in c['corpo_nao_contem']:
                    self.assertNotIn(s, r['corpo_html'])


class Exportacao(unittest.TestCase):
    def test_codigo_igual_ao_exportado(self):
        wf = json.load(open(RAIZ / 'workflows' / 'wf5-resumo-validacao.json', encoding='utf-8'))
        no = {n['name']: n for n in wf['nodes']}['Montar resumo']
        self.assertEqual(no['parameters']['jsCode'].strip(), JS.read_text(encoding='utf-8').strip())


if __name__ == '__main__':
    unittest.main()
