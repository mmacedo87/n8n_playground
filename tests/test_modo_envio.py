"""Modo de envio do WF3 (tabela configuracao): estrutura do export, lado seguro e esquema SQL (sem rede)."""
import json, re, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WF = json.load(open(RAIZ / 'workflows' / 'wf3-pedido-cotacao-frete.json', encoding='utf-8'))
N = {n['name']: n for n in WF['nodes']}
C = WF['connections']


def destinos(no, saida=0):
    return [x['node'] for x in C.get(no, {}).get('main', [[]] * (saida + 1))[saida]]


def a_jusante(inicio, saida=None):
    """Nós alcançáveis a partir de uma ligação."""
    vistos, fila = set(), [inicio]
    while fila:
        atual = fila.pop()
        for saidas in C.get(atual, {}).get('main', []):
            for x in saidas:
                if x['node'] not in vistos:
                    vistos.add(x['node']); fila.append(x['node'])
    return vistos


class Estrutura(unittest.TestCase):
    def test_registo_liga_ao_modo_e_nao_ao_envio(self):
        self.assertEqual(destinos('Registar pedido de cotação'), ['Ler modo de envio'])
        self.assertEqual(destinos('Ler modo de envio'), ['Modo automático?'])

    def test_so_o_if_chega_ao_envio(self):
        anteriores = [k for k, v in C.items() for saidas in v.get('main', []) for x in saidas
                      if x['node'] == 'Enviar email único às transportadoras']
        self.assertEqual(anteriores, ['Modo automático?'])
        self.assertEqual(destinos('Modo automático?', 0), ['Enviar email único às transportadoras'])
        self.assertEqual(destinos('Modo automático?', 1), ['Criar rascunho para revisão'])

    def test_leitura_da_configuracao(self):
        p = N['Ler modo de envio']['parameters']
        self.assertEqual(p['tableId'], 'configuracao')
        self.assertEqual(p['filters']['conditions'], [{'keyName': 'chave', 'condition': 'eq', 'keyValue': 'modo_envio'}])
        self.assertTrue(N['Ler modo de envio']['alwaysOutputData'])           # tabela vazia não pára o fluxo
        self.assertEqual(N['Ler modo de envio']['onError'], 'continueRegularOutput')  # erro de leitura não pára o fluxo

    def test_if_so_envia_com_automatico_exato(self):
        c = N['Modo automático?']['parameters']['conditions']['conditions']
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]['rightValue'], 'automatico')
        self.assertEqual(c[0]['operator'], {'type': 'string', 'operation': 'equals'})
        self.assertIn("'Ler modo de envio'", c[0]['leftValue'])

    def test_ramo_de_revisao_nunca_envia(self):
        ramo = a_jusante('Criar rascunho para revisão') | {'Criar rascunho para revisão'}
        # O n8n omite no export os valores por omissão: recurso 'message' (operação 'send') e, em 'draft', operação 'create'.
        def recurso_operacao(p):
            recurso = p.get('resource', 'message')
            return recurso, p.get('operation', 'create' if recurso == 'draft' else 'send')
        for nome in ramo:
            n = N[nome]
            if n['type'] == 'n8n-nodes-base.microsoftOutlook':
                self.assertNotEqual(recurso_operacao(n['parameters']), ('message', 'send'), nome)
        self.assertNotIn('Enviar email único às transportadoras', ramo)
        self.assertEqual(recurso_operacao(N['Criar rascunho para revisão']['parameters']), ('draft', 'create'))

    def test_ramo_de_revisao_marca_rascunho_e_avisa(self):
        self.assertEqual(destinos('Criar rascunho para revisão'), ['Procurar pasta To Check'])
        self.assertEqual(destinos('Procurar pasta To Check'), ['Mover rascunho para To Check'])
        self.assertEqual(destinos('Mover rascunho para To Check'), ['Marcar pedidos como rascunho'])
        self.assertEqual(sorted(destinos('Marcar pedidos como rascunho')), ['Avisar Slack: rascunho pronto', 'Registar uso de IA'])
        campos = N['Marcar pedidos como rascunho']['parameters']['fieldsUi']['fieldValues']
        self.assertEqual(campos, [{'fieldId': 'estado', 'fieldValue': 'rascunho'}])
        self.assertIn('RASCUNHO', N['Avisar Slack: rascunho pronto']['parameters']['workflowInputs']['value']['texto'])

    def test_falha_a_mover_nao_perde_o_rascunho(self):
        for nome in ('Procurar pasta To Check', 'Mover rascunho para To Check'):
            self.assertEqual(N[nome]['onError'], 'continueRegularOutput', nome)
            self.assertTrue(N[nome]['alwaysOutputData'], nome)

    def test_pasta_por_nome_na_configuracao(self):
        cfg = {a['name']: a['value'] for a in N['Configuração']['parameters']['assignments']['assignments']}
        self.assertEqual(cfg['pasta_revisao'], 'To Check')
        self.assertEqual(cfg['destinatario_teste'], '')  # regra de exportação: modo de teste vazio no Git
        self.assertIn('pasta_revisao', json.dumps(N['Procurar pasta To Check']['parameters']))

    def test_resumo_indica_o_modo(self):
        nomes = [a['name'] for a in N['Devolver resumo']['parameters']['assignments']['assignments']]
        self.assertIn('modo_envio', nomes)

    def test_sem_emails_nem_ids_de_pasta_no_export(self):
        txt = json.dumps(WF)
        self.assertNotRegex(txt, r'AQMkAD')                      # id de pasta/mensagem do Outlook
        self.assertNotIn('gmail.com', txt)


class Sql(unittest.TestCase):
    def test_migracao_esquema_e_reversao(self):
        mig = (RAIZ / 'supabase/migrations/0009_configuracao_modo_envio.sql').read_text(encoding='utf-8')
        rb = (RAIZ / 'supabase/rollbacks/0009_rollback.sql').read_text(encoding='utf-8')
        esq = (RAIZ / 'supabase/schema.sql').read_text(encoding='utf-8')
        for txt in (mig, esq):
            self.assertIn("valor in ('automatico','revisao')", txt)
            self.assertIn("'a_enviar','rascunho','enviado','falhou','respondido'", txt)
            self.assertIn('enable row level security', txt)
            self.assertRegex(txt, r"values\s*\('modo_envio',\s*'automatico'")
        self.assertIn('drop table if exists configuracao', rb)
        self.assertIn("set estado = 'a_enviar' where estado = 'rascunho'", rb)

    def test_reenvio_nao_trata_rascunho_como_falha(self):
        js = (RAIZ / 'scripts/wf3_code/listar.js').read_text(encoding='utf-8')
        self.assertIn("r.estado !== 'falhou'", js)   # rascunho conta como já contactada: não duplica


if __name__ == '__main__':
    unittest.main()
