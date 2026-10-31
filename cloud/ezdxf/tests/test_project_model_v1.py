"""Contract tests for the CAD-independent MVP 1.0 project model."""
import json
import pytest

from mcp_cad_cloud.project_model import Element, ProjectModel, ProjectModelError


def example():
    return ProjectModel(
        project_id="house-001", lot={"width": 10, "depth": 20},
        rooms=[Element("room-1", {"x": 0, "y": 0, "width": 4, "depth": 3})],
        walls=[Element("wall-1", {"x": 0, "y": 0, "length": 4, "thickness": .15},
                       {"rooms": ["room-1"]})],
        openings=[Element("door-1", {"x": 1, "y": 0, "width": .8},
                          {"walls": ["wall-1"]})],
    )


def test_roundtrip_preserves_ids_relationships_and_revision():
    original = example()
    original.revision = 3
    restored = ProjectModel.from_json(original.to_json())
    assert restored.to_dict() == original.to_dict()
    assert restored.openings[0].relationships["walls"] == ["wall-1"]


@pytest.mark.parametrize("mutate", [
    lambda m: setattr(m.rooms[0], "id", "wall-1"),
    lambda m: m.openings[0].relationships.update(walls=["missing"]),
    lambda m: m.rooms[0].geometry.update(width=-1),
    lambda m: m.rooms[0].geometry.update(x=float("nan")),
    lambda m: m.lot.update(width=float("inf")),
    lambda m: setattr(m, "revision", -1),
    lambda m: setattr(m, "schema_version", 2),
    lambda m: setattr(m, "units", "cm"),
    lambda m: m.rooms[0].metadata.update(note=object()),
])
def test_invalid_model_rejected(mutate):
    model = example()
    mutate(model)
    with pytest.raises(ProjectModelError):
        model.validate()


def test_missing_schema_version_is_not_silently_assumed():
    raw = example().to_dict()
    raw.pop("schema_version")
    with pytest.raises(ProjectModelError):
        ProjectModel.from_dict(raw)


def test_nonfinite_json_rejected():
    payload = example().to_json().replace('"revision": 0', '"revision": NaN')
    with pytest.raises(ProjectModelError):
        ProjectModel.from_json(payload)


def test_json_is_plain_and_deterministic():
    model = example()
    assert json.loads(model.to_json())["project_id"] == "house-001"
    assert model.to_json() == model.to_json()
