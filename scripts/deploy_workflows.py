#!/usr/bin/env python3
"""Instala (ou atualiza) todos os workflows de workflows/ numa instância n8n.

Uso:
  N8N_API_KEY=... python3 scripts/deploy_workflows.py --config deploy/config.json
  python3 scripts/deploy_workflows.py --config deploy/config.json --dry-run   # só escreve deploy/out/

O que faz, sem configuração manual no n8n:
- ordena os workflows pelas dependências ({{WF:Nome}} e errorWorkflow);
- cria cada um (ou atualiza, se já existir um com o mesmo nome) e troca os marcadores pelos IDs novos;
- aplica a configuração de produção (emails, canais Slack, URLs, credenciais) vinda de deploy/config.json;
- ativa os que o manifest marca como publish=true.
Falha antes de tocar na instância se a configuração estiver incompleta.
Só usa a biblioteca padrão. As credenciais têm de existir no destino (os IDs vão no config).
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF_DIR = ROOT / "workflows"
MARK = re.compile(r"\{\{WF:([^}]+)\}\}")
DEV_SLACK = {"C0C7T8J8D54": "propostas", "C0C7V2PU4PL": "cotacoes", "C0C7SN9MKQE": "estado"}
CORE_SETTINGS = {"executionOrder", "saveDataErrorExecution", "saveDataSuccessExecution",
                 "saveManualExecutions", "saveExecutionProgress", "executionTimeout",
                 "errorWorkflow", "timezone"}
REDACTED = "REDACTED@example.invalid"

# (nome do workflow, nome do nó, campo do Set) -> caminho no config ("emails.erros") ou "@url:/caminho"
BINDINGS = [
    ("Mail Error Flow", "Preparar aviso de erro", "destinatario", "emails.erros"),
    ("WF2 Error Flow - Pedido de proposta", "Preparar aviso do WF2", "destinatario", "emails.erros"),
    ("WF2 - Pedido de proposta", "Normalizar pedido", "destinatario_confirmacao", "emails.confirmacao_pedido"),
    ("WF3 - Pedido de cotação de frete", "Configuração", "destinatario_principal", "emails.cotacoes"),
    ("WF5 - Resumo para validação", "Normalizar código", "destinatario_validacao", "emails.validacao_barbara"),
    ("WF9 - Envio da proposta ao cliente", "Normalizar código", "cc_barbara", "emails.cc_barbara"),
    ("WF9 - Envio da proposta ao cliente", "Normalizar código", "url_confirmacao", "@url:/webhook/confirmar-proposta"),
    ("WF12 - Follow-up ao cliente", "Normalizar código", "cc_barbara", "emails.cc_barbara"),
    ("WF10 - Confirmação da encomenda", "Configuração", "email_madalena", "emails.madalena"),
    ("WF10 - Confirmação da encomenda", "Configuração", "email_barbara", "emails.barbara"),
    ("WF10 - Confirmação da encomenda", "Configuração", "url_base", "@url:/webhook/confirmar-proposta"),
    ("WF10 - Confirmação da encomenda", "Configuração", "url_form", "@url:/form/plano-expedicao"),
]


class DeployError(Exception):
    pass


def get_path(cfg, path):
    cur = cfg
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            raise DeployError("config em falta: %s" % path)
        cur = cur[p]
    if cur in ("", None, []) or (isinstance(cur, str) and not cur.strip()):
        raise DeployError("config vazia: %s" % path)
    return cur


def load_workflows():
    man = json.loads((WF_DIR / "manifest.json").read_text(encoding="utf-8"))
    out = {}
    for item in man["workflows"]:
        d = json.loads((WF_DIR / item["file"]).read_text(encoding="utf-8"))
        d["_publish"] = bool(item.get("publish"))
        d["_file"] = item["file"]
        out[d["name"]] = d
    return out


def refs(d):
    names = set(MARK.findall(json.dumps(d, ensure_ascii=False)))
    return names


def order(wfs):
    done, seq, visiting = set(), [], set()

    def visit(n):
        if n in done:
            return
        if n in visiting:
            raise DeployError("dependência circular em %s" % n)
        if n not in wfs:
            raise DeployError("workflow referido não existe em workflows/: %s" % n)
        visiting.add(n)
        for r in sorted(refs(wfs[n])):
            visit(r)
        visiting.discard(n)
        done.add(n)
        seq.append(n)

    for n in wfs:
        visit(n)
    return seq


def check_config(cfg, wfs):
    if not str(cfg.get("n8n_url", "")).startswith("http"):
        raise DeployError("config em falta: n8n_url")
    get_path(cfg, "emails.aprovadores")
    for k in DEV_SLACK.values():
        get_path(cfg, "slack_canais." + k)
    types = set()
    for d in wfs.values():
        for n in d["nodes"]:
            types.update((n.get("credentials") or {}).keys())
    for t in sorted(types):
        get_path(cfg, "credenciais." + t)
    for (_, _, _, path) in BINDINGS:
        if not path.startswith("@"):
            get_path(cfg, path)


def apply_config(d, cfg):
    base = cfg["n8n_url"].rstrip("/")
    for n in d["nodes"]:
        for t, c in (n.get("credentials") or {}).items():
            c["id"] = get_path(cfg, "credenciais." + t)
        params = n.get("parameters", {})
        for a in params.get("assignments", {}).get("assignments", []):
            for (w, node, field, path) in BINDINGS:
                if d["name"] == w and n["name"] == node and a["name"] == field:
                    a["value"] = base + path[5:] if path.startswith("@url:") else get_path(cfg, path)
        if d["name"].startswith("Notificar Slack"):
            s = json.dumps(params, ensure_ascii=False)
            for dev, key in DEV_SLACK.items():
                s = s.replace(dev, cfg["slack_canais"][key])
            n["parameters"] = json.loads(s)
        code = params.get("jsCode")
        if isinstance(code, str) and "AUTORIZADOS" in code:
            lst = json.dumps([e.lower() for e in get_path(cfg, "emails.aprovadores")])
            params["jsCode"] = code.replace("['%s']" % REDACTED, lst)
    return d


def finalize(d, ids):
    s = json.dumps(d, ensure_ascii=False)
    s = MARK.sub(lambda m: ids[m.group(1)], s)
    d = json.loads(s)
    left = []
    text = json.dumps(d, ensure_ascii=False)
    if REDACTED in text:
        left.append("email por preencher (REDACTED)")
    if "{{WF:" in text or "<ID do" in text:
        left.append("referência a workflow por resolver")
    for n in d["nodes"]:
        for a in n.get("parameters", {}).get("assignments", {}).get("assignments", []):
            if a.get("name") == "destinatario_teste" and str(a.get("value", "")).strip():
                left.append("destinatario_teste preenchido (modo de teste ligado)")
    if left:
        raise DeployError("%s: %s" % (d["name"], "; ".join(sorted(set(left)))))
    return d


def body(d):
    st = d.get("settings", {})
    return {"name": d["name"], "nodes": d["nodes"], "connections": d["connections"],
            "settings": {k: v for k, v in st.items() if k in CORE_SETTINGS or k in ("callerPolicy", "callerIds", "availableInMCP")}}


class Api:
    def __init__(self, url, key):
        self.base = url.rstrip("/") + "/api/v1"
        self.key = key

    def call(self, method, path, data=None):
        req = urllib.request.Request(self.base + path, method=method,
                                     data=json.dumps(data).encode() if data is not None else None,
                                     headers={"X-N8N-API-KEY": self.key, "Content-Type": "application/json",
                                              "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raise DeployError("%s %s -> HTTP %s %s" % (method, path, e.code, e.read().decode()[:300]))

    def list_all(self):
        res, cursor = [], None
        while True:
            q = "/workflows?limit=100" + ("&cursor=" + cursor if cursor else "")
            r = self.call("GET", q)
            res += r.get("data", [])
            cursor = r.get("nextCursor")
            if not cursor:
                return res


def save(api, existing, d):
    b = body(d)
    try:
        if d["name"] in existing:
            wid = existing[d["name"]]
            api.call("PUT", "/workflows/%s" % wid, b)
            return wid, "atualizado"
        return api.call("POST", "/workflows", b)["id"], "criado"
    except DeployError as e:
        if "HTTP 400" not in str(e):
            raise
        b["settings"] = {k: v for k, v in b["settings"].items() if k in CORE_SETTINGS}
        if d["name"] in existing:
            wid = existing[d["name"]]
            api.call("PUT", "/workflows/%s" % wid, b)
            return wid, "atualizado (definições reduzidas)"
        return api.call("POST", "/workflows", b)["id"], "criado (definições reduzidas)"


def run(cfg, dry_run=False, only=None, api=None, out_dir=None, progress=None):
    wfs = load_workflows()
    check_config(cfg, wfs)
    seq = order(wfs)
    if only:
        seq = [n for n in seq if n in only or any(only_n in n for only_n in only)]
    ids, report = {}, []
    total = len(seq)
    say = progress or (lambda *_: None)
    existing = {}
    if not dry_run:
        existing = {w["name"]: w["id"] for w in api.list_all()}
    # ids já existentes servem de referência mesmo com --only
    for n in wfs:
        if n in existing:
            ids[n] = existing[n]
    for i, name in enumerate(seq):
        say(i, total, name, "a instalar")
        d = apply_config(json.loads(json.dumps(wfs[name])), cfg)
        publish = d.pop("_publish")
        d.pop("_file")
        d.pop("meta", None)
        # dependências ainda sem ID (dry-run ou criadas nesta corrida) já têm ID porque a ordem as precede
        for r in refs(d):
            if r not in ids:
                raise DeployError("%s depende de %s, que não foi instalado (use sem --only)" % (name, r))
        d = finalize(d, ids)
        if dry_run:
            ids[name] = "DRYRUN-%02d" % i
            if out_dir:
                Path(out_dir).mkdir(parents=True, exist_ok=True)
                (Path(out_dir) / (re.sub(r"\W+", "_", name) + ".json")).write_text(
                    json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            report.append((name, "simulado", ids[name], publish))
            say(i + 1, total, name, "simulado")
            continue
        wid, estado = save(api, existing, d)
        ids[name] = wid
        existing[name] = wid
        if publish:
            api.call("POST", "/workflows/%s/activate" % wid)
            estado += ", ativo"
        report.append((name, estado, wid, publish))
        say(i + 1, total, name, estado)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "deploy" / "config.json"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    try:
        cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
        api = None
        if not a.dry_run:
            key = os.environ.get("N8N_API_KEY")
            if not key:
                raise DeployError("defina N8N_API_KEY (chave de API criada no n8n de destino)")
            api = Api(cfg["n8n_url"], key)
        rep = run(cfg, a.dry_run, a.only, api, ROOT / "deploy" / "out")
    except (DeployError, OSError, ValueError) as e:
        print("ERRO:", e, file=sys.stderr)
        sys.exit(1)
    for name, estado, wid, _ in rep:
        print("%-45s %-22s %s" % (name, estado, wid))


if __name__ == "__main__":
    main()
