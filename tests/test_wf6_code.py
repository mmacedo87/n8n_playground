"""Testes offline do código dos nós Code do WF6 (scripts/wf6_code/*.js) com casos anonimizados.
Corre o mesmo código que está no n8n: python3 -m unittest tests/test_wf6_code.py"""
import json, subprocess, tempfile, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HARNESS = RAIZ / 'tests' / 'harness_code_node.js'
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

    def test_registo_de_uso_de_ia(self):
        """Cada extração do LLM fica em ai_log, sem conteúdo do email, e uma falha do registo não pára o fluxo."""
        wf = json.load(open(RAIZ / 'workflows' / 'wf6-ler-cotacoes.json', encoding='utf-8'))
        nos = {n['name']: n for n in wf['nodes']}
        reg = nos['Registar uso de IA']
        self.assertEqual(reg['parameters']['tableId'], 'ai_log')
        self.assertEqual(reg.get('onError'), 'continueRegularOutput')
        destinos = [x['node'] for x in wf['connections']['Extrair cotação (LLM)']['main'][0]]
        self.assertIn('Registar uso de IA', destinos)
        self.assertIn('Validar extração', destinos)
        campos = {f['fieldId']: str(f['fieldValue']) for f in reg['parameters']['fieldsUi']['fieldValues']}
        self.assertTrue({'workflow', 'execucao_n8n_id', 'proposta_id', 'modelo', 'versao_prompt', 'input_resumo', 'output_resumo'} <= set(campos))
        for v in campos.values():  # minimização de dados: nunca o texto do email nem o remetente
            self.assertNotIn('.texto', v)
            self.assertNotIn('remetente', v)

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

    def test_gatilho_automatico_inbox(self):
        """Corre sozinho com emails novos não lidos na Inbox; a leitura corre uma vez e lê todos os não lidos."""
        wf = json.load(open(RAIZ / 'workflows' / 'wf6-ler-cotacoes.json', encoding='utf-8'))
        nos = {n['name']: n for n in wf['nodes']}
        g = nos['Email novo na Inbox']
        self.assertEqual(g['type'], 'n8n-nodes-base.microsoftOutlookTrigger')
        p = g['parameters']
        self.assertEqual(p['filters']['readStatus'], 'unread')
        self.assertEqual(p['filters']['foldersToInclude'], ['<ID da pasta Inbox no Outlook de destino>'])
        self.assertEqual(p['pollTimes']['item'][0], {'mode': 'everyX', 'unit': 'minutes', 'value': 5})
        for gatilho in ('Email novo na Inbox', 'Ler respostas das transportadoras'):
            self.assertEqual(wf['connections'][gatilho]['main'][0][0]['node'], 'Ler emails não lidos da caixa', gatilho)
        self.assertTrue(nos['Ler emails não lidos da caixa'].get('executeOnce'))
        self.assertNotIn('AQMk', json.dumps(wf))
