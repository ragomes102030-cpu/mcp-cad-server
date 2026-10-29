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
    doors = result["metricas"]["portas"]
    assert [d["id"] for d in doors] == ["P01","P02","P03","P04","P05"]
    assert [d["vao_nominal_m"] for d in doors] == pytest.approx([.90,.90,.90,.90,.80])
    assert not any(d["colisao_mobiliario_detectada"] for d in doors)
    assert all(isinstance(d["giros_sobrepostos_com"], list) for d in doors)
    assert all(len(d["pivo_m"]) == 2 for d in doors)
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


def test_social_integration_measured_across_real_opening(drawing):
    model, doc = drawing
    result = auditar_circulacao(model, doc)
    integ = result["metricas"]["integracao_sala_cozinha"]
    assert integ["ok"], integ
    assert integ["verificado"]
    assert integ["largura_abertura_estimada_m"] >= 0.80
    assert len(integ["ponto_passagem_m"]) == 2


def test_compact_layout_with_offset_room_zones_has_verified_social_connection():
    p = deepcopy(CASA)
    p.update(largura=8.7, terreno_largura=9.9, terreno_profundidade=13.2,
             recuo_lateral=.4, recuo_frente=2.0, recuo_fundo=1.0)
    areas = (16.0, 8.0, 4.5, 11.0, 10.0, 5.0)
    for room, area in zip(p["ambientes"], areas):
        room["area"] = area
    model = gerar_modelo(p)
    preview = cad.planta_criar_validada(
        programa=p, modo="preview", template="programa_sob_medida")
    assert preview["ok"], preview
    created = cad.planta_criar_validada(
        programa=p, modo="desenhar", template="programa_sob_medida",
        preview_token=preview["preview_token"])
    assert created["ok"], created

    integration = auditar_circulacao(model, _ensure())["metricas"][
        "integracao_sala_cozinha"]
    assert integration["ok"], integration
    assert integration["verificado"], integration
    assert integration["largura_abertura_estimada_m"] >= .6


def test_compact_layout_keeps_service_approach_clear_of_kitchen_furniture():
    p = deepcopy(CASA)
    p.update(largura=8.7, terreno_largura=9.9, terreno_profundidade=13.2,
             recuo_lateral=.4, recuo_frente=2.0, recuo_fundo=1.0)
    areas = (16.0, 8.0, 4.5, 11.0, 10.0, 5.0)
    for room, area in zip(p["ambientes"], areas):
        room["area"] = area
    model = gerar_modelo(p)
    preview = cad.planta_criar_validada(
        programa=p, modo="preview", template="programa_sob_medida")
    assert preview["ok"], preview
    created = cad.planta_criar_validada(
        programa=p, modo="desenhar", template="programa_sob_medida",
        preview_token=preview["preview_token"])
    assert created["ok"], created

    result = auditar_circulacao(model, _ensure())
    service = next(row for row in result["metricas"]["diagnostico_passagens"]["larguras"]
                   if row["ambiente"] == "Área de serviço")
    assert service["largura_estimativa_m"] >= .5, service
    assert not any(warning["chave"] == "passagem-estreita-estimada"
                   and warning["onde"] == "Área de serviço"
                   for warning in result["avisos"]), result["avisos"]


def test_wall_closing_social_integration_fails_even_if_room_names_unchanged(drawing):
    model, doc = drawing
    model = deepcopy(model)
    sala=next(a for a in model["ambientes"] if "Sala" in a["nome"])
    cozinha=next(a for a in model["ambientes"] if "Cozinha" in a["nome"])
    x=(sala["x2"]+cozinha["x1"])/2
    y1=max(sala["y1"],cozinha["y1"])
    y2=min(sala["y2"],cozinha["y2"])
    model["paredes"].append([x,y1-.20,x,y2+.20])
    result=auditar_circulacao(model,doc)
    integration=result["metricas"]["integracao_sala_cozinha"]
    assert not integration["ok"], result
    assert integration["verificado"]
    assert integration["largura_abertura_estimada_m"] == 0.0
    assert "sala-cozinha-integracao-nao-comprovada" in _keys(result)


def test_narrow_laundry_has_bottleneck_coordinate_and_nearby_obstacles(drawing):
    model, doc=drawing
    report=auditar_circulacao(model,doc)
    assert report["ok"],report
    detail=report["metricas"]["diagnostico_passagens"]
    assert detail["grade_m"] == .10
    assert detail["incerteza_quantizacao_aproximada_m"] >= .10
    assert len(detail["larguras"]) == 7
    entry=next(x for x in detail["larguras"]
               if "serviço" in x["ambiente"].casefold())
    assert entry["largura_estimativa_m"] >= .5, entry
    assert len(entry["ponto_critico_m"]) == 2
    assert entry["obstaculos_proximos"]
    assert all(o["id"] for o in entry["obstaculos_proximos"])


def test_narrowing_a_route_with_furniture_reduces_reported_width(drawing):
    model,doc=drawing
    from mcp_cad_cloud.auditoria_circulacao import _walk_grid,_reach,_entrance_seeds
    from mcp_cad_cloud.diagnostico_passagens import diagnosticar_larguras
    t=model["espessura_parede"]
    w=model["resumo_geometria"]["largura"]
    h=model["resumo_geometria"]["profundidade"]
    walls=model["paredes"] + [
        (float(e.dxf.start.x),float(e.dxf.start.y),
         float(e.dxf.end.x),float(e.dxf.end.y))
        for e in doc.modelspace().query('LINE[layer=="JANELAS"]')]
    def measure():
        furniture=[
            (min(p[0] for p in e.get_points("xy")),
             min(p[1] for p in e.get_points("xy")),
             max(p[0] for p in e.get_points("xy")),
             max(p[1] for p in e.get_points("xy")))
            for e in doc.modelspace().query('LWPOLYLINE[layer=="MOBILIARIO"]')]
        free=_walk_grid(w,h,walls,furniture,t,0.0)
        seen=_reach(free,[c for _,c in _entrance_seeds(model,free)])
        rows=diagnosticar_larguras(model,doc,free,seen)["larguras"]
        return next(x["largura_estimativa_m"] for x in rows
                    if x["ambiente"]=="Área de serviço")
    before=measure()
    # Additional fixture occupies the clear centre of the service zone.
    doc.modelspace().add_lwpolyline(
        [(7.65,1.95),(8.55,1.95),(8.55,2.40),(7.65,2.40)],
        close=True,dxfattribs={"layer":"MOBILIARIO"})
    after=measure()
    assert after is None or after <= before, (before,after)


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
    report_doors = result["metricas"]["portas"]
    assert any(d["colisao_mobiliario_detectada"] and
               d["moveis_interferentes"] for d in report_doors)


def test_doors_with_overlapping_sweep_return_warning_not_legal_failure(drawing):
    model,doc=drawing
    arc=list(doc.modelspace().query('ARC[layer=="PORTAS"]'))[-1]
    doc.modelspace().add_arc(
        center=arc.dxf.center,radius=arc.dxf.radius,
        start_angle=arc.dxf.start_angle,end_angle=arc.dxf.end_angle,
        dxfattribs={"layer":"PORTAS"})
    result=auditar_circulacao(model,doc)
    assert "giros-portas-sobrepostos" in _keys(result,"avisos")
    assert "P06" in result["metricas"]["portas"][4]["giros_sobrepostos_com"]
    assert "P05" in result["metricas"]["portas"][5]["giros_sobrepostos_com"]
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
    areas=result["quadro_areas_m2"]
    assert areas["ambientes_solicitados"]+areas["circulacao_hall"] == pytest.approx(
        areas["total_mapeado"], abs=.0001)
    assert len(result["auditoria_circulacao"]["metricas"]["portas"]) == 5
    assert result["auditoria_geometrica"]["ok"]
    assert result["auditoria"]["ok"]
    assert all(result["arquivos"].get(k) for k in
               ("dxf_url","pdf_url","png_url","zip_url"))
