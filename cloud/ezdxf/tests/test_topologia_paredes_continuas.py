"""Adversarial DXF-only verification of continuous wall spans and physical openings."""
import io
from math import hypot

import ezdxf
import pytest

from test_layout_compacto import CASA
from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.backend import _ensure
from mcp_cad_cloud.topologia_paredes import auditar_paredes_e_vaos_dxf


@pytest.fixture
def doc():
    preview = cad.planta_criar_validada(
        programa=CASA,template="programa_sob_medida",modo="preview")
    assert preview["ok"],preview
    result = cad.planta_criar_validada(
        programa=CASA,template="programa_sob_medida",
        modo="desenhar",preview_token=preview["preview_token"])
    assert result["ok"],result
    stream = io.StringIO()
    _ensure().write(stream)
    return ezdxf.read(io.StringIO(stream.getvalue()))


def _issues(result):
    return {x["codigo"] for x in result["erros"]}


def test_pilot_continuous_wall_groups_are_reconciled_from_dxf(doc):
    output=auditar_paredes_e_vaos_dxf(doc)
    assert output["ok"],output["erros"]
    assert output["resumo"]["alinhamentos"] == 10
    assert output["resumo"]["portas"] == 5
    assert output["resumo"]["janelas"] == 6
    assert output["resumo"]["vaos_sem_simbolo"] == 1
    assert output["resumo"]["vaos"] == 12
    assert output["status"] == "PARCIAL"
    for wall in output["paredes"]:
        assert wall["comprimento_bruto_m"] == pytest.approx(
            wall["comprimento_trechos_solidos_m"]+
            sum(g["largura_m"] for g in wall["vaos"]),abs=1e-5)
        assert wall["area_liquida_m2"] is None
        assert wall["volume_geometrico_m3"] is None
        assert wall["fonte"] == "DXF EIXOS-PAREDES/PORTAS/JANELAS"


def test_opening_ids_point_to_physical_dxf_entities_and_are_unique(doc):
    q=auditar_paredes_e_vaos_dxf(doc)
    physical={e.dxf.handle for e in doc.modelspace()}
    doors=[g for w in q["paredes"] for g in w["vaos"] if g["tipo"]=="PORTA"]
    windows=[g for w in q["paredes"] for g in w["vaos"] if g["tipo"]=="JANELA"]
    assert len(doors)==5 and len(windows)==6
    handles=[h for gap in doors+windows for h in gap["handles_simbolos"]]
    assert len(handles)==5*2+6*2
    assert len(set(handles))==len(handles)
    assert set(handles)<=physical
    assert all(g["largura_m"]>0 for g in doors+windows)


def test_missing_door_arc_is_detected_as_unidentified_gap(doc):
    arc=next(iter(doc.modelspace().query('ARC[layer=="PORTAS"]')))
    doc.modelspace().delete_entity(arc)
    result=auditar_paredes_e_vaos_dxf(doc)
    assert result["resumo"]["portas"]==4
    assert result["resumo"]["vaos_sem_simbolo"]==2
    assert result["status"]=="INVALIDO"
    assert "SIMBOLO_SEM_ABERTURA" in _issues(result)
    assert not result["aprovacao_arquitetonica"]


def test_door_without_a_matching_leaf_cannot_be_verified(doc):
    leaf=next(iter(doc.modelspace().query('LINE[layer=="PORTAS"]')))
    doc.modelspace().delete_entity(leaf)
    result=auditar_paredes_e_vaos_dxf(doc)
    assert not result["ok"]
    assert "FOLHA_PORTA_INCONSISTENTE" in _issues(result)


def test_ghost_door_leaf_without_arc_is_rejected(doc):
    doc.modelspace().add_line((13,13),(13.9,13),
                              dxfattribs={"layer":"PORTAS"})
    result=auditar_paredes_e_vaos_dxf(doc)
    assert not result["ok"]
    assert "SIMBOLO_SEM_ABERTURA" in _issues(result)


def test_ghost_door_arc_outside_any_wall_is_rejected(doc):
    doc.modelspace().add_arc(center=(12,12),radius=.9,start_angle=0,end_angle=90,
                             dxfattribs={"layer":"PORTAS"})
    result=auditar_paredes_e_vaos_dxf(doc)
    assert not result["ok"]
    assert "SIMBOLO_SEM_ABERTURA" in _issues(result)


def test_incomplete_glazing_pair_does_not_become_valid_window(doc):
    window=next(iter(doc.modelspace().query('LINE[layer=="JANELAS"]')))
    doc.modelspace().delete_entity(window)
    result=auditar_paredes_e_vaos_dxf(doc)
    assert not result["ok"]
    assert "JANELA_INCOMPLETA" in _issues(result)


def test_duplicate_door_symbol_rejected(doc):
    arc=next(iter(doc.modelspace().query('ARC[layer=="PORTAS"]')))
    doc.modelspace().add_arc(center=arc.dxf.center,radius=arc.dxf.radius,
                            start_angle=arc.dxf.start_angle,
                            end_angle=arc.dxf.end_angle,
                            dxfattribs={"layer":"PORTAS"})
    result=auditar_paredes_e_vaos_dxf(doc)
    assert not result["ok"]
    assert "SIMBOLOS_AMBIGUOS" in _issues(result)


def test_wrong_units_block_topological_metrage(doc):
    doc.header["$INSUNITS"]=4
    result=auditar_paredes_e_vaos_dxf(doc)
    assert result["status"]=="INVALIDO"
    assert "UNIDADES_INVALIDAS" in _issues(result)


def test_no_wall_axes_means_insufficient_evidence_not_made_up_gross_length():
    doc=ezdxf.new("R2013")
    doc.header["$INSUNITS"]=6
    doc.modelspace().add_line((0,0),(5,0),dxfattribs={"layer":"PAREDES"})
    result=auditar_paredes_e_vaos_dxf(doc)
    assert result["ok"]
    assert result["status"]=="DADOS_INSUFICIENTES"
    assert result["resumo"]["comprimento_bruto_m"]==0
    assert not result["paredes"]


def test_quantitativo_public_preserves_legacy_counts_and_exposes_topology():
    preview=cad.planta_criar_validada(
        programa=CASA,template="programa_sob_medida",modo="preview")
    assert preview["ok"]
    assert cad.planta_criar_validada(
        programa=CASA,template="programa_sob_medida",
        modo="desenhar",preview_token=preview["preview_token"])["ok"]
    q=cad.quantitativo(projeto_id="TOPOLOGIA-PILOTO")
    assert q["ok"]
    assert q["entities"]==175
    assert q["by_layer"]["EIXOS-PAREDES"]==22
    assert q["auditoria_paredes_continuas"]["resumo"]["portas"]==5
    assert q["quantitativos_construtivos"]["resumo"]["paredes"]==22


def test_gross_wall_area_does_not_deduct_or_assume_gap_heights(doc):
    result=auditar_paredes_e_vaos_dxf(
        doc,altura_paredes_m=2.8,altura_portas_m=2.1,altura_janelas_m=1.2,
        espessura_paredes_m=.15)
    assert result["ok"],result["erros"]
    assert all(x["area_bruta_m2"] is not None for x in result["paredes"])
    assert result["resumo"]["vaos_sem_simbolo"]==1
    assert all(x["volume_geometrico_m3"] is None for x in result["paredes"])
    assert any(x["area_liquida_m2"] is None for x in result["paredes"])
    assert "altura_passagens_m" in " ".join(result["pendencias"])


def test_analytic_gross_wall_and_opening_discount_from_independent_dxf():
    """4m gross, 0.9m door, 1.2m window, 3m wall: 8.76m2 net."""
    doc=ezdxf.new("R2013")
    doc.header["$INSUNITS"]=6
    for name in ("EIXOS-PAREDES","PORTAS","JANELAS"):
        doc.layers.new(name)
    ms=doc.modelspace()
    for a,b in ((0,1),(1.9,2),(3.2,4)):
        ms.add_line((a,0),(b,0),dxfattribs={"layer":"EIXOS-PAREDES"})
    ms.add_arc((1,0),.9,0,90,dxfattribs={"layer":"PORTAS"})
    ms.add_line((1,0),(1.9,0),dxfattribs={"layer":"PORTAS"})
    for y in (-.035,.035):
        ms.add_line((2,y),(3.2,y),dxfattribs={"layer":"JANELAS"})
    result=auditar_paredes_e_vaos_dxf(
        doc,altura_paredes_m=3,altura_portas_m=2,
        altura_janelas_m=1.2,espessura_paredes_m=.15)
    assert result["ok"],result["erros"]
    assert len(result["paredes"])==1
    wall=result["paredes"][0]
    assert wall["comprimento_bruto_m"]==4
    assert wall["comprimento_trechos_solidos_m"]==pytest.approx(1.9)
    assert wall["area_bruta_m2"]==12
    assert wall["area_aberturas_m2"]==pytest.approx(3.24)
    assert wall["area_liquida_m2"]==pytest.approx(8.76)
    assert wall["volume_geometrico_m3"] is None
    assert {gap["tipo"] for gap in wall["vaos"]}=={"PORTA","JANELA"}


def test_pilot_passage_height_never_inferred_from_other_door_heights(doc):
    result=auditar_paredes_e_vaos_dxf(
        doc,altura_paredes_m=2.8,altura_portas_m=2.1,
        altura_janelas_m=1.2,altura_passagens_m=2.8)
    assert result["ok"]
    passage=next(g for wall in result["paredes"] for g in wall["vaos"]
                 if g["tipo"]=="VAO_SEM_IDENTIFICACAO")
    assert passage["altura_m"] is None
    assert passage["area_m2"] is None
    assert any("altura_passagens_m" in p for p in result["pendencias"])
