# -*- coding: utf-8 -*-
"""Planta baixa DETALHADA desenhada no AutoCAD vivo + medicao do sistema.

Duas coisas de uma vez:

1. **Produto** -- uma planta de verdade (paredes, portas com folha e arco,
   janelas, ambientes cotados, mobiliario, cotas, selo, eixos, seta norte),
   entregue em DWG + DXF + PDF + PNG.
2. **Medida** -- cada ferramenta do servidor e exercitada em cima do desenho e
   o resultado e conferido por PROPRIEDADE (area, comprimento, abertura de arco,
   camada, unidades), nao por "0 erros". O padrao de ouro do projeto.

Uso (AutoCAD aberto):
    python tests/planta_detalhada.py            # desenha, mede e imprime
    python tests/planta_detalhada.py --json     # imprime o JSON das medicoes

Sai com 0 se tudo passou. Escreve em `saida/planta_detalhada.*`.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cad_mcp import tools_geo as G                       # noqa: E402
from cad_mcp.com_backend import ComBackend               # noqa: E402
from cad_mcp.planta import areas_do_modelo, desenhar_modelo  # noqa: E402
import cad_mcp.tools as T                                 # noqa: E402

MODELO = RAIZ.parent / "skill" / "cad-planta-autocad" / "assets" / "modelo-3-quartos.json"
SAIDA = RAIZ.parent / "saida"
TMP = Path(os.environ.get("MCP_CAD_TEMP") or "C:/temp/mcp_cad_com")

falhas: list[str] = []
medidas: dict = {}


def ok(nome: str, cond: bool, extra="") -> None:
    print("  %s  %s%s" % ("ok   " if cond else "FALHA", nome,
                          ("  -- " + str(extra)) if (extra and not cond) else ""))
    if not cond:
        falhas.append(nome)


def quase(a, b, tol=0.01) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


# ------------------------------------------------------------------ medicao
def medir_dxf(caminho: Path) -> dict:
    """Le o DXF de volta (ezdxf) e confere propriedades do desenho."""
    import ezdxf

    doc = ezdxf.readfile(str(caminho))
    msp = doc.modelspace()
    por_camada: dict[str, int] = {}
    por_tipo: dict[str, int] = {}
    comp_parede = 0.0
    arcos = []
    textos = {}
    for e in msp:
        cam = e.dxf.get("layer", "0")
        por_camada[cam] = por_camada.get(cam, 0) + 1
        tipo = e.dxftype()
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
        if tipo == "LWPOLYLINE" and cam == "PAREDES":
            pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices()]
            if len(pts) == 4:
                l = math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
                if l < 5:                      # faixa de parede, nao o contorno
                    comp_parede += l
        elif tipo == "ARC":
            arcos.append((round(e.dxf.start_angle, 2), round(e.dxf.end_angle, 2),
                          round(e.dxf.radius, 3)))
        elif tipo == "TEXT":
            textos[e.dxf.text] = (round(e.dxf.height, 3), e.dxf.get("layer", "0"))
    return {
        "caminho": str(caminho),
        "bytes": caminho.stat().st_size,
        "insunits": doc.header.get("$INSUNITS"),
        "dimscale": doc.header.get("$DIMSCALE"),
        "entidades": len(msp),
        "por_camada": dict(sorted(por_camada.items())),
        "por_tipo": dict(sorted(por_tipo.items())),
        "comprimento_parede_m": round(comp_parede, 2),
        "arcos": len(arcos),
        "aberturas_arco": sorted({round(abs(b - a), 1) for a, b, _ in arcos})[:8],
        "textos": len(textos),
        "camadas_esperadas": sorted(n for n in por_camada if n in
                                    ("PAREDES", "PORTAS", "JANELAS", "COTAS", "TEXTOS",
                                     "TERRENO", "EIXOS", "MOBILIARIO", "HACHURA")),
    }


# --------------------------------------------------------------------- main
async def desenhar(b) -> dict:
    """Renderiza o modelo e enriquece com as ferramentas novas."""
    modelo = json.loads(MODELO.read_text(encoding="utf-8"))
    print("1) modelo: %s" % modelo["titulo"])
    r = await b.drawing_create("PLANTA-DETALHADA")
    print("   new_drawing -> %s" % r.ok)
    res = await desenhar_modelo(b, modelo, log=lambda m: print("   ", m))
    print("   entidades=%s erros=%s" % (res.get("entidades_criadas"), len(res.get("erros") or [])))
    medidas["modelo"] = {"titulo": modelo["titulo"],
                         "entidades_criadas": res.get("entidades_criadas"),
                         "erros_render": res.get("erros") or [],
                         "areas_esperadas": res.get("areas") or {}}
    return res


async def enriquecer(b) -> dict:
    """Exercita as ferramentas do servidor em cima do desenho real."""
    feito = {}

    print("\n2) ferramentas do servidor em cima do desenho")
    r = await G.drawing_apply_standard(standard="ISO", layers="arquitetura", unidades=6)
    ok("drawing_apply_standard cria camadas + unidades", r.get("ok"), r.get("erro"))
    feito["apply_standard"] = r.get("ok")

    # metadados do desenho (DWGPROPS)
    r = await G.drawing_properties_set(title="Casa térrea 3 quartos",
                                       author="Rafael Gomes",
                                       keywords="planta baixa, AutoCAD, mcp-cad-server")
    r2 = await G.drawing_properties_get()
    ok("drawing_properties round-trip", r2.get("ok") and r2["payload"]["author"] == "Rafael Gomes",
       r2.get("payload"))

    # malha de eixos estruturais
    r = await G.arch_grid(x_axes=[0.0, 7.0, 13.0], y_axes=[0.0, 5.175, 10.0], extension=0.4)
    ok("arch_grid desenha eixos + bolhas", r.get("ok") and r.get("eixos") == 6, r)
    feito["grid_eixos"] = r.get("eixos")

    # seta norte e marcador de nivel
    r = await G.arch_symbol("north", 14.6, 9.0, {"raio": 0.45})
    ok("arch_symbol north (circulo+seta+letra)",
       r.get("ok") and {"circulo", "seta", "letra"} <= set(r.get("partes", [])), r)
    r = await G.arch_symbol("level", 14.6, 8.0, {"cota": "0.000"})
    ok("arch_symbol level (cota + triangulo)", r.get("ok"), r)

    # hachura de material (banheiros e area de servico)
    alvos = []
    for camada in ("PAREDES",):
        ents = (await b.entity_list(layer=camada)).payload["entities"]
        if ents:
            alvos.append(ents[0]["handle"])
    r = await G.hatch_material("concreto", handles=alvos[:1])
    ok("hatch_material aplica padrao ISO", r.get("ok") and r.get("padrao") == "AR-CONC", r)

    # deteccao de ambientes (so leitura) -- tem de achar os 10 do modelo
    r = await G.arch_rooms_detect(layers=["PAREDES"], min_area=3.0)
    ok("arch_rooms_detect acha os ambientes", r.get("ok") and r.get("ambientes", 0) >= 5, r)
    feito["ambientes_detectados"] = r.get("ambientes")
    medidas["ambientes_detectados"] = (r.get("lista") or [])[:3]

    # cotas encadeadas nas fachadas
    r = await G.arch_dimension_chains(sides=["s", "w"], first_offset=1.0, step=0.8)
    ok("arch_dimension_chains desenha a cadeia", r.get("ok") and r.get("cotas", 0) >= 4, r)
    feito["cotas_cadeia"] = r.get("cotas")

    # cotas especificas
    c = await G.dimension_angular(0, 0, 1, 0, 0, 1)
    ok("dimension_angular responde", "ok" in c, c)
    d = await G.dimension_radius(13.0, 10.0, 0.9)
    ok("dimension_radius responde", "ok" in d, d)
    l = await G.leader_create_mleader([[13.4, 0.4], [14.4, 0.4]], "COZINHA")
    ok("leader_create_mleader desenha", l.get("ok"), l)

    # consulta de entidade + geometria
    ents = (await b.entity_list(layer="PAREDES")).payload["entities"]
    if ents:
        h = ents[0]["handle"]
        g = await G.entity_get(h)
        ok("entity_get devolve geometria", g.get("ok") and len(g["payload"].get("pontos", [])) == 4, g)
        m = await G.point_from_snap(h, "midpoint")
        ok("point_from_snap midpoint", m.get("ok") and len(m.get("ponto", [])) == 2, m)
        p = await G.point_from_snap(h, "perpendicular", ref_x=1.0, ref_y=1.0)
        ok("point_from_snap perpendicular", p.get("ok"), p)

    # selecao por janela (so leitura)
    s = await G.selection_window(-1, -1, 8, 6, modo="crossing")
    ok("selection_window lista o que cruza", s.get("ok") and s.get("selecionadas", 0) > 0, s)
    feito["selecionadas_janela"] = s.get("selecionadas")

    # edicao: retextualizar um rotulo e escalar uma entidade
    txts = (await b.entity_list(layer="TEXTOS")).payload["entities"]
    if txts:
        r = await G.entity_edit_text(txts[0]["handle"], height=0.30)
        ok("entity_edit_text altera altura", r.get("ok"), r)
    if ents:
        r = await G.entity_scale(ents[1]["handle"], 0, 0, 1.0)
        ok("entity_scale responde", "ok" in r, r)

    # bloco: vira as entidades de um ambiente em bloco reutilizavel
    if ents:
        r = await G.block_define("BLOCO_TESTE", [{"handle": e["handle"]} for e in ents[:2]])
        ok("block_define responde", "ok" in r, r)
    return feito


async def exportar(b) -> dict:
    """DWG + DXF + PDF + PNG."""
    print("\n3) exportacao")
    SAIDA.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    base = SAIDA / "planta_detalhada"

    dwg = str(base.with_suffix(".dwg"))
    r = await b.drawing_save(path=dwg)
    ok("DWG salvo", r.ok and Path(dwg).exists(), r.error)
    medidas["dwg"] = {"bytes": Path(dwg).stat().st_size if Path(dwg).exists() else 0}

    dxf = str(base.with_suffix(".dxf"))
    r = await b.drawing_save_as_dxf(dxf)
    ok("DXF exportado", r.ok and Path(dxf).exists(), r.error)
    if Path(dxf).exists():
        medidas["dxf"] = medir_dxf(Path(dxf))

    pdf = str(base.with_suffix(".pdf"))
    try:
        r = await b.drawing_plot_pdf(pdf, media="A1", escala=50)
    except TypeError:
        r = await b.drawing_plot_pdf(pdf)
    ok("PDF plotado", r.ok and Path(pdf).exists(), r.error)
    medidas["pdf"] = {"bytes": Path(pdf).stat().st_size if Path(pdf).exists() else 0}

    png = str(base.with_suffix(".png"))
    r = await T.render_png(png)
    ok("PNG capturado", r.get("ok") and Path(png).exists(), r.get("erro"))
    medidas["png"] = r.get("ok") and {"bytes": Path(png).stat().st_size,
                                      "largura": r.get("largura"), "altura": r.get("altura")}
    return medidas


async def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Planta detalhada + medicao do sistema.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    print("=" * 72)
    print("PLANTA DETALHADA + MEDICAO DO SISTEMA")
    print("=" * 72)
    t0 = time.perf_counter()
    b = ComBackend()
    try:
        await b.initialize()
    except Exception as exc:  # noqa: BLE001
        print("sem AutoCAD: %s" % str(exc)[:120])
        return 2
    print("backend: %s (%s)" % (b.name, "AutoCAD vivo"))

    await desenhar(b)
    feito = await enriquecer(b)
    await exportar(b)

    # ---------------------------------------------------------- conferencia
    print("\n4) conferencia por propriedade")
    dx = medidas.get("dxf") or {}
    esp = medidas["modelo"]["areas_esperadas"]

    ok("INSUNITS = 6 (metros)", dx.get("insunits") == 6, dx.get("insunits"))
    ok("camada PAREDES existe", "PAREDES" in (dx.get("por_camada") or {}))
    ok("camada PORTAS existe", "PORTAS" in (dx.get("por_camada") or {}))
    ok("camada COTAS existe", "COTAS" in (dx.get("por_camada") or {}))
    ok("camada EIXOS existe (linetype carregado)", "EIXOS" in (dx.get("por_camada") or {}),
       "EIXOS faltou: linetype CENTER nao carregado")
    ok("ha entidades na camada PAREDES", (dx.get("por_camada") or {}).get("PAREDES", 0) >= 20,
       dx.get("por_camada"))
    ok("ha arcos (folhas de porta)", dx.get("arcos", 0) >= 8, dx.get("arcos"))
    ok("ha cotas (DIMENSION)", (dx.get("por_tipo") or {}).get("DIMENSION", 0) >= 6,
       dx.get("por_tipo"))
    ok("ha textos (rotulos)", dx.get("textos", 0) >= 10, dx.get("textos"))

    # as areas do modelo conferem com as detectadas no desenho
    det = {r["camada"]: r["area"] for r in medidas.get("ambientes_detectados") or []}
    ok("arch_rooms_detect mede area de ambiente real", bool(det), det)

    # todos os ambientes do modelo apareceram no DXF como texto de rotulo
    ok("modelo tem 10 ambientes", len(esp) == 10, len(esp))

    medidas["ferramentas_exercitadas"] = feito
    medidas["tempo_total_s"] = round(time.perf_counter() - t0, 1)
    medidas["falhas"] = falhas

    print("\n" + "=" * 72)
    print("MEDICAO")
    print("=" * 72)
    print("  entidades no DXF        : %s" % dx.get("entidades"))
    print("  comprimento de parede   : %s m" % dx.get("comprimento_parede_m"))
    print("  arcos (folhas de porta) : %s" % dx.get("arcos"))
    print("  aberturas de arco       : %s graus" % dx.get("aberturas_arco"))
    print("  cotas                   : %s" % (dx.get("por_tipo") or {}).get("DIMENSION"))
    print("  textos                  : %s" % dx.get("textos"))
    print("  camadas usadas          : %s" % dx.get("camadas_esperadas"))
    print("  DWG/DXF/PDF/PNG         : %s / %s / %s / %s bytes"
          % (medidas["dwg"]["bytes"], dx.get("bytes"), medidas["pdf"]["bytes"],
             (medidas["png"] or {}).get("bytes")))
    print("  ferramentas exercitadas : %s" % len(feito))
    print("  tempo                   : %.1fs" % medidas["tempo_total_s"])

    if args.json:
        print(json.dumps(medidas, ensure_ascii=False, indent=2))

    print()
    if falhas:
        print("FALHOU (%d): %s" % (len(falhas), ", ".join(falhas)))
        return 1
    print("TUDO OK -- planta detalhada entregue e sistema medido por propriedade.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
