"""Preliminary geometric subdivision for the four-unit pilot (metres).

This is an editable CAD-independent model, not a permit-ready floor plan.
Stair core and shared corridor still require redesign and access validation.
"""
from __future__ import annotations

from .multifamiliar import build_four_apartment_floor
from .project_model import Element, ProjectModel, ProjectModelError


def build_detailed_four_apartment_floor(*, width: float = 24.0, depth: float = 18.0) -> ProjectModel:
    model = build_four_apartment_floor(width=width, depth=depth)
    units = [r for r in model.rooms if r.metadata.get("type") == "apartment_zone"]
    for unit in units:
        x = float(unit.geometry["x"])
        y = float(unit.geometry["y"])
        w = float(unit.geometry["width"])
        d = float(unit.geometry["depth"])
        uid = unit.metadata["unit_id"]
        # Three longitudinal bands: living/kitchen, bedrooms and wet areas.
        bands = [
            ("living-kitchen", 0.0, 0.42, "living_kitchen"),
            ("bedrooms", 0.42, 0.37, "bedroom_zone"),
            ("wet-areas", 0.79, 0.21, "wet_area_zone"),
        ]
        for name, fraction, proportion, kind in bands:
            model.rooms.append(Element(
                id=f"{uid}-{name}",
                geometry={"x": round(x + w * fraction, 6), "y": y,
                          "width": round(w * proportion, 6), "depth": d},
                relationships={"within": [unit.id]},
                metadata={"type": kind, "unit_id": uid, "status": "preliminary_zone"},
            ))
        # Vertical dividing walls: explicit segments, thickness stored separately.
        for index, fraction in enumerate((0.42, 0.79), 1):
            model.walls.append(Element(
                id=f"{uid}-partition-{index}",
                geometry={"x": round(x + w * fraction, 6), "y": y,
                          "length": d, "thickness": 0.12},
                relationships={"within": [unit.id]},
                metadata={"orientation": "vertical", "unit_id": uid, "type": "partition"},
            ))
        # Access opening from the corridor, centered along the apartment frontage.
        corridor_edge_y = y + d if y == 0 else y
        model.openings.append(Element(
            id=f"{uid}-entrance",
            geometry={"x": round(x + w / 2 - 0.45, 6), "y": corridor_edge_y,
                      "width": 0.9},
            relationships={"connects": [unit.id, "common-corridor"]},
            metadata={"type": "door", "unit_id": uid, "status": "preliminary",
                      "swing": "not_defined"},
        ))
        # External facade glazing is represented as an opening placeholder.
        exterior_y = y if y == 0 else y + d
        model.openings.append(Element(
            id=f"{uid}-facade-window",
            geometry={"x": round(x + w * 0.20, 6), "y": exterior_y,
                      "width": round(w * 0.18, 6)},
            relationships={"serves": [unit.id]},
            metadata={"type": "window", "unit_id": uid, "status": "preliminary"},
        ))
    model.validate()
    return model
