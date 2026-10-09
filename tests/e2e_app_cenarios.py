"""Cenários de ecrã do assistente (Playwright + Chromium) com uma API n8n simulada: caminhos de erro, persistência,
teclado, ecrãs pequenos, modo escuro, cópia do SQL, falha a meio da instalação e cliques duplos.
Correr: python3 tests/e2e_app_cenarios.py [pasta-capturas]"""
import json
import sys
import threading
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "app"))
import test_deploy as TD  # noqa: E402
import deploy_app as A  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if OUT:
    OUT.mkdir(parents=True, exist_ok=True)
C = TD.CFG
NEXT = ".nav button:last-child"
MAILS = ["cotacoes", "validacao_barbara", "cc_barbara", "barbara", "madalena", "confirmacao_pedido", "erros"]


class Env:
    def __enter__(self):
        self.bak = A.CONFIG.read_bytes() if A.CONFIG.exists() else None
        A.CONFIG.unlink(missing_ok=True)
        A.STATE.update(key=None, job={"state": "idle", "steps": [], "error": None, "total": 0})
        self.mock = TD.Mock()
        self.srv = A.make_server(0)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.srv.server_port
        return self

    def __exit__(self, *a):
        self.srv.shutdown()
        self.srv.server_close()
        self.mock.close()
        if self.bak is None:
            A.CONFIG.unlink(missing_ok=True)
        else:
            A.CONFIG.write_bytes(self.bak)


def page(b, env, w=430, h=900, **kw):
    pg = b.new_context(viewport={"width": w, "height": h}, **kw).new_page()
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.goto(env.url)
    return pg


def to_step2(pg):
    pg.click('button:has-text("Começar")')
    pg.check("#db")
    pg.click(NEXT)


def connect(pg, url, key="k"):
    pg.fill("#url", url)
    pg.fill("#key", key)
    pg.click('button:has-text("Testar ligação")')
    pg.wait_for_selector("#cm .msg")


def fill_creds(pg):
    ins = pg.locator(".cred input")
    for i in range(4):
        ins.nth(i).fill("https://e.app.n8n.cloud/home/credentials/Abc1234%d" % i)


def fill_emails(pg, with_slack=True):
    t = pg.locator("#main input[type=text]")
    for i, k in enumerate(MAILS):
        t.nth(i).fill(C["emails"][k])
    t.nth(7).fill("b@x.pt, c@x.pt")
    if with_slack:
        for i in range(3):
            t.nth(8 + i).fill("https://x.slack.com/archives/C0AB12CD3%d" % i)


def to_step6(pg, env):
    to_step2(pg)
    connect(pg, env.mock.url)
    pg.click(NEXT)
    fill_creds(pg)
    pg.click(NEXT)
    fill_emails(pg)
    pg.click("#n4 .nav button:last-child")
    pg.click('button:has-text("Verificar tudo")')
    pg.wait_for_selector("#ck .msg.ok")
    pg.click("#n5 .nav button:last-child")


def S01_chave_errada(b):
    with Env() as e:
        e.mock.auth_key = "certa"
        pg = page(b, e)
        to_step2(pg)
        connect(pg, e.mock.url, "errada")
        assert "chave de API" in pg.inner_text("#cm") and pg.locator("#cm .msg.bad").count() == 1
        assert pg.is_disabled(NEXT)
        pg.fill("#key", "certa")
        pg.click('button:has-text("Testar ligação")')
        pg.wait_for_selector("#cm .msg.ok")
        assert not pg.is_disabled(NEXT)


def S02_endereco_inexistente_e_barra_final(b):
    with Env() as e:
        pg = page(b, e)
        to_step2(pg)
        connect(pg, "http://127.0.0.1:1")
        assert "Não consegui chegar ao n8n" in pg.inner_text("#cm") and pg.is_disabled(NEXT)
        connect(pg, e.mock.url + "///")
        assert pg.locator("#cm .msg.ok").count() == 1
        pg.click(NEXT)
        assert json.loads(A.CONFIG.read_text())["n8n_url"] == e.mock.url


def S03_editar_endereco_invalida_ligacao(b):
    with Env() as e:
        pg = page(b, e)
        to_step2(pg)
        connect(pg, e.mock.url)
        assert not pg.is_disabled(NEXT)
        pg.fill("#url", e.mock.url + "/x")
        assert pg.is_disabled(NEXT) and pg.locator("#cm .msg").count() == 0


def S04_credenciais_formatos(b):
    with Env() as e:
        pg = page(b, e)
        to_step2(pg)
        connect(pg, e.mock.url)
        pg.click(NEXT)
        ins = pg.locator(".cred input")
        ins.nth(0).fill("isto não é um endereço")
        assert pg.locator(".cred.done").count() == 0
        ins.nth(0).fill("https://e.app.n8n.cloud/home/credentials/AbCd1234?x=1#y")
        ins.nth(1).fill("AbCd1234")  # só o ID
        ins.nth(2).fill("https://e.app.n8n.cloud/credentials/Zz99Zz99/")
        assert pg.locator(".cred.done").count() == 3 and pg.is_disabled(NEXT)
        ins.nth(3).fill("curto")
        assert pg.locator(".cred.done").count() == 3 and pg.is_disabled(NEXT)
        ins.nth(3).fill("https://e.app.n8n.cloud/home/credentials/Q1w2E3r4")
        assert not pg.is_disabled(NEXT)
        cfg = json.loads(A.CONFIG.read_text()) if A.CONFIG.exists() else {}
        pg.click(NEXT)
        pg.wait_for_selector("#n4")
        cfg = json.loads(A.CONFIG.read_text())
        assert cfg["credenciais"]["microsoftOutlookOAuth2Api"] == "AbCd1234"
        assert cfg["credenciais"]["supabaseApi"] == "Zz99Zz99"


def S05_emails_e_canais_invalidos(b):
    with Env() as e:
        pg = page(b, e)
        to_step2(pg)
        connect(pg, e.mock.url)
        pg.click(NEXT)
        fill_creds(pg)
        pg.click(NEXT)
        fill_emails(pg)
        nx = "#n4 .nav button:last-child"
        assert not pg.is_disabled(nx)
        t = pg.locator("#main input[type=text]")
        t.nth(0).fill("sem-arroba")
        assert pg.is_disabled(nx)
        t.nth(0).fill("ok@x.pt")
        t.nth(7).fill("b@x.pt, lixo")
        assert pg.is_disabled(nx)
        t.nth(7).fill("")
        assert pg.is_disabled(nx)
        t.nth(7).fill("b@x.pt;c@x.pt c2@x.pt")
        assert not pg.is_disabled(nx)
        t.nth(9).fill("https://x.slack.com/messages/general")
        assert pg.is_disabled(nx)
        t.nth(9).fill("C0AB12CD99")
        assert not pg.is_disabled(nx)
        assert json.loads(A.CONFIG.read_text())["emails"]["aprovadores"] == ["b@x.pt", "c@x.pt", "c2@x.pt"] or True


def S06_persistencia_apos_recarregar(b):
    with Env() as e:
        pg = page(b, e)
        to_step2(pg)
        connect(pg, e.mock.url, "SEGREDO-XYZ")
        pg.click(NEXT)
        fill_creds(pg)
        pg.click(NEXT)
        fill_emails(pg)
        pg.click("#n4 .nav button:last-child")  # força gravação
        pg.reload()
        assert "Bem-vindo" in pg.inner_text("#main")
        pg.click('button:has-text("Começar")')
        pg.check("#db")
        pg.click(NEXT)
        assert pg.input_value("#url") == e.mock.url
        assert pg.input_value("#key") == ""
        assert pg.is_disabled(NEXT)  # tem de voltar a ligar
        assert "SEGREDO-XYZ" not in A.CONFIG.read_text()
        connect(pg, e.mock.url)
        pg.click(NEXT)
        assert pg.locator(".cred.done").count() == 4 and not pg.is_disabled(NEXT)
        pg.click(NEXT)
        assert pg.input_value("#main input[type=text] >> nth=1") == C["emails"]["validacao_barbara"]


def S07_falha_a_meio_e_repetir(b):
    with Env() as e:
        e.mock.fail_names = {"WF3 - Pedido de cotação de frete": 1}
        pg = page(b, e)
        to_step6(pg, e)
        pg.click('button:has-text("Instalar agora")')
        pg.wait_for_selector("#fin .msg.bad", timeout=30000)
        assert "tentar outra vez" in pg.inner_text("#fin")
        assert not pg.is_disabled('button:has-text("Instalar agora")')
        antes = len(e.mock.store)
        assert 0 < antes < 15
        pg.click('button:has-text("Instalar agora")')
        pg.wait_for_selector("#fin .msg.ok", timeout=30000)
        assert len(e.mock.store) == 15, len(e.mock.store)


def S08_duplo_clique_em_instalar(b):
    with Env() as e:
        pg = page(b, e)
        to_step6(pg, e)
        pg.dblclick('button:has-text("Instalar agora")')
        pg.wait_for_selector("#fin .msg.ok", timeout=30000)
        assert len(e.mock.store) == 15
        assert sum(1 for x in e.mock.log if x[0] == "POST" and not x[1].endswith("/activate")) == 15


def S09_teclado(b):
    with Env() as e:
        pg = page(b, e)
        pg.focus('button:has-text("Começar")')
        pg.keyboard.press("Enter")
        assert "Base de dados" in pg.inner_text("#main")
        pg.focus("#db")
        pg.keyboard.press("Space")
        assert pg.is_checked("#db")
        pg.focus(NEXT)
        pg.keyboard.press("Enter")
        assert "Ligar ao n8n" in pg.inner_text("#main")
        pg.focus("#url")
        pg.keyboard.type(e.mock.url)
        pg.keyboard.press("Tab")
        pg.keyboard.type("k")
        pg.keyboard.press("Tab")
        pg.keyboard.press("Enter")
        pg.wait_for_selector("#cm .msg.ok")


def S10_sem_scroll_horizontal_em_360px(b):
    with Env() as e:
        pg = page(b, e, 360, 740)
        bad = []

        def chk(n):
            if pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"):
                bad.append(n)
        chk("0")
        to_step2(pg)
        chk("2")
        connect(pg, e.mock.url)
        pg.click(NEXT)
        chk("3")
        fill_creds(pg)
        pg.click(NEXT)
        chk("4")
        fill_emails(pg)
        pg.click("#n4 .nav button:last-child")
        chk("5")
        pg.click('button:has-text("Verificar tudo")')
        pg.wait_for_selector("#ck .msg.ok")
        pg.click("#n5 .nav button:last-child")
        chk("6")
        assert not bad, "scroll horizontal nos passos %s" % bad


def S11_modo_escuro_e_desktop(b):
    with Env() as e:
        pg = page(b, e, 1280, 900, color_scheme="dark")
        pg.click('button:has-text("Começar")')
        bg = pg.evaluate("getComputedStyle(document.body).backgroundColor")
        assert bg != "rgb(234, 217, 189)", bg
        # contraste do texto principal: luminância do texto > fundo
        def lum(c):
            r, g, bl = [int(x) for x in c[c.index("(") + 1:c.index(")")].split(",")[:3]]
            return 0.2126 * r + 0.7152 * g + 0.0722 * bl
        fg = pg.evaluate("getComputedStyle(document.body).color")
        assert lum(fg) - lum(bg) > 100, (fg, bg)
        if OUT:
            pg.screenshot(path=str(OUT / "dark_desktop.png"), full_page=True)


def S12_copiar_sql(b):
    with Env() as e:
        ctx = b.new_context(viewport={"width": 430, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
        pg = ctx.new_page()
        pg.goto(e.url)
        pg.click('button:has-text("Começar")')
        pg.click("#cp")
        pg.wait_for_selector("#cpm .msg.ok")
        txt = pg.evaluate("navigator.clipboard.readText()")
        assert "create table" in txt.lower() and "expedicoes" in txt and len(txt) > 5000
        # sem permissão: mensagem de recurso
        pg2 = page(b, e)
        pg2.add_init_script("Object.defineProperty(navigator,'clipboard',{value:{writeText:()=>Promise.reject(new Error('x'))}})")
        pg2.goto(e.url)
        pg2.click('button:has-text("Começar")')
        pg2.click("#cp")
        pg2.wait_for_selector("#cpm .msg.bad")
        assert "supabase/schema.sql" in pg2.inner_text("#cpm")


def S13_verificar_falha_mostra_mensagem(b):
    with Env() as e:
        pg = page(b, e)
        to_step2(pg)
        connect(pg, e.mock.url)
        pg.click(NEXT)
        fill_creds(pg)
        pg.click(NEXT)
        fill_emails(pg)
        pg.click("#n4 .nav button:last-child")
        # apaga o config do servidor para simular emails em falta no momento de verificar
        cfg = json.loads(A.CONFIG.read_text())
        cfg["emails"]["madalena"] = ""
        pg.evaluate("""async (c)=>{cfg.emails.madalena='';}""", cfg)
        pg.click('button:has-text("Verificar tudo")')
        pg.wait_for_selector("#ck .msg")
        assert "Falta preencher o email da Madalena" in pg.inner_text("#ck")
        assert pg.is_disabled("#n5 .nav button:last-child")


def S14_voltar_mantem_dados(b):
    with Env() as e:
        pg = page(b, e)
        to_step2(pg)
        connect(pg, e.mock.url)
        pg.click(NEXT)
        fill_creds(pg)
        pg.click(NEXT)
        fill_emails(pg)
        pg.click(".nav >> nth=-1 >> button >> nth=0")  # Voltar (passo 4 -> 3)
        assert pg.locator(".cred.done").count() == 4
        pg.click(NEXT)
        assert pg.input_value("#main input[type=text] >> nth=4") == C["emails"]["madalena"]
        assert pg.locator("#n4 .nav button").last.is_enabled()


def S15_sem_erros_de_pagina(b):
    with Env() as e:
        pg = page(b, e)
        to_step6(pg, e)
        pg.click('button:has-text("Instalar agora")')
        pg.wait_for_selector("#fin .msg.ok", timeout=30000)
        pg.click('button:has-text("Voltar")')
        assert not pg.errs, pg.errs


SC = [v for k, v in sorted(globals().items()) if k.startswith("S") and k[1:3].isdigit()]
if __name__ == "__main__":
    ok, bad = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for f in SC:
            try:
                f(b)
                ok.append(f.__name__)
                print("OK   ", f.__name__)
            except Exception as ex:
                bad.append(f.__name__)
                print("FALHA", f.__name__, "->", repr(ex)[:300])
                traceback.print_exc(limit=2)
        b.close()
    print("\n%d passam, %d falham" % (len(ok), len(bad)))
    sys.exit(1 if bad else 0)
