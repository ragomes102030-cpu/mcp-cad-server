# -*- coding: utf-8 -*-
"""Catalogo de simbolos de planta (2D) por disciplina.

Simbolos sao PRIMITIVAS em coordenadas locais (origem no centro do simbolo,
metros na escala 1). `transformar()` leva para o mundo (rotacao + escala +
translacao); o tool `place_symbol` desenha via COM. Nada de 3D.

Primitivas: ("line",x1,y1,x2,y2) | ("circle",cx,cy,r) |
            ("arc",cx,cy,r,a1,a2)  | ("poly",[(x,y),...],closed)
"""
from __future__ import annotations

import math

__all__ = ["SIMBOLOS", "simbolo", "transformar", "CATEGORIAS"]


def _S(id_, nome, disciplina, camada, prims, texto=None):
    return {"id": id_, "nome": nome, "disciplina": disciplina, "camada": camada,
            "primitivas": prims, "texto": texto}


# ---------------------------------------------------------------- catalogo
SIMBOLOS = {
    # ---------------- eletrica ----------------
    "tomada_baixa": _S("tomada_baixa", "Tomada baixa", "eletrica", "E-TOMADA",
        [("arc", 0.0, 0.0, 0.10, 0.0, 180.0),
         ("line", -0.10, 0.0, 0.10, 0.0)]),
    "tomada_media": _S("tomada_media", "Tomada media", "eletrica", "E-TOMADA",
        [("arc", 0.0, 0.0, 0.10, 0.0, 180.0),
         ("line", -0.10, 0.0, 0.10, 0.0),
         ("line", -0.06, 0.0, -0.06, 0.06),
         ("line", 0.06, 0.0, 0.06, 0.06)]),
    "interruptor": _S("interruptor", "Interruptor simples", "eletrica", "E-ILUM",
        [("circle", 0.0, 0.0, 0.06),
         ("line", 0.0, 0.0, 0.12, 0.12)]),
    "luminaria_teto": _S("luminaria_teto", "Luminaria de teto", "eletrica", "E-ILUM",
        [("circle", 0.0, 0.0, 0.12),
         ("line", -0.12, -0.12, 0.12, 0.12),
         ("line", -0.12, 0.12, 0.12, -0.12)]),
    "quadro": _S("quadro", "Quadro de distribuicao", "eletrica", "E-QUADRO",
        [("poly", [(-0.15, -0.10), (0.15, -0.10), (0.15, 0.10), (-0.15, 0.10)], True),
         ("line", -0.15, -0.10, 0.15, 0.10)]),
    "ponto_teto": _S("ponto_teto", "Ponto de teto", "eletrica", "E-ILUM",
        [("circle", 0.0, 0.0, 0.04)]),
    # ---------------- hidraulica ----------------
    "bacia": _S("bacia", "Bacia sanitaria", "hidraulica", "H-ESGOTO",
        [("poly", [(-0.18, -0.12), (0.18, -0.12), (0.18, 0.12), (-0.18, 0.12)], True),
         ("circle", 0.0, 0.0, 0.10)]),
    "lavatorio": _S("lavatorio", "Lavatorio", "hidraulica", "H-AGUA-FRIA",
        [("circle", 0.0, 0.0, 0.12),
         ("line", -0.08, 0.0, 0.08, 0.0)]),
    "chuveiro": _S("chuveiro", "Chuveiro", "hidraulica", "H-AGUA-FRIA",
        [("circle", 0.0, 0.0, 0.10),
         ("line", -0.10, 0.0, 0.10, 0.0),
         ("line", 0.0, -0.10, 0.0, 0.10)]),
    "ralo": _S("ralo", "Ralo", "hidraulica", "H-ESGOTO",
        [("circle", 0.0, 0.0, 0.08),
         ("line", -0.08, -0.08, 0.08, 0.08),
         ("line", -0.08, 0.08, 0.08, -0.08)]),
    "registro": _S("registro", "Registro", "hidraulica", "H-AGUA-FRIA",
        [("poly", [(-0.06, -0.06), (0.06, -0.06), (0.06, 0.06), (-0.06, 0.06)], True),
         ("line", -0.06, -0.06, 0.06, 0.06)]),
}

CATEGORIAS = sorted({s["disciplina"] for s in SIMBOLOS.values()})


def simbolo(nome: str) -> dict:
    """Simbolo do catalogo (dict). Recusa nome desconhecido listando os validos."""
    if nome not in SIMBOLOS:
        raise ValueError("simbolo desconhecido: %r (use: %s)"
                         % (nome, ", ".join(sorted(SIMBOLOS))))
    return SIMBOLOS[nome]


def _tr(pt, ca, sa, scale, x, y):
    lx, ly = pt
    return (x + (lx * ca - ly * sa) * scale, y + (lx * sa + ly * ca) * scale)


def transformar(nome: str, x: float, y: float, rotation: float = 0.0,
                scale: float = 1.0) -> dict:
    """Simbolo -> primitivas no MUNDO (rotacionado em GRAUS, escalado, transladado).

    Devolve {"id","nome","camada","disciplina","primitivas":[...],"texto"}.
    """
    s = simbolo(nome)
    if scale <= 0:
        raise ValueError("scale deve ser > 0")
    ang = math.radians(rotation)
    ca, sa = math.cos(ang), math.sin(ang)
    out = []
    for prim in s["primitivas"]:
        kind = prim[0]
        if kind == "line":
            _, x1, y1, x2, y2 = prim
            out.append(("line",) + _tr((x1, y1), ca, sa, scale, x, y)
                                + _tr((x2, y2), ca, sa, scale, x, y))
        elif kind == "circle":
            _, cx, cy, r = prim
            px, py = _tr((cx, cy), ca, sa, scale, x, y)
            out.append(("circle", px, py, r * scale))
        elif kind == "arc":
            _, cx, cy, r, a1, a2 = prim
            px, py = _tr((cx, cy), ca, sa, scale, x, y)
            out.append(("arc", px, py, r * scale, a1 + rotation, a2 + rotation))
        elif kind == "poly":
            _, pts, closed = prim
            out.append(("poly", [_tr(p, ca, sa, scale, x, y) for p in pts], closed))
        else:
            raise ValueError("primitiva desconhecida: %r" % (kind,))
    return {"id": s["id"], "nome": s["nome"], "camada": s["camada"],
            "disciplina": s["disciplina"], "primitivas": out, "texto": s.get("texto")}
