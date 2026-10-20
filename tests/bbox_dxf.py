# -*- coding: utf-8 -*-
"""Onde esta a extensao maxima de um DXF (diagnostico de bbox)."""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import ezdxf

d = ezdxf.readfile(sys.argv[1] if len(sys.argv) > 1 else r"saida\planta_3q.dxf")
msp = d.modelspace()

piores = []
for e in msp:
    try:
        if e.dxftype() == "LWPOLYLINE":
            xs = [p[0] for p in e.get_points("xy")]
            ys = [p[1] for p in e.get_points("xy")]
        elif e.dxftype() == "LINE":
            xs = [e.dxf.start.x, e.dxf.end.x]
            ys = [e.dxf.start.y, e.dxf.end.y]
        elif e.dxftype() == "ARC":
            xs = [e.dxf.center.x - e.dxf.radius, e.dxf.center.x + e.dxf.radius]
            ys = [e.dxf.center.y - e.dxf.radius, e.dxf.center.y + e.dxf.radius]
        elif e.dxftype() in ("TEXT", "MTEXT"):
            xs = [e.dxf.insert.x]
            ys = [e.dxf.insert.y]
        elif e.dxftype() == "DIMENSION":
            xs = [e.dxf.defpoint.x, e.dxf.defpoint2.x, e.dxf.defpoint3.x]
            ys = [e.dxf.defpoint.y, e.dxf.defpoint2.y, e.dxf.defpoint3.y]
        else:
            continue
    except Exception as ex:
        piores.append((999, "erro %s: %s" % (e.dxftype(), ex)))
        continue
    piores.append((max(xs), "%s [%s] x %.3f..%.3f  y %.3f..%.3f"
                   % (e.dxftype(), e.dxf.layer, min(xs), max(xs), min(ys), max(ys))))

piores.sort(key=lambda t: -t[0])
print("== maiores X ==")
for _, s in piores[:8]:
    print("  ", s)

p = sorted(piores, key=lambda t: t[0])
print("== menores X ==")
for _, s in p[:4]:
    print("  ", s)

print("== DIMENSION detalhado ==")
for e in msp:
    if e.dxftype() == "DIMENSION":
        print("   %s defpoint=(%.2f,%.2f) dp2=(%.2f,%.2f) dp3=(%.2f,%.2f) text=%r"
              % (e.dxf.layer, e.dxf.defpoint.x, e.dxf.defpoint.y,
                 e.dxf.defpoint2.x, e.dxf.defpoint2.y,
                 e.dxf.defpoint3.x, e.dxf.defpoint3.y,
                 e.dxf.get("text", "")))
