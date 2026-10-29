"""Circulation pilot: real CAD obstacles and deliberately broken drawings."""
from copy import deepcopy

import pytest

from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.backend import _ensure
from mcp_cad_cloud.auditoria_circulacao import auditar_circulacao
from mcp_cad_cloud.planta_gerador import gerar_modelo
from test_layout_compacto import CASA

BRIEF = ("Desenhe residencia terrea de dois quartos, sala e cozinha "
         "integradas, banheiro e lavanderia no terreno de 10 x 20 m.")


@pytest.fixture
def drawing():
    p=deepcopy(CASA)
    model=gerar_modelo(p)
    preview=cad.planta_criar_validada(
        programa=p, modo="preview", template="programa_sob_medida")
    assert preview["ok"],preview
    created=cad.planta_criar_validada(
        programa=p, modo="desenhar", template="programa_sob_medida",
        preview_token=preview["preview_token"])
    assert created["ok"],created
    return model,_ensure()


def _keys(report, key="erros"):
    return [x["chave"] for x in report[key]]


def test_reference_layout_connects_seven_rooms_without_critical_collision(drawing):
    model,doc=drawing
    result=auditar_circulacao(model,doc)
    assert result["ok"],result
    assert not result["erros"]
    assert result["metricas"]["entradas_detectadas"] >= 1
    assert result["metricas"]["ambientes_total"] == 7
    assert result["metricas"]["ambientes_conectados"] == 7
    assert result["metricas"]["portas_verificadas"] == 5
    assert result["metricas"]["moveis_verificados"] == 12
    assert any("nao constitui rota acessivel" in x.casefold() for x in result["limitacoes"])


def test_wall_closing_only_hall_passage_disconnects_private_rooms(drawing):
    model,doc=drawing
    model=deepcopy(model)
    model["paredes"].append([4.10,4.70,5.25,4.70])
    result=auditar_circulacao(model,doc)
    assert not result["ok"]
    assert "ambiente-inacessivel" in _keys(result)


def test_window_glass_is_not_a_walkable_opening(drawing):
    from mcp_cad_cloud.auditoria_circulacao import _blocked
    model,doc=drawing
    walls=[tuple(map(float,p)) for p in model["paredes"]]
    glazing=[(
        float(e.dxf.start.x),float(e.dxf.start.y),
        float(e.dxf.end.x),float(e.dxf.end.y))
        for e in doc.modelspace().query('LINE[layer=="JANELAS"]')]
    # A valid window is represented by two glass lines. A person must not
    # traverse their centreline as though it were a door.
    first=model["janelas"][0]
    x=(first[0]+first[2])/2
    y=(first[1]+first[3])/2
    assert _blocked(x,y,walls+glazing,[],model["espessura_parede"],0.0)


def test_room_cannot_be_reached_by_going_through_its_window(drawing):
    model,doc=drawing
    model=deepcopy(model)
    # Seal the bedroom-1 door in the simplified model. The remaining
    # bedroom window must not count as a second entrance.
    left_bedroom = next(a for a in model["ambientes"] if a["nome"]=="Quarto 1")
    ydoor=next(p[1] for p in model["portas"] if
               abs(p[0]-(left_bedroom["x2"]+.075))<.01)
    xwall=left_bedroom["x2"]+.075
    model["paredes"].append([xwall, ydoor, xwall, ydoor+.90])
    report=auditar_circulacao(model,doc)
    bedroom=next(r for r in report["metricas"]["ambientes"] if
                 r["ambiente"]=="Quarto 1")
    assert not bedroom["conectado"],report
    assert "ambiente-inacessivel" in _keys(report)


def test_entrance_blocked_by_furniture_is_rejected(drawing):
    model,doc=drawing
    # Entire front door strip blocked by a new rectangular object.
    doc.modelspace().add_lwpolyline(
        [(.42,.15),(1.48,.15),(1.48,.78),(.42,.78)],
        close=True, dxfattribs={"layer":"MOBILIARIO"})
    result=auditar_circulacao(model,doc)
    assert not result["ok"]
    assert "porta-colide-mobiliario" in _keys(result)


def test_door_swing_to_furniture_collision_detected_even_if_document_is_valid(drawing):
    model,doc=drawing
    # Small cabinet inside the bathroom door's actual counterclockwise sweep.
    arc=list(doc.modelspace().query('ARC[layer=="PORTAS"]'))[-1]
    hx=float(arc.dxf.center.x);hy=float(arc.dxf.center.y)
    doc.modelspace().add_lwpolyline(
        [(hx+.25,hy+.25),(hx+.48,hy+.25),
         (hx+.48,hy+.48),(hx+.25,hy+.48)],
        close=True, dxfattribs={"layer":"MOBILIARIO"})
    result=auditar_circulacao(model,doc)
    assert not result["ok"]
    assert "porta-colide-mobiliario" in _keys(result)


def test_doors_with_overlapping_sweep_return_warning_not_legal_failure(drawing):
    model,doc=drawing
    arc=list(doc.modelspace().query('ARC[layer=="PORTAS"]'))[-1]
    doc.modelspace().add_arc(
        center=arc.dxf.center,radius=arc.dxf.radius,
        start_angle=arc.dxf.start_angle,end_angle=arc.dxf.end_angle,
        dxfattribs={"layer":"PORTAS"})
    result=auditar_circulacao(model,doc)
    assert "giros-portas-sobrepostos" in _keys(result,"avisos")
    # Arc-count mismatch is a separate, provable model/drawing failure.
    assert "portas-incompletas" in _keys(result)


def test_missing_facade_entrance_is_rejected(drawing):
    model,doc=drawing
    model=deepcopy(model)
    model["portas"]=[p for p in model["portas"] if p[1]>.2]
    result=auditar_circulacao(model,doc)
    assert not result["ok"]
    assert "entrada-inexistente" in _keys(result)


def test_critical_flow_failure_blocks_export(monkeypatch):
    from mcp_cad_cloud import auditoria_circulacao
    monkeypatch.setattr(
        auditoria_circulacao,"auditar_circulacao",
        lambda model,doc:{
            "ok":False,
            "erros":[{"chave":"ambiente-inacessivel",
                      "onde":"Quarto 2",
                      "detalhe":"Teste de obstrucao deliberada"}],
            "avisos":[]})
    result=cad.projetar_residencia(BRIEF)
    assert not result["ok"],result
    assert result["etapa"] == "auditoria_circulacao"
    assert result["code"] == "CIRCULACAO_INTERFERENCIA_CRITICA"
    assert "arquivos" not in result


def test_one_prompt_still_produces_all_four_files_and_audit():
    result=cad.projetar_residencia(BRIEF)
    assert result["ok"],result
    assert result["auditoria_circulacao"]["ok"]
    assert result["auditoria_geometrica"]["ok"]
    assert result["auditoria"]["ok"]
    assert all(result["arquivos"].get(k) for k in
               ("dxf_url","pdf_url","png_url","zip_url"))
