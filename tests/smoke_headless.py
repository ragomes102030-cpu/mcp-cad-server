# -*- coding: utf-8 -*-
"""Smoke test headless: camadas -> planta -> cotas -> quantitativo -> DXF.

Roda sem AutoCAD (backend ezdxf), provando o motor de ponta a ponta.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
os.environ["CAD_MCP_BACKEND"] = "ezdxf"          # força headless
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from cad_mcp import tools  # noqa: E402

SAIDA = RAIZ / "data" / "smoke"
SAIDA.mkdir(parents=True, exist_ok=True)


def linha(t=""):
    print(t, flush=True)


async def main():
    linha("=" * 70)
    st = await tools.cad_status()
    linha("BACKEND   : %s  (%s)" % (st["backend"], st["selecao"]))
    linha("=" * 70)

    r = await tools.new_drawing("CASA-TERREA-TESTE")
    linha("new_drawing        -> %s" % r.get("ok"))

    r = await tools.ensure_standard_layers()
    linha("camadas criadas    -> %d  (ja existiam: %d)" % (len(r["criadas"]), len(r["ja_existiam"])))

    # --- planta: 4 ambientes dentro de um terreno 10x8
    ambientes = [
        ("SALA",      0.0, 0.0, 4.0, 4.0),
        ("COZINHA",   4.0, 0.0, 3.0, 3.0),
        ("QUARTO",    0.0, 4.0, 3.5, 2.5),
        ("BANHEIRO",  3.5, 4.0, 2.0, 2.5),
    ]
    area_total = 0.0
    for nome, x, y, w, h in ambientes:
        res = await tools.desenhar_ambiente(nome, x, y, w, h)
        area_total += res.get("area", 0.0)
        linha("ambiente %-9s -> area %6.2f m²  contorno=%s" % (
            nome, res.get("area", 0), (res.get("contorno") or {}).get("handle")))

    # --- linha de divisa do terreno + cota
    await tools.draw_rectangle(0, 0, 10, 8, layer="TERRENO")
    await tools.dim_linear(0, 0, 10, 0, 5, -1.2)
    await tools.dim_linear(0, 0, 0, 8, -1.2, 4)
    await tools.draw_text(5, 8.6, "PLANTA BAIXA - TESTE", height=0.35, layer="TEXTOS")
    linha("terreno 10x8 + 2 cotas + titulo -> ok")

    # --- quantitativo (o que vai alimentar EAP/orcamento)
    q = await tools.quantitativo()
    linha("-" * 70)
    linha("QUANTITATIVO  backend=%s  unidades=%s" % (q.get("backend"), q.get("unidades")))
    linha("entidades: %s" % json.dumps(q.get("entidades_por_tipo", {}), ensure_ascii=False))
    linha("blocos   : %s" % json.dumps(q.get("blocos", {}), ensure_ascii=False))
    linha("comprimento por camada:")
    for cam, v in list(q.get("comprimento_por_camada", {}).items()):
        linha("   %-12s %10.2f" % (cam, v))
    linha("area fechada por camada:")
    for cam, v in list(q.get("area_fechada_por_camada", {}).items()):
        linha("   %-12s %10.2f" % (cam, v))
    linha("textos (%d): %s" % (q.get("total_textos", 0), q.get("textos", [])[:8]))
    linha("cotas  (%d): %s" % (q.get("total_cotas", 0), q.get("cotas", [])[:15]))

    # --- saidas em arquivo
    dxf = str(SAIDA / "smoke_planta.dxf")
    r = await tools.export_dxf(dxf)
    linha("export_dxf         -> %s  (%s)" % (r.get("ok"), dxf if Path(dxf).exists() else "arquivo ausente"))
    if Path(dxf).exists():
        linha("   bytes: %d" % Path(dxf).stat().st_size)

    pdf = str(SAIDA / "smoke_planta.pdf")
    r = await tools.plot_pdf(pdf)
    linha("plot_pdf           -> %s" % r.get("ok"))

    json.dump(q, open(SAIDA / "smoke_quantitativo.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2, default=str)
    linha("-" * 70)
    linha("area total dos ambientes: %.2f m²" % area_total)
    linha("OK" if q.get("ok") else "FALHOU")


asyncio.run(main())
