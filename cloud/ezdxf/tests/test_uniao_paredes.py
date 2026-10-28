"""Regressão da união real de paredes 2D nos encontros L, T e cruzamentos.

Inspeciona a geometria CAD (não pixels de uma imagem ilustrativa).
"""
import math
import pytest

from mcp_cad_cloud.planta_assistida import wall_boundary_segments
from mcp_cad_cloud.planta_gerador import gerar_modelo
from mcp_cad_cloud import tools_verified
from mcp_cad_cloud.backend import _ensure
from test_layout_compacto import CASA


def _collinear_overlap(a,b):
    tol=1e-7
    if abs(a[1]-a[3])<tol and abs(b[1]-b[3])<tol and abs(a[1]-b[1])<tol:
        return min(max(a[0],a[2]),max(b[0],b[2])) - max(min(a[0],a[2]),min(b[0],b[2]))
    if abs(a[0]-a[2])<tol and abs(b[0]-b[2])<tol and abs(a[0]-b[0])<tol:
        return min(max(a[1],a[3]),max(b[1],b[3])) - max(min(a[1],a[3]),min(b[1],b[3]))
    return 0.


def _assert_sem_sobreposicao(segments):
    assert segments
    unique=set()
    for s in segments:
        assert len(s)==4 and all(math.isfinite(v) for v in s)
        assert math.dist(s[:2],s[2:]) > 0.000001
        assert s[0]==s[2] or s[1]==s[3]
        canonical=tuple(sorted((tuple(round(v,7) for v in s[:2]),
                                tuple(round(v,7) for v in s[2:]))))
        assert canonical not in unique, f"linha duplicada: {s}"
        unique.add(canonical)
    for i,a in enumerate(segments):
        for b in segments[i+1:]:
            assert _collinear_overlap(a,b)<1e-7, f"faces sobrepostas: {a} e {b}"


def test_uniao_em_l_fecha_canto_sem_riscos_cruzando_faces():
    segments=wall_boundary_segments([[0,0,2,0],[0,0,0,2]],.15)
    _assert_sem_sobreposicao(segments)
    # Nada de parede interna no quadrado de junção dos dois eixos.
    for x1,y1,x2,y2 in segments:
        if abs(y1-y2)<1e-8:
            assert not (abs(y1-0.075)<1e-8 and
                        max(x1,x2) > 0.0 and min(x1,x2) < 0.075)
        else:
            assert not (abs(x1-0.075)<1e-8 and
                        max(y1,y2) > 0.0 and min(y1,y2) < 0.075)


@pytest.mark.parametrize("axes", [
    [[0,0,4,0],[2,0,2,2]],
    [[0,0,4,0],[2,-2,2,2]],
    [[0,0,4,0],[4,0,4,2]],
    [[0,0,2,0],[3,0,5,0]],  # abertura mantida
])
def test_t_cruzamento_canto_e_vaos_nao_geram_faces_duplicadas(axes):
    _assert_sem_sobreposicao(wall_boundary_segments(axes,.15))


def test_tem_abertura_verdadeira_para_porta_ou_janela():
    segments=wall_boundary_segments([[0,0,1,0],[2,0,4,0]],.15)
    _assert_sem_sobreposicao(segments)
    assert not any(min(x1,x2)<1.5<max(x1,x2) and abs(y1-y2)<1e-8
                   for x1,y1,x2,y2 in segments)
    assert (1,.075,1,-.075) not in segments  # orientação não é importante


def test_contorno_planta_compacta_sem_paredes_internas_sobrepostas():
    model=gerar_modelo(CASA)
    segments=wall_boundary_segments(model["paredes"],model["espessura_parede"])
    _assert_sem_sobreposicao(segments)
    assert len(segments)>20


def test_linhas_no_dxf_iguais_ao_contorno_fisico_sem_duplicacao():
    preview=tools_verified.planta_criar_validada(programa=CASA,modo="preview",
                                                 template="programa_sob_medida")
    assert preview["ok"],preview
    result=tools_verified.planta_criar_validada(programa=CASA,modo="desenhar",
                            template="programa_sob_medida",preview_token=preview["preview_token"])
    assert result["ok"],result
    real=[(float(line.dxf.start.x),float(line.dxf.start.y),
           float(line.dxf.end.x),float(line.dxf.end.y))
          for line in _ensure().modelspace().query("LINE[layer=='PAREDES']")]
    _assert_sem_sobreposicao(real)
    expected=wall_boundary_segments(preview["modelo"]["paredes"])
    assert len(real)==len(expected)
    assert tools_verified.drawing_audit()["ok"]
