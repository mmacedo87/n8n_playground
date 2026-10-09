#!/usr/bin/env python3
"""Cria dist/Kit-de-instalacao.zip: tudo o que a pessoa que instala precisa, num só ficheiro.
Uso: python3 scripts/build_kit.py"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "Kit-de-instalacao.zip"
FILES = [
    ("app/LEIA-ME-PRIMEIRO.html", "LEIA-ME-PRIMEIRO.html", 0o644),
    ("app/Iniciar-Windows.bat", "Iniciar-Windows.bat", 0o644),
    ("app/Iniciar-Mac.command", "Iniciar-Mac.command", 0o755),
    ("app/deploy_app.py", "app/deploy_app.py", 0o644),
    ("app/index.html", "app/index.html", 0o644),
    ("scripts/deploy_workflows.py", "scripts/deploy_workflows.py", 0o644),
    ("supabase/schema.sql", "supabase/schema.sql", 0o644),
    ("deploy/config.example.json", "deploy/config.example.json", 0o644),
]


def build():
    OUT.parent.mkdir(exist_ok=True)
    items = list(FILES) + [("workflows/" + p.name, "workflows/" + p.name, 0o644)
                           for p in sorted((ROOT / "workflows").glob("*.json"))]
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for src, dst, mode in items:
            info = zipfile.ZipInfo(dst, date_time=(2026, 10, 9, 0, 0, 0))
            info.external_attr = (0o100000 | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            data = (ROOT / src).read_bytes()
            if dst.endswith(".bat"):
                data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            z.writestr(info, data)
    return OUT


if __name__ == "__main__":
    print(build())
