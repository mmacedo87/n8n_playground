"""Testa a criação do repositório GitHub (scripts/github_setup.py) contra uma API GitHub simulada.
Correr: python3 -m unittest tests/test_github.py"""
import base64
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import github_setup as G  # noqa: E402
import repo_files  # noqa: E402


class MockGH:
    def __init__(self, user="ana", scopes="repo, workflow", ruleset_status=None, fail_blob_at=None):
        self.user, self.scopes, self.ruleset_status, self.fail_blob_at = user, scopes, ruleset_status, fail_blob_at
        self.repos = {}      # "owner/repo" -> {refs, commits, blobs, rulesets, actions, private}
        self.log, self.nblobs = [], 0
        m = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send(self, code, obj, hdr=None):
                raw = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Length", str(len(raw)))
                for k, v in (hdr or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(raw)

            def handle_any(self, method):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                path = self.path.split("?")[0]
                m.log.append((method, path))
                if self.headers.get("Authorization") != "Bearer tok":
                    return self.send(401, {"message": "Bad credentials"})
                if path == "/user":
                    return self.send(200, {"login": m.user}, {"X-OAuth-Scopes": m.scopes} if m.scopes is not None else {})
                if method == "POST" and path in ("/user/repos", "/orgs/acme/repos"):
                    if path == "/user/repos" and False:
                        pass
                    key = "%s/%s" % (m.user if path == "/user/repos" else "acme", body["name"])
                    if key in m.repos:
                        return self.send(422, {"message": "name already exists on this account"})
                    m.repos[key] = {"refs": {"main": "c0"}, "commits": ["c0"], "blobs": {}, "rulesets": [], "actions": None,
                                    "private": body["private"], "trees": {}, "cmsg": {}}
                    return self.send(201, {"full_name": key})
                parts = path.strip("/").split("/")
                if parts[0] == "repos" and len(parts) >= 3:
                    key = "%s/%s" % (parts[1], parts[2])
                    r = m.repos.get(key)
                    if r is None:
                        return self.send(404, {"message": "Not Found"})
                    rest = "/" + "/".join(parts[3:])
                    if rest.startswith("/branches/"):
                        b = rest.split("/")[2]
                        return self.send(200, {"name": b}) if b in r["refs"] else self.send(404, {"message": "Branch not found"})
                    if rest == "/commits":
                        return self.send(200, [{"sha": c} for c in r["commits"][::-1][:2]])
                    if rest.startswith("/git/ref/heads/"):
                        b = rest.rsplit("/", 1)[1]
                        return self.send(200, {"object": {"sha": r["refs"][b]}})
                    if rest == "/git/blobs":
                        m.nblobs += 1
                        if m.fail_blob_at and m.nblobs == m.fail_blob_at:
                            m.fail_blob_at = None
                            return self.send(502, {"message": "Bad gateway"})
                        sha = "b%d" % m.nblobs
                        r["blobs"][sha] = base64.b64decode(body["content"])
                        return self.send(201, {"sha": sha})
                    if rest == "/git/trees":
                        sha = "t%d" % (len(r["trees"]) + 1)
                        r["trees"][sha] = body["tree"]
                        return self.send(201, {"sha": sha})
                    if rest == "/git/commits":
                        sha = "c%d" % len(r["commits"])
                        r["commits"].append(sha)
                        r["cmsg"][sha] = (body["message"], body["tree"], body["parents"])
                        return self.send(201, {"sha": sha})
                    if rest == "/git/refs" and method == "POST":
                        b = body["ref"].replace("refs/heads/", "")
                        if b in r["refs"]:
                            return self.send(422, {"message": "Reference already exists"})
                        r["refs"][b] = body["sha"]
                        return self.send(201, {})
                    if rest.startswith("/git/refs/heads/") and method == "PATCH":
                        r["refs"][rest.rsplit("/", 1)[1]] = body["sha"]
                        return self.send(200, {})
                    if rest == "/actions/permissions":
                        r["actions"] = body
                        return self.send(204 if False else 200, {})
                    if rest == "/rulesets" and method == "GET":
                        return self.send(200, r["rulesets"])
                    if rest == "/rulesets" and method == "POST":
                        if m.ruleset_status:
                            return self.send(m.ruleset_status, {"message": "Upgrade to GitHub Pro or make this repository public to enable this feature."})
                        r["rulesets"].append(body)
                        return self.send(201, body)
                self.send(404, {"message": "Not Found"})

            def do_GET(self): self.handle_any("GET")
            def do_POST(self): self.handle_any("POST")
            def do_PUT(self): self.handle_any("PUT")
            def do_PATCH(self): self.handle_any("PATCH")

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = "http://127.0.0.1:%d" % self.srv.server_port
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


FILES = repo_files.collect(ROOT)


class T(unittest.TestCase):
    def setUp(self):
        self.m = MockGH()
        self.addCleanup(self.m.close)

    def run_(self, repo="propostas", owner="ana", **kw):
        steps = []
        r = G.run(owner, repo, FILES, "tok", base=self.m.url, progress=lambda s, e: steps.append((s, e)), **kw)
        return r, steps

    def test_G1_cria_tudo_com_o_mesmo_commit(self):
        r, steps = self.run_()
        repo = self.m.repos["ana/propostas"]
        self.assertEqual(r["url"], "https://github.com/ana/propostas")
        self.assertEqual(r["avisos"], [])
        self.assertEqual(sorted(repo["refs"]), ["dev", "main", "stable"])
        self.assertEqual(len(set(repo["refs"].values())), 1)
        self.assertNotEqual(repo["refs"]["main"], "c0")
        msg, tree, parents = repo["cmsg"][repo["refs"]["main"]]
        self.assertTrue(msg.startswith("chore(inicio):"))
        self.assertEqual(parents, ["c0"])
        self.assertEqual({e["path"] for e in repo["trees"][tree]}, set(FILES))
        self.assertTrue(repo["private"])
        self.assertEqual(repo["actions"], {"enabled": True, "allowed_actions": "all"})
        self.assertTrue(all(e in ("ok", "a fazer") for _, e in steps))

    def test_G2_conteudo_inclui_action_e_exclui_segredos(self):
        self.assertIn(".github/workflows/main-so-por-pr.yml", FILES)
        self.assertIn("workflows/manifest.json", FILES)
        self.assertEqual(len([p for p in FILES if p.startswith("workflows/") and p.endswith(".json")]), 16)
        for bad in ("deploy/config.json", "CLAUDE.md", "dist/Kit-de-instalacao.zip"):
            self.assertNotIn(bad, FILES)
        txt = b"".join(FILES.values()).decode(errors="ignore")
        import re
        for pat in (r"xoxb-\d{6,}", r"sk-or-v1-[0-9a-f]{10,}", r"ghp_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}", r"eyJ[A-Za-z0-9_-]{20,}"):
            self.assertIsNone(re.search(pat, txt), pat)

    def test_G3_ruleset_main_so_por_pr(self):
        self.run_()
        rs = self.m.repos["ana/propostas"]["rulesets"]
        self.assertEqual(len(rs), 1)
        rs = rs[0]
        self.assertEqual(rs["enforcement"], "active")
        self.assertEqual(rs["bypass_actors"], [])
        self.assertEqual(rs["conditions"]["ref_name"]["include"], ["refs/heads/main"])
        tipos = {x["type"] for x in rs["rules"]}
        self.assertEqual(tipos, {"deletion", "non_fast_forward", "pull_request", "required_status_checks"})
        chk = [x for x in rs["rules"] if x["type"] == "required_status_checks"][0]["parameters"]["required_status_checks"][0]
        self.assertEqual(chk["context"], "PR para main (origem dev + testes)")
        # o nome do check tem de existir mesmo na Action
        self.assertIn("name: PR para main (origem dev + testes)", FILES[".github/workflows/main-so-por-pr.yml"].decode())

    def test_G4_organizacao(self):
        r, _ = self.run_(owner="acme")
        self.assertIn("acme/propostas", self.m.repos)
        self.assertIn(("POST", "/orgs/acme/repos"), self.m.log)

    def test_G5_token_invalido(self):
        with self.assertRaises(G.GitHubError) as c:
            G.run("ana", "x", FILES, "errado", base=self.m.url)
        self.assertEqual(c.exception.status, 401)

    def test_G6_nome_ja_usado_com_conteudo(self):
        self.run_()
        # outro repo com conteúdo alheio
        self.m.repos["ana/outro"] = {"refs": {"main": "c1"}, "commits": ["c0", "c1"], "blobs": {}, "rulesets": [], "actions": None, "private": True, "trees": {}, "cmsg": {}}
        with self.assertRaises(G.GitHubError) as c:
            self.run_(repo="outro")
        self.assertIn("já tem conteúdo", str(c.exception))
        self.assertEqual(self.m.repos["ana/outro"]["refs"], {"main": "c1"})

    def test_G7_repetir_nao_duplica(self):
        self.run_()
        n = len(self.m.repos["ana/propostas"]["commits"])
        r, _ = self.run_()
        repo = self.m.repos["ana/propostas"]
        self.assertEqual(len(repo["commits"]), n)
        self.assertEqual(len(repo["rulesets"]), 1)
        self.assertEqual(r["avisos"], [])

    def test_G8_falha_a_meio_e_repetir(self):
        self.m.fail_blob_at = 5
        with self.assertRaises(G.GitHubError):
            self.run_()
        repo = self.m.repos["ana/propostas"]
        self.assertEqual(sorted(repo["refs"]), ["main"])      # nada de meio feito nos branches
        self.run_()
        self.assertEqual(sorted(repo["refs"]), ["dev", "main", "stable"])
        self.assertEqual(len(repo["rulesets"]), 1)

    def test_G9_plano_gratuito_privado_da_aviso(self):
        self.m.ruleset_status = 403
        r, steps = self.run_()
        self.assertEqual(len(r["avisos"]), 1)
        self.assertIn("plano pago", r["avisos"][0])
        self.assertIn(("Proteger o main (só por pull request)", "aviso"), steps)
        self.assertEqual(sorted(self.m.repos["ana/propostas"]["refs"]), ["dev", "main", "stable"])

    def test_G10_whoami_scopes(self):
        self.assertEqual(G.whoami("tok", self.m.url), {"login": "ana", "scopes": ["repo", "workflow"]})
        self.m.scopes = None
        self.assertIsNone(G.whoami("tok", self.m.url)["scopes"])

    def test_G11_executaveis(self):
        self.run_()
        repo = self.m.repos["ana/propostas"]
        tree = repo["cmsg"][repo["refs"]["main"]][1]
        modos = {e["path"]: e["mode"] for e in repo["trees"][tree]}
        self.assertEqual(modos["scripts/check_no_secrets.sh"], "100755")
        self.assertEqual(modos["app/Iniciar-Mac.command"], "100755")
        self.assertEqual(modos["workflows/manifest.json"], "100644")


if __name__ == "__main__":
    unittest.main()
