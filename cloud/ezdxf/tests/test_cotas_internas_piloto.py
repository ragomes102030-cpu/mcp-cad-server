"""Regression for measured, safely placed horizontal and vertical cotas."""
import math
from test_prancha_licenciamento import package as package_fixture
from mcp_cad_cloud.auditoria_legibilidade import auditar_legibilidade_vista


def _plan():
    package = package_fixture.__wrapped__()
    return package, next(v for v in package.views if v.view_id == "ARQ-PLANTA")


def _intersects_rect_line(segment, box):
    x1, y1, x2, y2 = map(float, box)
    if abs(segment.y1 - segment.y2) < 1e-8:
        return y1 < segment.y1 < y2 and (
            min(max(segment.x1, segment.x2), x2) -
            max(min(segment.x1, segment.x2), x1) > 1e-8)
    if abs(segment.x1 - segment.x2) < 1e-8:
        return x1 < segment.x1 < x2 and (
            min(max(segment.y1, segment.y2), y2) -
            max(min(segment.y1, segment.y2), y1) > 1e-8)
    return False


def test_room_dimensions_match_clear_face_bounds_on_both_axes():
    package, plan = _plan()
    assert len(package.source_plan["ambientes"]) == 7
    counts = {"width": 0, "depth": 0}
    for i, room in enumerate(package.source_plan["ambientes"]):
        for axis in ("width", "depth"):
            source = f"dimension:room:{i}:{axis}"
            graphic = [seg for seg in plan.segments if seg.source_id == source]
            label = [l for l in plan.labels
                     if l.source_id == f"dimension-label:room:{i}:{axis}"]
            assert len(graphic) == 3 * len(label), (source, graphic, label)
            if not label:
                assert any(l.source_id == f"schedule:room:{i}" for l in plan.labels)
                continue
            counts[axis] += 1
            baseline = graphic[0]
            assert baseline.layer == "COTAS-INTERIOR"
            expected = (float(room["x2"]) - float(room["x1"]) if axis == "width"
                        else float(room["y2"]) - float(room["y1"]))
            actual = (abs(baseline.x2 - baseline.x1) if axis == "width"
                      else abs(baseline.y2 - baseline.y1))
            assert math.isclose(actual, expected, abs_tol=1e-8)
            assert label[0].text == f"{expected:.2f} m"
            if axis == "width":
                assert baseline.y1 == baseline.y2
                assert abs(baseline.x1 - float(room["x1"])) < 1e-8
                assert abs(baseline.x2 - float(room["x2"])) < 1e-8
            else:
                assert baseline.x1 == baseline.x2
                assert abs(baseline.y1 - float(room["y1"])) < 1e-8
                assert abs(baseline.y2 - float(room["y2"])) < 1e-8
    assert counts["width"] == 7
    assert counts["depth"] >= 5


def test_dimension_baselines_do_not_cut_furniture_or_door_swing_boxes():
    package, plan = _plan()
    furniture = package.source_plan["moveis"]
    door_segments = [s for s in plan.segments if s.layer == "ESQUADRIA-PORTA"]
    for segment in plan.segments:
        if not segment.source_id.startswith("dimension:room:"):
            continue
        # Ticks at the endpoints are allowed to meet the wall faces.
        is_baseline = (abs(segment.x1 - segment.x2) < 1e-8
                       or abs(segment.y1 - segment.y2) < 1e-8)
        if not is_baseline:
            continue
        for box in furniture:
            assert not _intersects_rect_line(segment, box), (segment, box)
        for door in door_segments:
            box = (min(door.x1, door.x2), min(door.y1, door.y2),
                   max(door.x1, door.x2), max(door.y1, door.y2))
            assert not _intersects_rect_line(segment, box), (segment, door)


def test_graphic_dimension_labels_do_not_overlap_mapped_furniture():
    _, plan = _plan()
    report = auditar_legibilidade_vista(plan, 50)
    assert report["normative_approval"] is False
    assert not report["warnings"], report["warnings"]
