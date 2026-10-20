# -*- coding: utf-8 -*-
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import ezdxf

d = ezdxf.readfile(sys.argv[1] if len(sys.argv) > 1 else r"saida\planta_3q.dxf")
h = d.header
for v in ("$AUNITS", "$ANGBASE", "$ANGDIR", "$LUPREC", "$AUPREC", "$INSUNITS",
          "$MEASUREMENT", "$DIMSCALE", "$DIMTXT", "$DIMASZ", "$ATTDIA", "$FILEDIA"):
    try:
        print("%-12s %s" % (v, h.get(v)))
    except Exception as e:
        print("%-12s <erro %s>" % (v, e))

print()
for e in d.modelspace():
    if e.dxftype() == "ARC":
        print("ARC  c=(%9.4f,%9.4f) r=%.4f  a1=%r a2=%r"
              % (e.dxf.center.x, e.dxf.center.y, e.dxf.radius,
                 e.dxf.start_angle, e.dxf.end_angle))
