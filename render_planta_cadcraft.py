# -*- coding: utf-8 -*-
"""Renderiza uma planta baixa HEADLESS (sem AutoCAD) com ezdxf.

Fluxo:
  1. validar o modelo (regra de ouro do projeto: validar antes de desenhar);
  2. desenhar model  -> DXF (unidades em METROS, INSUNITS=6);
  3. salvar DXF em saida/ e entregar PNG/DWG via `cadcraft-cli convert`.

Uso:
    python render_planta_cadcraft.py skill/cad-planta-autocad/assets/modelo-3-quartos.json
    python render_planta_cadcraft.py modelo.json --nome mine --entrega .
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import ezdxf

BASE = Path(__file__).resolve().parent
if str(BASE / "codigo" / "src") not in sys.path:
    sys.path.insert(0, str(BASE / "codigo" / "src"))
from cad_mcp.validar_modelo import validar  # projeto (valida, nao desenha)

LAYER_COLORS = {  # nome -> (cor ACI, tipo linha)
    "PAREDES": (4, "CONTINUOUS"),
    "PORTAS": (3, "CONTINUOUS"),
    "JANELAS": (5, "CONTINUOUS"),
    "MOBILIARIO": (9, "CONTINUOUS"),
    "COTAS": (1, "CONTINUOUS"),
    "TEXTOS": (7, "CONTINUOUS"),
    "TERRENO": (6, "CONTINUOUS"),
}


def fprec(v: float, casas: int = 4) -> str:
    return ("%.*f" % (casas, float(v))).rstrip("0").rstrip(".") or "0"


def draw(modelo: dict, msp, doc) -> dict:
    t = float(modelo.get("espessura_parede", 0.15))
    mt = t / 2.0
    camadas = {}

    # ---- camadas ----
    for nome, (cor, lt) in LAYER_COLORS.items():
        camadas[nome] = doc.layers.add(nome, dxfattribs={"color": cor, "linetype": lt})

    # ---- unidade: metros (INSUNITS=6) ----
    doc.header["$INSUNITS"] = 6

    def camada(nome):
        return msp

    # ---- terreno ----
    if modelo.get("terreno"):
        tx1, ty1, tx2, ty2 = modelo["terreno"]
        msp.add_lwpolyline([(tx1, ty1), (tx2, ty1), (tx2, ty2), (tx1, ty2), (tx1, ty1)],
                           close=True, dxfattribs={"layer": "TERRENO"})

    # ---- paredes (eixos -> faixa de espessura) ----
    for (x1, y1, x2, y2) in modelo.get("paredes", []):
        if abs(y2 - y1) < 1e-9:          # horizontal
            pts = [(min(x1, x2), y1 - mt), (max(x1, x2), y1 - mt),
                   (max(x1, x2), y1 + mt), (min(x1, x2), y1 + mt)]
        elif abs(x2 - x1) < 1e-9:        # vertical
            pts = [(x1 - mt, min(y1, y2)), (x1 + mt, min(y1, y2)),
                   (x1 + mt, max(y1, y2)), (x1 - mt, max(y1, y2))]
        else:                            # diagonal (não esperado no modelo)
            pts = [(x1, y1), (x2, y2)]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "PAREDES"})

    # ---- ambientes (retângulo + rótulo + área) ----
    for amb in modelo.get("ambientes", []):
        x1, y1, x2, y2 = amb["x1"], amb["y1"], amb["x2"], amb["y2"]
        area = (x2 - x1) * (y2 - y1)
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        h = float(amb.get("h", 0.26))
        msp.add_text(amb["nome"], dxfattribs={"height": h, "layer": "TEXTOS",
                                              "insert": (cx, cy + 0.16)})
        msp.add_text("%s m2" % fprec(area, 2), dxfattribs={"height": h * 0.72,
                                                            "layer": "TEXTOS",
                                                            "insert": (cx, cy - 0.26)})

    # ---- portas (arco 90 + folha) ----
    for (px, py, ang, larg) in modelo.get("portas", []):
        msp.add_arc((px, py), larg, ang, ang + 90.0, dxfattribs={"layer": "PORTAS"})
        cx2 = px + larg * math.cos(math.radians(ang))
        cy2 = py + larg * math.sin(math.radians(ang))
        msp.add_line((px, py), (cx2, cy2), dxfattribs={"layer": "PORTAS"})

    # ---- janelas (duas linhas +/mt/2) ----
    for (x1, y1, x2, y2) in modelo.get("janelas", []):
        if abs(y2 - y1) < 1e-9:  # horizontal
            msp.add_line((x1, y1 - mt / 2), (x2, y2 - mt / 2), dxfattribs={"layer": "JANELAS"})
            msp.add_line((x1, y1 + mt / 2), (x2, y2 + mt / 2), dxfattribs={"layer": "JANELAS"})
        else:  # vertical
            msp.add_line((x1 - mt / 2, y1), (x2 - mt / 2, y2), dxfattribs={"layer": "JANELAS"})
            msp.add_line((x1 + mt / 2, y1), (x2 + mt / 2, y2), dxfattribs={"layer": "JANELAS"})

    # ---- móveis ----
    for (x1, y1, x2, y2) in modelo.get("moveis", []):
        msp.add_lwpolyline([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)],
                           close=True, dxfattribs={"layer": "MOBILIARIO"})

    # ---- cotas ----
    for (x1, x2, y, y_txt) in modelo.get("cotas_h", []):
        msp.add_linear_dim((x1, y), (x2, y), ((x1 + x2) / 2.0, y_txt),
                           dxfattribs={"layer": "COTAS"})
    for (x, y1, y2, x_txt) in modelo.get("cotas_v", []):
        msp.add_linear_dim((x, y1), (x, y2), (x_txt, (y1 + y2) / 2.0),
                           dxfattribs={"layer": "COTAS"})

    # ---- selo ----
    for (x, y, txt, h) in modelo.get("selo", []):
        msp.add_text(txt, dxfattribs={"height": h, "layer": "TEXTOS", "insert": (x, y)})

    return {"exc": camadas}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("modelo")
    ap.add_argument("--nome", default="planta_cadcraft")
    ap.add_argument("--entrega", default=None)
    args = ap.parse_args()

    modelo = json.loads(Path(args.modelo).read_text(encoding="utf-8"))
    valid = validar(modelo)

    if not valid["ok"]:
        print("VALIDACAO FALHOU:", valid["area_util"])
        for p in valid["problemas"]:
            print("  ERRO %s | %s | %s" % (p["chave"], p["onde"], p["detalhe"]))
        return 1
    print("VALIDO: %d erros, %d avisos | area util %.2f m2" %
          (len(valid["erros"]), len(valid["avisos"]), valid["area_util"]))

    doc = ezdxf.new("R2013")
    msp = doc.modelspace()
    draw(modelo, msp, doc)

    out = Path(args.entrega or BASE / "saida")
    out.mkdir(parents=True, exist_ok=True)
    dxf = out / ("%s.dxf" % args.nome)
    doc.saveas(dxf)
    print("DXF ->", dxf, "entidades:", len(list(msp)))

    # conferir: abrir e contar entidades
    d2 = ezdxf.readfile(dxf)
    m2 = d2.modelspace()
    print("conferido: %d entidades" % len(list(m2)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
