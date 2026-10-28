"""Regressão do cotamento 2D no modelo, DXF e prévia MCP cloud."""
import math
import pytest

from mcp_cad_cloud.planta_gerador import gerar_modelo
from mcp_cad_cloud import tools_verified
from mcp_cad_cloud.backend import _ensure

from test_layout_compacto import CASA


def test_cadeias_de_cotas_somam_largura_e_profundidade_externas():
    model=gerar_modelo(CASA)
    h=model["cotas_h_2d"]
    v=model["cotas_v_2d"]
    assert len(h)==4 and len(v)==4
    assert len([c for c in h if c["nivel"]=="parcial"])==3
    assert len([c for c in v if c["nivel"]=="parcial"])==3
    assert sum(c["x2"]-c["x1"] for c in h[:3]) == pytest.approx(9.0)
    assert sum(c["y2"]-c["y1"] for c in v[:3]) == pytest.approx(8.6)
    assert h[-1]["x1"]==0 and h[-1]["x2"]==9.0
    assert v[-1]["y1"]==0 and v[-1]["y2"]==pytest.approx(8.6)
    assert all(c["y_dim"] < 0 for c in h)
    assert all(c["x_dim"] > 9 for c in v)


def test_cotas_internas_derivam_da_area_util_de_cada_ambiente():
    model=gerar_modelo(CASA)
    medidas={c["nome"]:c for c in model["cotas_ambientes"]}
    assert len(medidas)==len(model["ambientes"])==7
    for room in model["ambientes"]:
        c=medidas[room["nome"]]
        assert c["largura"]==pytest.approx(room["x2"]-room["x1"],abs=.0001)
        assert c["profundidade"]==pytest.approx(room["y2"]-room["y1"],abs=.0001)
        assert c["area"]==pytest.approx((room["x2"]-room["x1"])*(room["y2"]-room["y1"]),abs=.0001)
        assert all(math.isfinite(v) for v in (c["largura"],c["profundidade"],c["area"]))
        assert c["largura"]>0 and c["profundidade"]>0


def test_dxf_contem_oito_cotas_dimension_e_sete_anotacoes_uteis():
    p=tools_verified.planta_criar_validada(
        programa=CASA,modo="preview",template="programa_sob_medida")
    assert p["ok"],p
    result=tools_verified.planta_criar_validada(
        programa=CASA,modo="desenhar",template="programa_sob_medida",
        preview_token=p["preview_token"])
    assert result["ok"],result
    doc=_ensure()
    msp=doc.modelspace()
    dimensions=list(msp.query("DIMENSION"))
    assert len(dimensions)==8
    # No DXF as cotas são DIMENSION reais, associadas aos pontos de referência;
    # não substituímos cotas por textos inventados.
    generated=[entity.text for dim in dimensions for entity in dim.virtual_entities()
               if entity.dxftype()=="MTEXT"]
    assert any("9.00 m" in t for t in generated), generated
    assert any("8.60 m" in t for t in generated), generated
    room_dims=list(msp.query("TEXT[layer=='COTAS_INT']"))
    assert len(room_dims)==7
    assert any(" x " in t.dxf.text and "m" in t.dxf.text for t in room_dims)
    assert tools_verified.drawing_audit()["ok"]
    assert tools_verified.export_dxf()["ok"]


def test_templates_antigos_continuam_com_cotas_originais():
    normal=tools_verified.planta_criar_validada(modo="preview")
    assert normal["ok"],normal
    assert "cotas_h_2d" not in normal["modelo"]
    tiny=tools_verified.planta_criar_validada(
        modo="preview",programa={"template":"tiny_house_10m2"})
    assert tiny["ok"],tiny
    assert "cotas_v_2d" not in tiny["modelo"]
