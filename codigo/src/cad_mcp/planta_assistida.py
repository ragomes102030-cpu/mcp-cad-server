"""Layout parametricamente seguro para modelos pequenos.

O modelo de linguagem escolhe o programa; este módulo escolhe coordenadas,
abre vãos e devolve um modelo completo para :func:`planta.desenhar_modelo`.
"""
from __future__ import annotations

from copy import deepcopy


ROOMS = (
    "Sala de estar/jantar", "Cozinha", "Área de serviço", "Banheiro social",
    "Circulação", "Quarto 2", "Quarto 3", "Suíte", "Banheiro da suíte",
    "Hall/closet",
)


def _split_wall(wall: tuple[float, float, float, float], openings: list[tuple[float, float]]) -> list[list[float]]:
    x1, y1, x2, y2 = wall
    horizontal = abs(y2 - y1) < 1e-9
    lo, hi = (min(x1, x2), max(x1, x2)) if horizontal else (min(y1, y2), max(y1, y2))
    cuts = sorted((max(lo, p), min(hi, p + width)) for p, width in openings)
    result: list[list[float]] = []
    cursor = lo
    for start, end in cuts:
        if end <= cursor or start >= hi:
            continue
        if start > cursor + 0.02:
            result.append([cursor, y1, start, y2] if horizontal else [x1, cursor, x2, start])
        cursor = max(cursor, end)
    if cursor < hi - 0.02:
        result.append([cursor, y1, hi, y2] if horizontal else [x1, cursor, x2, hi])
    return result


def _rooms() -> list[dict]:
    # Coordenadas das faces internas; eixos externos ficam em 0..12 / 0..11.
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
    result = []
    for n, x1, y1, x2, y2 in values:
        # O rótulo é reduzido somente quando necessário; o validador estima
        # 0,9 x altura por caractere para impedir texto sobre a parede.
        h = min(.22, max(.12, .82 * (x2 - x1) / (.9 * len(n))))
        result.append({"nome": n, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "h": h})
    return result


def build_assisted_model(programa: dict | None = None) -> dict:
    """Build a complete, validated-ready model from a small program request."""
    programa = deepcopy(programa or {})
    width = float(programa.get("largura_externa", 12.0))
    depth = float(programa.get("profundidade_externa", 11.0))
    thickness = float(programa.get("espessura_parede", .15))
    height = float(programa.get("pe_direito", 2.8))
    if abs(width - 12.0) > 1e-6 or abs(depth - 11.0) > 1e-6:
        raise ValueError("o primeiro template assistido exige casa externa de 12,00 x 11,00 m")
    if abs(thickness - .15) > 1e-6:
        raise ValueError("o primeiro template assistido exige parede de 0,15 m")
    if height <= 2.4 or height > 4.0:
        raise ValueError("pé-direito deve estar entre 2,40 m e 4,00 m")

    requested = programa.get("ambientes")
    if requested:
        names = [x.get("nome") if isinstance(x, dict) else x for x in requested]
        unknown = [name for name in names if name not in ROOMS]
        if unknown:
            raise ValueError("ambiente não suportado pelo template: %s" % ", ".join(map(str, unknown)))
        missing = [name for name in ROOMS if name not in names]
        if missing:
            raise ValueError("o template exige também: %s" % ", ".join(missing))

    doors = [
        (0.5, 0.0, 90.0, .90), (2.2, 5.0, 270.0, .90),
        (6.4, 5.0, 270.0, .90), (10.2, 5.0, 270.0, .70),
        (3.2, 6.2, 90.0, .90), (5.6, 6.2, 90.0, .90), (9.6, 6.2, 90.0, .90),
        (3.2, 8.6, 90.0, .90), (5.0, 2.0, 0.0, .90),
        (8.6, .9, 0.0, .90), (2.4, 6.6, 180.0, .90),
    ]
    wall_specs = [
        ((0, 0, 12, 0), [(.5, .90), (2.2, 2.0), (5.9, 1.4), (9.4, 1.2)]),
        ((0, 11, 12, 11), [(1.0, 1.2), (5.5, 2.0), (9.4, 1.5)]),
        ((0, 0, 0, 11), [(2.0, 1.4), (6.9, .8)]),
        ((12, 0, 12, 11), [(3.2, 1.0), (7.5, 2.0)]),
        ((0, 5.0, 12, 5.0), [(2.2, .90), (6.4, .90), (10.2, .70)]),
        ((0, 6.2, 12, 6.2), [(3.2, .90), (5.6, .90), (9.6, .90)]),
        ((8.6, 2.6, 12, 2.6), []), ((0, 8.6, 4.6, 8.6), [(3.2, .90)]),
        ((5.0, 0, 5.0, 5.0), [(2.0, .90)]),
        ((8.6, 0, 8.6, 5.0), [(.9, .90)]), ((8.6, 6.2, 8.6, 11), []),
        ((4.6, 6.2, 4.6, 11), []), ((2.4, 6.2, 2.4, 8.6), [(6.6, .90)]),
    ]
    walls: list[list[float]] = []
    for wall, openings in wall_specs:
        walls.extend(_split_wall(wall, openings) if openings else [list(wall)])

    model = {
        "titulo": programa.get("titulo", "PLANTA ASSISTIDA - RESIDÊNCIA UNIFAMILIAR"),
        "espessura_parede": thickness,
        "pe_direito": height,
        "terreno": (-1.5, -5.0, 13.5, 16.0),
        "paredes": walls,
        # O renderizador usa linhas de faces e vãos reais para este template;
        # não cria retângulos independentes que se sobrepõem nas junções.
        "parede_sem_sobreposicao": True,
        "ambientes": _rooms(),
        "portas": doors,
        "janelas": [
            (2.2, 0, 4.2, 0), (5.9, 0, 7.3, 0), (9.4, 0, 10.6, 0),
            (12, 3.2, 12, 4.2), (12, 7.5, 12, 9.5),
            (1.0, 11, 2.2, 11), (5.5, 11, 7.5, 11),
            (9.4, 11, 10.9, 11), (0, 2.0, 0, 3.4), (0, 6.9, 0, 7.7),
        ],
        "moveis": [
            (1.5, 1.3, 3.9, 2.1), (3.4, 3.4, 4.7, 4.6),
            (5.15, .15, 8.45, .75), (7.9, 4.0, 8.45, 4.85),
            (8.8, 1.85, 9.7, 2.45), (10.0, 1.85, 10.9, 2.45),
            (8.8, 2.8, 9.4, 3.5), (11.2, 2.8, 11.8, 3.3),
            (5.6, 9.3, 7.2, 10.85), (4.9, 10.0, 5.4, 10.5), (7.95, 6.4, 8.45, 8.0),
            (9.1, 9.3, 10.8, 10.85), (10.8, 6.5, 11.8, 7.2), (11.3, 8.3, 11.85, 10.6),
            (.25, 8.8, 1.75, 10.6), (0.2, 6.35, 1.1, 7.0),
            (0.3, 7.9, 0.9, 8.45), (1.3, 7.9, 2.1, 8.45),
        ],
        "cotas_h": [
            (0, 5, -1.0, -1.0), (5, 8.6, -1.0, -1.0),
            (8.6, 12, -1.0, -1.0), (0, 12, -2.0, -2.0),
            (0, 4.6, 12.0, 12.0), (4.6, 8.6, 12.0, 12.0),
            (8.6, 12, 12.0, 12.0), (0, 12, 13.0, 13.0),
        ],
        "cotas_v": [(12.8, 0, 6.0, 12.8), (12.8, 6.0, 11, 12.8), (13.8, 0, 11, 13.8)],
        "selo": [
            (-1.4, -5.45, "PLANTA BAIXA - RESIDÊNCIA UNIFAMILIAR", .16),
            (-1.4, -5.70, "Área útil: 120,67 m²", .16),
            (-1.4, -5.95, "Área construída: 132,00 m²", .16),
            (-1.4, -6.20, "Terreno: 15,00 x 21,00 m", .16),
            (-1.4, -6.45, "Recuos assumidos: frente/fundos 5,00 m; laterais 1,50 m", .16),
            (-1.4, -6.70, "Pé-direito: 2,80 m | Cotas em metros", .16),
        ],
        "area_pedida": programa.get("area_util_minima", 120.67),
    }
    return model
