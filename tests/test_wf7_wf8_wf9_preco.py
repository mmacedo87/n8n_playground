"""Testes offline do preço por formulário (fase 5 sem Moloni): WF7 (página, formulário, resultado), WF8 (não aprova sem preço)
e WF9 (email ao cliente com o preço decomposto). Casos anonimizados; o cálculo e as validações estão na BD (tests/supabase_bateria.sql, P1-P25)."""
import json, subprocess, tempfile, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TOKEN = 'a' * 64


def correr(js, nodes, entrada=None):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({'nodes': nodes, 'input': entrada or []}, f, ensure_ascii=False)
    r = subprocess.run(['node', str(RAIZ / 'tests' / 'harness_code_node.js'), str(RAIZ / 'scripts' / js), f.name], capture_output=True, text=True)
    Path(f.name).unlink()
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


CFG = {'token': TOKEN, 'url_pagina': 'https://n8n.exemplo.invalid/webhook/definir-preco', 'form': {}}
CONTEXTO = {'ok': True, 'utilizador': 'Teste', 'iva_sugerido': 'ue_isento', 'frete_obrigatorio': True,
            'limites': {'preco.max_eur_kg': '50', 'preco.max_desconto_pct': '50', 'preco.validade_dias': '30'},
            'proposta': {'codigo': 'PRP-2026-0101', 'cliente': 'Cliente <X>', 'produto': 'Granulado', 'densidade': '120-150 kg/m3', 'granulometria': '1-2',
                         'quantidade': 8, 'unidade': 't', 'quantidade_kg': 8000, 'embalagem': 'Big bag', 'incoterm': 'DAP', 'destino_pais': 'NL',
                         'preco_final': None, 'desconto_pct': 0},
            'cotacoes': [{'id': '11111111-1111-1111-1111-111111111111', 'transportadora': 'Transp <A>', 'modo': 'rodoviario', 'preco': 1850, 'moeda': 'EUR',
                          'preco_por': 'total', 'transito_dias': 3, 'validade': '2026-11-12', 'revisao': 'automatica', 'frete_proposto': 1850},
                         {'id': '22222222-2222-2222-2222-222222222222', 'transportadora': 'Transp B', 'modo': 'rodoviario', 'preco': 700, 'moeda': 'EUR',
                          'preco_por': 'nao_claro', 'revisao': 'a_rever', 'frete_proposto': None}]}


class Wf7Pagina(unittest.TestCase):
    def html(self, ctx):
        return correr('wf7_code/pagina.js', {'Configuração': [CFG]}, [ctx])[0]

    def test_pagina_completa(self):
        r = self.html(CONTEXTO)
        self.assertEqual(r['http'], 200)
        h = r['html']
        for s in ['Definir o preço · PRP-2026-0101', 'Cliente &lt;X&gt;', '120-150 kg/m3 · 1-2 mm', '8 000 kg (8,00 t)', 'Transp &lt;A&gt;',
                  'Frete proposto: <b>1 850,00 €</b>', 'Frete por calcular', 'cotação a rever', 'value="ue_isento" selected', '(sugerido)',
                  'name="t" value="' + TOKEN + '"', 'action="https://n8n.exemplo.invalid/webhook/definir-preco"', 'var D={"kg":8000,"fo":true}']:
            self.assertIn(s, h)
        self.assertNotIn('Cliente <X>', h)
        self.assertNotIn('kg/m3 kg/m³', h)

    def test_sem_frete_com_incoterm_f(self):
        ctx = json.loads(json.dumps(CONTEXTO)); ctx['frete_obrigatorio'] = False; ctx['proposta']['incoterm'] = 'FCA'
        h = self.html(ctx)['html']
        self.assertIn('o frete não entra no preço', h)
        self.assertNotIn('name="cotacao_id"', h)

    def test_sem_cotacoes_desativa_gravar(self):
        ctx = json.loads(json.dumps(CONTEXTO)); ctx['cotacoes'] = []
        h = self.html(ctx)['html']
        self.assertIn('ainda não há cotações de frete registadas', h)
        self.assertIn('<button type="submit" disabled>', h)

    def test_preco_existente_avisa(self):
        ctx = json.loads(json.dumps(CONTEXTO)); ctx['proposta'].update(preco_final=14846, preco_kg=1.71, cotacao_id='11111111-1111-1111-1111-111111111111', valor_frete=1850)
        h = self.html(ctx)['html']
        self.assertIn('Esta proposta já tem um preço: <b>14 846,00 €</b>', h)
        self.assertIn('value="1.71"', h)

    def test_erros_com_codigo_http(self):
        for erro, http in [('A ligação expirou. Use o botão do email de resumo mais recente.', 410), ('Não tem permissão para definir preços.', 403),
                           ('A ligação não é válida. Use o botão do email de resumo mais recente.', 404),
                           ('A proposta PRP-2026-0101 está no estado «aprovada»: o preço já não pode ser alterado.', 409)]:
            with self.subTest(http=http):
                r = self.html({'ok': False, 'erro': erro})
                self.assertEqual(r['http'], http)
                self.assertIn('Não é possível definir o preço', r['html'])
                self.assertNotIn('<form', r['html'])


class Wf7Formulario(unittest.TestCase):
    def rpc(self, form):
        cfg = dict(CFG, form=form)
        return correr('wf7_code/formulario.js', {'Configuração': [cfg]})[0]['rpc']

    def test_virgula_espacos_e_uuid(self):
        r = self.rpc({'preco_kg': '1,71', 'desconto_pct': ' 5 ', 'cotacao_id': '11111111-1111-1111-1111-111111111111', 'valor_frete': '',
                      'iva_regime': 'ue_isento', 'cliente_nif': 'NL 123', 'validade_dias': '30', 'notas': ''})
        self.assertEqual(r, {'p_token': TOKEN, 'p_preco_kg': 1.71, 'p_desconto_pct': 5, 'p_cotacao_id': '11111111-1111-1111-1111-111111111111',
                             'p_valor_frete': None, 'p_iva_regime': 'ue_isento', 'p_iva_pct': None, 'p_cliente_nif': 'NL 123',
                             'p_validade_dias': 30, 'p_notas': None})

    def test_texto_invalido_vira_valor_impossivel(self):
        r = self.rpc({'preco_kg': 'abc', 'desconto_pct': 'x', 'valor_frete': 'mil', 'cotacao_id': "1' or 1=1", 'validade_dias': 'z'})
        self.assertIsNone(r['p_preco_kg'])
        self.assertEqual(r['p_desconto_pct'], -1)
        self.assertEqual(r['p_valor_frete'], -1)
        self.assertIsNone(r['p_cotacao_id'])
        self.assertEqual(r['p_validade_dias'], 0)


class Wf7Resultado(unittest.TestCase):
    OK = {'ok': True, 'codigo': 'PRP-2026-0101', 'utilizador': 'Teste', 'quantidade_kg': 8000, 'preco_kg': 1.71, 'desconto_pct': 5, 'valor_produto': 12996,
          'valor_frete': 1850, 'frete_corrigido': False, 'valor_liquido': 14846, 'iva_regime': 'ue_isento', 'iva_pct': 0, 'valor_iva': 0, 'preco_final': 14846,
          'validade_proposta': '2026-12-01', 'preco_alterado': False, 'preco_anterior': None,
          'avisos': ['A cotação de frete é válida só até 12/11/2026, antes do fim da validade da proposta.']}

    def res(self, r):
        return correr('wf7_code/resultado.js', {'Configuração': [CFG]}, [r])[0]

    def test_gravado(self):
        r = self.res(self.OK)
        self.assertTrue(r['gravado']); self.assertEqual(r['http'], 200)
        for s in ['Preço gravado · PRP-2026-0101', '8 000 kg × 1,7100 €/kg − 5,00 %', '12 996,00 €', '1 850,00 €', 'Isento, UE (art. 14.º RITI)',
                  '14 846,00 €', 'até <b>01/12/2026</b>', 'código de aprovação novo', 'válida só até 12/11/2026']:
            self.assertIn(s, r['html'])
        self.assertIn('definido por Teste: total 14 846,00 €', r['slack_texto'])

    def test_alterado(self):
        r = self.res(dict(self.OK, preco_alterado=True, preco_anterior=14000, avisos=[]))
        self.assertIn('antes: 14 000,00 €', r['html'])
        self.assertIn('alterado por Teste', r['slack_texto'])

    def test_recusado(self):
        r = self.res({'ok': False, 'erro': 'O desconto tem de estar entre 0 e 50 %.'})
        self.assertFalse(r['gravado']); self.assertEqual(r['http'], 400)
        self.assertIn('Voltar à página do preço', r['html'])
        self.assertIn('definir-preco?t=' + TOKEN, r['html'])


class Wf8SemPreco(unittest.TestCase):
    def decidir(self, proposta, enviado='AB12CD'):
        resp = {'codigo': 'PRP-2026-0101', 'acao': 'aprovar', 'codigo_enviado': enviado, 'remetente': 'b@exemplo.invalid', 'comentario': 'OK ' + enviado}
        return correr('wf8_code/decidir.js', {'Interpretar resposta': [resp]}, [proposta])[0]

    def test_sem_preco_nao_aprova(self):
        r = self.decidir({'id': 'p1', 'estado': 'em_validacao', 'codigo_aprovacao': 'AB12CD', 'preco_final': None})
        self.assertFalse(r['aplicar'])
        self.assertIn('ainda não tem preço', r['slack_texto'])

    def test_com_preco_aprova(self):
        r = self.decidir({'id': 'p1', 'estado': 'em_validacao', 'codigo_aprovacao': 'AB12CD', 'preco_final': 14846, 'moeda': 'EUR'})
        self.assertTrue(r['aplicar'])
        self.assertIn('14846,00 EUR', r['slack_texto'])

    def test_codigo_de_resumo_anterior(self):
        r = self.decidir({'id': 'p1', 'estado': 'em_validacao', 'codigo_aprovacao': 'ZZ9ZZ9', 'preco_final': 14846})
        self.assertFalse(r['aplicar'])
        self.assertIn('resumo anterior', r['slack_texto'])


class Wf9Decomposicao(unittest.TestCase):
    P = {'id': 'p1', 'codigo': 'PRP-2026-0101', 'estado': 'aprovada', 'contacto_email': 'cliente@exemplo.invalid', 'produto': 'Granulado', 'densidade': '120-150',
         'granulometria': '1-2', 'quantidade': 8, 'unidade': 't', 'embalagem': 'Big bag', 'incoterm': 'DAP', 'destino_pais': 'NL', 'moeda': 'EUR',
         'token_confirmacao': 'b' * 64, 'token_expira_em': '2099-01-01T00:00:00Z', 'preco_tabela': 1.71, 'desconto_pct': 5, 'valor_produto': 12996,
         'valor_frete': 1850, 'valor_liquido': 14846, 'iva_regime': 'ue_isento', 'iva_pct': 0, 'valor_iva': 0, 'preco_final': 14846,
         'validade_proposta': '2026-12-01', 'cliente_nif': 'NL123456789B01'}
    CFG9 = {'codigo': 'PRP-2026-0101', 'destinatario_teste': '', 'cc_barbara': 'b@exemplo.invalid', 'url_confirmacao': 'https://n8n.exemplo.invalid/webhook/confirmar-proposta'}

    def email(self, p):
        return correr('wf9_code/montar.js', {'Normalizar código': [self.CFG9], 'Ler proposta': [p]})[0]

    def test_ingles_formato_e_isencao_ue(self):
        r = self.email(self.P)
        self.assertEqual(r['idioma'], 'en')
        for s in ['1.7100 EUR/kg × 8,000 kg', 'Discount', '12,996.00 EUR', 'Freight to destination (DAP)', '14,846.00 EUR', 'Offer valid until',
                  'article 14 of RITI', 'NL123456789B01']:
            self.assertIn(s, r['corpo_html'])

    def test_portugues_iva_23(self):
        p = dict(self.P, destino_pais='PT', iva_regime='pt_normal', iva_pct=23, valor_iva=3414.58, preco_final=18260.58, desconto_pct=0, cliente_nif=None)
        r = self.email(p)
        self.assertEqual(r['idioma'], 'pt')
        for s in ['1,7100 EUR/kg × 8 000 kg', 'IVA (23 %)', '3 414,58 EUR', '18 260,58 EUR', 'Proposta válida até', '01/12/2026']:
            self.assertIn(s, r['corpo_html'])
        self.assertNotIn('Desconto', r['corpo_html'])
        self.assertNotIn('isento', r['corpo_html'])

    def test_sem_preco_recusa(self):
        out = correr('wf9_code/montar.js', {'Normalizar código': [self.CFG9], 'Ler proposta': [dict(self.P, preco_final=None)]})
        self.assertIn('ainda não tem preço final (definir no WF7)', out['__erro'])


class Exportacoes(unittest.TestCase):
    """O código de cada nó exportado em workflows/ é igual ao ficheiro em scripts/."""
    CASOS = [('wf7-definir-preco.json', 'Montar página do preço', 'wf7_code/pagina.js'), ('wf7-definir-preco.json', 'Ler o formulário', 'wf7_code/formulario.js'),
             ('wf7-definir-preco.json', 'Montar resultado', 'wf7_code/resultado.js'), ('wf8-aprovacao-barbara.json', 'Decidir', 'wf8_code/decidir.js'),
             ('wf9-envio-cliente.json', 'Montar email da proposta', 'wf9_code/montar.js')]

    def test_codigo_igual(self):
        for wf, no, js in self.CASOS:
            with self.subTest(wf=wf, no=no):
                d = json.load(open(RAIZ / 'workflows' / wf, encoding='utf-8'))
                n = {x['name']: x for x in d['nodes']}[no]
                self.assertEqual(n['parameters']['jsCode'].strip(), (RAIZ / 'scripts' / js).read_text(encoding='utf-8').strip())

    def test_wf7_sem_llm_e_com_error_workflow(self):
        d = json.load(open(RAIZ / 'workflows' / 'wf7-definir-preco.json', encoding='utf-8'))
        self.assertFalse([n for n in d['nodes'] if 'langchain' in n['type']])
        self.assertEqual(d['settings'].get('errorWorkflow'), '{{WF:Mail Error Flow}}')
        self.assertEqual(d['settings'].get('saveDataSuccessExecution'), 'none')
        gravar = {n['name']: n for n in d['nodes']}['Gravar o preço (BD)']
        self.assertFalse(gravar.get('retryOnFail', False), 'uma escrita não se repete às cegas')


if __name__ == '__main__':
    unittest.main()
