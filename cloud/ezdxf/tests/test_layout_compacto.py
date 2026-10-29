"""2D: arquitetura funcional mensurável, independente da qualidade de render."""
from copy import deepcopy

import pytest

from mcp_cad_cloud.planta_gerador import gerar_modelo, ErroPrograma
from mcp_cad_cloud.validar_modelo import validar
from mcp_cad_cloud import tools_verified


CASA = {
    "largura": 9.0,
    "terreno_largura": 10.0,
    "terreno_profundidade": 20.0,
    "recuo_lateral": 0.5,
    "recuo_frente": 3.0,
    "recuo_fundo": 2.0,
    "ambientes": [
        {"nome":"Sala de estar", "area":18.0},
        {"nome":"Cozinha", "area":9.0},
        {"nome":"Área de serviço", "area":5.0},
        {"nome":"Quarto 1", "area":12.0},
        {"nome":"Quarto 2", "area":10.0},
        {"nome":"Banheiro social", "area":5.0},
    ],
}


def test_solucao_compacta_2d_tem_hall_nao_corredor_longo():
    m = gerar_modelo(CASA)
    assert m["estrategia"] == "compacto_2quartos"
    assert m["resumo_geometria"]["hall_livre"] >= 1.05
    assert m["resumo_geometria"]["profundidade"] < 9.0
    hall = next(a for a in m["ambientes"] if a["nome"] == "Hall / circulação")
    assert hall["x2"]-hall["x1"] < 2.9
    assert hall["y2"]-hall["y1"] < 1.55
    assert len(m["portas"]) == 5
    assert len(m["janelas"]) == 6
    assert len(m["moveis"]) >= 10
    report = validar(m,estrito=True)
    assert report["ok"], report["problemas"]


def test_areas_de_seis_comodos_sao_iguais_ao_programa():
    m = gerar_modelo(CASA)
    for requisito in CASA["ambientes"]:
        a = next(x for x in m["ambientes"] if x["nome"] == requisito["nome"])
        livre=(a["x2"]-a["x1"])*(a["y2"]-a["y1"])
        assert livre == pytest.approx(requisito["area"], abs=.0001), (a, requisito)
        assert a["x1"] <= a["texto_x"] <= a["x2"]
        assert a["y1"] <= a["texto_y"] <= a["y2"]


def test_quadro_areas_em_m2_e_hall_em_metros_sem_ambiguidade():
    m = gerar_modelo(CASA)
    resumo = m["resumo_geometria"]
    quadro = resumo["quadro_areas_m2"]
    hall = next(x for x in m["ambientes"] if x["nome"] == "Hall / circulação")
    area_hall = (hall["x2"]-hall["x1"])*(hall["y2"]-hall["y1"])
    assert quadro["ambientes_solicitados"] == pytest.approx(59.0)
    assert quadro["circulacao_hall"] == pytest.approx(3.508, abs=.0001)
    assert quadro["circulacao_hall"] == pytest.approx(area_hall, abs=.0001)
    assert quadro["total_mapeado"] == pytest.approx(62.508)
    assert quadro["ambientes_solicitados"] + quadro["circulacao_hall"] == pytest.approx(
        quadro["total_mapeado"], abs=.0001)
    assert quadro["projecao_externa"] == pytest.approx(77.4)
    assert resumo["hall_profundidade_livre_m"] == pytest.approx(hall["y2"]-hall["y1"])
    assert resumo["area_util_total"] == pytest.approx(quadro["total_mapeado"])


def test_banheiro_e_dormitorios_acessiveis_por_hall_central():
    m=gerar_modelo(CASA)
    h = next(a for a in m["ambientes"] if "Hall" in a["nome"])
    y1,y2=h["y1"],h["y2"]
    verticais = [p for p in m["portas"] if y1 <= p[1] <= y2 and p[2] in (0,90)]
    horizontais = [p for p in m["portas"] if p[1] > y2 and p[2] in (0,90)]
    assert len(verticais) >= 2  # um quarto em cada lateral
    assert len(horizontais) >= 1  # banheiro independente


@pytest.mark.parametrize("alteracao", [
    {"largura": 8.8, "ambientes": [{"nome":"Quarto 1","area":20},{"nome":"Quarto 2","area":20},
                                  {"nome":"Sala de estar","area":18},{"nome":"Cozinha","area":9},
                                  {"nome":"Área de serviço","area":5},{"nome":"Banheiro social","area":5}]},
    {"largura":9.0, "estrategia":"compacto_2quartos",
     "ambientes":[{"nome":"Sala", "area":15}, {"nome":"Banheiro","area":4}]},
])
def test_programas_inviaveis_rejeitados_em_vez_de_desenhar(alteracao):
    p=deepcopy(CASA)
    p.update(alteracao)
    with pytest.raises(ErroPrograma):
        gerar_modelo(p)


def test_mcp_previa_compacta_token_desenho_e_dxf_real():
    preview=tools_verified.planta_criar_validada(
        programa=CASA,modo="preview",template="programa_sob_medida")
    assert preview["ok"], preview
    m=preview["modelo"]
    assert m["estrategia"] == "compacto_2quartos"
    assert preview["validacao"]["ok"]
    assert preview["resumo_geometria"]["tipo"] == "compacto_2quartos"
    result=tools_verified.planta_criar_validada(
        programa=CASA,modo="desenhar",template="programa_sob_medida",
        preview_token=preview["preview_token"])
    assert result["ok"], result
    audit=tools_verified.drawing_audit()
    assert audit["ok"], audit
    assert tools_verified.export_dxf()["ok"]


def test_generico_legado_continua_disponivel_explicitamente():
    base=deepcopy(CASA)
    base["estrategia"]="duas_faixas"
    assert gerar_modelo(base)["resumo_geometria"]["corredor_livre"] == pytest.approx(1.05)


def test_folhas_das_portas_nao_cruzam_mobiliario():
    m=gerar_modelo(CASA)
    assert m["portas_folhas"] == [90,0,180,0,90]
    from math import cos, sin, radians
    for (x,y,ang,w),angle_leaf in zip(m["portas"],m["portas_folhas"]):
        # A zona quadrada do giro (verificação conservadora) não pode
        # ser ocupada por nenhum mobiliário esquemático.
        a0,a1=sorted((x,x+w*cos(radians(angle_leaf))))
        b0,b1=sorted((y,y+w*sin(radians(angle_leaf))))
        # Incluir a faixa do arco, não apenas o traço da folha.
        if ang==0:
            sx,ex=x,x+w
            sy,ey=y,y+w
        else:
            sx,ex=x-w,x
            sy,ey=y,y+w
        for x1,y1,x2,y2 in m["moveis"]:
            assert not (min(ex,x2)-max(sx,x1)>.01 and
                        min(ey,y2)-max(sy,y1)>.01), ((x,y,ang,w), (x1,y1,x2,y2))


@pytest.mark.parametrize("corromper", [
    lambda m: m["paredes"].append([0,float("nan"),2,0]),
    lambda m: m["janelas"].append([0,1,float("inf"),1]),
    lambda m: m["ambientes"][0].update({"x1":float("nan")}),
    lambda m: m["moveis"].append([0,1,2]),
])
def test_validador_bloqueia_geometria_nao_finita_e_tuplas_incompletas(corromper):
    m=deepcopy(gerar_modelo(CASA))
    corromper(m)
    report=validar(m)
    assert report["ok"] is False
    assert report["erros"]
