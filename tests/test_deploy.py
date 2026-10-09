"""Testes do deploy (scripts/deploy_workflows.py) contra uma API n8n simulada. Correr: python3 -m unittest tests/test_deploy.py"""
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import deploy_workflows as D  # noqa: E402
import sanitize_workflow as S  # noqa: E402

CFG = {
    "n8n_url": "https://prod.example.invalid",
    "emails": {"erros": "erros@x.pt", "confirmacao_pedido": "conf@x.pt", "cotacoes": "cot@x.pt",
               "validacao_barbara": "b@x.pt", "cc_barbara": "b@x.pt", "madalena": "m@x.pt",
               "barbara": "b@x.pt", "aprovadores": ["B@X.pt", "c@x.pt"]},
    "slack_canais": {"propostas": "CPROP", "cotacoes": "CCOT", "estado": "CEST"},
    "credenciais": {"microsoftOutlookOAuth2Api": "cred-o", "slackApi": "cred-s",
                    "supabaseApi": "cred-d", "openRouterApi": "cred-r"},
}


class Mock:
    def __init__(self):
        self.store, self.log, self.n = {}, [], 0
        mock = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, obj, code=200):
                raw = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _body(self):
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n)) if n else {}

            def do_GET(self):
                mock.log.append(("GET", self.path))
                self._send({"data": [{"id": i, "name": w["name"]} for i, w in mock.store.items()], "nextCursor": None})

            def do_POST(self):
                mock.log.append(("POST", self.path))
                if self.path.endswith("/activate"):
                    wid = self.path.split("/")[-2]
                    mock.store[wid]["active"] = True
                    return self._send({"id": wid})
                mock.n += 1
                wid = "ID%03d" % mock.n
                mock.store[wid] = self._body()
                self._send({"id": wid})

            def do_PUT(self):
                mock.log.append(("PUT", self.path))
                wid = self.path.split("/")[-1]
                mock.store[wid] = self._body()
                self._send({"id": wid})

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.srv.server_port

    def by_name(self, name):
        return next(w for w in self.store.values() if w["name"] == name)

    def close(self):
        self.srv.shutdown()


class T(unittest.TestCase):
    def test_D1_manifest_cobre_ficheiros_e_referencias(self):
        files = {p.name for p in (ROOT / "workflows").glob("*.json")} - {"manifest.json"}
        man = {w["file"] for w in json.loads((ROOT / "workflows" / "manifest.json").read_text())["workflows"]}
        self.assertEqual(files, man)
        wfs = D.load_workflows()
        for d in wfs.values():
            for r in D.refs(d):
                self.assertIn(r, wfs)

    def test_D2_ordem_por_dependencias(self):
        seq = D.order(D.load_workflows())
        pos = {n: i for i, n in enumerate(seq)}
        self.assertEqual(seq[0], "Mail Error Flow")
        self.assertLess(pos["Notificar Slack"], pos["WF2 - Pedido de proposta"])
        self.assertLess(pos["WF3 - Pedido de cotação de frete"], pos["WF2 - Pedido de proposta"])
        self.assertLess(pos["WF9 - Envio da proposta ao cliente"], pos["WF8 - Aprovação da Bárbara por email"])
        self.assertLess(pos["WF12 - Follow-up ao cliente"], pos["WF11 - Plano de expedição"])

    def test_D3_dry_run_sem_marcadores(self):
        rep = D.run(CFG, dry_run=True)
        self.assertEqual(len(rep), 15)
        self.assertTrue(all(r[1] == "simulado" for r in rep))

    def test_D4_config_incompleta_falha_sem_tocar_na_api(self):
        m = Mock()
        try:
            cfg = json.loads(json.dumps(CFG))
            cfg["emails"]["madalena"] = ""
            with self.assertRaises(D.DeployError):
                D.run(cfg, api=D.Api(m.url, "k"))
            cfg = json.loads(json.dumps(CFG))
            del cfg["credenciais"]["slackApi"]
            with self.assertRaises(D.DeployError):
                D.run(cfg, api=D.Api(m.url, "k"))
            self.assertEqual(m.log, [])
        finally:
            m.close()

    def test_D5_deploy_resolve_ids_e_config(self):
        m = Mock()
        try:
            rep = D.run(CFG, api=D.Api(m.url, "k"))
            self.assertEqual(len(m.store), 15)
            ids = {w["name"]: i for i, w in m.store.items()}
            wf2 = m.by_name("WF2 - Pedido de proposta")
            called = {n["parameters"]["workflowId"]["value"] for n in wf2["nodes"] if n["type"] == "n8n-nodes-base.executeWorkflow"}
            self.assertEqual(called, {ids["WF3 - Pedido de cotação de frete"], ids["WF4 - Enriquecimento de proposta"], ids["Notificar Slack"]})
            self.assertEqual(wf2["settings"]["errorWorkflow"], ids["Mail Error Flow"])
            txt = json.dumps(list(m.store.values()), ensure_ascii=False)
            for bad in ("{{WF:", "REDACTED@example.invalid", "<ID do", "C0C7T8J8D54", "C0C7V2PU4PL", "C0C7SN9MKQE"):
                self.assertNotIn(bad, txt)
            wf8 = m.by_name("WF8 - Aprovação da Bárbara por email")
            code = next(n["parameters"]["jsCode"] for n in wf8["nodes"] if n["name"] == "Interpretar resposta")
            self.assertIn('["b@x.pt", "c@x.pt"]', code)
            wf10 = m.by_name("WF10 - Confirmação da encomenda")
            cfgset = next(n for n in wf10["nodes"] if n["name"] == "Configuração")
            vals = {a["name"]: a["value"] for a in cfgset["parameters"]["assignments"]["assignments"]}
            self.assertEqual(vals["url_base"], "https://prod.example.invalid/webhook/confirmar-proposta")
            self.assertEqual(vals["url_form"], "https://prod.example.invalid/form/plano-expedicao")
            self.assertEqual(vals["email_madalena"], "m@x.pt")
            slack = m.by_name("Notificar Slack")
            self.assertIn("CPROP", json.dumps(slack))
            creds = {c["id"] for w in m.store.values() for n in w["nodes"] for c in (n.get("credentials") or {}).values()}
            self.assertEqual(creds, {"cred-o", "cred-s", "cred-d", "cred-r"})
            ativos = {w["name"] for w in m.store.values() if w.get("active")}
            self.assertEqual(len(ativos), 12)
            self.assertNotIn("WF8 - Aprovação da Bárbara por email", ativos)
            self.assertNotIn("WF6 - Ler cotações das transportadoras", ativos)
            self.assertEqual(sum(1 for r in rep if "criado" in r[1]), 15)
        finally:
            m.close()

    def test_D6_segunda_corrida_atualiza_sem_duplicar(self):
        m = Mock()
        try:
            D.run(CFG, api=D.Api(m.url, "k"))
            n_posts = sum(1 for x in m.log if x[0] == "POST" and not x[1].endswith("/activate"))
            rep = D.run(CFG, api=D.Api(m.url, "k"))
            self.assertEqual(len(m.store), 15)
            self.assertEqual(n_posts, 15)
            self.assertTrue(all("atualizado" in r[1] for r in rep))
            self.assertEqual(sum(1 for x in m.log if x[0] == "POST" and not x[1].endswith("/activate")), 15)
        finally:
            m.close()

    def test_D7_modo_de_teste_ligado_bloqueia(self):
        orig = D.load_workflows

        def patched():
            w = orig()
            for n in w["WF3 - Pedido de cotação de frete"]["nodes"]:
                for a in n.get("parameters", {}).get("assignments", {}).get("assignments", []):
                    if a["name"] == "destinatario_teste":
                        a["value"] = "teste@x.pt"
            return w
        D.load_workflows = patched
        try:
            with self.assertRaises(D.DeployError):
                D.run(CFG, dry_run=True)
        finally:
            D.load_workflows = orig

    def test_D8_sanitizer_gera_marcadores(self):
        d = {"name": "X", "settings": {"errorWorkflow": "abc"}, "nodes": [
            {"type": "n8n-nodes-base.executeWorkflow", "parameters": {"workflowId": {"mode": "id", "value": "N7BZddGLl0WlSl9Q"}}}]}
        out = S.placeholders(d, {"N7BZddGLl0WlSl9Q": "Notificar Slack"})
        self.assertEqual(out["nodes"][0]["parameters"]["workflowId"]["value"], "{{WF:Notificar Slack}}")
        self.assertEqual(out["settings"]["errorWorkflow"], "{{WF:Mail Error Flow}}")

    def test_D9_chave_de_api_em_falta(self):
        import subprocess
        cfgp = ROOT / "deploy" / "out" / "_cfg_test.json"
        cfgp.parent.mkdir(parents=True, exist_ok=True)
        cfgp.write_text(json.dumps(CFG))
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "deploy_workflows.py"), "--config", str(cfgp)],
                           capture_output=True, text=True, env={"PATH": ""})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("N8N_API_KEY", r.stderr)
        cfgp.unlink()


if __name__ == "__main__":
    unittest.main()
