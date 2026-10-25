"""Atualizador de definições (scripts/atualizar_config.py) e endpoints do assistente, contra um Supabase (PostgREST) simulado.
Correr: python3 -m unittest tests/test_atualizar_config.py"""
import io
import json
import os
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "app"))
import atualizar_config as UC  # noqa: E402
import deploy_app as A  # noqa: E402

CHAVE = "SEGREDO-service-role-123"


class FakeSupabase:
    """Tabela configuracao em memória, com a mesma validação da restrição SQL."""

    def __init__(self):
        self.linhas = {"modo_envio": {"chave": "modo_envio", "valor": "automatico", "atualizado_em": "2026-10-25T18:00:00+00:00", "atualizado_por": "migracao 0009"}}
        self.sem_tabela = False
        self.pedidos = []
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _enviar(self, code, obj):
                raw = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _tratar(self):
                n = int(self.headers.get("Content-Length") or 0)
                corpo = json.loads(self.rfile.read(n) or b"{}")
                fake.pedidos.append((self.command, self.path, corpo))
                if self.headers.get("apikey") != CHAVE or self.headers.get("Authorization") != "Bearer " + CHAVE:
                    return self._enviar(401, {"message": "Invalid API key"})
                if fake.sem_tabela:
                    return self._enviar(404, {"code": "PGRST205", "message": "Could not find the table 'public.configuracao' in the schema cache"})
                u = urllib.parse.urlparse(self.path)
                if self.command == "GET":
                    return self._enviar(200, list(fake.linhas.values()))
                if self.command == "PATCH":
                    chave = urllib.parse.parse_qs(u.query)["chave"][0][len("eq."):]
                    if chave == "modo_envio" and corpo.get("valor") not in ("automatico", "revisao"):
                        return self._enviar(400, {"code": "23514", "message": "violates check constraint configuracao_modo_envio_valido"})
                    if chave not in fake.linhas:
                        return self._enviar(200, [])
                    fake.linhas[chave].update(corpo)
                    return self._enviar(200, [fake.linhas[chave]])
                self._enviar(405, {})

            do_GET = do_PATCH = do_POST = _tratar

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.srv.server_port

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


class Modulo(unittest.TestCase):
    def setUp(self):
        self.fake = FakeSupabase()

    def tearDown(self):
        self.fake.close()

    def test_ler_e_definir(self):
        c = UC.Cliente(self.fake.url, CHAVE)
        self.assertEqual(c.ler()["modo_envio"]["valor"], "automatico")
        self.assertEqual(c.definir("modo_envio", "revisao", "teste"), "revisao")
        self.assertEqual(self.fake.linhas["modo_envio"]["valor"], "revisao")
        self.assertEqual(self.fake.linhas["modo_envio"]["atualizado_por"], "teste")
        self.assertEqual(c.definir("modo_envio", "automatico"), "automatico")

    def test_valor_ou_chave_invalidos_nem_chegam_ao_supabase(self):
        c = UC.Cliente(self.fake.url, CHAVE)
        for chave, valor in (("modo_envio", "talvez"), ("modo_envio", ""), ("outra", "x"), ("modo_envio", "AUTOMATICO")):
            with self.assertRaises(UC.AtualizadorError):
                c.definir(chave, valor)
        self.assertEqual(self.fake.pedidos, [])

    def test_chave_errada_da_mensagem_em_portugues_sem_a_chave(self):
        c = UC.Cliente(self.fake.url, "outra-chave-errada")
        with self.assertRaises(UC.AtualizadorError) as cm:
            c.ler()
        self.assertIn("service_role", str(cm.exception))
        self.assertNotIn("outra-chave-errada", str(cm.exception))

    def test_falta_a_migracao(self):
        self.fake.sem_tabela = True
        with self.assertRaises(UC.AtualizadorError) as cm:
            UC.Cliente(self.fake.url, CHAVE).ler()
        self.assertTrue(cm.exception.falta_migracao)
        self.assertIn("0009", str(cm.exception))

    def test_definicao_inexistente(self):
        self.fake.linhas.clear()
        with self.assertRaises(UC.AtualizadorError) as cm:
            UC.Cliente(self.fake.url, CHAVE).definir("modo_envio", "revisao")
        self.assertTrue(cm.exception.falta_migracao)

    def test_url_invalido_e_sem_rede(self):
        for u in ("", "ftp://x.supabase.co", "https://x.supabase.co/rest/v1", "isto nao e url", "https://x.supabase.co?a=1"):
            with self.assertRaises(UC.AtualizadorError, msg=u):
                UC.Cliente(u, CHAVE)
        with self.assertRaises(UC.AtualizadorError):
            UC.Cliente("", "")
        with self.assertRaises(UC.AtualizadorError) as cm:
            UC.Cliente("http://127.0.0.1:1", CHAVE, timeout=2).ler()
        self.assertIn("Não consegui chegar ao Supabase", str(cm.exception))

    def test_definicoes_coerentes_com_o_esquema_sql(self):
        sql = (ROOT / "supabase/migrations/0009_configuracao_modo_envio.sql").read_text(encoding="utf-8")
        for o in UC.DEFINICOES["modo_envio"]["opcoes"]:
            self.assertIn("'%s'" % o["valor"], sql)
        self.assertIn(UC.DEFINICOES["modo_envio"]["por_omissao"], ("automatico", "revisao"))


class CLI(unittest.TestCase):
    def setUp(self):
        self.fake = FakeSupabase()
        self.env = dict(os.environ, SUPABASE_SERVICE_KEY=CHAVE)

    def tearDown(self):
        self.fake.close()

    def correr(self, *args, env=None):
        return subprocess.run([sys.executable, str(ROOT / "scripts/atualizar_config.py"), "--url", self.fake.url, *args],
                              capture_output=True, text=True, env=env or self.env, timeout=60, stdin=subprocess.DEVNULL)

    def test_ver(self):
        r = self.correr("ver")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("modo_envio = automatico", r.stdout)

    def test_simular_nao_altera(self):
        r = self.correr("--simular", "definir", "modo_envio", "revisao")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("simulação", r.stdout)
        self.assertEqual(self.fake.linhas["modo_envio"]["valor"], "automatico")
        self.assertFalse([p for p in self.fake.pedidos if p[0] == "PATCH"])

    def test_definir_e_chave_nunca_aparece(self):
        r = self.correr("definir", "modo_envio", "revisao")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("automatico -> revisao", r.stdout)
        self.assertEqual(self.fake.linhas["modo_envio"]["valor"], "revisao")
        self.assertNotIn(CHAVE, r.stdout + r.stderr)

    def test_valor_invalido_falha_com_mensagem(self):
        r = self.correr("definir", "modo_envio", "talvez")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Valores aceites: automatico, revisao", r.stderr)
        self.assertEqual(self.fake.linhas["modo_envio"]["valor"], "automatico")


class Assistente(unittest.TestCase):
    def setUp(self):
        self.bak = A.CONFIG.read_bytes() if A.CONFIG.exists() else None
        A.STATE.update(key=None, sb=None)
        self.fake = FakeSupabase()
        self.srv = A.make_server(0)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.srv.server_port

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.fake.close()
        A.STATE["sb"] = None
        if self.bak is None:
            A.CONFIG.unlink(missing_ok=True)
        else:
            A.CONFIG.write_bytes(self.bak)

    def req(self, path, body=None, host=None):
        r = urllib.request.Request(self.base + path, method="POST" if body is not None else "GET",
                                   data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"})
        if host:
            r.add_header("Host", host)
        try:
            with urllib.request.urlopen(r, timeout=30) as x:
                return x.status, json.loads(x.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_fluxo_completo_e_chave_nao_fica_em_disco(self):
        c, r = self.req("/api/sb/connect", {"url": self.fake.url, "key": CHAVE})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["atual"]["modo_envio"]["valor"], "automatico")
        c, r = self.req("/api/sb/set", {"chave": "modo_envio", "valor": "revisao"})
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.fake.linhas["modo_envio"]["valor"], "revisao")
        self.assertEqual(self.fake.linhas["modo_envio"]["atualizado_por"], "assistente de updates")
        self.req("/api/config", {"n8n_url": "", "supabase_url": self.fake.url, "emails": {}, "slack_canais": {}, "credenciais": {}})
        self.assertNotIn(CHAVE, A.CONFIG.read_text(encoding="utf-8"))

    def test_set_sem_ligar_e_valor_invalido(self):
        c, r = self.req("/api/sb/set", {"chave": "modo_envio", "valor": "revisao"})
        self.assertFalse(r["ok"])
        self.assertIn("ligar ao Supabase", r["error"])
        self.req("/api/sb/connect", {"url": self.fake.url, "key": CHAVE})
        c, r = self.req("/api/sb/set", {"chave": "modo_envio", "valor": "talvez"})
        self.assertFalse(r["ok"])
        self.assertEqual(self.fake.linhas["modo_envio"]["valor"], "automatico")

    def test_ligacao_falhada_nao_deixa_cliente_ligado(self):
        c, r = self.req("/api/sb/connect", {"url": self.fake.url, "key": "errada"})
        self.assertFalse(r["ok"])
        self.assertIsNone(A.STATE["sb"])
        self.fake.sem_tabela = True
        c, r = self.req("/api/sb/connect", {"url": self.fake.url, "key": CHAVE})
        self.assertFalse(r["ok"])
        self.assertTrue(r["falta_migracao"])

    def test_migracao_so_ficheiros_conhecidos(self):
        c, r = self.req("/api/migracao/0009_configuracao_modo_envio")
        self.assertEqual(c, 200)
        self.assertIn("create table configuracao", r["sql"])
        for mau in ("../../app/deploy_app", "..%2F..%2Fapp%2Fdeploy_app", "0009", "9999_nao_existe", "0009_configuracao_modo_envio.sql"):
            c, r = self.req("/api/migracao/" + mau)
            self.assertEqual(c, 404, mau)

    def test_pagina_tem_menu_com_as_duas_opcoes(self):
        raw = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        for t in ("Deploy Inicial", "Updates ao fluxo", "#instalar", "Ligar e ver definições", "/api/sb/connect", "/api/sb/set"):
            self.assertIn(t, raw)
        self.assertNotIn("localStorage.setItem(\"service", raw)   # a chave service_role nunca vai para o browser storage

    def test_updates_lista_e_so_local(self):
        c, r = self.req("/api/updates")
        self.assertEqual(c, 200)
        self.assertIn("modo_envio", r["definicoes"])
        c, r = self.req("/api/sb/connect", {"url": self.fake.url, "key": CHAVE}, host="evil.example.com")
        self.assertEqual(c, 403)
        self.assertIsNone(A.STATE["sb"])


if __name__ == "__main__":
    unittest.main()
