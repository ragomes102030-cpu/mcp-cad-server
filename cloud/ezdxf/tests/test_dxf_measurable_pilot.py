"""Prove standalone DXF measurement entities exist and reject tampering.

The new layers are evidence of SOLID wall-axis segments and preliminary
rectangular room footprint polygons, not finished-wall/finished-floor amounts.
"""
from copy import deepcopy
import pytest
from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.backend import _ensure
from mcp_cad_cloud.auditoria_geometrica import auditar_dxf_serializado
from mcp_cad_cloud.planta_gerador import gerar_modelo
from test_layout_compacto import CASA


@pytest.fixture
def model_dxf():
    program=deepcopy(CASA)
    m=gerar_modelo(program)
    before=cad.planta_criar_validada(programa=program, template="programa_sob_medida",
                                    modo="preview")
    assert before["ok"], before
    drawn=cad.planta_criar_validada(
        programa=program, template="programa_sob_medida",
        modo="desenhar", preview_token=before["preview_token"])
    assert drawn["ok"], drawn
    return m,_ensure()


def _codes(audit):
    return {item["chave"] for item in audit.get("erros", [])}


def test_room_footprints_are_real_closed_dxf_polygons_and_match_independent_area(model_dxf):
    model,doc=model_dxf
    polys=list(doc.modelspace().query('LWPOLYLINE[layer=="PISOS"]'))
    assert len(polys)==7
    expected=sorted(round((r["x2"]-r["x1"])*(r["y2"]-r["y1"]),4)
                    for r in model["ambientes"])
    actual=sorted(round(abs(sum(
        float(a[0])*float(b[1])-float(b[0])*float(a[1])
        for a,b in zip(p.get_points("xy"),list(p.get_points("xy"))[1:]+list(p.get_points("xy"))[:1]))/2),4)
        for p in polys)
    assert all(p.closed for p in polys)
    assert actual==expected
    assert auditar_dxf_serializado(model,doc)["ok"]


def test_only_solid_wall_axis_segments_measured_not_double_face_lengths(model_dxf):
    model,doc=model_dxf
    axes=list(doc.modelspace().query('LINE[layer=="EIXOS-PAREDES"]'))
    assert len(axes)==len(model["paredes"])
    q=cad.quantitativo(projeto_id="PILOTO-CONTORNO")
    assert q["ok"],q
    geo=q["quantitativos_construtivos"]
    expected=sum(((b-a)**2+(d-c)**2)**.5 for a,c,b,d in model["paredes"])
    assert geo["resumo"]["comprimento_paredes_m"]==pytest.approx(expected,abs=1e-5)
    assert geo["resumo"]["area_pisos_m2"]==pytest.approx(
        sum((r["x2"]-r["x1"])*(r["y2"]-r["y1"]) for r in model["ambientes"]),abs=1e-5)
    for item in geo["itens"]:
        if item["tipo"]=="parede":
            assert item["metricas"]["area_liquida_m2"] is None
            assert item["metricas"]["volume_geometrico_m3"] is None
            assert item["completude"]=="DADOS_INSUFICIENTES"


def test_deleted_measurement_axis_must_block_serialized_dxf_audit(model_dxf):
    model,doc=model_dxf
    e=next(iter(doc.modelspace().query('LINE[layer=="EIXOS-PAREDES"]')))
    doc.modelspace().delete_entity(e)
    audit=auditar_dxf_serializado(model,doc)
    assert not audit["ok"]
    assert "medicao-eixos-divergentes" in _codes(audit)


def test_tampered_room_measurement_polygon_must_block_export(model_dxf):
    model,doc=model_dxf
    p=next(iter(doc.modelspace().query('LWPOLYLINE[layer=="PISOS"]')))
    pts=list(p.get_points("xy"))
    pts[1]=(pts[1][0]+.42,pts[1][1])
    p.set_points(pts,format="xy")
    audit=auditar_dxf_serializado(model,doc)
    assert not audit["ok"]
    assert "medicao-pisos-divergentes" in _codes(audit)


def test_measurement_layer_is_not_printed_and_does_not_relabel_finished_floor(model_dxf):
    _model,doc=model_dxf
    for name in ("EIXOS-PAREDES","PISOS"):
        assert name in doc.layers
        assert doc.layers.get(name).is_off()
    q=cad.quantitativo()["quantitativos_construtivos"]
    assert q["status"]=="PARCIAL"
    assert any(i["tipo"]=="piso" and i["completude"]=="DADOS_INSUFICIENTES"
               for i in q["itens"])
