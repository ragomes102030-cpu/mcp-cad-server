# -*- coding: utf-8 -*-
"""Descobre a rota DXF que funciona no AutoCAD 2025 (WBLOCK / DXFOUT / SaveAs)."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cad_mcp.com_backend import ComBackend  # noqa: E402

TMP = Path(r"C:/temp/mcp_cad_com")
TMP.mkdir(parents=True, exist_ok=True)


def valida(p: Path) -> str:
    if not p.exists():
        return "nao existe"
    b = p.read_bytes()[:64]
    tam = p.stat().st_size
    if b.startswith(b"AutoCAD Binary DXF"):
        return "DXF binario OK (%d B)" % tam
    if b.startswith(b"  0\r\nSECTION") or b.startswith(b"0\nSECTION") or b.lstrip().startswith(b"0"):
        return "DXF texto OK (%d B) %r" % (tam, b[:20])
    if b.startswith(b"AC10"):
        return "DWG (%d B)" % tam
    return "formato ? (%d B) %r" % (tam, b[:24])


async def main():
    b = ComBackend()
    r = await b.initialize()
    print("init:", r.ok, r.error)
    doc = b._d()
    print("documento:", doc.Name)
    try:
        b._chamar(doc.SetVariable, "FILEDIA", 0)
        b._chamar(doc.SetVariable, "CMDDIA", 0)
    except Exception:
        pass

    # --- rota 1: WBLOCK (nao altera o documento atual)
    alvo = TMP / "rota_wblock.dxf"
    if alvo.exists():
        alvo.unlink()
    print("\n[1] WBLOCK ->", alvo)
    b._send('_.WBLOCK "%s" * ' % str(alvo).replace("\\", "/"))
    t0 = time.time()
    while time.time() - t0 < 25:
        if alvo.exists() and alvo.stat().st_size > 200:
            break
        time.sleep(0.2)
    print("    %.1fs ->" % (time.time() - t0), valida(alvo))

    # --- rota 2: DXFOUT
    alvo2 = TMP / "rota_dxfout.dxf"
    if alvo2.exists():
        alvo2.unlink()
    print("\n[2] DXFOUT ->", alvo2)
    b._send('_.DXFOUT "%s" V 2018 16 ' % str(alvo2).replace("\\", "/"))
    t0 = time.time()
    while time.time() - t0 < 25:
        if alvo2.exists() and alvo2.stat().st_size > 200:
            break
        time.sleep(0.2)
    print("    %.1fs ->" % (time.time() - t0), valida(alvo2))

    # --- rota 3: SaveAs com cada codigo de tipo
    print("\n[3] SaveAs com codigos de tipo")
    for tipo in (65, 61, 37, 33, 29, 25, 21, 17, 13, 1):
        alvo3 = TMP / ("rota_saveas_%s.dxf" % tipo)
        if alvo3.exists():
            alvo3.unlink()
        try:
            b._chamar(doc.SaveAs, str(alvo3).replace("\\", "/"), tipo)
            time.sleep(0.25)
            print("    tipo %-3s -> %s" % (tipo, valida(alvo3)))
            if "OK" in valida(alvo3):
                break
        except Exception as e:
            print("    tipo %-3s -> erro %s" % (tipo, str(e)[:70]))

    # volta o documento a nao ter caminho "sujo": salva de novo em DWG
    try:
        b._chamar(doc.SaveAs, str(TMP / "planta_mcp.dwg").replace("\\", "/"))
        print("\ndocumento resalvo como DWG")
    except Exception as e:
        print("\nnao consegui resalvar DWG: %s" % str(e)[:80])
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
