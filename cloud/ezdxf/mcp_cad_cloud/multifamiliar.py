"""Pilot multifamily floor model: four independent apartments and common circulation.

Geometry is conceptual and in metres. This is not a code-compliance certificate.
"""
from __future__ import annotations

from .project_model import Element, ProjectModel, ProjectModelError


def build_four_apartment_floor(*, width: float = 24.0, depth: float = 18.0) -> ProjectModel:
    """Create four apartment zones around a continuous central common corridor.

    The stair core is represented as a reserved zone; detailed stairs, doors,
    windows, shared wall topology and DXF output are subsequent milestones.
    """
    if width < 16 or depth < 14:
        raise ProjectModelError("pilot requires width >= 16m and depth >= 14m")
    corridor_width = 2.0
    half_width = width / 2
    apartment_depth = (depth - corridor_width) / 2
    rooms = []
    for row, y in enumerate((0.0, apartment_depth)):
        if row == 1:
            y += corridor_width
        for col, x in enumerate((0.0, half_width)):
            number = row * 2 + col + 1
            rooms.append(Element(
                id=f"apt-{number:02d}",
                geometry={"x": x, "y": y, "width": half_width, "depth": apartment_depth},
                metadata={"type": "apartment_zone", "unit_id": f"AP{number:02d}", "private": True},
            ))
    rooms.append(Element(
        id="common-corridor",
        geometry={"x": 0.0, "y": apartment_depth, "width": width, "depth": corridor_width},
        metadata={"type": "common_circulation", "private": False},
    ))
    rooms.append(Element(
        id="stair-reservation",
        geometry={"x": width / 2 - 2, "y": apartment_depth, "width": 4.0, "depth": corridor_width},
        metadata={"type": "stair_core_reservation", "private": False, "status": "not_detailed"},
    ))
    model = ProjectModel(
        project_id="multifamily-four-units-pilot",
        lot={"width": width, "depth": depth},
        rooms=rooms,
    )
    model.validate()
    return model
