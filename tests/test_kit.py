"""Testa o kit de instalação: constrói o zip, extrai para uma pasta limpa e arranca o assistente. Correr: python3 -m unittest tests/test_kit.py"""
import json
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_kit  # noqa: E402


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zip = build_kit.build()
        cls.tmp = tempfile.TemporaryDirectory()
        zipfile.ZipFile(cls.zip).extractall(cls.tmp.name)
        cls.dir = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_K1_conteudo(self):
        for f in ["LEIA-ME-PRIMEIRO.html", "Iniciar-Windows.bat", "Iniciar-Mac.command", "app/deploy_app.py", "app/index.html",
                  "scripts/deploy_workflows.py", "supabase/schema.sql", "deploy/config.example.json", "workflows/manifest.json"]:
            self.assertTrue((self.dir / f).exists(), f)
        self.assertEqual(len(list((self.dir / "workflows").glob("*.json"))), 16)
        self.assertFalse((self.dir / "deploy" / "config.json").exists())

    def test_K2_sem_segredos_nem_dados_pessoais(self):
        txt = "".join(p.read_text(errors="ignore") for p in self.dir.rglob("*") if p.is_file())
        import re
        for bad in (r"xoxb-\d{6,}", r"sk-or-v1-[0-9a-f]{10,}", r"mm\.n8n\.wflow", r"live\.com\.pt", r"eyJ[A-Za-z0-9_-]{20,}"):
            self.assertIsNone(re.search(bad, txt), bad)

    def test_K3_launchers(self):
        bat = (self.dir / "Iniciar-Windows.bat").read_bytes()
        self.assertIn(b"\r\n", bat)
        self.assertIn(b"python.org/downloads", bat)
        mac = zipfile.ZipFile(self.zip).getinfo("Iniciar-Mac.command")
        self.assertTrue((mac.external_attr >> 16) & 0o100)

    def test_K4_assistente_arranca_a_partir_do_kit(self):
        s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
        p = subprocess.Popen([sys.executable, str(self.dir / "app" / "deploy_app.py"), "--no-browser", "--port", str(port)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try:
                    raw = urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=2).read()
                    break
                except OSError:
                    time.sleep(0.1)
            self.assertIn("Instalação da automação".encode(), raw)
            cfg = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/api/config" % port).read())
            self.assertEqual(cfg["n8n_url"], "")
            chk = urllib.request.Request("http://127.0.0.1:%d/api/check" % port, data=b"{}", method="POST",
                                         headers={"Content-Type": "application/json"})
            r = json.loads(urllib.request.urlopen(chk).read())
            self.assertFalse(r["ok"])
            self.assertTrue(r["error"].startswith("Falta preencher"))
        finally:
            p.kill()
            p.wait()
            (self.dir / "deploy" / "config.json").unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
