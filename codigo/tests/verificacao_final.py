# -*- coding: utf-8 -*-
"""Verificacao final e entrega: quantitativo do DXF + validacao e copia dos artefatos."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(r"C:\Users\Correta Engenharia\mcp-cad-server")
sys.path.insert(0, str(RAIZ / "src"))

from cad_mcp.quantitativo import analisar  # noqa: E402

SAIDA = RAIZ / "saida"
DXF = SAIDA / "planta_mcp.dxf"
PDF = SAIDA / "planta_mcp.pdf"
DWG = SAIDA / "planta_mcp.dwg"

DESTINOS = [
    Path(r"C:\Users\Correta Engenharia\AppData\Roaming\Arquimedes\arquimedes\conversations\users\system_default_user\2026\10\16\aionrs-temp-65d9ff37"),
    Path(r"C:\Users\Correta Engenharia\Desktop"),
]

print("=" * 74)
print("ARTEFATOS")
print("=" * 74)
for p in (DWG, DXF, PDF):
    print("  %-34s %9d bytes  %s" % (p.name, p.stat().st_size if p.exists() else -1, "OK" if p.exists() else "AUSENTE"))

print()
print("=" * 74)
print("QUANTITATIVO DO DXF (o mesmo motor que o MCP usa)")
print("=" * 74)
q = analisar(DXF)
print("unidades informadas : %s" % q.get("unidades"))
print("versao DXF          : %s" % q.get("versao_dxf"))
print("total entidades     : %s" % json.dumps(q.get("total_entidades"), ensure_ascii=False))
print("composto por camada :")
for cam, cont in sorted((q.get("total_por_camada") or q.get("por_camada") or {}).items()):
    if isinstance(cont, dict):
        print("   %-14s %s" % (cam, json.dumps(cont, ensure_ascii=False)))
    else:
        print("   %-14s %s" % (cam, cont))
print("comprimento (m)     :")
for cam, v in sorted((q.get("comprimento_por_camada") or {}).items()):
    print("   %-14s %8.2f" % (cam, v))
print("area fechada (m2)   :")
for cam, v in sorted((q.get("area_fechada_por_camada") or {}).items()):
    print("   %-14s %8.2f" % (cam, v))
print("textos              :")
for t in (q.get("textos") or []):
    print("   %s" % t)
print("cotas               : %s" % (q.get("cotas") or []))

print()
print("=" * 74)
print("PREVIEW + ENTREGA")
print("=" * 74)
try:
    import fitz

    doc = fitz.open(str(PDF))
    pix = doc[0].get_pixmap(dpi=160)
    png = PDF.with_suffix(".png")
    pix.save(str(png))
    print("  preview : %s (%dx%d px)" % (png.name, pix.width, pix.height))
except ImportError:
    print("  PyMuPDF ausente: sem preview")
    png = None

for d in DESTINOS:
    if not d.exists():
        print("  (nao existe) %s" % d)
        continue
    for origem in (PDF, png, DXF, DWG):
        if origem and origem.exists():
            alvo = d / origem.name
            shutil.copy2(origem, alvo)
            print("  copiado -> %s" % alvo)
