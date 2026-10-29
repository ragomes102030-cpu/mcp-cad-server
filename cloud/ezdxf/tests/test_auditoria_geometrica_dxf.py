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
