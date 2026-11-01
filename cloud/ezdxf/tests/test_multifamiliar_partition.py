"""Regression tests for the preliminary partitioned multifamily floor."""
import pytest

from mcp_cad_cloud.multifamiliar_partition import build_partitioned_four_apartment_floor
from mcp_cad_cloud.project_model import ProjectModel, ProjectModelError


def test_four_apartments_have_six_spaces_and_external_windows():
    model = build_partitioned_four_apartment_floor()
    for number in range(1, 5):
        unit = f"AP{number:02d}"
        spaces = [r for r in model.rooms if r.metadata.get("unit_id") == unit]
        assert len(spaces) == 6
        assert {r.metadata["type"] for r in spaces} == {
            "living-kitchen", "bathroom", "laundry", "hall",
            "bedroom-1", "bedroom-2",
        }
        assert len([o for o in model.openings if o.metadata.get("unit_id") == unit
                    and o.metadata.get("type") == "window"]) == 2
        entrances = [o for o in model.openings if o.id == f"{unit}-entrance"]
        assert len(entrances) == 1
        assert "common-corridor" in entrances[0].relationships["connects"]
    assert ProjectModel.from_json(model.to_json()).to_dict() == model.to_dict()


def test_room_areas_partition_unit_rectangle():
    model = build_partitioned_four_apartment_floor()
    for unit in ("AP01", "AP02", "AP03", "AP04"):
        rooms = [r for r in model.rooms if r.metadata.get("unit_id") == unit]
        assert sum(r.geometry["width"] * r.geometry["depth"] for r in rooms) == pytest.approx(96.0)


@pytest.mark.parametrize("width,depth", [(15, 18), (24, 13)])
def test_reject_small_dimensions(width, depth):
    with pytest.raises(ProjectModelError):
        build_partitioned_four_apartment_floor(width=width, depth=depth)
