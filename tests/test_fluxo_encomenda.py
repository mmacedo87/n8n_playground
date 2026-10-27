"""Testes offline do encadeamento Read Outlook -> WF2 e WF10 -> WF13 -> WF11 (nós Code lidos dos exports)."""
import json, subprocess, tempfile, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HARNESS = RAIZ / 'tests' / 'harness_code_node.js'


def wf(ficheiro):
    return json.load(open(RAIZ / 'workflows' / ficheiro, encoding='utf-8'))


def no(w, nome):
    return {n['name']: n for n in w['nodes']}[nome]


def correr(w, nome_no, nodes, entrada=None, item=False):
    codigo = no(w, nome_no)['parameters']['jsCode']
    if item:  # o harness só simula .first(); neste nó o código usa .item
        codigo = codigo.replace('.item.json', '.first().json')
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write(codigo)
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as g:
        json.dump({'nodes': nodes, 'input': entrada or []}, g, ensure_ascii=False)
    r = subprocess.run(['node', str(HARNESS), f.name, g.name], capture_output=True, text=True)
    Path(f.name).unlink(); Path(g.name).unlink()
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def ligado(w, de, para, saida=0):
    return any(l['node'] == para for l in w['connections'][de]['main'][saida])


# ---------- Read Outlook -> WF2
WF1_OK = {'email_id': 'm1', 'e_pedido': True, 'falhou_llm': False, 'confianca': 0.93, 'campos_em_falta': [], 'empresa': 'Cliente Teste SA',
          'remetente_nome': 'Ana', 'remetente_email': 'Ana@Exemplo.invalid', 'contacto_email': '', 'produto': 'cork granules', 'densidade': '90 kg/m3',
          'granulometria': '2-4 mm', 'embalagem': 'big bag', 'incoterm': 'fob', 'destino_pais': 'es', 'quantidade': 8, 'unidade': 'toneladas'}


class ReadOutlook(unittest.TestCase):
    w = wf('read-outlook-messages.json')

    def prep(self, **alt):
        return correr(self.w, 'Preparar pedido para WF2', {'Extrair pedido (WF1)': [{**WF1_OK, **alt}]}, item=True)

    def test_encadeamento(self):
        self.assertTrue(ligado(self.w, 'Marcar original como lido', 'Preparar pedido para WF2'))
        self.assertTrue(ligado(self.w, 'Preparar pedido para WF2', 'Pedido pronto para proposta?'))
        self.assertTrue(ligado(self.w, 'Pedido pronto para proposta?', 'Chamar WF2 - Pedido de proposta', 0))
        self.assertEqual(len(self.w['connections']['Pedido pronto para proposta?']['main']), 1, 'o ramo falso não faz nada')
        c = no(self.w, 'Chamar WF2 - Pedido de proposta')
        self.assertFalse(c.get('disabled'))
        self.assertTrue(c['parameters']['options']['waitForSubWorkflow'])
        self.assertEqual(c['parameters']['workflowInputs']['value']['contacto_email'], '={{ $json.contacto_email }}')

    def test_pedido_completo_fica_pronto(self):
        r = self.prep()[0]
        self.assertTrue(r['pronto'], r['motivos'])
        self.assertEqual((r['produto'], r['densidade'], r['granulometria'], r['embalagem'], r['incoterm'], r['destino'], r['quantidade']),
                         ('Granulado de cortiça', '80-100 kg/m3', '2-4 mm', 'Big bag 1 m3', 'FOB', 'ES', 8000))
        self.assertEqual(r['contacto_email'], 'ana@exemplo.invalid')  # sem contacto, usa o remetente

    def test_so_avanca_com_tudo_certo(self):
        casos = {'confianca_baixa': {'confianca': 0.79}, 'campos_em_falta': {'campos_em_falta': ['incoterm']}, 'nao_e_pedido': {'e_pedido': False},
                 'destino': {'destino_pais': 'PT'}, 'densidade': {'densidade': '300 kg/m3'}, 'granulometria': {'granulometria': '20-30 mm'},
                 'incoterm': {'incoterm': 'XYZ'}, 'quantidade': {'quantidade': 0}, 'falhou_llm': {'falhou_llm': True}}
        for motivo, alt in casos.items():
            with self.subTest(motivo):
                r = self.prep(**alt)[0]
                self.assertFalse(r['pronto'])
                self.assertIn(motivo, r['motivos'])


# ---------- WF2
class Wf2(unittest.TestCase):
    def test_contacto_email_chega_a_proposta(self):
        w = wf('wf2-pedido-proposta.json')
        self.assertIn('contacto_email', [v['name'] for v in no(w, 'Chamado pelo workflow principal')['parameters']['workflowInputs']['values']])
        campos = {v['fieldId']: v['fieldValue'] for v in no(w, 'Criar proposta no Supabase')['parameters']['fieldsUi']['fieldValues']}
        self.assertIn('contacto_email', campos)
        self.assertIn('Chamado pelo workflow principal', campos['contacto_email'])
        self.assertIn('try', campos['contacto_email'])  # o formulário não tem este campo: não pode falhar


# ---------- WF10
class Wf10(unittest.TestCase):
    w = wf('wf10-confirmacao-encomenda.json')
    CFG = {'chave': 'a' * 64, 'chave_ok': True, 'confirmar': True, 'destinatario_teste': '', 'email_madalena': 'm@exemplo.invalid',
           'email_barbara': 'b@exemplo.invalid', 'url_base': 'https://x/webhook/confirmar-proposta', 'url_form': 'https://x/form/plano-expedicao'}
    P = {'id': 'p1', 'codigo': 'PRP-2026-0099', 'cliente': 'Cliente', 'produto': 'Granulado', 'quantidade': 100, 'unidade': 'kg', 'embalagem': 'Big bag',
         'incoterm': 'FOB', 'destino_pais': 'ES'}

    def test_cadeia_da_reserva(self):
        for a, b in [('Responder confirmação', 'Ler reserva confirmada'), ('Ler reserva confirmada', 'Ler transportadora da reserva'),
                     ('Ler transportadora da reserva', 'Avisar expedição por email'), ('Avisar expedição por email', 'Avisar Slack: proposta confirmada')]:
            self.assertTrue(ligado(self.w, a, b), (a, b))
        self.assertTrue(no(self.w, 'Ler reserva confirmada').get('alwaysOutputData'), 'sem reserva o ramo do email não pode parar')

    def test_resultado_leva_link_e_marcador(self):
        r = correr(self.w, 'Resultado da confirmação', {'Configuração': [self.CFG], 'Ler proposta pela ligação': [self.P]}, [{'id': 'p1'}])[0]
        self.assertTrue(r['confirmou'])
        self.assertEqual(r['para'], 'm@exemplo.invalid')
        self.assertEqual(r['cc'], 'b@exemplo.invalid')
        self.assertTrue(r['link_plano'].endswith('?codigo=PRP-2026-0099'))
        self.assertIn('<!--PLANO-->', r['corpo_html'])
        self.assertIn('Encomenda confirmada pelo cliente', r['assunto'])

    def test_email_cobre_com_e_sem_reserva(self):
        expr = no(self.w, 'Avisar expedição por email')['parameters']['bodyContent']
        for s in ['Reserva de frete', 'confirme que os dados da reserva estão corretos', 'ainda não está confirmada', "replace('<!--PLANO-->'"]:
            self.assertIn(s, expr)

    def test_sem_reserva_nao_confirmou_de_novo(self):
        r = correr(self.w, 'Resultado da confirmação', {'Configuração': [self.CFG], 'Ler proposta pela ligação': [self.P]}, [{}])[0]
        self.assertFalse(r['confirmou'])


# ---------- WF11
PLANO = {'codigo': 'PRP-2026-0099', 'reserva_ok': True, 'tempo_producao_dias': 5, 'stock_ok': True, 'data_recolha': '2099-03-10', 'notas': '', 'planeada_por': 'Madalena', 'proposta_id': 'p1'}
COT = {'id': 'c1', 'estado_reserva': 'confirmada', 'modo': 'rodoviario', 'transito_dias': 3, 'ref_transportadora': 'Q-1', 'validade': '2099-12-31', 'transportadora_id': 't1'}
TRANSP = {'id': 't1', 'nome': 'Transp A'}


class Wf11(unittest.TestCase):
    w = wf('wf11-plano-expedicao.json')

    def decidir(self, plano=None, cot=None, transp=TRANSP):
        return correr(self.w, 'Decidir plano', {'Verificar proposta': [{**PLANO, **(plano or {})}], 'Ler cotação escolhida': [{**COT, **(cot or {})}], 'Ler transportadora da reserva': [transp]})

    def validar(self, form):
        return correr(self.w, 'Validar plano', {}, [form])

    FORM = {'codigo': 'prp-2026-0099', 'O seu nome': 'Madalena', 'Os dados da reserva estão corretos?': 'Sim', 'Tempo de produção (dias)': 5,
            'Stock disponível': 'Sim', 'Data de recolha': '2099-03-10', 'Notas': ''}

    def test_cadeia(self):
        for a, b in [('Verificar proposta', 'Ler cotação escolhida'), ('Ler cotação escolhida', 'Ler transportadora da reserva'),
                     ('Ler transportadora da reserva', 'Decidir plano'), ('Decidir plano', 'Reserva correta?'), ('Gravar plano de expedição', 'Conferir gravação'),
                     ('Chamar WF12 (follow-up ao cliente)', 'Avisar Slack: plano guardado'), ('Avisar reserva a corrigir', 'Avisar Slack: reserva a corrigir')]:
            self.assertTrue(ligado(self.w, a, b), (a, b))
        self.assertTrue(ligado(self.w, 'Reserva correta?', 'Gravar plano de expedição', 0))
        self.assertTrue(ligado(self.w, 'Reserva correta?', 'Avisar reserva a corrigir', 1))

    def test_formulario_tem_a_pergunta_e_nao_pede_modo_nem_transportadora(self):
        campos = [f.get('fieldLabel') or f.get('fieldName') for f in no(self.w, 'Madalena preenche o plano de expedição')['parameters']['formFields']['values']]
        self.assertIn('Os dados da reserva estão corretos?', campos)
        self.assertFalse({'Modo de expedição', 'Transportadora'} & set(campos))

    def test_so_o_ramo_sim_grava(self):
        # só o ramo «Sim» chega aos nós que escrevem no Supabase
        self.assertFalse(ligado(self.w, 'Avisar reserva a corrigir', 'Gravar plano de expedição'))
        for n in ('Avisar reserva a corrigir', 'Avisar Slack: reserva a corrigir'):
            self.assertNotIn(n, [l['node'] for x in self.w['connections'].get('Gravar plano de expedição', {}).get('main', []) for l in x])

    def test_validar_nao_dispensa_campos_so_se_for_nao(self):
        r = self.validar({**self.FORM, 'Os dados da reserva estão corretos?': 'Não', 'Tempo de produção (dias)': '', 'Data de recolha': ''})[0]
        self.assertFalse(r['reserva_ok'])
        self.assertEqual(r['codigo'], 'PRP-2026-0099')
        self.assertIn('__erro', self.validar({**self.FORM, 'Tempo de produção (dias)': 'x'}))
        self.assertIn('__erro', self.validar({**self.FORM, 'Data de recolha': '2000-01-01'}))
        self.assertIn('__erro', self.validar({**self.FORM, 'codigo': 'xx'}))
        self.assertTrue(self.validar(self.FORM)[0]['reserva_ok'])

    def test_sim_grava_com_modo_da_cotacao_e_chegada(self):
        r = self.decidir()[0]
        self.assertTrue(r['seguir'])
        self.assertEqual((r['modo'], r['transportadora'], r['chegada_estimada'], r['aviso_validade']), ('rodoviario', 'Transp A', '2099-03-13', False))

    def test_aviso_se_recolha_depois_da_validade(self):
        r = self.decidir(cot={'validade': '2099-03-01'})[0]
        self.assertTrue(r['seguir'] and r['aviso_validade'])
        self.assertIn('validade da cotação', r['slack_texto'])

    def test_nao_avisa_barbara_e_nao_segue(self):
        r = self.decidir(plano={'reserva_ok': False, 'notas': 'ref errada'})[0]
        self.assertFalse(r['seguir'])
        self.assertEqual((r['para'], r['cc']), ('REDACTED@example.invalid', 'REDACTED@example.invalid'))  # Bárbara e Madalena (config em produção)
        self.assertIn('ref errada', r['corpo_html'])
        self.assertIn('Reserva de frete a corrigir', r['assunto'])

    def test_recusa_reserva_nao_confirmada_modo_invalido_ou_sem_transportadora(self):
        for alt in ({'cot': {'estado_reserva': 'standby'}}, {'cot': {'modo': 'drone'}}, {'transp': {}}):
            with self.subTest(alt):
                self.assertIn('__erro', self.decidir(**alt))

    def test_emails_do_codigo_sao_substituiveis_no_deploy(self):
        for const in ('MADALENA', 'BARBARA'):
            self.assertIn("const %s = 'REDACTED@example.invalid';" % const, no(self.w, 'Decidir plano')['parameters']['jsCode'])


# ---------- WF13 -> Madalena
class Wf13(unittest.TestCase):
    w = wf('wf13-confirmacao-reserva.json')
    P = {'id': 'p1', 'codigo': 'PRP-2026-0099', 'cliente': 'Cliente', 'produto': 'Granulado', 'quantidade': 100, 'unidade': 'kg', 'embalagem': 'Big bag', 'incoterm': 'FOB', 'destino_pais': 'ES', 'estado': 'aceite'}
    D = {'acao': 'confirmada', 'cotacao_id': 'c1', 'transportadora': 'Transp A'}

    def madalena(self, d=None, p=None, teste=''):
        nodes = {'Decidir': [{**self.D, **(d or {})}], 'Ler proposta': [{**self.P, **(p or {})}], 'Normalizar pedido': [{'destinatario_teste': teste}],
                 'Ler cotações': [{'id': 'c1', 'modo': 'rodoviario', 'ref_transportadora': 'Q-1', 'transito_dias': 3, 'preco': 1850, 'moeda': 'EUR', 'preco_por': 'total', 'validade': '2099-12-31'}]}
        return correr(self.w, 'Plano para a Madalena', nodes)

    def test_envia_link_so_quando_confirmada_e_cliente_ja_aceitou(self):
        r = self.madalena()[0]
        self.assertIn('/form/plano-expedicao?codigo=PRP-2026-0099', r['corpo_html'])
        for s in ('Encomenda', 'Reserva de frete', 'Transp A', 'Q-1', '1850 EUR (total)', 'Não'):
            self.assertIn(s, r['corpo_html'])
        self.assertEqual(self.madalena(d={'acao': 'rascunho'}), [])
        self.assertEqual(self.madalena(d={'acao': 'cancelada'}), [])
        self.assertEqual(self.madalena(p={'estado': 'aprovada'}), [], 'o cliente ainda não aceitou: o link vai pelo WF10')
        self.assertEqual(self.madalena(p={'estado': 'enviada'}), [])

    def test_modo_de_teste_desvia_o_email(self):
        self.assertEqual(self.madalena(teste='teste@exemplo.invalid')[0]['para'], 'teste@exemplo.invalid')
        self.assertTrue(self.madalena(teste='teste@exemplo.invalid')[0]['assunto'].startswith('[TESTE]'))

    def test_ligacao(self):
        self.assertTrue(ligado(self.w, 'Atualizar frete escolhido', 'Plano para a Madalena'))
        self.assertTrue(ligado(self.w, 'Atualizar frete escolhido', 'Reservas a libertar'))
        self.assertTrue(ligado(self.w, 'Plano para a Madalena', 'Enviar plano à Madalena'))

    def test_email_da_madalena_substituivel_no_deploy(self):
        self.assertIn("const EMAIL_MADALENA = 'REDACTED@example.invalid';", no(self.w, 'Plano para a Madalena')['parameters']['jsCode'])


if __name__ == '__main__':
    unittest.main()
