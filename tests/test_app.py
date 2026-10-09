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
        A.STATE.update(key=None, job={"state": "idle", "steps": [], "error": None, "total": 0})
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


if __name__ == "__main__":
    unittest.main()
