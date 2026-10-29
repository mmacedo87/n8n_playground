"""Verificações estruturais dos exports (campos novos de carga coerentes entre formulário, normalização, gravação e esquema SQL)."""
import json, re, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMPOS = ['tipo_carga', 'n_camioes', 'n_paletes', 'peso_palete_kg', 'palete_c_m', 'palete_l_m', 'palete_a_m', 'morada_carga', 'morada_descarga', 'cp_descarga']


def carregar(nome):
    wf = json.load(open(RAIZ / 'workflows' / nome, encoding='utf-8'))
    return wf, {n['name']: n for n in wf['nodes']}


class WF2(unittest.TestCase):
    def test_campos_de_carga(self):
        wf, n = carregar('wf2-pedido-proposta.json')
        form = {c['fieldName']: c for c in n['Formulário de pedido de proposta']['parameters']['formFields']['values']}
        norm = {a['name'] for a in n['Normalizar pedido']['parameters']['assignments']['assignments']}
        grav = {f['fieldId'] for f in n['Criar proposta no Supabase']['parameters']['fieldsUi']['fieldValues']}
        entrada = {i['name'] for i in n['Chamado pelo workflow principal']['parameters']['workflowInputs']['values']}
        sql = (RAIZ / 'supabase' / 'schema.sql').read_text(encoding='utf-8')
        for c in CAMPOS:
            self.assertIn(c, form); self.assertFalse(form[c]['requiredField'], c)
            self.assertIn(c, norm); self.assertIn(c, grav); self.assertIn(c, entrada)
            self.assertRegex(sql, r'\b%s\b' % c)
        self.assertIn('carga_ok', norm)

    def test_validacao_usa_carga_ok_e_destinatario_continua_oculto(self):
        wf, n = carregar('wf2-pedido-proposta.json')
        self.assertIn('$json.carga_ok === true', n['Dados válidos?']['parameters']['conditions']['conditions'][0]['leftValue'])
        valores = [a['value'] for a in n['Normalizar pedido']['parameters']['assignments']['assignments'] if a['name'] == 'destinatario_confirmacao']
        self.assertEqual(valores, ['REDACTED@example.invalid'])  # o valor real fica só no n8n


if __name__ == '__main__':
    unittest.main()
