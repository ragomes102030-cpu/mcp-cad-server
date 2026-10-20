# -*- coding: utf-8 -*-
"""Testa o ComBackend passo a passo num AutoCAD ja aberto."""
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

from cad_mcp.com_backend import ComBackend  # noqa: E402


def p(t):
    print("\n### " + t)


async def main():
    b = ComBackend()
    p("initialize")
    r = await b.initialize()
    print("  ok=%s erro=%s payload=%s" % (r.ok, r.error, json.dumps(r.payload, ensure_ascii=False)))
    if not r.ok:
        return 1

    p("drawing_info")
    r = await b.drawing_info()
    print("  ok=%s erro=%s" % (r.ok, r.error))
    print("  %s" % json.dumps(r.payload, ensure_ascii=False))

    p("entity_count")
    r = await b.entity_count()
    print("  ok=%s erro=%s -> %s" % (r.ok, r.error, r.payload))

    p("layer_create + layer_list")
    r = await b.layer_create("MCP_TESTE", 3)
    print("  criar camada: ok=%s erro=%s -> %s" % (r.ok, r.error, r.payload))
    r = await b.layer_list()
    print("  ok=%s erro=%s n=%s" % (r.ok, r.error, len(r.payload or [])))
    for c in (r.payload or [])[:6]:
        print("    %s" % c)

    p("create_line + handle")
    r = await b.create_line(0, 0, 100, 0, "MCP_TESTE")
    print("  ok=%s erro=%s -> handle=%s" % (r.ok, r.error, r.payload))

    p("create_rectangle")
    r = await b.create_rectangle(0, 0, 40, 30, "MCP_TESTE")
    print("  ok=%s erro=%s -> handle=%s" % (r.ok, r.error, r.payload))
    rect = r.payload

    p("create_dimension_linear (H e V)")
    print("  H:", (await b.create_dimension_linear(0, 0, 40, 0, 20, -5)).payload)
    print("  V:", (await b.create_dimension_linear(0, 0, 0, 30, -5, 15)).payload)

    p("create_text")
    print("   ", (await b.create_text(5, 32, "SALA 12.00 m2", 2.5, 0, "MCP_TESTE")).payload)

    p("entity_list (camada MCP_TESTE)")
    r = await b.entity_list("MCP_TESTE")
    print("  ok=%s erro=%s n=%s" % (r.ok, r.error, len(r.payload or [])))
    for e in (r.payload or []):
        print("    %s" % e)

    p("execute_lisp")
    r = await b.execute_lisp('(setq x 21)')
    print("  ok=%s erro=%s -> %s" % (r.ok, r.error, r.payload))

    p("zoom_extents")
    r = await b.zoom_extents()
    print("  ok=%s erro=%s -> %s" % (r.ok, r.error, r.payload))

    p("drawing_save_as_dxf")
    dxf = Path(r"C:/temp/mcp_cad_com/teste_com.dxf")
    r = await b.drawing_save_as_dxf(str(dxf))
    print("  ok=%s erro=%s -> %s" % (r.ok, r.error, json.dumps(r.payload, ensure_ascii=False)))
    if dxf.exists():
        cabeca = dxf.read_bytes()[:40]
        print("  bytes=%s cabeca=%r" % (dxf.stat().st_size, cabeca[:30]))

    p("drawing_plot_pdf")
    pdf = Path(r"C:/temp/mcp_cad_com/teste_com.pdf")
    r = await b.drawing_plot_pdf(str(pdf))
    print("  ok=%s erro=%s -> %s" % (r.ok, r.error, json.dumps(r.payload, ensure_ascii=False)))
    if pdf.exists():
        print("  assinatura=%r" % pdf.read_bytes()[:8])

    p("get_screenshot")
    r = await b.get_screenshot()
    print("  ok=%s erro=%s -> %s" % (r.ok, r.error, r.payload))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
