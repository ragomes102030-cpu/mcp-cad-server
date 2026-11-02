import pytest
import ezdxf
from mcp_cad_cloud.components import CATALOG, Component, footprint, place_component, read_component

def test_catalog_has_required_architectural_fixtures():
    assert {"bed_double", "sofa", "wardrobe", "kitchen_sink", "toilet", "shower"} <= CATALOG.keys()

def test_reject_invalid_dimensions_and_coordinates():
    with pytest.raises(ValueError):
        Component("bad", -1, 2)
    with pytest.raises(ValueError):
        footprint(CATALOG["sofa"], (float("nan"), 0))

def test_rotation_preserves_dimensions():
    pts = footprint(Component("test", 2, 1), (5, 6), 90)
    assert pts[0] == (5, 6)
    assert pts[1][0] == pytest.approx(5)
    assert pts[1][1] == pytest.approx(8)

def test_dxf_roundtrip_preserves_editable_metadata(tmp_path):
    doc = ezdxf.new("R2010")
    ent = place_component(doc, "toilet", (2, 3), 90)
    assert ent.closed
    assert read_component(ent)["kind"] == "toilet"
    target = tmp_path / "components.dxf"
    doc.saveas(target)
    reopened = ezdxf.readfile(target)
    assert not reopened.audit().has_errors
    restored = list(reopened.modelspace().query("LWPOLYLINE"))
    assert len(restored) == 1
    assert read_component(restored[0])["angle_deg"] == 90

def test_unknown_component_fails_closed():
    with pytest.raises(KeyError):
        place_component(ezdxf.new(), "unknown", (0, 0))
