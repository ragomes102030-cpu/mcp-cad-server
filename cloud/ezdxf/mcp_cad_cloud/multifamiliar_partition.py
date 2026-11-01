"""Deterministic preliminary partition plan for the four-unit pilot.

All dimensions are metres. Rectangular spaces and centerline wall segments are
schematic; doors/windows, wall thickness and code compliance need separate audit.
"""
from __future__ import annotations

from .multifamiliar import build_four_apartment_floor
from .project_model import Element, ProjectModel, ProjectModelError


def build_partitioned_four_apartment_floor(*, width: float = 24.0, depth: float = 18.0) -> ProjectModel:
    """Build four two-bedroom unit layouts, common hall and access openings.

    The 2 m common hall is kept continuous. A stair reservation is retained
    only as a conceptual zone, NOT a usable or dimensioned stair.
    """
    model = build_four_apartment_floor(width=width, depth=depth)
    model.rooms = [r for r in model.rooms if r.metadata.get("type") != "apartment_zone"]
    unit_width = width / 2
    unit_depth = (depth - 2.0) / 2
    if unit_width < 8 or unit_depth < 6:
        raise ProjectModelError("insufficient room dimensions")
    for row in range(2):
        y0 = 0.0 if row == 0 else unit_depth + 2.0
        for col in range(2):
            x0 = col * unit_width
            uid = f"AP{row * 2 + col + 1:02d}"
            # Layout: living/kitchen near corridor, two bedrooms on exterior,
            # bathroom and laundry at the intermediate service strip.
            band = unit_depth * 0.36
            service = unit_depth * 0.22
            # Mirror the apartment so living areas face the common corridor.
            if row == 0:
                living_y = y0 + unit_depth - band
                service_y = living_y - service
                bedroom_y = y0
            else:
                living_y = y0
                service_y = living_y + band
                bedroom_y = service_y + service
            bedroom_depth = unit_depth - band - service
            spaces = (
                ("living-kitchen", x0, living_y, unit_width, band),
                ("bathroom", x0, service_y, unit_width * .35, service),
                ("laundry", x0 + unit_width * .35, service_y, unit_width * .20, service),
                ("hall", x0 + unit_width * .55, service_y, unit_width * .45, service),
                ("bedroom-1", x0, bedroom_y, unit_width * .5, bedroom_depth),
                ("bedroom-2", x0 + unit_width * .5, bedroom_y, unit_width * .5, bedroom_depth),
            )
            for name, x, y, w, d in spaces:
                model.rooms.append(Element(
                    id=f"{uid}-{name}",
                    geometry={"x": x, "y": y, "width": w, "depth": d},
                    metadata={"type": name, "unit_id": uid, "private": True},
                ))
            door_y = unit_depth if row == 0 else unit_depth + 2.0
            model.openings.append(Element(
                id=f"{uid}-entrance",
                geometry={"x": x0 + unit_width * .70, "y": door_y, "width": .90},
                relationships={"connects": [f"{uid}-living-kitchen", "common-corridor"]},
                metadata={"type": "door", "unit_id": uid, "status": "schematic"},
            ))
            # Exterior bedroom windows, only schematic positions.
            outer_y = y0 if row == 0 else y0 + unit_depth
            for j in range(2):
                model.openings.append(Element(
                    id=f"{uid}-window-{j+1}",
                    geometry={"x": x0 + unit_width * (.25 + j * .5) - .60,
                              "y": outer_y, "width": 1.20},
                    relationships={"serves": [f"{uid}-bedroom-{j+1}"]},
                    metadata={"type": "window", "unit_id": uid, "status": "schematic"},
                ))
    # Shared centerline partitions, not double-counted per unit.
    for x in (0.0, width / 2, width):
        model.walls.append(Element(
            id=f"wall-vertical-{int(x * 100)}",
            geometry={"x": x, "y": 0.0, "length": depth},
            metadata={"type": "wall_centerline", "axis": "vertical", "status": "schematic"},
        ))
    for y in (0.0, unit_depth, unit_depth + 2.0, depth):
        model.walls.append(Element(
            id=f"wall-horizontal-{int(y * 100)}",
            geometry={"x": 0.0, "y": y, "length": width},
            metadata={"type": "wall_centerline", "axis": "horizontal", "status": "schematic"},
        ))
    model.validate()
    return model
