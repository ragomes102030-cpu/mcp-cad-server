"""Independent, low-resolution route-width estimates from physical DXF data."""
from __future__ import annotations

from heapq import heappop, heappush
import math
import unicodedata


def _xy(point):
    return float(point[0]), float(point[1])


def _point_segment_distance(point, segment):
    x, y = point
    x1, y1, x2, y2 = segment
    dx, dy = x2 - x1, y2 - y1
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return math.hypot(x - x1, y - y1)
    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / length_squared))
    return math.hypot(x - x1 - t * dx, y - y1 - t * dy)


def _point_rect_distance(point, rect):
    x, y = point
    x1, y1, x2, y2 = rect
    dx = max(x1 - x, 0.0, x - x2)
    dy = max(y1 - y, 0.0, y - y2)
    return math.hypot(dx, dy)


def _text_anchor(doc):
    for entity in doc.modelspace().query('TEXT[layer=="TEXTOS"]'):
        label = unicodedata.normalize("NFKD", str(entity.dxf.text))
        label = label.encode("ascii", "ignore").decode("ascii").casefold()
        if "servico" in label or "lavanderia" in label:
            return _xy(entity.dxf.insert)
    return None


def _entrance_anchor(doc, bounds):
    min_x, min_y, max_x, max_y = bounds
    doors = list(doc.modelspace().query('ARC[layer=="PORTAS"]'))
    candidates = []
    for door in doors:
        center = _xy(door.dxf.center)
        distances = ((center[0] - min_x, (1, 0)), (max_x - center[0], (-1, 0)),
                     (center[1] - min_y, (0, 1)), (max_y - center[1], (0, -1)))
        distance, inward = min(distances, key=lambda item: item[0])
        if distance <= 0.25:
            inset = max(0.35, float(door.dxf.radius) * 0.8)
            candidates.append((distance, (center[0] + inward[0] * inset,
                                          center[1] + inward[1] * inset)))
    return min(candidates, default=(None, None), key=lambda item: item[0])[1]


def _geometry(doc):
    segments = []
    for layer, padding in (("PAREDES", 0.08), ("JANELAS", 0.04)):
        for entity in doc.modelspace().query(f'LINE[layer=="{layer}"]'):
            segments.append(((_xy(entity.dxf.start)[0], _xy(entity.dxf.start)[1],
                              _xy(entity.dxf.end)[0], _xy(entity.dxf.end)[1]), padding))
    rectangles = []
    for entity in doc.modelspace().query('LWPOLYLINE[layer=="MOBILIARIO"]'):
        points = [_xy(point) for point in entity.get_points("xy")]
        if len(points) == 4:
            rectangles.append((min(p[0] for p in points), min(p[1] for p in points),
                               max(p[0] for p in points), max(p[1] for p in points)))
    return segments, rectangles


def _widest_route(doc, step):
    walls = list(doc.modelspace().query('LINE[layer=="PAREDES"]'))
    if not walls:
        return None, "DXF has no physical wall entities"
    xs = [float(value) for wall in walls for value in (wall.dxf.start.x, wall.dxf.end.x)]
    ys = [float(value) for wall in walls for value in (wall.dxf.start.y, wall.dxf.end.y)]
    bounds = min(xs), min(ys), max(xs), max(ys)
    source = _entrance_anchor(doc, bounds)
    target = _text_anchor(doc)
    if source is None or target is None:
        return None, "Exterior entrance or service-room text anchor is missing"

    segments, furniture = _geometry(doc)
    min_x, min_y, max_x, max_y = bounds
    nx = max(1, math.ceil((max_x - min_x) / step))
    ny = max(1, math.ceil((max_y - min_y) / step))
    clearance = {}
    coords = {}
    for i in range(nx):
        x = min_x + (i + 0.5) * step
        if x >= max_x:
            continue
        for j in range(ny):
            y = min_y + (j + 0.5) * step
            if y >= max_y:
                continue
            point = (x, y)
            distances = [(_point_segment_distance(point, segment) - padding)
                         for segment, padding in segments]
            distances.extend(_point_rect_distance(point, rect) for rect in furniture)
            if not distances or min(distances) <= 1e-9:
                continue
            cell = (i, j)
            coords[cell] = point
            clearance[cell] = min(distances)

    def nearby(anchor, radius):
        matches = [cell for cell, point in coords.items()
                   if math.dist(point, anchor) <= radius]
        return matches

    starts = nearby(source, 0.55)
    targets = set(nearby(target, 0.75))
    if not starts or not targets:
        return None, "No free grid cell near the entry or service-room label"

    capacity = {}
    queue = []
    for cell in starts:
        value = clearance[cell]
        if value > capacity.get(cell, -1.0):
            capacity[cell] = value
            heappush(queue, (-value, cell))
    while queue:
        negative, cell = heappop(queue)
        value = -negative
        if value < capacity.get(cell, -1.0) - 1e-12:
            continue
        if cell in targets:
            return round(2 * value, 3), None
        i, j = cell
        for neighbor in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if neighbor not in clearance:
                continue
            candidate = min(value, clearance[neighbor])
            if candidate > capacity.get(neighbor, -1.0) + 1e-12:
                capacity[neighbor] = candidate
                heappush(queue, (-candidate, neighbor))
    return None, "Service-room label is not reachable from the exterior entrance on this grid"


def measure_route_widths(doc, scenario=None, steps=(0.05, 0.10, 0.15)) -> dict:
    """Estimate route clearance at several grids using reopened DXF entities.

    The result is a sensitivity indicator, not a physical survey or legal
    width. Production audit functions are not called by this routine.
    """
    measurements = []
    for step in steps:
        width, reason = _widest_route(doc, float(step))
        measurements.append({
            "grid_m": float(step),
            "width_m": width,
            "status": "estimated" if width is not None else "inconclusive",
            "reason": reason,
            "quantization_indicator_m": round(2 * float(step), 3),
            "approximate": True,
        })
    return {
        "method": "independent_dxf_grid_approximation",
        "measurements": measurements,
        "limitation": (
            "Approximate widest-route diameter from reopened wall, glazing, and furniture entities; "
            "does not certify minimum clear width, accessibility, or legal compliance."
        ),
    }
