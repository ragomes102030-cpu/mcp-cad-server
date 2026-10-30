"""Five distinct compact variants retaining independent DXF geometry/circulation gates."""
from copy import deepcopy
import pytest
from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.backend import _ensure
from mcp_cad_cloud.planta_gerador import gerar_modelo
from mcp_cad_cloud.auditoria_geometrica import auditar_dxf_serializado
from mcp_cad_cloud.auditoria_circulacao import auditar_circulacao
from mcp_cad_cloud.camadas_medicao import auditar_evidencias_de_medicao
from tools.plant_lab.scenarios import VALID_SCENARIOS


@pytest.mark.parametrize("index",(0,6,12,18,24))
def test_five_supported_width_variants_still_pass_geometric_and_circulation_gates(index):
    case=deepcopy(VALID_SCENARIOS[index])
    program=case["program"]
    model=gerar_modelo(program)
    preview=cad.planta_criar_validada(
        programa=program,template="programa_sob_medida",modo="preview")
    assert preview["ok"],(case["id"],preview)
    draw=cad.planta_criar_validada(
        programa=program,template="programa_sob_medida",
        modo="desenhar",preview_token=preview["preview_token"])
    assert draw["ok"],(case["id"],draw)
    physical=auditar_dxf_serializado(model,_ensure())
    circulation=auditar_circulacao(model,_ensure())
    assert physical["ok"],(case["id"],physical["erros"])
    assert circulation["ok"],(case["id"],circulation["erros"])
    assert auditar_evidencias_de_medicao(model,_ensure())==[]
    quantitative=cad.quantitativo(projeto_id="BENCH-"+case["id"])
    assert quantitative["ok"],quantitative
    q=quantitative["quantitativos_construtivos"]
    assert q["resumo"]["paredes"]==len(model["paredes"])
    assert q["resumo"]["pisos"]==len(model["ambientes"])
    assert q["resumo"]["area_pisos_m2"]==pytest.approx(
        sum((r["x2"]-r["x1"])*(r["y2"]-r["y1"]) for r in model["ambientes"]),abs=1e-4)
    assert q["status"]=="PARCIAL"
    assert all(x["metricas"]["volume_geometrico_m3"] is None
               for x in q["itens"] if x["tipo"]=="parede")


def test_independent_auditor_rejects_axes_if_physical_wall_faces_deleted():
    case=deepcopy(VALID_SCENARIOS[0])
    program=case["program"]
    model=gerar_modelo(program)
    preview=cad.planta_criar_validada(
        programa=program,template="programa_sob_medida",modo="preview")
    assert preview["ok"]
    assert cad.planta_criar_validada(
        programa=program,template="programa_sob_medida",modo="desenhar",
        preview_token=preview["preview_token"])["ok"]
    msp=_ensure().modelspace()
    assert auditar_evidencias_de_medicao(model,_ensure())==[]
    for ent in list(msp.query('LINE[layer=="PAREDES"]')):
        msp.delete_entity(ent)
    errors=auditar_evidencias_de_medicao(model,_ensure())
    assert "medicao-eixos-sem-suporte-fisico" in {x["chave"] for x in errors}
