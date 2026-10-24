# -*- coding: utf-8 -*-
"""Teste offline do symbol_counts (registro de simbolos colocados)."""
import sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
RAIZ = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(RAIZ / "src"))
import cad_mcp.tools as t  # noqa: E402
falhas = []
def chk(n, c, e=""):
    print("  %s  %s%s" % ("ok  " if c else "FALHA", n, (" -- " + str(e)) if (e and not c) else ""))
    if not c: falhas.append(n)
t._PLACED.clear()
t._PLACED["tomada_baixa"] = 4
t._PLACED["luminaria_teto"] = 2
t._PLACED["simbolo_inexistente"] = 99   # deve ser ignorado
r = t.symbol_counts()
chk("ok", r.get("ok"))
chk("total 6 (ignora desconhecido)", r["payload"]["total"] == 6, r["payload"]["total"])
d = {i["simbolo"]: i["qtd"] for i in r["payload"]["itens"]}
chk("itens corretos", d == {"tomada_baixa": 4, "luminaria_teto": 2}, d)
t._PLACED.clear()
r2 = t.symbol_counts()
chk("vazio -> total 0", r2["payload"]["total"] == 0, r2["payload"]["total"])
print()
if falhas: print("FALHOU:", falhas); raise SystemExit(1)
print("TUDO OK -- symbol_counts: contagem e filtro conferidos.")
