#!/usr/bin/env python3
"""Sanitiza um workflow n8n exportado antes de o guardar no Git.

Uso: python3 scripts/sanitize_workflow.py entrada.json > workflows/nome.json

Remove ou substitui:
- ids de credenciais (mantém só o nome)
- webhookId (é o caminho do URL público dos formulários)
- emails (substituídos por REDACTED@example.invalid)
- campos de ambiente (id, versionId, createdAt, updatedAt, scopes, activeVersion...)
"""
import json
import re
import sys

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


def main():
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    data = data.get("workflow", data)
    data = {k: v for k, v in data.items() if k not in DROP_TOP}
    json.dump(clean(data), sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
