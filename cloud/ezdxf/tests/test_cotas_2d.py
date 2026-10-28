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


def test_linhas_de_extensao_nao_sobram_nem_se_sobrepoem_no_dxf():
    """Nenhuma linha repetida nos encontros e nenhuma extensão além das cotas."""
    preview=tools_verified.planta_criar_validada(
        programa=CASA,modo="preview",template="programa_sob_medida")
    assert preview["ok"],preview
    draw=tools_verified.planta_criar_validada(
        programa=CASA,modo="desenhar",template="programa_sob_medida",
        preview_token=preview["preview_token"])
    assert draw["ok"],draw
    model=preview["modelo"]
    half=model["espessura_parede"]/2
    h_partial=model["cotas_h_2d"][0]["y_dim"]
    h_total=model["cotas_h_2d"][-1]["y_dim"]
    v_partial=model["cotas_v_2d"][0]["x_dim"]
    v_total=model["cotas_v_2d"][-1]["x_dim"]
    msp=_ensure().modelspace()
    lines=[]
    def xy(v):
        return (float(v.x),float(v.y))
    for d in msp.query("DIMENSION"):
        lines.extend((xy(e.dxf.start),xy(e.dxf.end))
                     for e in d.virtual_entities() if e.dxftype()=="LINE")
    lines.extend((xy(e.dxf.start),xy(e.dxf.end))
                 for e in msp.query("LINE[layer=='COTAS']"))
    assert len(lines)>=16
    for (x1,y1),(x2,y2) in lines:
        assert all(math.isfinite(v) for v in (x1,y1,x2,y2))
        assert min(x1,x2)>=-0.000001 and max(x1,x2)<=v_total+1e-6
        assert min(y1,y2)>=h_total-1e-6 and max(y1,y2)<=model["resumo_geometria"]["profundidade"]+1e-6
        if abs(x1-x2)<1e-7 and abs(y1-y2)>1e-7 and x1<=model["resumo_geometria"]["largura"]+1e-7:
            # Extensões verticais sobem apenas até a face externa da parede.
            assert max(y1,y2)<=-half+1e-6
        if abs(y1-y2)<1e-7 and abs(x1-x2)>1e-7 and y1>=-1e-7:
            # Extensões horizontais começam fora da face direita.
            if x1>model["resumo_geometria"]["largura"]+1e-6 and x2>model["resumo_geometria"]["largura"]+1e-6:
                assert min(x1,x2)>=model["resumo_geometria"]["largura"]+half-1e-6

    # Colinearidade geométrica, com tolerância de 10 micrômetros.
    for i,(p,q) in enumerate(lines):
        for a,b in lines[i+1:]:
            if abs(p[1]-q[1])<1e-7 and abs(a[1]-b[1])<1e-7 and abs(p[1]-a[1])<1e-7:
                overlap=min(max(p[0],q[0]),max(a[0],b[0]))-max(min(p[0],q[0]),min(a[0],b[0]))
                assert overlap<1e-5, f"cotas horizontais duplicadas: {p,q,a,b}"
            if abs(p[0]-q[0])<1e-7 and abs(a[0]-b[0])<1e-7 and abs(p[0]-a[0])<1e-7:
                overlap=min(max(p[1],q[1]),max(a[1],b[1]))-max(min(p[1],q[1]),min(a[1],b[1]))
                assert overlap<1e-5, f"cotas verticais duplicadas: {p,q,a,b}"
