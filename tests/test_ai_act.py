"""Testes estruturais de compliance AI Act (sem rede): rodapés honestos e aviso de IA nos emails."""
import json, unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def codigo(ficheiro, no):
    wf = json.load(open(RAIZ / 'workflows' / ficheiro, encoding='utf-8'))
    return next(n for n in wf['nodes'] if n['name'] == no)['parameters']['jsCode']


class Rodapes(unittest.TestCase):
    def test_wf12_nao_afirma_revisao_humana(self):
        js = codigo('wf12-followup-cliente.json', 'Montar email final')
        self.assertNotIn('revista pela nossa equipa', js)
        self.assertNotIn('reviewed by our team', js)
        self.assertIn('enviada automaticamente', js)

    def test_wf3_aviso_ia_em_codigo(self):
        js = codigo('wf3-pedido-cotacao-frete.json', 'Montar email')
        self.assertIn('redigida com apoio de um sistema de inteligência artificial', js)

    def test_workflows_sem_llm_nos_emails_ao_cliente(self):
        for f in ('wf9-envio-cliente.json', 'wf10-confirmacao-encomenda.json', 'wf12-followup-cliente.json'):
            wf = json.load(open(RAIZ / 'workflows' / f, encoding='utf-8'))
            tipos = ' '.join(n['type'] for n in wf['nodes'])
            self.assertNotIn('langchain', tipos, f)


class AprovacaoWF8(unittest.TestCase):
    """AI Act H6: a aprovação por email exige OK + código de aprovação da proposta."""

    def test_wf8_exige_codigo(self):
        i = codigo('wf8-aprovacao-barbara.json', 'Interpretar resposta')
        d = codigo('wf8-aprovacao-barbara.json', 'Decidir')
        self.assertIn('codigo_enviado', i)
        self.assertIn('codigo_aprovacao', d)
        self.assertIn('!r.codigo_enviado', d)
        # «OK» sozinho nunca devolve aplicar:true: a verificação do código vem antes do ramo que aplica
        self.assertLess(d.index('!r.codigo_enviado'), d.index('aplicar: true'))
        self.assertLess(d.index('toUpperCase() !== r.codigo_enviado'), d.index('aplicar: true'))

    def test_wf5_envia_codigo(self):
        js = codigo('wf5-resumo-validacao.json', 'Montar resumo')
        self.assertIn('codigo_aprovacao', js)
        self.assertNotIn('apenas com a palavra OK', js)

    def test_migracao_0008(self):
        sql = (RAIZ / 'supabase' / 'migrations' / '0008_hardening_ai_act.sql').read_text(encoding='utf-8')
        for s in ('revoke all on all tables', 'codigo_aprovacao', 'produtos_validado_auditado'):
            self.assertIn(s, sql)
        self.assertTrue((RAIZ / 'supabase' / 'rollbacks' / '0008_rollback.sql').exists())


if __name__ == '__main__':
    unittest.main()
