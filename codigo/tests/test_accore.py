# -*- coding: utf-8 -*-
"""Testa SOMENTE a rota accoreconsole headless (DWG -> DXF)."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TMP = Path(r"C:/temp/mcp_cad_com")
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


def main():
    origem = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:/temp/mcp_cad_com/planta_mcp.dwg")
    destino = TMP / "ac.dxf"
    if destino.exists():
        destino.unlink()
    scr = TMP / "conv.scr"
    dp = str(destino).replace("\\", "/")
    scr.write_text(
        "FILEDIA\n0\nCMDDIA\n0\n"
        "_.DXFOUT\n%s\n_V\n2018\n16\n" % dp,
        encoding="ascii",
    )
    print("origem :", origem, "existe:", origem.exists())
    print("script :", repr(scr.read_text(encoding="ascii")))
    t0 = time.time()
    try:
        p = subprocess.run([ACCORE, "/i", str(origem), "/s", str(scr)],
                           capture_output=True, text=True, timeout=240)
        print("exit=%s em %.1fs" % (p.returncode, time.time() - t0))
        print("stdout:", (p.stdout or "")[-1500:])
        print("stderr:", (p.stderr or "")[-600:])
    except subprocess.TimeoutExpired as e:
        print("TIMEOUT em %.1fs" % (time.time() - t0))
        print("stdout parcial:", (e.stdout or b"")[-800:])
    print("->", valida(destino))
    return 0


if __name__ == "__main__":
    sys.exit(main())
