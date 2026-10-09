#!/usr/bin/env python3
"""Assistente de instalação (corre só no seu computador, em http://127.0.0.1:8765).

Abre uma página com passos simples. A chave de API nunca é guardada em disco;
o resto da configuração fica em deploy/config.json para poder continuar mais tarde.
Só usa a biblioteca padrão do Python.
"""
import argparse
import json
import re
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import deploy_workflows as D  # noqa: E402
import github_setup as GS  # noqa: E402
import repo_files  # noqa: E402

CONFIG = ROOT / "deploy" / "config.json"
EXAMPLE = ROOT / "deploy" / "config.example.json"
INDEX = Path(__file__).resolve().parent / "index.html"

LABELS = {
    "n8n_url": "o endereço do n8n",
    "emails.erros": "o email dos avisos de erro",
    "emails.confirmacao_pedido": "o email que recebe a confirmação de cada pedido",
    "emails.cotacoes": "o email da empresa para os pedidos de cotação",
    "emails.validacao_barbara": "o email da Bárbara para validação",
    "emails.cc_barbara": "o email da Bárbara em cópia",
    "emails.madalena": "o email da Madalena",
    "emails.barbara": "o email da Bárbara (expedição)",
    "emails.aprovadores": "pelo menos um email autorizado a aprovar",
    "slack_canais.propostas": "o canal do Slack das propostas",
    "slack_canais.cotacoes": "o canal do Slack das cotações",
    "slack_canais.estado": "o canal do Slack do estado",
    "credenciais.microsoftOutlookOAuth2Api": "a conta do Outlook",
    "credenciais.slackApi": "a conta do Slack",
    "credenciais.supabaseApi": "a conta do Supabase (base de dados)",
    "credenciais.openRouterApi": "a conta do OpenRouter (IA)",
}

def novo_gjob():
    return {"state": "idle", "steps": [], "error": None, "url": None, "avisos": []}


STATE = {"key": None, "job": {"state": "idle", "steps": [], "error": None, "total": 0}, "gh": None, "gjob": novo_gjob()}
LOCK = threading.Lock()


def friendly(msg):
    m = re.search(r"config (?:em falta|vazia): (\S+)", msg)
    if m:
        return "Falta preencher %s." % LABELS.get(m.group(1), m.group(1))
    if "HTTP 401" in msg or "HTTP 403" in msg:
        return "O n8n não aceitou a chave de API. Crie uma nova e cole-a outra vez."
    if re.search(r"HTTP 5\d\d", msg):
        return "O n8n teve um erro temporário ao instalar. Clique em Instalar para tentar outra vez: o que já foi instalado não se duplica."
    if "HTTP 404" in msg:
        return "O n8n respondeu, mas sem a função de API. Confirme o endereço e que a API está ativa."
    if "destinatario_teste" in msg:
        return "O modo de teste está ligado num workflow (destinatário de teste preenchido). Tem de ficar vazio em produção."
    if "REDACTED" in msg:
        return "Ficou um email por preencher: %s" % msg
    return msg


def gh_friendly(e):
    st, msg = getattr(e, "status", None), str(e)
    if st == 401:
        return "O GitHub não aceitou a chave. Crie uma nova (passo 1 desta página) e cole-a outra vez."
    if st == 403 or st == 404:
        return "A chave não tem permissão para isto. Crie-a de novo marcando as caixas «repo» e «workflow» (passo 1 desta página)."
    if st == 0:
        return "Não consegui ligar ao GitHub. Confirme a internet e tente outra vez."
    if st and st >= 500:
        return "O GitHub teve um erro temporário. Clique outra vez em Criar: o que já foi feito não se duplica."
    return msg.replace("HTTP %s: " % st, "") if st else msg


def repo_root():
    return ROOT / "repositorio" if (ROOT / "repositorio").is_dir() else ROOT


def gh_check(token):
    try:
        w = GS.whoami(token)
    except GS.GitHubError as e:
        return {"ok": False, "error": gh_friendly(e)}
    sc = w["scopes"]
    if sc is not None and not ({"repo", "workflow"} <= set(sc)):
        return {"ok": False, "error": "A chave funciona, mas falta marcar as caixas «repo» e «workflow». Crie-a de novo (passo 1 desta página)."}
    STATE["gh"] = token
    return {"ok": True, "login": w["login"]}


def gh_job(owner, repo, private):
    job = STATE["gjob"]

    def prog(passo, estado):
        with LOCK:
            st = job["steps"]
            if estado == "a fazer":
                st.append({"name": passo, "estado": estado})
            elif st and st[-1]["name"] == passo:
                st[-1]["estado"] = estado
    try:
        files = repo_files.collect(repo_root())
        r = GS.run(owner, repo, files, STATE["gh"], private=private, progress=prog)
        job.update(state="done", url=r["url"], avisos=r["avisos"])
    except GS.GitHubError as e:
        job.update(state="error", error=gh_friendly(e))
    except Exception as e:
        job.update(state="error", error="Erro inesperado: %s" % e)


def load_cfg():
    if CONFIG.exists():
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    return {"n8n_url": "", "emails": {k: ([] if k == "aprovadores" else "") for k in json.loads(EXAMPLE.read_text(encoding="utf-8"))["emails"]},
            "slack_canais": {"propostas": "", "cotacoes": "", "estado": ""},
            "credenciais": {"microsoftOutlookOAuth2Api": "", "slackApi": "", "supabaseApi": "", "openRouterApi": ""}}


def save_cfg(cfg):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def connect(url, key):
    try:
        api = D.Api(url, key)
        api.call("GET", "/workflows?limit=1")
        return True, "Ligação feita com sucesso."
    except D.DeployError as e:
        return False, friendly(str(e))
    except Exception as e:  # rede, endereço inválido
        return False, "Não consegui chegar ao n8n. Confirme o endereço e a internet. (%s)" % type(e).__name__


def check():
    try:
        rep = D.run(load_cfg(), dry_run=True)
        return {"ok": True, "total": len(rep), "workflows": [r[0] for r in rep]}
    except (D.DeployError, OSError, ValueError) as e:
        return {"ok": False, "error": friendly(str(e))}


def deploy_job():
    job = STATE["job"]

    def prog(i, total, name, estado):
        with LOCK:
            job["total"] = total
            steps = job["steps"]
            if estado == "a instalar":
                steps.append({"name": name, "estado": estado})
            elif steps and steps[-1]["name"] == name:
                steps[-1]["estado"] = estado
    try:
        cfg = load_cfg()
        api = D.Api(cfg["n8n_url"], STATE["key"])
        D.run(cfg, api=api, progress=prog)
        job["state"] = "done"
    except (D.DeployError, OSError, ValueError) as e:
        job["state"] = "error"
        job["error"] = friendly(str(e))
    except Exception as e:
        job["state"] = "error"
        job["error"] = "Erro inesperado: %s" % e


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        raw = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _local(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self._local():
            return self._json({"erro": "só local"}, 403)
        if self.path == "/":
            raw = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif self.path == "/api/config":
            self._json(load_cfg())
        elif self.path == "/api/status":
            with LOCK:
                self._json(STATE["job"])
        elif self.path == "/api/github/status":
            with LOCK:
                self._json(STATE["gjob"])
        elif self.path == "/api/schema":
            sql = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
            self._json({"sql": sql})
        else:
            self._json({"erro": "não existe"}, 404)

    def do_POST(self):
        if not self._local():
            return self._json({"erro": "só local"}, 403)
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/api/config":
            save_cfg(body)
            self._json({"ok": True})
        elif self.path == "/api/connect":
            ok, msg = connect(body.get("url", ""), body.get("key", ""))
            if ok:
                STATE["key"] = body["key"]
            self._json({"ok": ok, "msg": msg})
        elif self.path == "/api/check":
            self._json(check())
        elif self.path == "/api/deploy":
            if not STATE["key"]:
                return self._json({"ok": False, "error": "Falta ligar ao n8n (passo 2)."})
            c = check()
            if not c["ok"]:
                return self._json({"ok": False, "error": c["error"]})
            with LOCK:
                if STATE["job"]["state"] == "running":
                    return self._json({"ok": False, "error": "A instalação já está a decorrer."})
                STATE["job"].update(state="running", steps=[], error=None, total=c["total"])
            threading.Thread(target=deploy_job, daemon=True).start()
            self._json({"ok": True})
        elif self.path == "/api/github/check":
            self._json(gh_check((body.get("token") or "").strip()))
        elif self.path == "/api/github/create":
            if not STATE["gh"]:
                return self._json({"ok": False, "error": "Falta ligar ao GitHub (teste a chave primeiro)."})
            owner, repo = (body.get("owner") or "").strip(), (body.get("repo") or "").strip()
            if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", owner):
                return self._json({"ok": False, "error": "O nome da conta GitHub não é válido."})
            if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", repo) or repo in (".", ".."):
                return self._json({"ok": False, "error": "O nome do repositório só pode ter letras, números, hífen, ponto e sublinhado, sem espaços."})
            with LOCK:
                if STATE["gjob"]["state"] == "running":
                    return self._json({"ok": False, "error": "A criação já está a decorrer."})
                STATE["gjob"] = novo_gjob()
                STATE["gjob"]["state"] = "running"
            threading.Thread(target=gh_job, args=(owner, repo, bool(body.get("private", True))), daemon=True).start()
            self._json({"ok": True})
        else:
            self._json({"erro": "não existe"}, 404)


def make_server(port=8765):
    return ThreadingHTTPServer(("127.0.0.1", port), H)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    srv = make_server(a.port)
    url = "http://127.0.0.1:%d" % srv.server_port
    print("\n  Assistente de instalação a correr.\n  Se o browser não abrir, copie este endereço para o browser:\n  %s\n\n  Para terminar, feche esta janela.\n" % url)
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
