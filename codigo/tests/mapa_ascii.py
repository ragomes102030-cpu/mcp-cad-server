# -*- coding: utf-8 -*-
"""Rasteriza as PAREDES do DXF em ASCII para conferir a planta 'a olho'."""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import ezdxf

arq = Path(sys.argv[1] if len(sys.argv) > 1 else r"saida\planta_3q.dxf")
d = ezdxf.readfile(arq)
msp = d.modelspace()

paredes = []
for e in msp:
    if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "PAREDES":
        pts = [(p[0], p[1]) for p in e.get_points("xy")]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        paredes.append((min(xs), min(ys), max(xs), max(ys)))

portas = [(e.dxf.center.x, e.dxf.center.y) for e in msp if e.dxftype() == "ARC"]
textos = [(e.dxf.insert.x, e.dxf.insert.y, e.dxf.text) for e in msp
          if e.dxftype() == "TEXT" and e.dxf.layer == "TEXTOS"]

x0, x1, y0, y1 = -0.3, 13.3, -0.3, 10.3
passo = 0.2
sub = 5          # 5x5 sub-amostras por celula (evita aliasing das paredes de 0,15 m)


def dentro(px, py, r):
    return r[0] <= px <= r[2] and r[1] <= py <= r[3]


def parede(px, py):
    for r in paredes:
        for a in range(sub):
            for b in range(sub):
                qx = px + (a + 0.5) / sub * passo - passo / 2.0
                qy = py + (b + 0.5) / sub * passo - passo / 2.0
                if dentro(qx, qy, r):
                    return True
    return False


ny = int((y1 - y0) / passo)
nx = int((x1 - x0) / passo)

print("Planta %s  (0,2 m por caracter)  # = parede  o = porta  * = texto" % arq.name)
print("    " + "".join(str(int((x0 + i * passo) // 10) % 10) if i % 5 == 0 else " "
                      for i in range(nx)))
for j in range(ny, -1, -1):
    py = y0 + j * passo
    linha = []
    for i in range(nx):
        px = x0 + i * passo
        ch = "."
        if parede(px, py):
            ch = "#"
        if any(abs(px - p[0]) <= passo and abs(py - p[1]) <= passo for p in portas):
            ch = "o"
        if any(abs(px - t[0]) <= passo and abs(py - t[1]) <= 0.3 for t in textos):
            ch = "*"
        linha.append(ch)
    print("%5.1f %s" % (py, "".join(linha)))
