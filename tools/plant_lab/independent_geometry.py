"""Independent, test-only checks over physical entities in a reopened DXF.

This deliberately does not consume the generator model or production audit
results. It is a bounded contract check, not an architectural certification.
"""
from __future__ import annotations

import math
import re


TOLERANCE = 0.002


def _issue(code: str, detail: str, severity: str = "error") -> dict:
    return {"code": code, "severity": severity, "detail": detail}


def _xy(point) -> tuple[float, float]:
    return float(point[0]), float(point[1])


def _bbox(points) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _close(left: float, right: float) -> bool:
    return abs(left - right) <= TOLERANCE


def _inside(bounds, point) -> bool:
    x1, y1, x2, y2 = bounds
    x, y = point
    return (x1 - TOLERANCE <= x <= x2 + TOLERANCE
            and y1 - TOLERANCE <= y <= y2 + TOLERANCE)


def _segments_pair(first, second) -> bool:
    a, b = first
    c, d = second
    first_horizontal = _close(a[1], b[1])
    second_horizontal = _close(c[1], d[1])
    if first_horizontal and second_horizontal:
        same_projection = (_close(min(a[0], b[0]), min(c[0], d[0]))
                           and _close(max(a[0], b[0]), max(c[0], d[0])))
        return same_projection and _close(abs(a[1] - c[1]), 0.075)
    first_vertical = _close(a[0], b[0])
    second_vertical = _close(c[0], d[0])
    if first_vertical and second_vertical:
        same_projection = (_close(min(a[1], b[1]), min(c[1], d[1]))
                           and _close(max(a[1], b[1]), max(c[1], d[1])))
        return same_projection and _close(abs(a[0] - c[0]), 0.075)
    return False


def _window_segment(entity):
    return _xy(entity.dxf.start), _xy(entity.dxf.end)


def _valid_window_pairs(entities) -> int:
    segments = [_window_segment(entity) for entity in entities]
    used: set[int] = set()
    pairs = 0
    for index, first in enumerate(segments):
        if index in used:
            continue
        a, b = first
        for other_index in range(index + 1, len(segments)):
            if other_index in used:
                continue
            c, d = segments[other_index]
            if not _segments_pair(first, (c, d)):
                continue
            used.update((index, other_index))
            pairs += 1
            break
    return pairs


def _door_leaf_matches(arcs, leaves) -> bool:
    if len(arcs) != len(leaves):
        return False
    remaining = list(leaves)
    for arc in arcs:
        center = _xy(arc.dxf.center)
        radius = float(arc.dxf.radius)
        match = None
        for index, leaf in enumerate(remaining):
            start, end = _xy(leaf.dxf.start), _xy(leaf.dxf.end)
            length = math.dist(start, end)
            if math.dist(center, start) <= TOLERANCE and _close(radius, length):
                match = index
                break
        if match is None:
            return False
        remaining.pop(match)
    return not remaining


def evaluate_reopened_dxf(doc, scenario: dict) -> list[dict]:
    """Return independent geometry issues from a serialized, reopened DXF.

    `scenario` contains only independent expectations: `terrain_bounds`,
    `expected_doors`, and `expected_window_pairs`. This evaluator does not
    inspect any claimed generator summary or call production audit helpers.
    """
    issues: list[dict] = []
    msp = doc.modelspace()
    lot_bounds = tuple(float(v) for v in scenario["terrain_bounds"])

    if int(doc.header.get("$INSUNITS", 0)) != 6:
        issues.append(_issue("units-not-meters", "DXF $INSUNITS must declare meters."))

    lots = list(msp.query('LWPOLYLINE[layer=="TERRENO"]'))
    if len(lots) != 1:
        issues.append(_issue("lot-count-mismatch", f"Expected one lot outline, found {len(lots)}."))
    else:
        lot = lots[0]
        vertices = [_xy(point) for point in lot.get_points("xy")]
        valid_shape = (lot.closed and len(vertices) == 4
                       and all(_close(vertices[i][0], vertices[(i + 1) % 4][0])
                               or _close(vertices[i][1], vertices[(i + 1) % 4][1])
                               for i in range(4)))
        if not valid_shape or any(not _close(actual, expected)
                                  for actual, expected in zip(_bbox(vertices), lot_bounds)):
            issues.append(_issue("lot-bounds-mismatch",
                                 "Closed lot polyline does not match the scenario bounds."))

    walls = list(msp.query('LINE[layer=="PAREDES"]'))
    if not walls:
        issues.append(_issue("walls-missing", "No physical wall lines were found."))
    for wall in walls:
        start, end = _xy(wall.dxf.start), _xy(wall.dxf.end)
        if (math.dist(start, end) <= TOLERANCE
                or (not _close(start[0], end[0]) and not _close(start[1], end[1]))
                or not _inside(lot_bounds, start) or not _inside(lot_bounds, end)):
            issues.append(_issue("wall-invalid-geometry",
                                 f"Wall segment {wall.dxf.handle} is degenerate, diagonal, or outside the lot."))
            break

    doors = list(msp.query('ARC[layer=="PORTAS"]'))
    leaves = list(msp.query('LINE[layer=="PORTAS"]'))
    expected_doors = int(scenario["expected_doors"])
    if len(doors) != expected_doors or len(leaves) != expected_doors:
        issues.append(_issue("door-count-mismatch",
                             f"Expected {expected_doors} door arcs and leaves; found {len(doors)} and {len(leaves)}."))
    elif not _door_leaf_matches(doors, leaves):
        issues.append(_issue("door-leaf-mismatch", "Door leaves do not match their physical swing arcs."))

    windows = list(msp.query('LINE[layer=="JANELAS"]'))
    expected_pairs = int(scenario["expected_window_pairs"])
    if len(windows) != expected_pairs * 2 or _valid_window_pairs(windows) != expected_pairs:
        issues.append(_issue("window-pair-mismatch",
                             f"Expected {expected_pairs} matching two-line glazing pairs; found {len(windows)} lines."))

    # The current DXF records each room's free dimensions as text, but does
    # not encode closed room polygons. Compare those physical DXF annotations
    # to briefing areas and report this as label consistency, not measured area.
    area_labels = []
    for entity in msp.query('TEXT[layer=="COTAS_INT"]'):
        match = re.fullmatch(
            r"\s*(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*m\s*",
            str(entity.dxf.text), re.IGNORECASE)
        if match:
            width, depth = (float(value.replace(",", ".")) for value in match.groups())
            area_labels.append(width * depth)
    unmatched_areas = list(float(area) for area in scenario.get("expected_room_areas_m2", []))
    for expected_area in unmatched_areas[:]:
        candidates = [(abs(actual - expected_area), index)
                      for index, actual in enumerate(area_labels)
                      if abs(actual - expected_area) <= 0.06]
        if candidates:
            _, match_index = min(candidates)
            area_labels.pop(match_index)
            unmatched_areas.remove(expected_area)
    if unmatched_areas:
        issues.append(_issue("room-area-label-mismatch",
                             "DXF room-dimension labels do not match briefing areas within 0.06 m²: "
                             + ", ".join(f"{area:g}" for area in unmatched_areas) + "."))

    furniture = list(msp.query('LWPOLYLINE[layer=="MOBILIARIO"]'))
    footprints = []
    for entity in furniture:
        points = [_xy(point) for point in entity.get_points("xy")]
        if (not entity.closed or len(points) != 4
                or any(not _close(points[i][0], points[(i + 1) % 4][0])
                       and not _close(points[i][1], points[(i + 1) % 4][1])
                       for i in range(4))):
            issues.append(_issue("furniture-invalid-footprint",
                                 f"Furniture {entity.dxf.handle} is not a closed orthogonal quadrilateral."))
            continue
        bounds = _bbox(points)
        if (bounds[2] - bounds[0] <= TOLERANCE or bounds[3] - bounds[1] <= TOLERANCE):
            issues.append(_issue("furniture-invalid-footprint",
                                 f"Furniture {entity.dxf.handle} has no positive footprint."))
            continue
        footprints.append((entity.dxf.handle, bounds))
        if any(not _inside(lot_bounds, point) for point in points):
            issues.append(_issue("furniture-outside-lot",
                                 f"Furniture {entity.dxf.handle} extends outside the lot."))

    for index, (left_id, left) in enumerate(footprints):
        for right_id, right in footprints[index + 1:]:
            overlap_x = min(left[2], right[2]) - max(left[0], right[0])
            overlap_y = min(left[3], right[3]) - max(left[1], right[1])
            if overlap_x > TOLERANCE and overlap_y > TOLERANCE:
                issues.append(_issue("furniture-overlap",
                                     f"Furniture footprints {left_id} and {right_id} overlap."))
    return issues
