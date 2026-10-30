"""Auditoria geometrica do arquivo DXF contra o contrato da planta compacta.

Diferente de ezdxf.audit(), le as ENTIDADES reais de um DXF serializado,
sem confiar em contagens ou resumos declarados pelo gerador.
Escopo: planta compacta, ortogonal, sem certificacao arquitetonica/normativa.
"""
from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import tempfile

import ezdxf


PRECISION = 4
TOL = 0.002


def _point(v):
    return (round(float(v[0]), PRECISION), round(float(v[1]), PRECISION))


def _segment(a, b):
    return tuple(sorted((_point(a), _point(b))))


def _wall(p):
    return _segment(p[:2], p[2:])


def _keys(values):
    return Counter(values)


def _diff(chave, esperados, reais, erros):
    absent = esperados - reais
    extra = reais - esperados
    if absent or extra:
        erros.append({
            "chave": chave,
            "detalhe": "Entidades diferentes do contrato geometrico",
            "ausentes": sum(absent.values()),
            "extras": sum(extra.values()),
        })


def _auditar_arestas_paredes(entities, tol=1e-7):
    """Independent line-geometry checks; does not call the wall generator.

    In the supported orthogonal pilot, visible wall boundary LINEs may touch
    at endpoints but must never have positive-length collinear overlap.
    """
    issues = []
    horizontal, vertical = {}, {}
    for ent in entities:
        start, end = _point(ent.dxf.start), _point(ent.dxf.end)
        x1, y1 = start
        x2, y2 = end
        if math.hypot(x2 - x1, y2 - y1) <= tol:
            issues.append({"chave": "parede-segmento-degenerado",
                           "handle": ent.dxf.handle})
        elif abs(y1 - y2) <= tol:
            horizontal.setdefault(round(y1, PRECISION), []).append(
                (min(x1, x2), max(x1, x2), ent.dxf.handle))
        elif abs(x1 - x2) <= tol:
            vertical.setdefault(round(x1, PRECISION), []).append(
                (min(y1, y2), max(y1, y2), ent.dxf.handle))
        else:
            issues.append({"chave": "parede-segmento-nao-ortogonal",
                           "handle": ent.dxf.handle})

    # Compare intervals on each shared ordinate. Strictly positive
    # intersection is invalid; touching endpoints is deliberately allowed.
    for groups in (horizontal, vertical):
        for ordinate, segments in groups.items():
            segments.sort()
            for index, (lo, hi, handle) in enumerate(segments):
                for other_lo, other_hi, other_handle in segments[index + 1:]:
                    if other_lo >= hi - tol:
                        break
                    if min(hi, other_hi) - max(lo, other_lo) > tol:
                        issues.append({"chave": "paredes-arestas-sobrepostas",
                                       "handles": [handle, other_handle],
                                       "ordenada": ordinate})
    return issues


def _rooms(model):
    rooms = model.get("ambientes", [])
    living = next((a for a in rooms if "sala" in a["nome"].casefold()), None)
    kitchen = next((a for a in rooms if "cozinha" in a["nome"].casefold()), None)
    return living, kitchen


def auditar_documento(model: dict, doc) -> dict:
    """Check the physical DXF drawing; errors are explicit and machine-readable."""
    erros = []
    msp = doc.modelspace()
    if doc.header.get("$INSUNITS", 0) != 6:
        erros.append({"chave": "unidades-incorretas",
                      "detalhe": "Arquivo DXF deve usar metros ($INSUNITS=6)"})

    # TERRENO: exact real polyline vertices, not the metadata or drawing label.
    lot = tuple(float(v) for v in model["terreno"])
    expected_corners = _keys(_point(p) for p in (
        (lot[0], lot[1]), (lot[2], lot[1]),
        (lot[2], lot[3]), (lot[0], lot[3])))
    lot_polys = list(msp.query('LWPOLYLINE[layer=="TERRENO"]'))
    other_lot = [e for e in msp if e.dxf.layer == "TERRENO" and e.dxftype() != "LWPOLYLINE"]
    if len(lot_polys) != 1 or other_lot:
        erros.append({"chave": "terreno-entidades",
                      "detalhe": "Terreno exige uma polilinha fechada com quatro vertices"})
    else:
        poly = lot_polys[0]
        vertices = list(poly.get_points("xy"))
        if not poly.closed or len(vertices) != 4 or _keys(_point(p) for p in vertices) != expected_corners:
            erros.append({"chave": "terreno-dimensoes",
                          "detalhe": "Vertices reais do terreno divergem do lote informado"})
    lote_medidas = {
        "largura": round(lot[2] - lot[0], 4),
        "profundidade": round(lot[3] - lot[1], 4),
    }

    # PAREDES: compare the complete visible face network, not just counts.
    from mcp_cad_cloud.planta_assistida import wall_boundary_segments
    expected_walls = _keys(_wall(p) for p in
                           wall_boundary_segments(model["paredes"], model["espessura_parede"]))
    actual_wall_entities = list(msp.query('LINE[layer=="PAREDES"]'))
    others = [e for e in msp if e.dxf.layer == "PAREDES" and e.dxftype() != "LINE"]
    if others:
        erros.append({"chave": "paredes-tipo",
                      "detalhe": "Layer PAREDES deve conter somente LINE"})
    actual_walls = _keys(_segment(e.dxf.start, e.dxf.end) for e in actual_wall_entities)
    _diff("paredes-divergentes", expected_walls, actual_walls, erros)
    erros.extend(_auditar_arestas_paredes(actual_wall_entities))
    # Independent evidence check reads the actual physical PAREDES faces
    # and measurable DXF entities, never the face generator helper.
    from mcp_cad_cloud.camadas_medicao import auditar_evidencias_de_medicao
    erros.extend(auditar_evidencias_de_medicao(model, doc))
    resumo = model.get("resumo_geometria") or {}
    building_dims = None
    if actual_wall_entities:
        xs = [float(v) for e in actual_wall_entities for v in (e.dxf.start.x, e.dxf.end.x)]
        ys = [float(v) for e in actual_wall_entities for v in (e.dxf.start.y, e.dxf.end.y)]
        building_dims = (max(xs)-min(xs), max(ys)-min(ys))
        if resumo and (abs(building_dims[0] - float(resumo["largura"])) > TOL or
                       abs(building_dims[1] - float(resumo["profundidade"])) > TOL or
                       abs(building_dims[0]*building_dims[1] -
                           float(resumo["area_construida"])) > 0.03):
            erros.append({"chave": "projecao-divergente",
                          "detalhe": "Projecao medida nas paredes diverge do modelo"})
        # The footprint must remain inside the real terrain polygon.
        if xs and (min(xs) < lot[0]-TOL or max(xs) > lot[2]+TOL or
                   min(ys) < lot[1]-TOL or max(ys) > lot[3]+TOL):
            erros.append({"chave": "edificacao-fora-terreno",
                          "detalhe": "Contorno das paredes ultrapassa o lote"})

    # PORTAS: arcs and actual leaf LINEs must match their hinges and widths.
    expected_arcs = _keys((
        _point((p[0], p[1])), round(float(p[3]), PRECISION),
        round(float(p[2]) % 360, PRECISION),
        round(float((p[2]+90) % 360), PRECISION))
        for p in model["portas"])
    actual_arcs = _keys((
        _point(e.dxf.center), round(float(e.dxf.radius), PRECISION),
        round(float(e.dxf.start_angle) % 360, PRECISION),
        round(float(e.dxf.end_angle) % 360, PRECISION))
        for e in msp.query('ARC[layer=="PORTAS"]'))
    _diff("portas-arcos", expected_arcs, actual_arcs, erros)
    leaves = model.get("portas_folhas", [])
    expected_leaves = _keys(_segment(
        (p[0], p[1]),
        (p[0] + p[3]*math.cos(math.radians(leaves[i] if i < len(leaves) else p[2])),
         p[1] + p[3]*math.sin(math.radians(leaves[i] if i < len(leaves) else p[2]))))
        for i, p in enumerate(model["portas"]))
    real_leaves = _keys(_segment(e.dxf.start, e.dxf.end)
                        for e in msp.query('LINE[layer=="PORTAS"]'))
    _diff("portas-folhas", expected_leaves, real_leaves, erros)

    # JANELAS: verify each of the two physical glass lines, not only entity count.
    offset = float(model["espessura_parede"]) / 4
    glazing = []
    for a, b, c, d in model["janelas"]:
        if abs(d-b) < 1e-9:
            glazing.extend([
                _segment((a, b-offset), (c, d-offset)),
                _segment((a, b+offset), (c, d+offset)),
            ])
        else:
            glazing.extend([
                _segment((a-offset, b), (c-offset, d)),
                _segment((a+offset, b), (c+offset, d)),
            ])
    actual_windows = _keys(_segment(e.dxf.start, e.dxf.end)
                           for e in msp.query('LINE[layer=="JANELAS"]'))
    _diff("janelas-divergentes", _keys(glazing), actual_windows, erros)

    # MOBILIARIO: validate the four physical vertices of each closed polyline.
    expected_furniture = _keys(tuple(sorted(_point(p) for p in (
        (x1, y1), (x2, y1), (x2, y2), (x1, y2))))
        for x1, y1, x2, y2 in model["moveis"])
    furniture = list(msp.query('LWPOLYLINE[layer=="MOBILIARIO"]'))
    actual_furniture = Counter()
    for ent in furniture:
        points = [_point(v) for v in ent.get_points("xy")]
        if not ent.closed or len(points) != 4 or len(set(points)) != 4:
            erros.append({"chave": "mobiliario-formato",
                          "detalhe": "Mobiliario exige quatro vertices distintos e polilinha fechada"})
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)
        canonical = ((x1, y1), (x2, y1), (x2, y2), (x1, y2))
        expected_edges = Counter(_segment(canonical[i], canonical[(i + 1) % 4])
                                 for i in range(4))
        actual_edges = Counter(_segment(points[i], points[(i + 1) % 4])
                               for i in range(4))
        if x2 <= x1 or y2 <= y1 or actual_edges != expected_edges:
            erros.append({"chave": "mobiliario-contorno-invalido",
                          "detalhe": "Arestas cruzadas, degeneradas ou nao ortogonais no mobiliario",
                          "handle": ent.dxf.handle})
            continue
        actual_furniture[tuple(sorted(points))] += 1
    other_furniture = [e for e in msp if e.dxf.layer == "MOBILIARIO" and
                       e.dxftype() != "LWPOLYLINE"]
    if other_furniture:
        erros.append({"chave": "mobiliario-tipo",
                      "detalhe": "Entidades inesperadas na camada MOBILIARIO"})
    _diff("mobiliario-divergente", expected_furniture, actual_furniture, erros)

    # COTAS: compare actual DIMENSION extension origins with model endpoints.
    def dimension_pair(p, q):
        return _segment(p, q)
    expected_dims = _keys([
        dimension_pair((c["x1"], c["y_ref"]), (c["x2"], c["y_ref"]))
        for c in model.get("cotas_h_2d", [])
    ] + [
        dimension_pair((c["x_ref"], c["y1"]), (c["x_ref"], c["y2"]))
        for c in model.get("cotas_v_2d", [])
    ])
    dimensions = list(msp.query('DIMENSION[layer=="COTAS"]'))
    actual_dims = _keys(dimension_pair(e.dxf.defpoint2, e.dxf.defpoint3)
                        for e in dimensions)
    _diff("cotas-divergentes", expected_dims, actual_dims, erros)
    if len(dimensions) != sum(expected_dims.values()):
        erros.append({"chave": "cotas-quantidade",
                      "detalhe": "Faltam ou sobram entidades DIMENSION"})
    # Internal dimension labels are physical entities, not only a summary field.
    dim_labels = list(msp.query('TEXT[layer=="COTAS_INT"]'))
    if len(dim_labels) != len(model.get("cotas_ambientes", [])):
        erros.append({"chave": "cotas-internas",
                      "detalhe": "Numero de anotacoes de dimensoes internas divergente"})

    # Simple, narrow test of open connection between living room and kitchen.
    # This is NOT a complete accessibility or furniture clearance audit.
    sala, cozinha = _rooms(model)
    if sala is None or cozinha is None:
        erros.append({"chave": "integracao-sem-ambientes",
                      "detalhe": "Sala e cozinha nao foram identificadas"})
    else:
        lo = max(float(sala["y1"]), float(cozinha["y1"]))
        hi = min(float(sala["y2"]), float(cozinha["y2"]))
        if hi-lo < 0.6:
            erros.append({"chave": "integracao-sem-sobreposicao",
                          "detalhe": "Sala e cozinha nao possuem faixa aberta comum"})
        else:
            # A closed vertical wall across the entire shared passage blocks integration.
            xa = min(float(sala["x2"]), float(cozinha["x1"])) - 0.15
            xb = max(float(sala["x2"]), float(cozinha["x1"])) + 0.15
            cuts = []
            for e in actual_wall_entities:
                x1, y1 = _point(e.dxf.start)
                x2, y2 = _point(e.dxf.end)
                if abs(x1-x2) < TOL and xa <= x1 <= xb:
                    cuts.append((min(y1, y2), max(y1, y2)))
            # A set of disjoint segments could jointly close the opening.
            # The full passage is blocked only if every sampled y intersects.
            samples = [lo+(hi-lo)*f for f in (0.25, 0.5, 0.75)]
            if all(any(a-TOL <= y <= b+TOL for a,b in cuts) for y in samples):
                erros.append({"chave": "sala-cozinha-bloqueada",
                              "detalhe": "Parede vertical bloqueia a abertura entre sala e cozinha"})

    return {
        "ok": not erros,
        "tipo": "comparacao_modelo_dxf",
        "escopo": "planta_compacta_geometria_sem_aprovacao_normativa",
        "erros": erros,
        "metricas": {
            "terreno": lote_medidas,
            "edificacao": None if building_dims is None else {
                "largura": round(building_dims[0], 4),
                "profundidade": round(building_dims[1], 4),
            },
            "paredes_line": len(actual_wall_entities),
            "portas_arc": sum(actual_arcs.values()),
            "janelas_line": sum(actual_windows.values()),
            "mobiliario": len(furniture),
            "dimension": len(dimensions),
        },
        "limitacoes": [
            "Comparacao baseada no mesmo algoritmo de extracao de faces das paredes; "
            "falhas compartilhadas entre modelo e gerador exigem testes adicionais.",
            "Nao certifica acessibilidade, ventilacao, iluminacao, recuos legais "
            "ou qualidade funcional de projeto.",
        ],
    }


def auditar_dxf_serializado(model: dict, doc) -> dict:
    """Persist real bytes and reopen via ezdxf before auditing actual entities."""
    with tempfile.TemporaryDirectory(prefix="cad_geom_") as tmp:
        path = Path(tmp) / "planta_auditada.dxf"
        doc.saveas(path)
        reopened = ezdxf.readfile(path)
        result = auditar_documento(model, reopened)
        file_audit = reopened.audit()
        if file_audit.has_errors:
            result["ok"] = False
            result["erros"].append({
                "chave": "dxf-integridade",
                "detalhe": f"Arquivo DXF reaberto possui {len(file_audit.errors)} erros",
            })
        result["arquivo_reaberto"] = True
        return result
