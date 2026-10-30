"""Known-exact benchmarks independent of any architectural model metadata."""
import ezdxf
import pytest

from mcp_cad_cloud.quantitativos_engenharia import extrair_quantitativos_dxf
from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.backend import _ensure, reset_drawing


def _base():
    doc=ezdxf.new("R2013")
    doc.header["$INSUNITS"]=6
    for layer in ("EIXOS-PAREDES","VAOS-PORTAS","VAOS-JANELAS","PISOS"):
        doc.layers.new(layer)
    msp=doc.modelspace()
    wall=msp.add_line((0,0),(4,0),dxfattribs={"layer":"EIXOS-PAREDES"})
    door=msp.add_line((1,0),(1.9,0),dxfattribs={"layer":"VAOS-PORTAS"})
    window=msp.add_line((2,0),(3.2,0),dxfattribs={"layer":"VAOS-JANELAS"})
    floor=msp.add_lwpolyline([(0,0),(4,0),(4,3),(0,3)],close=True,
                            dxfattribs={"layer":"PISOS"})
    return doc,wall,door,window,floor


def test_exact_rectangle_wall_openings_floor_perimeter_and_no_prices():
    doc,wall,door,window,floor=_base()
    q=extrair_quantitativos_dxf(
        doc,projeto_id="BENCH-001",altura_paredes_m=3,
        espessura_paredes_m=.15,altura_portas_m=2,
        altura_janelas_m=1.2,
        aberturas_por_parede={wall.dxf.handle:[door.dxf.handle,window.dxf.handle]},
        inventario_aberturas_completo=True,
    )
    assert q["ok"],q
    assert q["resumo"]["paredes"]==1
    assert q["resumo"]["portas"]==1
    assert q["resumo"]["janelas"]==1
    assert q["resumo"]["pisos"]==1
    assert q["resumo"]["comprimento_paredes_m"]==4
    assert q["resumo"]["area_pisos_m2"]==12
    w=next(x for x in q["itens"] if x["tipo"]=="parede")
    assert w["metricas"]["area_bruta_m2"]==12
    assert w["metricas"]["area_aberturas_m2"]==pytest.approx(3.24)
    assert w["metricas"]["area_liquida_m2"]==pytest.approx(8.76)
    assert w["metricas"]["volume_geometrico_m3"]==pytest.approx(1.314)
    p=next(x for x in q["itens"] if x["tipo"]=="piso")
    assert p["metricas"]["perimetro_m"]==14
    assert p["metricas"]["area_m2"]==12
    assert all(x["id_projeto"]=="BENCH-001" and x["versao_calculo"]
               for x in q["itens"])
    assert q["integracao"]["precos"] is None
    assert q["integracao"]["bdi"] is None
    assert q["integracao"]["dependencia_obrigatoria"] is False


def test_no_wall_height_or_completeness_never_fabricates_net_volume():
    doc,wall,door,window,_=_base()
    q=extrair_quantitativos_dxf(doc)
    assert q["ok"]
    w=next(x for x in q["itens"] if x["tipo"]=="parede")
    assert w["metricas"]["comprimento_m"]==4
    assert w["metricas"]["area_bruta_m2"] is None
    assert w["metricas"]["area_liquida_m2"] is None
    assert w["metricas"]["volume_geometrico_m3"] is None
    assert w["completude"]=="DADOS_INSUFICIENTES"
    assert any("altura" in x for x in w["campos_ausentes"])
    q2=extrair_quantitativos_dxf(doc,altura_paredes_m=3,
                                espessura_paredes_m=.15)
    assert next(x for x in q2["itens"] if x["tipo"]=="parede")["metricas"]["area_liquida_m2"] is None


def test_construction_wall_axes_are_not_fake_from_double_faces():
    doc,_,_,_,_=_base()
    doc.modelspace().delete_entity(next(iter(doc.modelspace().query('LINE[layer=="EIXOS-PAREDES"]'))))
    doc.layers.new("PAREDES")
    doc.modelspace().add_line((0,0),(4,0),dxfattribs={"layer":"PAREDES"})
    doc.modelspace().add_line((0,.15),(4,.15),dxfattribs={"layer":"PAREDES"})
    q=extrair_quantitativos_dxf(doc,altura_paredes_m=3)
    assert q["resumo"]["paredes"]==0
    assert q["resumo"]["comprimento_paredes_m"]==0
    assert any("EIXOS-PAREDES" in x for x in q["pendencias"])


def test_bow_tie_floor_self_intersection_is_rejected():
    doc,*_= _base()
    p=next(iter(doc.modelspace().query('LWPOLYLINE[layer=="PISOS"]')))
    p.set_points([(0,0),(4,3),(4,0),(0,3)],format="xy")
    q=extrair_quantitativos_dxf(doc)
    assert not q["ok"]
    assert any(x["codigo"]=="PISO_CONTORNO_INVALIDO" for x in q["erros"])
    assert q["resumo"]["area_pisos_m2"]==0


def test_open_polygon_and_duplicate_wall_fails():
    doc,wall,*_=_base()
    p=next(iter(doc.modelspace().query('LWPOLYLINE[layer=="PISOS"]')))
    p.closed=False
    doc.modelspace().add_line((1,0),(2,0),dxfattribs={"layer":"EIXOS-PAREDES"})
    q=extrair_quantitativos_dxf(doc)
    assert not q["ok"]
    assert {"PISO_ABERTO","SEGMENTOS_SOBREPOSTOS"} <= {x["codigo"] for x in q["erros"]}


def test_wrong_units_and_opening_references_reject():
    doc,wall,door,window,_=_base()
    doc.header["$INSUNITS"]=4
    q=extrair_quantitativos_dxf(doc)
    assert not q["ok"] and q["status"]=="INVALIDO"
    doc.header["$INSUNITS"]=6
    q=extrair_quantitativos_dxf(doc,aberturas_por_parede={
        wall.dxf.handle:[door.dxf.handle,"ABCDEF"]},inventario_aberturas_completo=True)
    assert not q["ok"]
    assert any(x["codigo"]=="ABERTURA_REFERENCIADA_INEXISTENTE" for x in q["erros"])


def test_false_opening_association_is_rejected_even_if_inventory_complete():
    doc,wall,door,window,_=_base()
    door.dxf.start=(1,1,0)
    door.dxf.end=(1.9,1,0)
    q=extrair_quantitativos_dxf(doc,altura_paredes_m=3,
        espessura_paredes_m=.15,altura_portas_m=2,altura_janelas_m=1.2,
        aberturas_por_parede={wall.dxf.handle:[door.dxf.handle,window.dxf.handle]},
        inventario_aberturas_completo=True)
    assert not q["ok"]
    assert any(x["codigo"]=="ABERTURA_FORA_EIXO_PAREDE" for x in q["erros"])


def test_existing_quantitativo_api_keeps_counts_and_adds_structured_result():
    reset_drawing()
    response=cad.quantitativo(projeto_id="QA")
    assert response["ok"]
    assert response["entities"]==0
    assert response["by_layer"]=={}
    assert response["by_type"]=={}
    assert response["quantitativos_construtivos"]["status"]=="DADOS_INSUFICIENTES"
    assert response["quantitativos_construtivos"]["projeto_id"]=="QA"
