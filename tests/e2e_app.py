"""Teste de ecrã do assistente com um browser real (Playwright) e uma API n8n simulada.
Correr: python3 tests/e2e_app.py [pasta-para-capturas]   (precisa de playwright e chromium)"""
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "app"))
import test_deploy as TD  # noqa: E402
import deploy_app as A  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if out:
    out.mkdir(parents=True, exist_ok=True)
bak = A.CONFIG.read_bytes() if A.CONFIG.exists() else None
A.CONFIG.unlink(missing_ok=True)
mock = TD.Mock()
srv = A.make_server(0)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = "http://127.0.0.1:%d" % srv.server_port
c = TD.CFG
errors = []


def shot(pg, n):
    if out:
        pg.screenshot(path=str(out / ("%d.png" % n)), full_page=True)


try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 430, "height": 900})
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(url)
        assert "Bem-vindo" in pg.inner_text("#main")
        shot(pg, 0)
        pg.click("button:has-text(\"Começar\")")
        # passo 1 bloqueado até confirmar
        assert pg.is_disabled(".nav button:last-child")
        pg.check("#db")
        shot(pg, 1)
        pg.click(".nav button:last-child")
        # passo 2
        pg.fill("#url", mock.url)
        assert pg.is_disabled(".nav button:last-child")
        pg.fill("#key", "chave")
        pg.click("button:has-text(\"Testar ligação\")")
        pg.wait_for_selector(".msg.ok")
        assert not pg.is_disabled(".nav button:last-child")
        shot(pg, 2)
        pg.click(".nav button:last-child")
        # passo 3: cola endereços completos
        ins = pg.locator(".cred input")
        for i, k in enumerate(["microsoftOutlookOAuth2Api", "slackApi", "supabaseApi", "openRouterApi"]):
            assert pg.is_disabled(".nav button:last-child")
            ins.nth(i).fill("https://empresa.app.n8n.cloud/home/credentials/Abc12345%d" % i)
        assert pg.locator(".cred.done").count() == 4
        assert not pg.is_disabled(".nav button:last-child")
        shot(pg, 3)
        pg.click(".nav button:last-child")
        # passo 4
        txt = pg.locator("#main input[type=text]")
        mails = ["cotacoes", "validacao_barbara", "cc_barbara", "barbara", "madalena", "confirmacao_pedido", "erros"]
        for i, k in enumerate(mails):
            txt.nth(i).fill(c["emails"][k])
        txt.nth(7).fill("b@x.pt, c@x.pt")
        for i, k in enumerate(["propostas", "cotacoes", "estado"]):
            assert pg.is_disabled("#n4 .nav button:last-child")
            txt.nth(8 + i).fill("https://x.slack.com/archives/C0AB12CD3%d" % i)
        assert not pg.is_disabled("#n4 .nav button:last-child")
        shot(pg, 4)
        pg.click("#n4 .nav button:last-child")
        # passo 5
        assert pg.is_disabled("#n5 .nav button:last-child")
        pg.click("button:has-text(\"Verificar tudo\")")
        pg.wait_for_selector("#ck .msg")
        pg.wait_for_selector("#ck .msg.ok")
        shot(pg, 5)
        pg.click("#n5 .nav button:last-child")
        # passo 6
        pg.click("button:has-text(\"Instalar agora\")")
        pg.wait_for_selector("#fin .msg.ok", timeout=30000)
        shot(pg, 6)
        assert len(mock.store) == 15
        cfg = json.loads(A.CONFIG.read_text())
        assert cfg["credenciais"]["slackApi"] == "Abc123451"
        assert cfg["slack_canais"]["estado"] == "C0AB12CD32"
        assert cfg["emails"]["aprovadores"] == ["b@x.pt", "c@x.pt"]
        b.close()
    assert not errors, errors
    print("E2E OK: 7 passos percorridos, 15 workflows instalados na API simulada")
finally:
    srv.shutdown()
    mock.close()
    if bak is None:
        A.CONFIG.unlink(missing_ok=True)
    else:
        A.CONFIG.write_bytes(bak)
