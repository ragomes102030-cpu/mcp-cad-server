"""Reusable, unit-aware CAD components for architectural preliminary studies.

All dimensions are in metres in modelspace. No normative compliance implied.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import cos, sin, radians, isfinite

@dataclass(frozen=True)
class Component:
    kind: str
    width_m: float
    depth_m: float
    clearance_m: float = 0.0

    def __post_init__(self):
        if not all(isfinite(v) for v in (self.width_m, self.depth_m, self.clearance_m)):
            raise ValueError("Component dimensions must be finite")
        if self.width_m <= 0 or self.depth_m <= 0 or self.clearance_m < 0:
            raise ValueError("Invalid component dimensions")

CATALOG = {
    "bed_single": Component("bed_single", .90, 1.90, .45),
    "bed_double": Component("bed_double", 1.40, 1.90, .50),
    "sofa": Component("sofa", 2.00, .85, .60),
    "wardrobe": Component("wardrobe", 1.60, .60, .70),
    "kitchen_sink": Component("kitchen_sink", 1.20, .60, .80),
    "washbasin": Component("washbasin", .60, .48, .60),
    "toilet": Component("toilet", .40, .70, .60),
    "shower": Component("shower", .90, .90, .0),
}

def footprint(component: Component, origin: tuple[float, float], angle_deg: float = 0):
    """Return the four vertices of a rotated component footprint."""
    x, y = origin
    if not all(isfinite(v) for v in (x, y, angle_deg)):
        raise ValueError("Non-finite position or angle")
    c, s = cos(radians(angle_deg)), sin(radians(angle_deg))
    return tuple((x + dx*c - dy*s, y + dx*s + dy*c)
                 for dx, dy in ((0, 0), (component.width_m, 0),
                                (component.width_m, component.depth_m),
                                (0, component.depth_m)))

def place_component(doc, kind: str, origin: tuple[float, float],
                    angle_deg: float = 0, layer: str = "ARQ-MOBILIARIO"):
    """Add a closed CAD polyline and structured XDATA for later editing."""
    if kind not in CATALOG:
        raise KeyError(f"Unknown component: {kind}")
    component = CATALOG[kind]
    points = footprint(component, origin, angle_deg)
    if layer not in doc.layers:
        doc.layers.new(layer, dxfattribs={"color": 8})
    if "MCP_CAD" not in doc.appids:
        doc.appids.new("MCP_CAD")
    entity = doc.modelspace().add_lwpolyline(
        points, close=True, dxfattribs={"layer": layer})
    entity.set_xdata("MCP_CAD", [(1000, "component:v1"),
                                 (1000, kind),
                                 (1040, component.width_m),
                                 (1040, component.depth_m),
                                 (1040, component.clearance_m),
                                 (1040, angle_deg)])
    return entity

def read_component(entity):
    """Return editable component metadata; reject ordinary untagged entities."""
    tags = entity.get_xdata("MCP_CAD")
    values = [tag.value for tag in tags]
    if len(values) != 6 or values[0] != "component:v1":
        raise ValueError("Unsupported component metadata")
    kind = values[1]
    if kind not in CATALOG:
        raise ValueError("Unknown component type")
    return {"kind": kind, "width_m": values[2], "depth_m": values[3],
            "clearance_m": values[4], "angle_deg": values[5]}
