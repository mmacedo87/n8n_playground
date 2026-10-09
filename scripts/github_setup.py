#!/usr/bin/env python3
"""Cria o repositório GitHub de produção: ficheiros, branches dev/stable/main (mesmo commit), GitHub Action e
regras de proteção do main (só por pull request). Só usa a biblioteca padrão. O token nunca é guardado."""
import base64
import json
import os
import urllib.error
import urllib.request

API = "https://api.github.com"
RULESET_NAME = "proteger-main"
CHECK = "PR para main (origem dev + testes)"
COMMIT_MSG = "chore(inicio): criação do repositório pelo assistente de instalação"
ACTIONS_APP_ID = 15368


class GitHubError(Exception):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status = status


class Gh:
    def __init__(self, token, base=None):
        self.token = token
        self.base = (base or os.environ.get("GITHUB_API_URL") or API).rstrip("/")

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={
            "Authorization": "Bearer " + self.token, "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json", "User-Agent": "instalador-cortica"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else {}), r.headers
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                msg = json.loads(raw).get("message", "")
            except ValueError:
                msg = raw.decode(errors="ignore")[:200]
            raise GitHubError(e.code, "HTTP %d: %s" % (e.code, msg))
        except (urllib.error.URLError, OSError) as e:
            raise GitHubError(0, "sem ligação ao GitHub (%s)" % e)


def whoami(token, base=None):
    """Valida o token. Devolve {login, scopes[]|None}. scopes None = token fine-grained (não dá para saber)."""
    _, u, h = Gh(token, base).call("GET", "/user")
    sc = h.get("X-OAuth-Scopes")
    scopes = None if sc is None else [s.strip() for s in sc.split(",") if s.strip()]
    return {"login": u["login"], "scopes": scopes}


def ruleset():
    return {
        "name": RULESET_NAME, "target": "branch", "enforcement": "active", "bypass_actors": [],
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "rules": [
            {"type": "deletion"}, {"type": "non_fast_forward"},
            {"type": "pull_request", "parameters": {
                "required_approving_review_count": 0, "dismiss_stale_reviews_on_push": False,
                "require_code_owner_review": False, "require_last_push_approval": False,
                "required_review_thread_resolution": False}},
            {"type": "required_status_checks", "parameters": {
                "strict_required_status_checks_policy": False, "do_not_enforce_on_create": True,
                "required_status_checks": [{"context": CHECK, "integration_id": ACTIONS_APP_ID}]}},
        ],
    }


def run(owner, repo, files, token, private=True, progress=None, base=None):
    """files: {caminho: bytes}. progress(passo, estado). Devolve {url, avisos[]}. Pode ser repetido sem duplicar."""
    gh = Gh(token, base)
    P = progress or (lambda *a: None)
    avisos = []
    me = whoami(token, base)["login"]

    P("Criar o repositório", "a fazer")
    st = None
    try:
        body = {"name": repo, "private": bool(private), "auto_init": True, "description": "Automação de propostas comerciais"}
        gh.call("POST", "/user/repos" if owner.lower() == me.lower() else "/orgs/%s/repos" % owner, body)
    except GitHubError as e:
        if e.status != 422:
            raise
        st = "existe"
    if st == "existe":
        try:
            gh.call("GET", "/repos/%s/%s/branches/dev" % (owner, repo))
            ja_feito = True
        except GitHubError as e:
            if e.status != 404:
                raise
            ja_feito = False
        if not ja_feito:
            _, cs, _ = gh.call("GET", "/repos/%s/%s/commits?per_page=2" % (owner, repo))
            if len(cs) > 1:
                raise GitHubError(422, "Esse repositório já existe e já tem conteúdo. Escolha outro nome.")
    else:
        ja_feito = False
    P("Criar o repositório", "ok")

    R = "/repos/%s/%s" % (owner, repo)
    if not ja_feito:
        P("Enviar os ficheiros", "a fazer")
        _, ref, _ = gh.call("GET", R + "/git/ref/heads/main")
        parent = ref["object"]["sha"]
        entries = []
        for path, data in files.items():
            _, b, _ = gh.call("POST", R + "/git/blobs", {"content": base64.b64encode(data).decode(), "encoding": "base64"})
            entries.append({"path": path, "mode": "100755" if path.endswith((".sh", ".command")) else "100644",
                            "type": "blob", "sha": b["sha"]})
        _, tree, _ = gh.call("POST", R + "/git/trees", {"tree": entries})
        _, com, _ = gh.call("POST", R + "/git/commits", {"message": COMMIT_MSG, "tree": tree["sha"], "parents": [parent]})
        P("Enviar os ficheiros", "ok")
        P("Criar os branches dev, stable e main", "a fazer")
        gh.call("PATCH", R + "/git/refs/heads/main", {"sha": com["sha"]})
        for b in ("dev", "stable"):
            gh.call("POST", R + "/git/refs", {"ref": "refs/heads/" + b, "sha": com["sha"]})
        P("Criar os branches dev, stable e main", "ok")

    P("Ativar o GitHub Actions", "a fazer")
    try:
        gh.call("PUT", R + "/actions/permissions", {"enabled": True, "allowed_actions": "all"})
        P("Ativar o GitHub Actions", "ok")
    except GitHubError as e:
        avisos.append("Não consegui confirmar que o GitHub Actions está ativo (%s). Veja em Settings → Actions." % e)
        P("Ativar o GitHub Actions", "aviso")

    P("Proteger o main (só por pull request)", "a fazer")
    try:
        _, rs, _ = gh.call("GET", R + "/rulesets")
        if not any(r.get("name") == RULESET_NAME for r in rs):
            gh.call("POST", R + "/rulesets", ruleset())
        P("Proteger o main (só por pull request)", "ok")
    except GitHubError as e:
        if e.status in (403, 404, 422):
            avisos.append("O GitHub não deixou ativar a proteção do main automaticamente. Em repositórios privados isto "
                          "exige um plano pago (Pro/Team). Pode torná-lo público ou ativar a regra à mão "
                          "(Settings → Rules → New ruleset → main). Detalhe: %s" % e)
            P("Proteger o main (só por pull request)", "aviso")
        else:
            raise
    return {"url": "https://github.com/%s/%s" % (owner, repo), "avisos": avisos}
