"""Room clear-face dimensions must be physically represented in the DXF."""
import math

from test_prancha_licenciamento import package as package_fixture


def test_internal_dimensions_are_measured_from_room_geometry():
    pkg = package_fixture.__wrapped__()
    plan = next(v for v in pkg.views if v.view_id == "ARQ-PLANTA")
    assert len(pkg.source_plan["ambientes"]) == 7
    drawn = 0
    for index, room in enumerate(pkg.source_plan["ambientes"]):
        source = f"dimension:room:{index}:width"
        graphic = [s for s in plan.segments if s.source_id == source]
        label = [l for l in plan.labels
                 if l.source_id == f"dimension-label:room:{index}:width"]
        assert len(graphic) == 3 * len(label), (index, graphic, label)
        if not label:
            # The full room dimensions remain available in the schedule.
            assert any(l.source_id == f"schedule:room:{index}" for l in plan.labels)
            continue
        drawn += 1
        assert graphic[0].layer == "COTAS-INTERIOR"
        assert graphic[0].y1 == graphic[0].y2
        assert math.isclose(
            abs(graphic[0].x2 - graphic[0].x1),
            float(room["x2"]) - float(room["x1"]), abs_tol=1e-8)
        assert label[0].text == f"{float(room['x2']) - float(room['x1']):.2f} m"
    assert drawn >= 4  # Baseline 10 x 20 pilot: the others remain in schedule.


def test_internal_dimension_lines_do_not_cross_furniture():
    pkg = package_fixture.__wrapped__()
    plan = next(v for v in pkg.views if v.view_id == "ARQ-PLANTA")
    for s in plan.segments:
        if not s.source_id.startswith("dimension:room:") or abs(s.y2-s.y1)>1e-9:
            continue
        y=s.y1
        for x1,y1,x2,y2 in pkg.source_plan["moveis"]:
            assert not (y1 < y < y2 and min(s.x2,x2) > max(s.x1,x1)), (s,(x1,y1,x2,y2))
