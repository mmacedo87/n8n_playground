"""Testes offline do código dos nós Code do WF6 (scripts/wf6_code/*.js) com casos anonimizados.
Corre o mesmo código que está no n8n: python3 -m unittest tests/test_wf6_code.py"""
import json, subprocess, tempfile, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HARNESS = RAIZ / 'tests' / 'wf6_harness.js'
FIX = RAIZ / 'tests' / 'fixtures' / 'wf6'


def correr(codigo, entrada):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(entrada, f, ensure_ascii=False)
    r = subprocess.run(['node', str(HARNESS), str(RAIZ / 'scripts' / 'wf6_code' / codigo), f.name], capture_output=True, text=True)
    Path(f.name).unlink()
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def subconjunto(esperado, real):
    return all(real.get(k) == v for k, v in esperado.items())


class Casar(unittest.TestCase):
    def test_casos(self):
        for c in json.load(open(FIX / 'casar_casos.json', encoding='utf-8')):
            with self.subTest(c['id'], desc=c['desc']):
                out = correr('casar.js', {'nodes': c['nodes']})
                self.assertEqual(len(out), len(c['expect']), out)
                for e, r in zip(c['expect'], out):
                    self.assertTrue(subconjunto(e, r), (e, r))
                for r in out:
                    t = r.get('texto', '')
                    for s in c.get('texto_contem', []):
                        self.assertIn(s, t)
                    for s in c.get('texto_nao_contem', []):
                        self.assertNotIn(s, t)


class Validar(unittest.TestCase):
    def test_casos(self):
        for c in json.load(open(FIX / 'validar_casos.json', encoding='utf-8')):
            with self.subTest(c['id'], desc=c['desc']):
                out = correr('validar.js', {'nodes': c['nodes'], 'input': c['input']})
                self.assertEqual(len(out), len(c['expect']), out)
                for e, r in zip(c['expect'], out):
                    self.assertTrue(subconjunto(e, r), (e, r))
                if 'condicoes_contem' in c:
                    self.assertIn(c['condicoes_contem'], out[0]['condicoes'] or '')


if __name__ == '__main__':
    unittest.main()


class Exportacao(unittest.TestCase):
    """O que está em git (workflows/wf6-ler-cotacoes.json) tem de ser o mesmo código que se testa."""
    def test_codigo_igual_ao_exportado(self):
        wf = json.load(open(RAIZ / 'workflows' / 'wf6-ler-cotacoes.json', encoding='utf-8'))
        nos = {n['name']: n for n in wf['nodes']}
        norm = lambda s: s.replace(' ', '\\u00a0').strip()
        for no, ficheiro in (('Casar email com proposta e transportadora', 'casar.js'), ('Validar extração', 'validar.js')):
            self.assertEqual(norm(nos[no]['parameters']['jsCode']), norm((RAIZ / 'scripts' / 'wf6_code' / ficheiro).read_text(encoding='utf-8')), no)

    def test_ligacoes(self):
        wf = json.load(open(RAIZ / 'workflows' / 'wf6-ler-cotacoes.json', encoding='utf-8'))
        c = wf['connections']
        self.assertEqual(c['Casar email com proposta e transportadora']['main'][0][0]['node'], 'Associado?')
        self.assertEqual(c['Associado?']['main'][0][0]['node'], 'Ler email com anexos')
        self.assertEqual(c['Associado?']['main'][1][0]['node'], 'Avisar Slack: email por associar')
        gravar = [n for n in wf['nodes'] if n['name'] == 'Gravar cotação'][0]['parameters']
        self.assertNotIn('operation', gravar)  # criar é o valor por omissão; getAll só lia
        campos = {f['fieldId'] for f in gravar['fieldsUi']['fieldValues']}
        self.assertTrue({'tipo_entrega', 'preco_por', 'estado_reserva', 'ref_transportadora', 'pedido_cotacao_id'} <= campos)
