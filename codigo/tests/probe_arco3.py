# -*- coding: utf-8 -*-
"""Probe 3: entmakex -> SALVA DWG -> DXF. Reproduz o erro dos angulos?"""
from __future__ import annotations

import asyncio
import json
import shutil
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

TMP = Path(r"C:\temp\mcp_cad_com")
DWG = TMP / "probe_arco.dwg"
DXF = TMP / "probe_arco.dxf"


async def main():
    b = ComBackend()
    r = await b.initialize()
    if not r.ok:
        print("init falhou:", r.error)
        return 2

    # como esta a base
    r = await b.drawing_get_variables(["ANGDIR", "ANGBASE", "AUNITS", "AUPREC",
                                       "INSUNITS", "MEASUREMENT", "UCSXDIR"])
    print("variaveis:", json.dumps(r.payload if r.ok else r.error, ensure_ascii=False))

    pedidos = [(90.0, 180.0), (0.0, 90.0), (30.0, 120.0)]
    criados = []
    for a1, a2 in pedidos:
        res = await b.entmakex(CORPO % (repr(a1), repr(a2)))
        h = res.payload
        h = h.get("resultado") if isinstance(h, dict) else h
        criados.append(h)
        print("criado %s  pedido %.1f..%.1f" % (h, a1, a2))

    for f in (DWG, DXF):
        if f.exists():
            f.unlink()
    r = await b.drawing_save(str(DWG))
    print("save:", r.ok, r.payload if r.ok else r.error)
    r = await b.drawing_save_as_dxf(str(DXF))
    print("dxf :", r.ok)

    if DXF.exists():
        d = ezdxf.readfile(DXF)
        print("-- ARC em (0,0) no DXF exportado --")
        for e in d.modelspace():
            if e.dxftype() == "ARC" and abs(e.dxf.center.x) < 1e-9 and abs(e.dxf.center.y) < 1e-9:
                print("   r=%.2f a1=%r a2=%r ext=%s"
                      % (e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle,
                         tuple(e.dxf.extrusion)))
        print("-- todas as ARCs --")
        for e in d.modelspace():
            if e.dxftype() == "ARC":
                print("   c=(%.2f,%.2f) r=%.2f a1=%.3f a2=%.3f camada=%s"
                      % (e.dxf.center.x, e.dxf.center.y, e.dxf.radius,
                         e.dxf.start_angle, e.dxf.end_angle, e.dxf.layer))

    for h in criados:
        await b.execute_lisp('(progn (entdel (handent "%s")) (princ))' % h)
    print("limpo.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
