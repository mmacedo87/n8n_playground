"""Lista dos ficheiros que vão para o repositório GitHub de produção (sem segredos, sem dados desta instância)."""
from pathlib import Path

INCLUDE = [
    ".github/workflows/*.yml", ".gitignore", "README.md", "workflows/*.json", "scripts/*.py", "scripts/*.sh",
    "supabase/schema.sql", "supabase/migrations/*", "deploy/config.example.json", "app/*.py", "app/*.html",
    "app/*.bat", "app/*.command", "tests/test_*.py", "tests/e2e*.py", "tests/BATERIA.md",
    "docs/passagem-producao.md", "docs/versionamento.md", "docs/resumo-cliente.html",
]
EXECUTAVEIS = (".sh", ".command")


def collect(root):
    """Devolve {caminho_relativo: bytes} ordenado."""
    root = Path(root)
    out = {}
    for pat in INCLUDE:
        for p in sorted(root.glob(pat)):
            if p.is_file() and "__pycache__" not in p.parts:
                out[p.relative_to(root).as_posix()] = p.read_bytes()
    return dict(sorted(out.items()))
