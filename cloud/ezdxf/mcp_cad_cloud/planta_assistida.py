"""Template residencial determinístico para o MCP cloud (ezdxf)."""
from __future__ import annotations

import math
from copy import deepcopy

from mcp_cad_cloud.backend import _ensure, reset_drawing


ROOMS = (
    "Sala de estar/jantar", "Cozinha", "Área de serviço", "Banheiro social",
    "Circulação", "Quarto 2", "Quarto 3", "Suíte", "Banheiro da suíte",
    "Hall/closet",
)


def _split_wall(wall, openings):
    x1, y1, x2, y2 = wall
    horizontal = abs(y2 - y1) < 1e-9
    lo, hi = (min(x1, x2), max(x1, x2)) if horizontal else (min(y1, y2), max(y1, y2))
    cuts = sorted((max(lo, p), min(hi, p + width)) for p, width in openings)
    out, cursor = [], lo
    for start, end in cuts:
        if end <= cursor or start >= hi:
            continue
        if start > cursor + 0.02:
            out.append([cursor, y1, start, y2] if horizontal else [x1, cursor, x2, start])
        cursor = max(cursor, end)
    if cursor < hi - 0.02:
        out.append([cursor, y1, hi, y2] if horizontal else [x1, cursor, x2, hi])
    return out


def _rooms():
    values = [
        ("Sala de estar/jantar", .075, .075, 4.925, 4.925),
        ("Cozinha", 5.075, .075, 8.525, 4.925),
        ("Área de serviço", 8.675, .075, 11.925, 2.525),
        ("Banheiro social", 8.675, 2.675, 11.925, 4.925),
        ("Circulação", .075, 5.075, 11.925, 6.125),
        ("Quarto 2", 4.675, 6.275, 8.525, 10.925),
        ("Quarto 3", 8.675, 6.275, 11.925, 10.925),
        ("Suíte", .075, 8.675, 4.525, 10.925),
        ("Banheiro da suíte", .075, 6.275, 2.325, 8.525),
        ("Hall/closet", 2.475, 6.275, 4.525, 8.525),
    ]
    out = []
    for name, x1, y1, x2, y2 in values:
        h = min(.22, max(.12, .82 * (x2 - x1) / (.9 * len(name))))
        out.append({"nome": name, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "h": h})
    return out


def build_assisted_model(programa=None):
    programa = deepcopy(programa or {})
    if (float(programa.get("largura_externa", 12.0)) != 12.0 or
            float(programa.get("profundidade_externa", 11.0)) != 11.0):
        raise ValueError("o template exige casa externa de 12,00 x 11,00 m")
    if abs(float(programa.get("espessura_parede", .15)) - .15) > 1e-9:
        raise ValueError("o template exige parede de 0,15 m")
    if float(programa.get("pe_direito", 2.8)) <= 2.4:
        raise ValueError("pé-direito incompatível")

    specs = [
        ((0, 0, 12, 0), [(.5, .9), (2.2, 2.0), (5.9, 1.4), (9.4, 1.2)]),
        ((0, 11, 12, 11), [(1.0, 1.2), (5.5, 2.0), (9.4, 1.5)]),
        ((0, 0, 0, 11), [(2.0, 1.4), (6.9, .8)]),
        ((12, 0, 12, 11), [(3.2, 1.0), (7.5, 2.0)]),
        ((0, 5, 12, 5), [(2.2, .9), (6.4, .9), (10.2, .7)]),
        ((0, 6.2, 12, 6.2), [(3.2, .9), (5.6, .9), (9.6, .9)]),
        ((8.6, 2.6, 12, 2.6), []), ((0, 8.6, 4.6, 8.6), [(3.2, .9)]),
        ((5, 0, 5, 5), [(2, .9)]), ((8.6, 0, 8.6, 5), [(.9, .9)]),
        ((8.6, 6.2, 8.6, 11), []), ((4.6, 6.2, 4.6, 11), []),
        ((2.4, 6.2, 2.4, 8.6), [(6.6, .9)]),
    ]
    walls = [seg for wall, openings in specs for seg in (_split_wall(wall, openings) if openings else [list(wall)])]
    return {
        "titulo": programa.get("titulo", "PLANTA ASSISTIDA - RESIDÊNCIA UNIFAMILIAR"),
        "espessura_parede": .15, "pe_direito": float(programa.get("pe_direito", 2.8)),
        "terreno": (-1.5, -5.0, 13.5, 16.0), "paredes": walls,
        "parede_sem_sobreposicao": True, "ambientes": _rooms(),
        "portas": [(0.5, 0, 90, .9), (2.2, 5, 270, .9), (6.4, 5, 270, .9),
                   (10.2, 5, 270, .7), (3.2, 6.2, 90, .9), (5.6, 6.2, 90, .9),
                   (9.6, 6.2, 90, .9), (3.2, 8.6, 90, .9), (5, 2, 0, .9),
                   (8.6, .9, 0, .9), (2.4, 6.6, 180, .9)],
        "janelas": [(2.2, 0, 4.2, 0), (5.9, 0, 7.3, 0), (9.4, 0, 10.6, 0),
                    (12, 3.2, 12, 4.2), (12, 7.5, 12, 9.5), (1, 11, 2.2, 11),
                    (5.5, 11, 7.5, 11), (9.4, 11, 10.9, 11), (0, 2, 0, 3.4),
                    (0, 6.9, 0, 7.7)],
        "moveis": [(1.5, 1.3, 3.9, 2.1), (3.4, 3.4, 4.7, 4.6),
                   (5.15, .15, 8.45, .75), (7.9, 4, 8.45, 4.85),
                   (8.8, 1.85, 9.7, 2.45), (10, 1.85, 10.9, 2.45),
                   (8.8, 2.8, 9.4, 3.5), (11.2, 2.8, 11.8, 3.3),
                   (5.6, 9.3, 7.2, 10.85), (4.9, 10, 5.4, 10.5),
                   (7.95, 6.4, 8.45, 8), (9.1, 9.3, 10.8, 10.85),
                   (10.8, 6.5, 11.8, 7.2), (11.3, 8.3, 11.85, 10.6),
                   (.25, 8.8, 1.75, 10.6), (.2, 6.35, 1.1, 7),
                   (.3, 7.9, .9, 8.45), (1.3, 7.9, 2.1, 8.45)],
        "cotas_h": [(0, 5, -1, -1), (5, 8.6, -1, -1), (8.6, 12, -1, -1),
                    (0, 12, -2, -2), (0, 4.6, 12, 12), (4.6, 8.6, 12, 12),
                    (8.6, 12, 12, 12), (0, 12, 13, 13)],
        "cotas_v": [(12.8, 0, 6, 12.8), (12.8, 6, 11, 12.8), (13.8, 0, 11, 13.8)],
        "selo": [(-1.4, -5.45, "PLANTA BAIXA - RESIDÊNCIA UNIFAMILIAR", .16),
                 (-1.4, -5.7, "Área útil: 120,67 m²", .16),
                 (-1.4, -5.95, "Área construída: 132,00 m²", .16),
                 (-1.4, -6.2, "Terreno: 15,00 x 21,00 m", .16),
                 (-1.4, -6.45, "Recuos assumidos: frente/fundos 5,00 m; laterais 1,50 m", .16),
                 (-1.4, -6.7, "Pé-direito: 2,80 m | Cotas em metros", .16)],
        "area_pedida": float(programa.get("area_util_minima", 120.67)),
    }


def wall_boundary_segments(walls, t=.15):
    half, out, seen = float(t) / 2, [], set()
    def add(a, b):
        key = tuple(round(v, 8) for v in (*a, *b))
        rev = tuple(round(v, 8) for v in (*b, *a))
        if key not in seen and rev not in seen:
            seen.update((key, rev)); out.append((*a, *b))
    def connected(x, y, current):
        for other in walls:
            if other == current: continue
            x1, y1, x2, y2 = other
            if abs(y2-y1) < 1e-9 and abs(y-y1) < 1e-9 and min(x1,x2)-1e-7 <= x <= max(x1,x2)+1e-7:
                return True
            if abs(x2-x1) < 1e-9 and abs(x-x1) < 1e-9 and min(y1,y2)-1e-7 <= y <= max(y1,y2)+1e-7:
                return True
        return False
    for current in walls:
        x1, y1, x2, y2 = current
        if abs(y2-y1) < 1e-9:
            lo, hi = sorted((x1, x2)); add((lo, y1-half), (hi, y1-half)); add((lo, y1+half), (hi, y1+half))
            if not connected(lo, y1, current): add((lo, y1-half), (lo, y1+half))
            if not connected(hi, y1, current): add((hi, y1-half), (hi, y1+half))
        else:
            lo, hi = sorted((y1, y2)); add((x1-half, lo), (x1-half, hi)); add((x1+half, lo), (x1+half, hi))
            if not connected(x1, lo, current): add((x1-half, lo), (x1+half, lo))
            if not connected(x1, hi, current): add((x1-half, hi), (x1+half, hi))
    return out


def _summary(model):
    areas = {a["nome"]: round((a["x2"]-a["x1"])*(a["y2"]-a["y1"]), 4) for a in model["ambientes"]}
    return {"titulo": model["titulo"], "ambientes": len(model["ambientes"]),
            "paredes": len(model["paredes"]), "portas": len(model["portas"]),
            "janelas": len(model["janelas"]), "areas": areas,
            "area_util": round(sum(areas.values()), 4), "espessura_parede": .15,
            "pe_direito": model["pe_direito"], "unidades": "metros"}


def _ensure_layers(doc):
    for name, color in (("TERRENO", 6), ("PAREDES", 7), ("PORTAS", 3), ("JANELAS", 5),
                        ("MOBILIARIO", 2), ("COTAS", 1), ("TEXTOS", 7)):
        if name not in doc.layers:
            doc.layers.new(name, dxfattribs={"color": color})


def planta_assistida(programa=None, modo="preview", nome=None):
    model = build_assisted_model(programa)
    summary = _summary(model)
    if modo == "preview":
        return {"ok": True, "etapa": "preview", "backend": "ezdxf", "resumo": summary, "modelo": model}
    if modo != "desenhar":
        return {"ok": False, "code": "INVALID_MODE", "error": "modo deve ser preview ou desenhar"}

    reset_drawing()
    doc = _ensure(); _ensure_layers(doc); msp = doc.modelspace()
    if nome: global DRAWING_NAME; DRAWING_NAME = str(nome)
    for x1, y1, x2, y2 in wall_boundary_segments(model["paredes"]):
        msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "PAREDES"})
    x1, y1, x2, y2 = model["terreno"]
    msp.add_lwpolyline([(x1,y1),(x2,y1),(x2,y2),(x1,y2)], close=True, dxfattribs={"layer":"TERRENO"})
    for px, py, ang, width in model["portas"]:
        msp.add_arc((px, py), width, ang, ang + 90, dxfattribs={"layer":"PORTAS"})
        r = math.radians(ang); msp.add_line((px,py),(px+width*math.cos(r),py+width*math.sin(r)), dxfattribs={"layer":"PORTAS"})
    half = .15 / 2
    for a, b, c, d in model["janelas"]:
        if abs(d-b) < 1e-9:
            msp.add_line((a,b-half/2),(c,d-half/2), dxfattribs={"layer":"JANELAS"})
            msp.add_line((a,b+half/2),(c,d+half/2), dxfattribs={"layer":"JANELAS"})
        else:
            msp.add_line((a-half/2,b),(c-half/2,d), dxfattribs={"layer":"JANELAS"})
            msp.add_line((a+half/2,b),(c+half/2,d), dxfattribs={"layer":"JANELAS"})
    for x1, y1, x2, y2 in model["moveis"]:
        msp.add_lwpolyline([(x1,y1),(x2,y1),(x2,y2),(x1,y2)], close=True, dxfattribs={"layer":"MOBILIARIO"})
    for amb in model["ambientes"]:
        cx, cy = (amb["x1"]+amb["x2"])/2, (amb["y1"]+amb["y2"])/2
        msp.add_text(amb["nome"], dxfattribs={"height":amb["h"],"insert":(cx,cy+.16),"layer":"TEXTOS"})
    for x1, x2, y, distance in model["cotas_h"]:
        dim = msp.add_aligned_dim((x1,0),(x2,0),distance=distance,dxfattribs={"layer":"COTAS"}); dim.render()
    for x, y1, y2, distance in model["cotas_v"]:
        dim = msp.add_aligned_dim((x,y1),(x,y2),distance=distance,dxfattribs={"layer":"COTAS"}); dim.render()
    for x, y, text, height in model["selo"]:
        msp.add_text(text, dxfattribs={"height":height,"insert":(x,y),"layer":"TEXTOS"})
    return {"ok": True, "etapa": "desenho", "backend": "ezdxf", "resumo": summary,
            "entities": len(msp), "drawing": DRAWING_NAME}


DRAWING_NAME = "planta_sem_nome"
