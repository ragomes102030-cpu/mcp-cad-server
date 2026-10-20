# -*- coding: utf-8 -*-
"""Acha o que esta fora da area esperada do desenho (inclui cotas renderizadas)."""
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
msp = d.modelspace()

linhas = []
for e in msp:
    try:
        if e.dxftype() == "DIMENSION":
            ex = bbox.extents(e.virtual_entities(), fast=True)
        else:
            ex = bbox.extents([e], fast=True)
    except Exception as erro:
        linhas.append((999.0, "%s [%s] <sem extents: %s>" % (e.dxftype(), e.dxf.layer, erro)))
        continue
    linhas.append((ex.extmax.x,
                   "%-11s [%-16s] x %8.3f .. %8.3f | y %8.3f .. %8.3f"
                   % (e.dxftype(), e.dxf.layer, ex.extmin.x, ex.extmax.x,
                      ex.extmin.y, ex.extmax.y)))

linhas.sort(key=lambda t: -t[0])
print("== 8 maiores X ==")
for _, s in linhas[:8]:
    print("  ", s)
linhas.sort(key=lambda t: t[0])
print("== 5 menores X ==")
for _, s in linhas[:5]:
    print("  ", s)

print("\n== detalhe das DIMENSION ==")
for e in msp:
    if e.dxftype() == "DIMENSION":
        ex = bbox.extents(e.virtual_entities(), fast=True)
        print("   [%s] defpoint=(%.2f,%.2f)  render x %.3f..%.3f  y %.3f..%.3f"
              % (e.dxf.layer, e.dxf.defpoint.x, e.dxf.defpoint.y,
                 ex.extmin.x, ex.extmax.x, ex.extmin.y, ex.extmax.y))
