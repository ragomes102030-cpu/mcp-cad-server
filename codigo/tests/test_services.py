# -*- coding: utf-8 -*-
"""Testes do modulo de servicos (sem AutoCAD): comprimento e catalogo."""
import sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
RAIZ = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(RAIZ / "src"))
from cad_mcp.services import SERVICOS, servico, comprimento  # noqa: E402
falhas = []
def chk(n, c, e=""):
    print("  %s  %s%s" % ("ok  " if c else "FALHA", n, (" -- " + str(e)) if (e and not c) else ""))
    if not c: falhas.append(n)
def perto(a, b): return abs(a - b) < 1e-9
chk("5 servicos", len(SERVICOS) == 5, len(SERVICOS))
chk("comprimento 3+4 = 7", perto(comprimento([[0,0],[3,0],[3,4]]), 7.0))
chk("comprimento aberto = 3", perto(comprimento([[0,0],[3,0]]), 3.0))
chk("comprimento fechado 3+4+5 = 12", perto(comprimento([[0,0],[3,0],[3,4]], closed=True), 12.0))
try:
    servico("inexistente"); chk("recusa servico invalido", False)
except ValueError as e:
    chk("recusa servico invalido (%s)" % str(e)[:30], True)
print()
if falhas: print("FALHOU:", falhas); raise SystemExit(1)
print("TUDO OK -- servicos: comprimento e catalogo conferidos.")
