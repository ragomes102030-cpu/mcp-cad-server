# -*- coding: utf-8 -*-
"""Testes do catalogo de simbolos (sem AutoCAD). Prova transformacao e integridade."""
from __future__ import annotations
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cad_mcp.catalogue import SIMBOLOS, simbolo, transformar  # noqa: E402

falhas = []
def checar(nome, cond, extra=""):
    print("  %s  %s%s" % ("ok  " if cond else "FALHA", nome,
                          (" -- " + str(extra)) if (extra and not cond) else ""))
    if not cond:
        falhas.append(nome)

def perto(a, b, tol=1e-9):
    return abs(a - b) <= tol

def prim(g, kind):
    return [p for p in g["primitivas"] if p[0] == kind][0]

print("1) catalogo bem formado")
checar("11 simbolos", len(SIMBOLOS) == 11, len(SIMBOLOS))
for k, s in SIMBOLOS.items():
    checar("simbolo %r integro" % k,
           s["id"] == k and bool(s["camada"]) and bool(s["primitivas"]), s)

print("\n2) translacao pura (rot 0, escala 1)")
g = transformar("tomada_baixa", 5.0, 3.0)
ln = prim(g, "line")
checar("line 4,9->5,1 em y=3", perto(ln[1], 4.9) and perto(ln[2], 3.0)
       and perto(ln[3], 5.1) and perto(ln[4], 3.0), ln)

print("\n3) rotacao 90 (line horizontal vira vertical)")
g90 = transformar("tomada_baixa", 0.0, 0.0, rotation=90)
ln90 = prim(g90, "line")
checar("line (0,-0,1)->(0,0,1)", perto(ln90[1], 0.0) and perto(ln90[2], -0.1)
       and perto(ln90[3], 0.0) and perto(ln90[4], 0.1), ln90)

print("\n4) escala 2 dobra coordenadas")
g2 = transformar("tomada_baixa", 0.0, 0.0, scale=2)
ln2 = prim(g2, "line")
checar("line -0,2 -> 0,2", perto(ln2[1], -0.2) and perto(ln2[3], 0.2), ln2)

print("\n5) arco: raio escala e angulos rotacionam")
g3 = transformar("tomada_baixa", 0.0, 0.0, rotation=90, scale=2)
arc = prim(g3, "arc")
checar("raio 0,20", perto(arc[3], 0.2), arc)
checar("angulos 90..270", perto(arc[4], 90.0) and perto(arc[5], 270.0), arc)

print("\n6) polyline fechada preservada")
gq = transformar("quadro", 0.0, 0.0)
poly = prim(gq, "poly")
checar("quadro poly closed", poly[2] is True and len(poly[1]) == 4, poly)

print("\n7) simbolo desconhecido recusado")
try:
    simbolo("inexistente")
    checar("recusa simbolo invalido", False)
except ValueError as e:
    checar("recusa simbolo invalido (%s)" % str(e)[:40], True)

print("\n8) escala invalida recusada")
try:
    transformar("tomada_baixa", 0, 0, scale=0)
    checar("recusa scale<=0", False)
except ValueError:
    checar("recusa scale<=0", True)

print()
if falhas:
    print("FALHOU: %d caso(s): %s" % (len(falhas), ", ".join(falhas)))
    raise SystemExit(1)
print("TUDO OK -- catalogo de simbolos: transformacao e integridade conferidas.")
