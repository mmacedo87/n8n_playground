"""Testes offline do código dos nós Code do WF3 (scripts/wf3_code/*.js), casos anonimizados em tests/fixtures/wf3/casos.json."""
import json, subprocess, tempfile, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HARNESS = RAIZ / 'tests' / 'harness_code_node.js'
FICHEIRO = {'montar': 'montar.js', 'listar': 'listar.js', 'escolher': 'escolher.js'}


def correr(codigo, entrada):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(entrada, f, ensure_ascii=False)
    r = subprocess.run(['node', str(HARNESS), str(RAIZ / 'scripts' / 'wf3_code' / codigo), f.name], capture_output=True, text=True)
    Path(f.name).unlink()
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def contido(esperado, real):
    return all(real.get(k) == v for k, v in esperado.items())


class Casos(unittest.TestCase):
    def test_casos(self):
        with open(RAIZ / 'tests' / 'fixtures' / 'wf3' / 'casos.json', encoding='utf-8') as f:
            casos = json.load(f)
        for c in casos:
            with self.subTest(c['id'], desc=c['desc']):
                out = correr(FICHEIRO[c['tipo']], {'nodes': c['nodes'], 'input': c.get('input', [])})
                if c.get('erro'):
                    self.assertIn('__erro', out)
                    self.assertIn(c['erro'], out['__erro'])
                    continue
                self.assertNotIn('__erro', out if isinstance(out, dict) else {}, out)
                if c['tipo'] == 'montar':
                    for e, r in zip(c['expect'], out):
                        self.assertTrue(contido(e, r), (e, {k: r.get(k) for k in e}))
                    corpo = out[0]['corpo_html']
                    for s in c['corpo_contem']:
                        self.assertIn(s, corpo)
                    for s in c['corpo_nao_contem']:
                        self.assertNotIn(s, corpo)
                    self.assertEqual(len(out), len(c['nodes']['Escolher transportadoras']))
                elif c['tipo'] == 'listar':
                    e = dict(c['expect']); cands = e.pop('cands', None)
                    self.assertTrue(contido(e, out[0]), out[0])
                    if cands:
                        self.assertEqual([[x['id'], x['versao'], x['substitui_id']] for x in out[0]['candidatas']], cands)
                else:
                    self.assertEqual(len(out), len(c['expect']))
                    for e, r in zip(c['expect'], out):
                        self.assertTrue(contido(e, r), (e, {k: r.get(k) for k in e}))


class AvisoIA(unittest.TestCase):
    """AI Act (T1/T2): a frase de transparência é acrescentada em código, em todos os emails, venha ou não texto do LLM."""
    AVISO = 'Esta mensagem foi redigida com apoio de um sistema de inteligência artificial'

    def test_todos_os_emails_tem_aviso(self):
        with open(RAIZ / 'tests' / 'fixtures' / 'wf3' / 'casos.json', encoding='utf-8') as f:
            casos = [c for c in json.load(f) if c['tipo'] == 'montar' and not c.get('erro')]
        self.assertTrue(casos)
        for c in casos:
            with self.subTest(c['id']):
                out = correr('montar.js', {'nodes': c['nodes'], 'input': c.get('input', [])})
                self.assertIn(self.AVISO, out[0]['corpo_html'])
                self.assertEqual(out[0]['corpo_html'].count(self.AVISO), 1)

    def test_aviso_nao_depende_do_llm(self):
        with open(RAIZ / 'tests' / 'fixtures' / 'wf3' / 'casos.json', encoding='utf-8') as f:
            c = next(c for c in json.load(f) if c['tipo'] == 'montar' and not c.get('erro'))
        out = correr('montar.js', {'nodes': c['nodes'], 'input': [{'json': {'output': {}}}]})
        self.assertIn(self.AVISO, out[0]['corpo_html'])


class Exportacao(unittest.TestCase):
    def test_codigo_igual_ao_exportado(self):
        wf = json.load(open(RAIZ / 'workflows' / 'wf3-pedido-cotacao-frete.json', encoding='utf-8'))
        nos = {n['name']: n for n in wf['nodes']}
        for no, f in (('Listar candidatas', 'listar.js'), ('Escolher transportadoras', 'escolher.js'), ('Montar email', 'montar.js')):
            self.assertEqual(nos[no]['parameters']['jsCode'].strip(), (RAIZ / 'scripts' / 'wf3_code' / f).read_text(encoding='utf-8').strip(), no)


if __name__ == '__main__':
    unittest.main()
