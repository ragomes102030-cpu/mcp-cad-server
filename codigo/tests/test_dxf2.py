# -*- coding: utf-8 -*-
"""Testa rota DXF sem dialogo: -WBLOCK e accoreconsole headless."""
from __future__ import annotations

import asyncio
import subprocess
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
ACCORE = r"C:\Program Files\Autodesk\AutoCAD 2025\accoreconsole.exe"


def valida(p: Path) -> str:
    if not p.exists():
        return "NAO EXISTE"
    b = p.read_bytes()[:64]
    tam = p.stat().st_size
    if b.startswith(b"AutoCAD Binary DXF"):
        return "DXF binario OK (%d B)" % tam
    if b.lstrip()[:1] == b"0":
        return "DXF texto OK (%d B)" % tam
    if b.startswith(b"AC10"):
        return "DWG (%d B)" % tam
    return "formato ? (%d B) %r" % (tam, b[:24])


async def wblock():
    b = ComBackend()
    r = await b.initialize()
    print("  init:", r.ok, r.error)
    doc = b._d()
    try:
        b._chamar(doc.SetVariable, "FILEDIA", 0)
        b._chamar(doc.SetVariable, "CMDDIA", 0)
        b._chamar(doc.SetVariable, "EXPERT", 5)
    except Exception:
        pass
    alvo = TMP / "w.dxf"
    if alvo.exists():
        alvo.unlink()
    b._send('_.-WBLOCK "%s" * ' % str(alvo).replace("\\", "/"))
    t0 = time.time()
    while time.time() - t0 < 30:
        if alvo.exists() and alvo.stat().st_size > 200:
            break
        time.sleep(0.2)
    return alvo, time.time() - t0


async def main():
    print("[A] -WBLOCK")
    alvo, dt = await wblock()
    print("    %.1fs -> %s" % (dt, valida(alvo)))
    if "NAO EXISTE" in valida(alvo):
        print("    (procurando dialogo pendente...)")
        return 1

    print("\n[B] accoreconsole headless (DWG -> DXF)")
    origem = Path(r"C:/temp/mcp_cad_com/planta_mcp.dwg")
    destino = Path(r"C:/temp/mcp_cad_com/ac.dxf")
    if destino.exists():
        destino.unlink()
    scr = TMP / "conv.scr"
    scr.write_text(
        "FILEDIA\n0\nCMDDIA\n0\nDXFOUT\n%s\n2018\n16\n" % str(destino).replace("\\", "/"),
        encoding="ascii",
    )
    if not origem.exists():
        print("    origem ausente:", origem)
        return 1
    t0 = time.time()
    p = subprocess.run(
        [ACCORE, "/i", str(origem), "/s", str(scr), "/l", "pt-BR"],
        capture_output=True, text=True, timeout=180,
    )
    print("    exit=%s em %.1fs" % (p.returncode, time.time() - t0))
    if p.stdout:
        print("    stdout:", p.stdout[-700:].replace("\n", " | "))
    if p.stderr:
        print("    stderr:", p.stderr[-400:].replace("\n", " | "))
    print("    ->", valida(destino))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
