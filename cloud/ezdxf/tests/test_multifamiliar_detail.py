"""Regression checks for the preliminary four-apartment geometric model."""
from mcp_cad_cloud.multifamiliar_detail import build_detailed_four_apartment_floor
from mcp_cad_cloud.project_model import ProjectModel


def test_detailed_floor_has_four_subdivided_units():
    model = build_detailed_four_apartment_floor()
    assert len([r for r in model.rooms if r.metadata.get("type") == "apartment_zone"]) == 4
    for uid in ("AP01", "AP02", "AP03", "AP04"):
        assert len([r for r in model.rooms if r.metadata.get("unit_id") == uid and r.metadata.get("status") == "preliminary_zone"]) == 3
        assert len([w for w in model.walls if w.metadata.get("unit_id") == uid]) == 2
        assert len([o for o in model.openings if o.metadata.get("unit_id") == uid]) == 2


def test_detailed_floor_serialization_and_corridor_connections():
    model = build_detailed_four_apartment_floor()
    restored = ProjectModel.from_json(model.to_json())
    assert restored.to_dict() == model.to_dict()
    entrances = [o for o in model.openings if o.metadata.get("type") == "door"]
    assert len(entrances) == 4
    assert all("common-corridor" in e.relationships["connects"] for e in entrances)
