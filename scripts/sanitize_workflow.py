#!/usr/bin/env python3
"""Sanitiza um workflow n8n exportado antes de o guardar no Git.

Uso: python3 scripts/sanitize_workflow.py entrada.json > workflows/nome.json

Remove ou substitui:
- ids de credenciais (mantém só o nome)
- webhookId (é o caminho do URL público dos formulários)
- emails (substituídos por REDACTED@example.invalid)
- campos de ambiente (id, versionId, createdAt, updatedAt, scopes, activeVersion...)
- referências a outros workflows (Execute Workflow e errorWorkflow): passam a marcadores
  {{WF:Nome do workflow}}, resolvidos por scripts/deploy_workflows.py na instância de destino
"""
import json
import re
import sys
from pathlib import Path

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
DROP_TOP = {"id", "versionId", "activeVersionId", "createdAt", "updatedAt", "scopes",
            "activeVersion", "triggerCount", "active", "isArchived", "parentFolderId", "nodeGroups"}


def clean(value):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k == "webhookId":
                continue
            if k == "credentials" and isinstance(v, dict):
                out[k] = {t: {"name": c.get("name")} for t, c in v.items()}
                continue
            out[k] = clean(v)
        return out
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, str):
        return EMAIL.sub("REDACTED@example.invalid", value)
    return value


def id_to_name(extra=None):
    """Mapa id de origem -> nome, a partir de workflows/*.json (meta.sourceWorkflowId)."""
    m = dict(extra or {})
    for f in (Path(__file__).resolve().parent.parent / "workflows").glob("*.json"):
        try:
            d = json.load(open(f, encoding="utf-8"))
            m[d["meta"]["sourceWorkflowId"]] = d["name"]
        except (KeyError, ValueError):
            pass
    return m


def placeholders(data, ids):
    """Troca ids de workflows (Execute Workflow, errorWorkflow) por {{WF:Nome}}."""
    def ref(v):
        if isinstance(v, str) and v in ids:
            return "{{WF:%s}}" % ids[v]
        return v
    ew = data.get("settings", {}).get("errorWorkflow")
    if ew:
        data["settings"]["errorWorkflow"] = ref(ew) if ew in ids else "{{WF:Mail Error Flow}}"
    for n in data.get("nodes", []):
        if n.get("type") == "n8n-nodes-base.executeWorkflow":
            w = n["parameters"].get("workflowId")
            if isinstance(w, dict) and isinstance(w.get("value"), str):
                v = w["value"]
                w["value"] = ref(v) if v in ids else v
    return data


def main():
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    data = data.get("workflow", data)
    own = {data["id"]: data["name"]} if "id" in data and "name" in data else {}
    data = {k: v for k, v in data.items() if k not in DROP_TOP}
    data = placeholders(clean(data), id_to_name(own))
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
