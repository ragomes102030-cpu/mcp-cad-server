"""Acceptance and deliberate-mutation tests for physical DXF contract audit."""
from copy import deepcopy

import pytest

from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.auditoria_geometrica import auditar_documento, auditar_dxf_serializado
from mcp_cad_cloud.backend import _ensure
from mcp_cad_cloud.planta_gerador import gerar_modelo
from test_layout_compacto import CASA

PROMPT = (
    "Desenhe residencia terrea com dois quartos, banheiro, sala "
    "e cozinha integradas e lavanderia em terreno de 10 x 20 metros."
)


@pytest.fixture
def drawing():
    model = gerar_modelo(CASA)
    preview = cad.planta_criar_validada(
        programa=deepcopy(CASA), template="programa_sob_medida", modo="preview")
    assert preview["ok"], preview
    result = cad.planta_criar_validada(
        programa=deepcopy(CASA), template="programa_sob_medida", modo="desenhar",
        preview_token=preview["preview_token"])
    assert result["ok"], result
    return model, _ensure()


def _keys(result):
    return {e["chave"] for e in result["erros"]}


def test_real_dxf_roundtrip_matches_seven_room_model(drawing):
    model, doc = drawing
    r = auditar_dxf_serializado(model, doc)
    assert r["ok"], r
    assert r["arquivo_reaberto"] is True
    assert r["metricas"]["terreno"] == {"largura": 10.0, "profundidade": 20.0}
    assert r["metricas"]["edificacao"] == {"largura": 9.0, "profundidade": 8.6}
    assert r["metricas"]["portas_arc"] == 5
    assert r["metricas"]["janelas_line"] == 12
    assert r["metricas"]["mobiliario"] == 12
    assert r["metricas"]["dimension"] == 8


def test_lot_geometry_changed_without_updating_metadata_fails(drawing):
    model, doc = drawing
    e = next(iter(doc.modelspace().query('LWPOLYLINE[layer=="TERRENO"]')))
    coords = list(e.get_points("xy"))
    e.set_points([(x + (1.0 if x > 0 else 0.0), y) for x, y in coords], format="xy")
    r = auditar_dxf_serializado(model, doc)
    assert not r["ok"]
    assert "terreno-dimensoes" in _keys(r)


def test_lot_not_closed_fails(drawing):
    model, doc = drawing
    e = next(iter(doc.modelspace().query('LWPOLYLINE[layer=="TERRENO"]')))
    e.closed = False
    assert "terreno-dimensoes" in _keys(auditar_documento(model, doc))


def test_wall_deleted_after_model_validation_fails(drawing):
    model, doc = drawing
    ent = next(iter(doc.modelspace().query('LINE[layer=="PAREDES"]')))
    doc.modelspace().delete_entity(ent)
    assert "paredes-divergentes" in _keys(auditar_documento(model, doc))


def test_duplicate_wall_face_fails(drawing):
    model, doc = drawing
    ent = next(iter(doc.modelspace().query('LINE[layer=="PAREDES"]')))
    doc.modelspace().add_line(ent.dxf.start, ent.dxf.end, dxfattribs={"layer": "PAREDES"})
    assert "paredes-divergentes" in _keys(auditar_documento(model, doc))


def test_closing_sala_cozinha_opening_fails(drawing):
    model, doc = drawing
    doc.modelspace().add_line((4.2, 0.25), (4.2, 2.6), dxfattribs={"layer": "PAREDES"})
    r = auditar_documento(model, doc)
    assert not r["ok"]
    assert "paredes-divergentes" in _keys(r)
    assert "sala-cozinha-bloqueada" in _keys(r)


def test_missing_door_arc_and_leaf_fails(drawing):
    model, doc = drawing
    msp = doc.modelspace()
    msp.delete_entity(next(iter(msp.query('ARC[layer=="PORTAS"]'))))
    msp.delete_entity(next(iter(msp.query('LINE[layer=="PORTAS"]'))))
    keys = _keys(auditar_documento(model, doc))
    assert "portas-arcos" in keys
    assert "portas-folhas" in keys


def test_window_shifted_fails(drawing):
    model, doc = drawing
    e = next(iter(doc.modelspace().query('LINE[layer=="JANELAS"]')))
    e.dxf.start = (float(e.dxf.start.x)+.2, float(e.dxf.start.y), 0)
    assert "janelas-divergentes" in _keys(auditar_documento(model, doc))


def test_furniture_missing_fails(drawing):
    model, doc = drawing
    msp=doc.modelspace()
    msp.delete_entity(next(iter(msp.query('LWPOLYLINE[layer=="MOBILIARIO"]'))))
    assert "mobiliario-divergente" in _keys(auditar_documento(model, doc))


def test_dimension_wrong_extension_point_fails(drawing):
    model, doc = drawing
    ent = next(iter(doc.modelspace().query('DIMENSION[layer=="COTAS"]')))
    origin = ent.dxf.defpoint3
    ent.dxf.defpoint3 = (origin.x+0.33, origin.y, origin.z)
    assert "cotas-divergentes" in _keys(auditar_documento(model, doc))


def test_wrong_units_fails(drawing):
    model, doc = drawing
    doc.header["$INSUNITS"] = 4
    assert "unidades-incorretas" in _keys(auditar_documento(model, doc))


def test_generated_pipeline_surfaces_geometry_and_fails_closed(monkeypatch):
    result = cad.projetar_residencia(PROMPT)
    assert result["ok"], result
    assert result["auditoria_geometrica"]["ok"]
    assert result["auditoria_geometrica"]["arquivo_reaberto"]

    from mcp_cad_cloud import auditoria_geometrica
    monkeypatch.setattr(
        auditoria_geometrica, "auditar_dxf_serializado",
        lambda _model, _doc: {"ok": False,
                              "erros": [{"chave": "terreno-dimensoes",
                                         "detalhe": "Teste de falha intencional"}]})
    rejected = cad.projetar_residencia(PROMPT)
    assert rejected["ok"] is False
    assert rejected["etapa"] == "auditoria_geometrica"
    assert rejected["code"] == "CONTRATO_GEOMETRICO_VIOLADO"
    assert "arquivos" not in rejected


def test_furniture_bow_tie_same_corners_is_rejected(drawing):
    """Same four corners must not let a self-intersecting polyline pass."""
    model, doc = drawing
    ent = next(iter(doc.modelspace().query('LWPOLYLINE[layer=="MOBILIARIO"]')))
    points = list(ent.get_points("xy"))
    assert len(points) == 4
    ent.set_points([points[i] for i in (0, 2, 1, 3)], format="xy")
    result = auditar_dxf_serializado(model, doc)
    assert not result["ok"]
    assert "mobiliario-contorno-invalido" in _keys(result)


def test_unexpected_furniture_entity_is_rejected(drawing):
    model, doc = drawing
    doc.modelspace().add_line((1.1, 1.2), (1.7, 1.2),
                              dxfattribs={"layer": "MOBILIARIO"})
    result = auditar_dxf_serializado(model, doc)
    assert not result["ok"]
    assert "mobiliario-tipo" in _keys(result)


def test_furniture_duplicate_vertex_is_rejected(drawing):
    model, doc = drawing
    ent = next(iter(doc.modelspace().query('LWPOLYLINE[layer=="MOBILIARIO"]')))
    points = list(ent.get_points("xy"))
    points[2] = points[1]
    ent.set_points(points, format="xy")
    result = auditar_documento(model, doc)
    assert not result["ok"]
    assert "mobiliario-formato" in _keys(result)


def test_existing_wall_edges_have_no_independent_topology_errors(drawing):
    from mcp_cad_cloud.auditoria_geometrica import _auditar_arestas_paredes
    _, doc = drawing
    wall_lines = list(doc.modelspace().query('LINE[layer=="PAREDES"]'))
    assert wall_lines
    assert _auditar_arestas_paredes(wall_lines) == []


def test_partially_overlapping_wall_edge_rejected_by_independent_check(drawing):
    model, doc = drawing
    lines = list(doc.modelspace().query('LINE[layer=="PAREDES"]'))
    ent = next(e for e in lines if
               abs(e.dxf.end.x - e.dxf.start.x) > 0.4 and
               abs(e.dxf.end.y - e.dxf.start.y) < 1e-8)
    a, b = ent.dxf.start, ent.dxf.end
    doc.modelspace().add_line(
        (a.x * .75 + b.x * .25, a.y),
        (a.x * .25 + b.x * .75, b.y),
        dxfattribs={"layer": "PAREDES"},
    )
    result = auditar_dxf_serializado(model, doc)
    assert not result["ok"]
    assert "paredes-arestas-sobrepostas" in _keys(result)


def test_diagonal_and_zero_length_wall_edges_rejected(drawing):
    model, doc = drawing
    msp = doc.modelspace()
    msp.add_line((0.3, 0.4), (0.5, 0.7),
                 dxfattribs={"layer": "PAREDES"})
    msp.add_line((0.6, 0.6), (0.6, 0.6),
                 dxfattribs={"layer": "PAREDES"})
    result = auditar_documento(model, doc)
    assert not result["ok"]
    assert "parede-segmento-nao-ortogonal" in _keys(result)
    assert "parede-segmento-degenerado" in _keys(result)
