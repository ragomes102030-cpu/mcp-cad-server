"""Validated component placement against room boundaries and existing CAD geometry."""
from __future__ import annotations
from .components import CATALOG, footprint, place_component

class PlacementError(ValueError):
    pass

def place_checked(doc, kind, origin, room_rect, *, angle_deg=0, clearance_m=None):
    """Fail closed on wall, door sweep or existing furniture intersections.

    Clearance is a conservative footprint buffer, not a regulatory approval.
    """
    from shapely.geometry import Polygon, box, LineString
    from shapely.ops import unary_union
    from math import cos, sin, radians
    if kind not in CATALOG:
        raise PlacementError("Unknown component")
    component = CATALOG[kind]
    clearance = component.clearance_m if clearance_m is None else clearance_m
    if clearance < 0:
        raise PlacementError("Negative clearance")
    polygon = Polygon(footprint(component, origin, angle_deg))
    x0, y0, x1, y1 = room_rect
    if not box(x0, y0, x1, y1).covers(polygon.buffer(clearance)):
        raise PlacementError("Component or clearance outside room")
    m = doc.modelspace()
    for e in m.query("LWPOLYLINE"):
        if e.dxf.layer not in {"ARQ-PAREDES", "ARQ-MOBILIARIO", "ARQ-DETALHES"}:
            continue
        points = list(e.get_points("xy"))
        if len(points) < 2:
            continue
        obstacle = Polygon(points) if e.closed and len(points) >= 3 else LineString(points)
        if not obstacle.is_valid:
            raise PlacementError("Invalid obstacle geometry")
        if polygon.buffer(clearance).intersects(obstacle):
            raise PlacementError("Component collides with existing geometry")
    for arc in m.query("ARC"):
        if arc.dxf.layer != "ARQ-PORTAS":
            continue
        a = float(arc.dxf.start_angle)
        b = float(arc.dxf.end_angle)
        if b < a:
            b += 360
        cx, cy = arc.dxf.center.x, arc.dxf.center.y
        radius = float(arc.dxf.radius)
        path = LineString([(cx + radius*cos(radians(a+(b-a)*i/24)),
                            cy + radius*sin(radians(a+(b-a)*i/24)))
                           for i in range(25)])
        if polygon.buffer(clearance).intersects(path.buffer(.05)):
            raise PlacementError("Component obstructs door swing")
    return place_component(doc, kind, origin, angle_deg)
