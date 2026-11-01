"""Teste de ecrã do «Updates ao fluxo» com um browser real (Playwright) e um Supabase simulado.
Correr: python3 tests/e2e_updates.py [pasta-para-capturas]   (precisa de playwright e chromium)"""
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "app"))
import deploy_app as A  # noqa: E402
import test_atualizar_config as TU  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if out:
    out.mkdir(parents=True, exist_ok=True)
bak = A.CONFIG.read_bytes() if A.CONFIG.exists() else None
A.CONFIG.unlink(missing_ok=True)
fake = TU.FakeSupabase()
srv = A.make_server(0)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = "http://127.0.0.1:%d" % srv.server_port
errors = []


def shot(pg, n):
    if out:
        pg.screenshot(path=str(out / ("u%d.png" % n)), full_page=True)


def ligar(pg, chave):
    pg.fill("#sburl", fake.url)
    pg.fill("#sbkey", chave)
    pg.click("button:has-text(\"Ligar e ver definições\")")
    pg.wait_for_selector("#sbm .msg")


try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 430, "height": 900})
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(url)
        pg.click("button.big:has-text(\"Updates ao fluxo\")")
        assert "Updates ao fluxo" in pg.inner_text("#main")
        assert pg.locator(".bar i").count() == 0  # a barra de passos é só do instalador
        # chave errada
        ligar(pg, "chave-errada")
        assert "service_role" in pg.inner_text("#sbm") and pg.locator("#defs .card").count() == 0
        # falta a migração
        fake.sem_tabela = True
        ligar(pg, TU.CHAVE)
        assert "migração 0009" in pg.inner_text("#sbm") and pg.locator("button:has-text(\"Copiar o texto da atualização\")").count() == 1
        shot(pg, 1)
        fake.sem_tabela = False
        # ligação certa: mostra a definição atual (automático)
        ligar(pg, TU.CHAVE)
        pg.wait_for_selector("#defs .card")
        assert "Enviar automaticamente" in pg.inner_text("#cur_modo_envio")
        assert pg.is_disabled("#ap_modo_envio")
        shot(pg, 2)
        # passa a revisão humana
        pg.check("input[value=revisao]")
        assert not pg.is_disabled("#ap_modo_envio")
        pg.click("#ap_modo_envio")
        pg.wait_for_selector("#rs_modo_envio .msg.ok")
        assert fake.linhas["modo_envio"]["valor"] == "revisao"
        assert fake.linhas["modo_envio"]["atualizado_por"] == "assistente de updates"
        assert "revisão humana" in pg.inner_text("#cur_modo_envio")
        assert pg.is_disabled("#ap_modo_envio")
        shot(pg, 3)
        # e volta a automático
        pg.check("input[value=automatico]")
        pg.click("#ap_modo_envio")
        pg.wait_for_selector("#rs_modo_envio .msg.ok:has-text(\"Enviar automaticamente\")")
        assert fake.linhas["modo_envio"]["valor"] == "automatico"
        # sem scroll horizontal no telemóvel
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        # a chave nunca fica em disco
        assert TU.CHAVE not in (A.CONFIG.read_text(encoding="utf-8") if A.CONFIG.exists() else "")
        # voltar ao menu
        pg.click(".nav button:has-text(\"Menu\")")
        assert "O que quer fazer?" in pg.inner_text("#main")
        # ligação direta e botão Menu do instalador
        pg.goto(url + "#instalar")
        pg.reload()  # só mudar o # não recarrega a página
        assert "Bem-vindo" in pg.inner_text("#main")
        pg.click(".nav button:has-text(\"Menu\")")
        assert "O que quer fazer?" in pg.inner_text("#main")
        b.close()
    assert not errors, errors
    print("E2E UPDATES OK: menu, ligação (chave errada, sem migração, certa), mudança de modo nos dois sentidos")
finally:
    srv.shutdown()
    fake.close()
    if bak is None:
        A.CONFIG.unlink(missing_ok=True)
    else:
        A.CONFIG.write_bytes(bak)
