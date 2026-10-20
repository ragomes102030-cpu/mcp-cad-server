# -*- coding: utf-8 -*-
"""End-to-end: planta viva no AutoCAD -> DXF (accoreconsole) -> quantitativo."""
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

from cad_mcp import accore  # noqa: E402
from cad_mcp.com_backend import ComBackend  # noqa: E402
from cad_mcp.quantitativo import analisar  # noqa: E402

TMP = Path(r"C:/temp/mcp_cad_com")
SAIDA = RAIZ / "saida"


async def main():
    print("accoreconsole:", accore.achar_accore())
    b = ComBackend()
    r = await b.initialize()
    print("init:", r.ok, r.error, r.payload)

    print("\n[1] exportando DXF do desenho vivo...")
    dxf = SAIDA / "planta_mcp.dxf"
    r = await b.drawing_save_as_dxf(str(dxf))
    print("   ok=%s erro=%s" % (r.ok, r.error))
    if r.ok:
        info = dict(r.payload)
        info.pop("saida", None)
        print("   %s" % json.dumps(info, ensure_ascii=False))
    if not dxf.exists():
        print("   DXF nao gerado; abortando")
        return 1

    print("\n[2] quantitativo do DXF (ezdxf)...")
    q = analisar(dxf)
    print("   arquivo   : %s" % dxf)
    print("   unidades  : %s  (versao %s)" % (q.get("unidades"), q.get("versao_dxf")))
    print("   entidades : %s" % json.dumps(q.get("total_entidades"), ensure_ascii=False))
    print("   camadas   : %s" % ", ".join(sorted((q.get("por_camada") or {}).keys())))
    print("   comprimento por camada:")
    for k, v in (q.get("comprimento_por_camada") or {}).items():
        print("      %-10s %8.2f m" % (k, v))
    print("   area fechada por camada:")
    for k, v in (q.get("area_fechada_por_camada") or {}).items():
        print("      %-10s %8.2f m2" % (k, v))
    print("   textos (trecho):")
    for t in (q.get("textos") or [])[:14]:
        print("      %s" % t)
    print("   cotas: %s" % (q.get("cotas") or [])[:12])
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
