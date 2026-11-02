"""Regression checks for four-unit conceptual floor zoning."""
import pytest

from mcp_cad_cloud.multifamiliar import build_four_apartment_floor
from mcp_cad_cloud.project_model import ProjectModel, ProjectModelError


def test_four_distinct_units_and_shared_corridor():
    model = build_four_apartment_floor()
    units = [r for r in model.rooms if r.metadata.get("type") == "apartment_zone"]
    assert len(units) == 4
    assert {r.metadata["unit_id"] for r in units} == {"AP01", "AP02", "AP03", "AP04"}
    assert len([r for r in model.rooms if r.id == "common-corridor"]) == 1
    assert ProjectModel.from_json(model.to_json()).to_dict() == model.to_dict()


@pytest.mark.parametrize("width,depth", [(15, 18), (24, 13), (0, 18)])
def test_reject_undersized_floor(width, depth):
    with pytest.raises(ProjectModelError):
        build_four_apartment_floor(width=width, depth=depth)
