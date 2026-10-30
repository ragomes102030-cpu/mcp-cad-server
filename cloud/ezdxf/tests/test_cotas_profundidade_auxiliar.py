"""Auxiliary cotas must be faithful, distinguishable, and not cross rooms."""
from test_prancha_licenciamento import package as package_fixture
from mcp_cad_cloud.auditoria_legibilidade import auditar_legibilidade_vista


def test_auxiliary_depth_cotas_use_actual_room_y_coordinates():
    package = package_fixture.__wrapped__()
    floor = next(view for view in package.views if view.view_id == "ARQ-PLANTA")
    width = float(package.source_plan["resumo_geometria"]["largura"])
    indices = [2, 5]
    for index in indices:
        room = package.source_plan["ambientes"][index]
        source = f"dimension:room:{index}:depth:aux"
        segments = [s for s in floor.segments if s.source_id == source]
        assert len(segments) == 3
        baseline = segments[0]
        assert baseline.layer == "COTAS-AUXILIAR"
        assert baseline.x1 == baseline.x2
        assert width < baseline.x1 < width + .65
        assert abs(baseline.y1 - float(room["y1"])) < 1e-8
        assert abs(baseline.y2 - float(room["y2"])) < 1e-8
        tag = next(l for l in floor.labels
                   if l.source_id == f"dimension-label:room:{index}:depth:aux")
        assert room["nome"] in tag.text
        assert f"{room['y2']-room['y1']:.2f} m" in tag.text
    assert any(l.source_id == "aux-depth:legend" for l in floor.labels)


def test_auxiliary_rails_never_traverse_room_or_door_geometry():
    package = package_fixture.__wrapped__()
    floor = next(view for view in package.views if view.view_id == "ARQ-PLANTA")
    rails = [
        s for s in floor.segments
        if s.source_id.endswith(":depth:aux") and s.x1 == s.x2
    ]
    assert len(rails) == 2
    for rail in rails:
        assert all(float(room["x2"]) < rail.x1
                   for room in package.source_plan["ambientes"])
        assert all(float(furniture[2]) < rail.x1
                   for furniture in package.source_plan["moveis"])
    report = auditar_legibilidade_vista(floor, 50)
    assert not report["warnings"], report["warnings"]
    assert report["normative_approval"] is False


def test_auxiliary_rails_are_not_in_situ_wall_dimensions():
    package = package_fixture.__wrapped__()
    floor = next(view for view in package.views if view.view_id == "ARQ-PLANTA")
    assert sum(seg.layer == "COTAS-AUXILIAR" for seg in floor.segments) == 6
    assert len([label for label in floor.labels
                if label.source_id.startswith("dimension-label:room:")
                and label.source_id.endswith(":depth:aux")]) == 2
