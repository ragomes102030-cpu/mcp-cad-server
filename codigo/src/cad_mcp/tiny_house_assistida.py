"""Template deterministico de Tiny House compacta de 10 m2."""
from __future__ import annotations

from copy import deepcopy


def _split_wall(wall, openings):
    x1, y1, x2, y2 = wall
    horizontal = abs(y2 - y1) < 1e-9
    lo, hi = (min(x1, x2), max(x1, x2)) if horizontal else (min(y1, y2), max(y1, y2))
    cuts = sorted((max(lo, p), min(hi, p + width)) for p, width in openings)
    result, cursor = [], lo
    for start, end in cuts:
        if end <= cursor or start >= hi:
            continue
        if start > cursor + 0.02:
            result.append([cursor, y1, start, y2] if horizontal else [x1, cursor, x2, start])
        cursor = max(cursor, end)
    if cursor < hi - 0.02:
        result.append([cursor, y1, hi, y2] if horizontal else [x1, cursor, x2, hi])
    return result


def build_tiny_house_model(programa: dict | None = None) -> dict:
    programa = deepcopy(programa or {})
    width = float(programa.get("largura_externa", 2.5))
    depth = float(programa.get("profundidade_externa", 4.0))
    thickness = float(programa.get("espessura_parede", 0.15))
    height = float(programa.get("pe_direito", 2.8))
    if abs(width - 2.5) > 1e-6 or abs(depth - 4.0) > 1e-6:
        raise ValueError("o template tiny_house_10m2 exige modulo externo de 2,50 x 4,00 m")
    if abs(thickness - 0.15) > 1e-6:
        raise ValueError("o template tiny_house_10m2 exige parede de 0,15 m")
    if height <= 2.4 or height > 4.0:
        raise ValueError("pe-direito deve estar entre 2,40 m e 4,00 m")

    specs = [
        ((0, 0, 2.5, 0), [(0.8, 0.9), (1.8, 0.5)]),
        ((0, 4, 2.5, 4), [(0.4, 0.8)]),
        ((0, 0, 0, 4), [(2.4, 0.8)]),
        ((2.5, 0, 2.5, 4), [(0.7, 0.7)]),
        ((0, 2, 2.5, 2), [(0.8, 0.7)]),
    ]
    walls = [seg for wall, openings in specs for seg in _split_wall(wall, openings)]
    return {
        "titulo": programa.get("titulo", "TINY HOUSE - ESTUDIO COM BANHEIRO"),
        "espessura_parede": thickness,
        "pe_direito": height,
        "terreno": (-3.75, -5.0, 6.25, 15.0),
        "paredes": walls,
        "parede_sem_sobreposicao": True,
        "ambientes": [
            {"nome": "Estar/cozinha", "x1": 0.075, "y1": 0.075, "x2": 2.425, "y2": 1.925, "h": 0.14},
            {"nome": "Banheiro", "x1": 0.075, "y1": 2.075, "x2": 2.425, "y2": 3.925, "h": 0.14},
        ],
        "portas": [(0.8, 0, 90.0, 0.9), (0.8, 2.0, 90.0, 0.7)],
        "janelas": [
            (1.8, 0, 2.3, 0), (0.4, 4, 1.2, 4),
            (0, 2.4, 0, 3.2), (2.5, 0.7, 2.5, 1.4),
        ],
        "moveis": [
            (0.2, 0.3, 1.2, 0.7), (1.45, 0.3, 2.35, 0.7),
            (0.2, 2.2, 1.0, 2.9), (1.1, 2.2, 1.7, 2.9),
            (1.8, 3.2, 2.3, 3.7),
        ],
        "cotas_h": [(0, 2.5, -0.8, -0.8), (0, 0.8, 4.8, 4.8), (0.8, 2.5, 4.8, 4.8),
                    (-3.75, 6.25, -6.0, -6.0)],
        "cotas_v": [(3.3, 0, 4, 3.3), (3.7, 0, 2, 3.7), (4.1, 2, 4, 4.1),
                    (7.0, -5, 15, 7.0)],
        "selo": [
            (-3.5, -6.55, "TINY HOUSE - ESTUDIO", 0.16),
            (-3.5, -6.8, "Area construida: 10,00 m2", 0.14),
            (-3.5, -7.03, "Terreno: 10,00 x 20,00 m", 0.14),
            (-3.5, -7.26, "Parede: 0,15 m | Pe-direito: 2,80 m", 0.14),
        ],
        "area_pedida": 10.0,
    }
