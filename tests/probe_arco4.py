# -*- coding: utf-8 -*-
"""Probe 4: entmakex espera RADIANOS nos grupos de angulo (50/51)?"""
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

TMP = Path(r"C:\temp\mcp_cad_com")
DWG = TMP / "probe_arco5.dwg"
DXF = TMP / "probe_arco5.dxf"

ARCO = ('(list (cons 0 "ARC") (cons 100 "AcDbEntity") (cons 8 "0")'
        ' (cons 100 "AcDbCircle") (cons 10 (list 0.0 0.0 0.0)) (cons 40 1.0)'
        ' (cons 100 "AcDbArc") (cons 50 %s) (cons 51 %s))')

TEXTO = ('(list (cons 0 "TEXT") (cons 100 "AcDbEntity") (cons 8 "0")'
         ' (cons 100 "AcDbText") (cons 10 (list 0.0 0.0 0.0)) (cons 40 1.0)'
         ' (cons 1 "X") (cons 50 %s))')

CASOS = [
    ("arco 90 graus -> rad", ARCO % (repr(1.5707963267948966), repr(3.141592653589793))),
    ("arco 90 em graus      ", ARCO % (repr(90.0), repr(180.0))),
    ("arco 90 inteiro       ", ARCO % ("90", "180")),
    ("texto rot 90 graus    ", TEXTO % repr(90.0)),
    ("texto rot 90 rad      ", TEXTO % repr(1.5707963267948966)),
]


async def main():
    b = ComBackend()
    r = await b.initialize()
    if not r.ok:
        print("init falhou:", r.error)
        return 2

    marcados = []
    for i, (nome, corpo) in enumerate(CASOS):
        await b.execute_lisp('(setq __mcp_ini (entlast))')
        res = await b.entmakex(corpo)
        if not res.ok:
            print("%s -> ERRO %s" % (nome, res.error))
            continue
        h = res.payload
        h = h.get("resultado") if isinstance(h, dict) else h
        marcados.append((h, nome))

    for f in (DWG, DXF):
        if f.exists():
            f.unlink()
    await b.drawing_save(str(DWG))
    await b.drawing_save_as_dxf(str(DXF))
    print("salvo DWG + DXF\n")

    d = ezdxf.readfile(DXF)
    mapa = {e.dxf.handle: e for e in d.modelspace()}
    for h, nome in marcados:
        e = mapa.get(h)
        if e is None:
            print("  %s (handle %s) NAO ENCONTRADO" % (nome, h))
            continue
        if e.dxftype() == "ARC":
            print("  %s -> ARC  a1=%.4f a2=%.4f" % (nome, e.dxf.start_angle, e.dxf.end_angle))
        elif e.dxftype() == "TEXT":
            print("  %s -> TEXT rot=%.4f" % (nome, e.dxf.rotation))

    for h, _ in marcados:
        await b.execute_lisp('(progn (entdel (handent "%s")) (princ))' % h)
    print("\nlimpo.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
