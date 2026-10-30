"""Source-traceable elevations and level dimensions for section/facade pilot."""
from math import radians, tan
from importlib import import_module

from test_projeto_arquitetonico import generate
from test_prancha_licenciamento import package as package_fixture


def _labels(view):
    return {label.source_id: label.text for label in view.labels}


def _only_line(view, source):
    matched = [segment for segment in view.segments if segment.source_id == source]
    assert len(matched) == 1, (view.view_id, source, matched)
    return matched[0]


def test_all_sections_and_elevations_show_measured_floor_and_wall_datums():
    package = package_fixture.__wrapped__()
    env = package.envelope
    floor = float(env.floor_level_m)
    top = floor + float(env.wall_height_m)
    for view in package.views:
        if not view.view_id.startswith(("ARQ-CORTE-", "ARQ-FACHADA-")):
            continue
        labels = _labels(view)
        assert labels[f"datum:{view.view_id}:floor:label"].endswith(f"{floor:+.2f} m")
        assert labels[f"datum:{view.view_id}:wall:label"].endswith(f"{top:+.2f} m")
        assert labels[f"height:{view.view_id}:wall:label"] == (
            f"ALTURA PAREDE {top-floor:.2f} m"
        )
        wall = _only_line(view, f"height:{view.view_id}:wall")
        assert abs(wall.y1 - floor) < 1e-8
        assert abs(wall.y2 - top) < 1e-8
        assert abs(wall.x1 - wall.x2) < 1e-8
        assert wall.layer == "COTAS-NIVEIS"


def test_orthogonal_roof_ridge_has_one_consistent_elevation_in_each_drawn_view():
    api = import_module("mcp_cad_cloud.projeto_arquitetonico")
    for axis in ("x", "y"):
        package = generate(api, ridge_axis=axis)
        env = package.envelope
        top = env.floor_level_m + env.wall_height_m
        transverse = (package.source_plan["resumo_geometria"]["profundidade"]
                      if axis == "x" else
                      package.source_plan["resumo_geometria"]["largura"])
        ridge = top + (transverse/2 + env.roof_overhang_m) * tan(radians(env.roof_pitch_degrees))
        for view in package.views:
            if not view.view_id.startswith(("ARQ-CORTE-", "ARQ-FACHADA-")):
                continue
            labels = _labels(view)
            # A parallel-to-ridge elevation shows its eaves, not a fake
            # ridge at the top of the walls.
            gable = (axis == "x" and view.view_id.endswith(("LATERAL-ESQ", "LATERAL-DIR"))
                     or axis == "y" and view.view_id.endswith(("FRONTAL", "FUNDOS")))
            visible = view.view_id.startswith("ARQ-CORTE-") or gable
            key = f"datum:{view.view_id}:ridge:label"
            if visible:
                assert labels[key].endswith(f"{ridge:+.2f} m")
                line = _only_line(view, f"height:{view.view_id}:roof")
                assert abs(line.y1-top) < 1e-8
                assert abs(line.y2-ridge) < 1e-8
            else:
                assert key not in labels
                assert not [s for s in view.segments
                            if s.source_id == f"height:{view.view_id}:roof"]


def test_facade_window_and_door_tags_reference_the_actual_openings():
    package = package_fixture.__wrapped__()
    for view in package.views:
        if not view.view_id.startswith("ARQ-FACHADA-"):
            continue
        for segment in view.segments:
            if segment.layer == "ESQUADRIA-JANELA":
                side, index = segment.source_id.split(":")[1:]
                tag = f"facade:{side}:window-tag:{index}"
                assert _labels(view)[tag] == f"J{int(index)+1:02d}"
            if segment.layer == "ESQUADRIA-PORTA":
                side, index = segment.source_id.split(":")[1:]
                tag = f"facade:{side}:door-tag:{index}"
                assert _labels(view)[tag] == f"P{int(index)+1:02d}"


def test_cross_view_audit_blocks_corrupted_level_text_even_with_valid_xdata():
    from dataclasses import replace
    from mcp_cad_cloud.auditoria_coerencia import audit_architecture_coherence

    package = package_fixture.__wrapped__()
    target = "ARQ-CORTE-A"
    altered = []
    for view in package.views:
        if view.view_id != target:
            altered.append(view)
            continue
        altered.append(replace(view, labels=tuple(
            replace(label, text="TOPO PAREDE +99.00 m")
            if label.source_id == f"datum:{target}:wall:label"
            else label for label in view.labels
        )))
    bad = replace(package, views=tuple(altered))
    audit = audit_architecture_coherence(bad)
    assert audit["ok"] is False
    assert any(item["code"] == "datum-label-mismatch"
               and item["view_id"] == target for item in audit["errors"])


def test_cross_view_audit_blocks_fake_ridge_in_parallel_facade():
    from dataclasses import replace
    from mcp_cad_cloud.projeto_arquitetonico import ViewLabel
    from mcp_cad_cloud.auditoria_coerencia import audit_architecture_coherence

    package = package_fixture.__wrapped__()
    view_id = "ARQ-FACHADA-FRONTAL"  # ridge_axis=x: parallel gable not projected
    altered = []
    for view in package.views:
        if view.view_id == view_id:
            fake = ViewLabel("CUMEEIRA +5.01 m", 10, 5.01,
                             f"datum:{view_id}:ridge:label")
            altered.append(replace(view, labels=(*view.labels, fake)))
        else:
            altered.append(view)
    audit = audit_architecture_coherence(replace(package, views=tuple(altered)))
    assert audit["ok"] is False
    assert any(item["code"] == "datum-unprojected-ridge"
               and item["view_id"] == view_id for item in audit["errors"])
