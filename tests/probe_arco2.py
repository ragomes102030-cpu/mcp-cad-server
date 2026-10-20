# -*- coding: utf-8 -*-
"""Probe 2: entmakex -> DWG -> DXF. Onde os angulos do ARC se perdem?"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import ezdxf  # noqa: E402

from cad_mcp.com_backend import ComBackend  # noqa: E402

CORPO = ('(list (cons 0 "ARC") (cons 100 "AcDbEntity") (cons 8 "0")'
         ' (cons 100 "AcDbCircle") (cons 10 (list 0.0 0.0 0.0)) (cons 40 1.0)'
         ' (cons 100 "AcDbArc") (cons 50 %s) (cons 51 %s))')

DXF = Path(r"C:\temp\mcp_cad_com\probe_arco.dxf")


async def main():
    b = ComBackend()
    r = await b.initialize()
    if not r.ok:
        print("init falhou:", r.error)
        return 2

    pedidos = [(90.0, 180.0), (0.0, 90.0), (30.0, 120.0)]
    handles = []
    for a1, a2 in pedidos:
        res = await b.entmakex(CORPO % (repr(a1), repr(a2)))
        h = res.payload
        h = h.get("resultado") if isinstance(h, dict) else h
        handles.append((h, a1, a2))
        print("criado %s  pedido %s..%s" % (h, a1, a2))

    print("\nexportando DXF...")
    if DXF.exists():
        DXF.unlink()
    r = await b.drawing_save_as_dxf(str(DXF))
    print("  ok=%s" % r.ok)

    if DXF.exists():
        d = ezdxf.readfile(DXF)
        print("\n-- ARC no DXF exportado --")
        for e in d.modelspace():
            if e.dxftype() == "ARC" and abs(e.dxf.center.x) < 1e-9 and abs(e.dxf.center.y) < 1e-9:
                print("  c=(0,0) r=%.2f  a1=%r a2=%r  ext=%s"
                      % (e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle,
                         tuple(e.dxf.extrusion)))

    # tambem tenta ler via COM (get via VLISP angtos)
    for h, a1, a2 in handles:
        r = await b.execute_lisp(
            '(vl-princ-to-string (cdr (assoc 50 (entget (handent "%s")))))' % h)
        print("  leitura COM do %s: %s" % (h, json.dumps(r.payload, ensure_ascii=False)))

    for h, _, _ in handles:
        await b.execute_lisp('(progn (entdel (handent "%s")) (princ))' % h)
    print("\nlimpo.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
