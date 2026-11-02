import pytest
import ezdxf
from mcp_cad_cloud.component_placement import PlacementError, place_checked

def test_places_component_inside_empty_room():
    doc = ezdxf.new()
    entity = place_checked(doc, "toilet", (2, 2), (0, 0, 5, 5))
    assert entity.dxf.layer == "ARQ-MOBILIARIO"

def test_rejects_room_boundary_without_mutation():
    doc = ezdxf.new()
    with pytest.raises(PlacementError, match="outside room"):
        place_checked(doc, "sofa", (4, 4), (0, 0, 5, 5))
    assert len(doc.modelspace()) == 0

def test_rejects_existing_fixture():
    doc = ezdxf.new()
    place_checked(doc, "toilet", (2, 2), (0, 0, 6, 6), clearance_m=0)
    with pytest.raises(PlacementError, match="collides"):
        place_checked(doc, "toilet", (2, 2), (0, 0, 6, 6), clearance_m=0)

def test_rejects_wall():
    doc = ezdxf.new()
    doc.layers.new("ARQ-PAREDES")
    doc.modelspace().add_line((2, 0), (2, 6), dxfattribs={"layer":"ARQ-PAREDES"})
    with pytest.raises(PlacementError, match="collides"):
        place_checked(doc, "bed_single", (1.5, 2), (0, 0, 6, 6), clearance_m=0)

def test_rejects_door_swing():
    doc = ezdxf.new()
    doc.layers.new("ARQ-PORTAS")
    doc.modelspace().add_arc((2, 2), 1, 0, 90, dxfattribs={"layer":"ARQ-PORTAS"})
    with pytest.raises(PlacementError, match="door swing"):
        place_checked(doc, "toilet", (2.7, 2.2), (0, 0, 6, 6), clearance_m=0)
