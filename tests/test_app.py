"""Testes do assistente (app/deploy_app.py) contra uma API n8n simulada. Correr: python3 -m unittest tests/test_app.py"""
import json
import shutil
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "app"))
import test_deploy as TD  # noqa: E402
import deploy_app as A  # noqa: E402
import test_github as TG  # noqa: E402
import os  # noqa: E402


def req(base, path, body=None, host=None):
    r = urllib.request.Request(base + path, method="POST" if body is not None else "GET",
                               data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json"})
    if host:
        r.add_header("Host", host)
    try:
        with urllib.request.urlopen(r, timeout=30) as x:
            return x.status, x.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class T(unittest.TestCase):
    def setUp(self):
        self.bak = A.CONFIG.read_bytes() if A.CONFIG.exists() else None
        A.STATE.update(key=None, job={"state": "idle", "steps": [], "error": None, "total": 0}, gh=None, gjob=A.novo_gjob())
        self.mock = TD.Mock()
        self.srv = A.make_server(0)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.srv.server_port
        self.cfg = json.loads(json.dumps(TD.CFG))
        self.cfg["n8n_url"] = self.mock.url

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.mock.close()
        if self.bak is None:
            A.CONFIG.unlink(missing_ok=True)
        else:
            A.CONFIG.write_bytes(self.bak)

    def test_A1_pagina_e_config_vazia(self):
        c, raw = req(self.base, "/")
        self.assertEqual(c, 200)
        self.assertIn("Instalação da automação".encode(), raw)
        A.CONFIG.unlink(missing_ok=True)
        c, raw = req(self.base, "/api/config")
        cfg = json.loads(raw)
        self.assertEqual(cfg["n8n_url"], "")
        self.assertEqual(cfg["emails"]["aprovadores"], [])

    def test_A2_guarda_config_sem_chave(self):
        req(self.base, "/api/config", self.cfg)
        req(self.base, "/api/connect", {"url": self.mock.url, "key": "SEGREDO123"})
        self.assertNotIn("SEGREDO123", A.CONFIG.read_text())
        self.assertEqual(json.loads(A.CONFIG.read_text())["emails"]["madalena"], "m@x.pt")

    def test_A3_ligacao_ok_e_falha(self):
        c, raw = req(self.base, "/api/connect", {"url": self.mock.url, "key": "k"})
        self.assertTrue(json.loads(raw)["ok"])
        c, raw = req(self.base, "/api/connect", {"url": "http://127.0.0.1:1", "key": "k"})
        r = json.loads(raw)
        self.assertFalse(r["ok"])
        self.assertIn("Não consegui chegar ao n8n", r["msg"])

    def test_A4_verificar_mensagem_em_portugues(self):
        self.cfg["emails"]["madalena"] = ""
        req(self.base, "/api/config", self.cfg)
        c, raw = req(self.base, "/api/check", {})
        r = json.loads(raw)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "Falta preencher o email da Madalena.")

    def test_A5_verificar_ok(self):
        req(self.base, "/api/config", self.cfg)
        r = json.loads(req(self.base, "/api/check", {})[1])
        self.assertTrue(r["ok"])
        self.assertEqual(r["total"], 15)

    def test_A6_instalar_sem_ligar_recusa(self):
        req(self.base, "/api/config", self.cfg)
        r = json.loads(req(self.base, "/api/deploy", {})[1])
        self.assertFalse(r["ok"])
        self.assertIn("ligar ao n8n", r["error"])

    def test_A7_instalar_ate_ao_fim(self):
        req(self.base, "/api/config", self.cfg)
        req(self.base, "/api/connect", {"url": self.mock.url, "key": "k"})
        self.assertTrue(json.loads(req(self.base, "/api/deploy", {})[1])["ok"])
        for _ in range(100):
            s = json.loads(req(self.base, "/api/status")[1])
            if s["state"] != "running":
                break
            time.sleep(0.1)
        self.assertEqual(s["state"], "done")
        self.assertEqual(len(s["steps"]), 15)
        self.assertEqual(len(self.mock.store), 15)

    def test_A8_erro_de_chave_traduzido(self):
        self.assertIn("chave de API", A.friendly("GET /workflows -> HTTP 401 x"))

    def test_A9_so_aceita_acessos_locais(self):
        c, _ = req(self.base, "/api/config", host="evil.example.com")
        self.assertEqual(c, 403)
        c, _ = req(self.base, "/api/config", {}, host="evil.example.com")
        self.assertEqual(c, 403)

    def test_A10_schema_servido(self):
        r = json.loads(req(self.base, "/api/schema")[1])
        self.assertIn("create table", r["sql"].lower())
        self.assertIn("expedicoes", r["sql"])

    # --- repositório GitHub ---
    def gh_setup(self, **kw):
        self.gm = TG.MockGH(**kw)
        self.addCleanup(self.gm.close)
        os.environ["GITHUB_API_URL"] = self.gm.url
        self.addCleanup(os.environ.pop, "GITHUB_API_URL", None)

    def gh_wait(self):
        for _ in range(300):
            s = json.loads(req(self.base, "/api/github/status")[1])
            if s["state"] != "running":
                return s
            time.sleep(0.1)
        self.fail("GitHub não terminou")

    def test_A11_github_chave_e_criacao(self):
        self.gh_setup()
        r = json.loads(req(self.base, "/api/github/check", {"token": "errado"})[1])
        self.assertFalse(r["ok"])
        self.assertIn("não aceitou a chave", r["error"])
        r = json.loads(req(self.base, "/api/github/check", {"token": "tok"})[1])
        self.assertEqual(r, {"ok": True, "login": "ana"})
        r = json.loads(req(self.base, "/api/github/create", {"owner": "ana", "repo": "propostas", "private": True})[1])
        self.assertTrue(r["ok"])
        s = self.gh_wait()
        self.assertEqual(s["state"], "done")
        self.assertEqual(s["url"], "https://github.com/ana/propostas")
        self.assertEqual([x["estado"] for x in s["steps"]], ["ok"] * 5)
        self.assertEqual(sorted(self.gm.repos["ana/propostas"]["refs"]), ["dev", "main", "stable"])

    def test_A12_github_sem_chave_ou_nomes_invalidos(self):
        self.gh_setup()
        r = json.loads(req(self.base, "/api/github/create", {"owner": "ana", "repo": "x"})[1])
        self.assertIn("Falta ligar ao GitHub", r["error"])
        req(self.base, "/api/github/check", {"token": "tok"})
        for owner, repo in (("ana", "tem espaços"), ("ana", ".."), ("a/b", "x"), ("", "x")):
            r = json.loads(req(self.base, "/api/github/create", {"owner": owner, "repo": repo})[1])
            self.assertFalse(r["ok"], (owner, repo))
        self.assertEqual(self.gm.repos, {})

    def test_A13_github_chave_sem_permissoes(self):
        self.gh_setup(scopes="read:user")
        r = json.loads(req(self.base, "/api/github/check", {"token": "tok"})[1])
        self.assertFalse(r["ok"])
        self.assertIn("«workflow»", r["error"])
        self.assertIsNone(A.STATE["gh"])

    def test_A14_github_plano_gratuito_aviso_e_token_nao_fica_em_disco(self):
        self.gh_setup(ruleset_status=403)
        req(self.base, "/api/github/check", {"token": "tok"})
        req(self.base, "/api/github/create", {"owner": "ana", "repo": "p2", "private": True})
        s = self.gh_wait()
        self.assertEqual(s["state"], "done")
        self.assertEqual(len(s["avisos"]), 1)
        req(self.base, "/api/config", {"github": {"owner": "ana", "repo": "p2", "private": True}, "n8n_url": "x"})
        self.assertNotIn("tok", A.CONFIG.read_text())
        self.assertNotIn("ghp_", A.CONFIG.read_text())

    def test_A15_github_erro_traduzido(self):
        self.assertIn("permissão", A.gh_friendly(TG.G.GitHubError(403, "HTTP 403: x")))
        self.assertIn("erro temporário", A.gh_friendly(TG.G.GitHubError(502, "HTTP 502: x")))
        self.assertIn("internet", A.gh_friendly(TG.G.GitHubError(0, "sem ligação")))


if __name__ == "__main__":
    unittest.main()
