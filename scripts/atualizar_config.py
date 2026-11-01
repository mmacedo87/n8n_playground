#!/usr/bin/env python3
"""Atualizador de definições (tabela `configuracao` no Supabase).

Muda definições do sistema SEM tocar nos workflows do n8n (não é preciso editar nem publicar nada).
A primeira definição é `modo_envio` (WF3: enviar já ou criar rascunho para revisão).

Uso na linha de comandos (a chave service_role nunca é guardada nem mostrada):
  SUPABASE_SERVICE_KEY=... python3 scripts/atualizar_config.py --url https://xxxx.supabase.co ver
  SUPABASE_SERVICE_KEY=... python3 scripts/atualizar_config.py --url https://xxxx.supabase.co definir modo_envio revisao
  (acrescentar --simular para só mostrar o que mudaria)

O assistente (app/deploy_app.py) usa as mesmas funções. Só usa a biblioteca padrão do Python.
"""
import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# Lista fechada das definições que este atualizador pode mudar. Para acrescentar uma, basta uma entrada aqui
# (e a linha correspondente na tabela `configuracao`, com a restrição de valores na base de dados).
DEFINICOES = {
    "modo_envio": {
        "titulo": "Pedidos de cotação às transportadoras (WF3)",
        "descricao": "Decide o que o sistema faz com o email do pedido de cotação de frete.",
        "por_omissao": "automatico",
        "opcoes": [
            {"valor": "automatico", "titulo": "Enviar automaticamente",
             "detalhe": "O sistema envia o pedido às transportadoras (em cópia oculta), sem ninguém rever."},
            {"valor": "revisao", "titulo": "Preparar para revisão humana",
             "detalhe": "O sistema cria um rascunho na pasta «To Check» do Outlook e avisa no Slack. Uma pessoa revê e envia."},
        ],
    },
}


class AtualizadorError(Exception):
    def __init__(self, msg, falta_migracao=False):
        super().__init__(msg)
        self.falta_migracao = falta_migracao


def normalizar_url(url):
    url = (url or "").strip().rstrip("/")
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("https", "http") or not p.netloc or p.path not in ("", "/") or p.query or p.fragment:
        raise AtualizadorError("O endereço do Supabase não é válido. Use o «Project URL», por exemplo https://xxxx.supabase.co")
    return "%s://%s" % (p.scheme, p.netloc)


def validar(chave, valor):
    d = DEFINICOES.get(chave)
    if not d:
        raise AtualizadorError("Definição desconhecida: %s. Disponíveis: %s." % (chave, ", ".join(DEFINICOES)))
    if valor not in [o["valor"] for o in d["opcoes"]]:
        raise AtualizadorError("Valor inválido para %s: %r. Valores aceites: %s." % (chave, valor, ", ".join(o["valor"] for o in d["opcoes"])))


class Cliente:
    """Cliente mínimo da API REST (PostgREST) do Supabase, com a chave service_role."""

    def __init__(self, url, chave_api, timeout=20):
        self.url = normalizar_url(url)
        self._key = (chave_api or "").strip()
        self.timeout = timeout
        if not self._key:
            raise AtualizadorError("Falta a chave service_role do Supabase.")

    def _pedido(self, metodo, caminho, corpo=None):
        dados = json.dumps(corpo).encode() if corpo is not None else None
        r = urllib.request.Request(self.url + "/rest/v1/" + caminho, data=dados, method=metodo, headers={
            "apikey": self._key, "Authorization": "Bearer " + self._key,
            "Content-Type": "application/json", "Prefer": "return=representation"})
        try:
            with urllib.request.urlopen(r, timeout=self.timeout) as x:
                raw = x.read()
                return json.loads(raw) if raw else []
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            if e.code in (401, 403):
                raise AtualizadorError("O Supabase não aceitou a chave. Confirme que copiou a chave «service_role» (e não a «anon») do projeto certo.")
            if e.code == 404 and ("PGRST205" in raw or "PGRST202" in raw or "configuracao" in raw):
                raise AtualizadorError("A base de dados ainda não tem a atualização das definições (migração 0009). Aplique-a primeiro no SQL Editor do Supabase.", falta_migracao=True)
            raise AtualizadorError("O Supabase respondeu com um erro (HTTP %s)." % e.code)
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise AtualizadorError("Não consegui chegar ao Supabase. Confirme o endereço e a internet. (%s)" % type(e).__name__)

    def ler(self):
        """{chave: {valor, atualizado_em, atualizado_por}} só das definições conhecidas."""
        linhas = self._pedido("GET", "configuracao?select=chave,valor,atualizado_em,atualizado_por")
        return {l["chave"]: {k: l.get(k) for k in ("valor", "atualizado_em", "atualizado_por")} for l in linhas if l.get("chave") in DEFINICOES}

    def definir(self, chave, valor, quem="atualizador"):
        validar(chave, valor)
        r = self._pedido("PATCH", "configuracao?chave=eq.%s" % urllib.parse.quote(chave, safe=""), {"valor": valor, "atualizado_por": quem})
        if not r:
            raise AtualizadorError("A definição «%s» não existe na base de dados. Aplique a migração 0009." % chave, falta_migracao=True)
        return r[0]["valor"]


def _args():
    ap = argparse.ArgumentParser(description="Atualiza definições do sistema (tabela configuracao do Supabase).")
    ap.add_argument("--url", required=True, help="Project URL do Supabase")
    ap.add_argument("--simular", action="store_true", help="só mostra o que mudaria")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ver")
    d = sub.add_parser("definir")
    d.add_argument("chave", choices=sorted(DEFINICOES))
    d.add_argument("valor")
    return ap.parse_args()


def main():
    a = _args()
    chave_api = os.environ.get("SUPABASE_SERVICE_KEY") or getpass.getpass("Chave service_role do Supabase (não aparece enquanto escreve): ")
    try:
        c = Cliente(a.url, chave_api)
        atual = c.ler()
        if a.cmd == "ver":
            for k, d in DEFINICOES.items():
                print("%s = %s" % (k, atual.get(k, {}).get("valor", "(sem valor)")))
            return 0
        validar(a.chave, a.valor)
        antes = atual.get(a.chave, {}).get("valor")
        if a.simular:
            print("[simulação] %s: %s -> %s (nada foi alterado)" % (a.chave, antes, a.valor))
            return 0
        depois = c.definir(a.chave, a.valor, "atualizador (linha de comandos)")
        print("%s: %s -> %s" % (a.chave, antes, depois))
        return 0
    except AtualizadorError as e:
        print("Erro: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
