# -*- coding: utf-8 -*-
"""Testa se texto ACENTUADO sobrevive ao SendCommand (COM -> AutoCAD)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, r"C:\Users\Correta Engenharia\mcp-cad-server\src")

from cad_mcp.com_backend import ComBackend  # noqa: E402

ALVO = "ÁREA DE SERVIÇO - 10,46 m² - CIRCULAÇÃO - SUÍTE"


async def main():
    b = ComBackend()
    r = await b.initialize()
    print("init:", r.ok, r.error)
    if not r.ok:
        return 1
    # texto centrado no meio do desenho atual
    r = await b.create_text(6.0, 5.0, ALVO, 0.4, 0.0, "TEXTOS")
    print("create_text ok=%s erro=%s handle=%s" % (r.ok, r.error, r.payload))
    if not r.ok or not r.payload:
        return 1
    h = r.payload
    r2 = await b.entity_get(h)
    print("entity_get ok=%s erro=%s" % (r2.ok, r2.error))
    dxf = (r2.payload or {}).get("dxf") if isinstance(r2.payload, dict) else None
    achou = None
    if isinstance(r2.payload, list):  # alist -> lista de pares
        for par in r2.payload:
            if isinstance(par, list) and len(par) == 2 and str(par[0]).lower() == "dxf":
                dxf = par[1]
    if dxf:
        import re

        m = re.findall(r'\(1 \. "([^"]*)"\)', str(dxf))
        achou = m[0] if m else None
    print("esperado : %r" % ALVO)
    print("lido     : %r" % achou)
    print("IGUAL    : %s" % (achou == ALVO))
    # limpa
    await b.entity_erase(h)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
