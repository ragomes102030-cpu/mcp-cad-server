# -*- coding: utf-8 -*-
"""Conferencia quantitativa de um DXF gerado pelo mcp-cad-server."""
import collections
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import ezdxf
from ezdxf import bbox

arq = Path(sys.argv[1] if len(sys.argv) > 1 else r"saida\planta_3q.dxf")
d = ezdxf.readfile(arq)
print("arquivo : %s (%.1f KB)" % (arq, arq.stat().st_size / 1024.0))
print("versao  : %s" % d.dxfversion)
print("INSUNITS: %s (6 = metros)   MEASUREMENT: %s"
      % (d.header.get("$INSUNITS"), d.header.get("$MEASUREMENT")))

msp = d.modelspace()
print("entidades: %d" % len(msp))
print("tipos    : %s" % dict(collections.Counter(e.dxftype() for e in msp)))
print("camadas  : %s" % dict(collections.Counter(e.dxf.layer for e in msp)))

ext = bbox.extents(msp)
print("extensao : x %.2f..%.2f (%.2f m) | y %.2f..%.2f (%.2f m)"
      % (ext.extmin.x, ext.extmax.x, ext.size.x,
         ext.extmin.y, ext.extmax.y, ext.size.y))

textos = [e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text
          for e in msp if e.dxftype() in ("TEXT", "MTEXT")]
print("textos (%d):" % len(textos))
for t in textos:
    print("    %s" % t)

# soma dos comprimentos por camada
comp = collections.defaultdict(float)
for e in msp:
    t = e.dxftype()
    if t == "LINE":
        comp[e.dxf.layer] += e.dxf.start.distance(e.dxf.end)
    elif t == "CIRCLE":
        comp[e.dxf.layer] += 2 * 3.14159265358979 * e.dxf.radius
print("comprimentos (m): %s" % {k: round(v, 2) for k, v in sorted(comp.items())})

# areas dos poligonos fechados
def area_poly(e):
    pts = [(p[0], p[1]) for p in e.get_points("xy")]
    if len(pts) < 3:
        return 0.0
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0

areas = collections.defaultdict(float)
for e in msp:
    if e.dxftype() == "LWPOLYLINE" and e.closed:
        areas[e.dxf.layer] += area_poly(e)
print("areas de polil. fechadas (m2): %s"
      % {k: round(v, 2) for k, v in sorted(areas.items())})
