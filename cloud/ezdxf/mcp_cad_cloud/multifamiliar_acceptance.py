"""Architectural acceptance gate independent of DXF file validity.

The multifamily pilot must not be presented as an approved architectural plan
until actual doors, windows, internal walls and stairs are modeled and audited.
"""
from __future__ import annotations

from .project_model import ProjectModel


def audit_multifamily_architecture(model: ProjectModel) -> dict:
    model.validate()
    errors = []
    units = {f"AP{i:02d}" for i in range(1, 5)}
    for uid in sorted(units):
        rooms = [r for r in model.rooms if r.metadata.get("unit_id") == uid]
        room_types = {r.metadata.get("type") for r in rooms}
        for required in ("living-kitchen", "bedroom-1", "bedroom-2",
                         "bathroom", "laundry", "hall"):
            if required not in room_types:
                errors.append(f"{uid}: missing {required}")
        walls = [w for w in model.walls if w.metadata.get("unit_id") == uid
                 and w.metadata.get("type") == "partition"]
        if not walls:
            errors.append(f"{uid}: interior walls not constructed")
        doors = [o for o in model.openings if o.metadata.get("unit_id") == uid
                 and o.metadata.get("type") == "door"
                 and o.metadata.get("status") == "detailed"
                 and o.metadata.get("swing") in {"left", "right"}]
        if len(doors) < 5:
            errors.append(f"{uid}: interior doors and door swings not detailed")
        windows = [o for o in model.openings if o.metadata.get("unit_id") == uid
                   and o.metadata.get("type") == "window"
                   and o.metadata.get("status") == "detailed"]
        if len(windows) < 2:
            errors.append(f"{uid}: facade windows not detailed")
    stairs = [r for r in model.rooms if r.metadata.get("type") == "stair_core"
              and r.metadata.get("status") == "detailed"]
    if not stairs:
        errors.append("common core: stairs not designed")
    if not any(r.metadata.get("type") == "common_circulation"
               for r in model.rooms):
        errors.append("common circulation missing")
    return {"ok": not errors, "errors": errors,
            "stage": "architectural_acceptance",
            "note": "Passing this structural gate alone does not certify code compliance."}


def require_architectural_acceptance(model: ProjectModel) -> None:
    result = audit_multifamily_architecture(model)
    if not result["ok"]:
        raise ValueError("Architectural drawing rejected: " + "; ".join(result["errors"]))
