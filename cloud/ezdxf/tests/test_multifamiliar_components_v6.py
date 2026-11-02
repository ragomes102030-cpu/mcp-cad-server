"""Regression gate for four-apartment parametric components, V5 routes and real A3."""
import json
from pathlib import Path

import ezdxf
import pytest

from mcp_cad_cloud.components import CATALOG, adopt_component, read_component
from mcp_cad_cloud.multifamiliar_arch_v6 import (
    audit_apartment_components, generate_multifamily_v6,
)


@pytest.fixture(scope="module")
def v6_files(tmp_path_factory):
    return generate_multifamily_v6(tmp_path_factory.mktemp("multifamiliar_v6"))


def test_four_units_have_five_semantic_components_each(v6_files):
    doc = ezdxf.readfile(v6_files["dxf"])
    tagged = [e for e in doc.modelspace().query("LWPOLYLINE")
              if e.has_xdata("MCP_CAD")]
    assert len(tagged) == 20
    for uid in ("AP01", "AP02", "AP03", "AP04"):
        components = [read_component(e) for e in tagged
                      if read_component(e)["unit_id"] == uid]
        assert len(components) == 5
        assert sorted(x["kind"] for x in components) == sorted(
            ["bed_double", "bed_double", "dining_table",
             "shower_existing", "washbasin_existing"])
    assert not doc.audit().has_errors
    assert "ARQ-01 A3 REV06" in doc.layouts
    assert "ARQ-02 A3 ESCADA REV06" in doc.layouts


def test_audits_cover_doors_windows_walls_and_circulation(v6_files):
    audit = json.loads(Path(v6_files["audit"]).read_text(encoding="utf-8"))
    assert audit["ok"], audit["errors"]
    assert audit["components"] == 20
    assert audit["doors"] == 21
    assert audit["window_segments"] >= 60
    assert audit["dxf_audit_errors"] == 0
    assert all(r["connected"] for r in audit["functional_routes"].values())


def test_real_two_page_vector_a3_pdf(v6_files):
    pdf = Path(v6_files["pdf"])
    assert pdf.stat().st_size > 15000
    assert pdf.read_bytes().startswith(b"%PDF-")
    fitz = pytest.importorskip("fitz")
    with fitz.open(pdf) as pages:
        assert len(pages) == 2
        for page in pages:
            assert page.rect.width == pytest.approx(420 / 25.4 * 72, abs=1)
            assert page.rect.height == pytest.approx(297 / 25.4 * 72, abs=1)
        assert "REVISAO 06" in pages[0].get_text()
        assert "20 COMPONENTES" in pages[0].get_text()


def test_wall_intersection_is_rejected(v6_files):
    doc = ezdxf.readfile(v6_files["dxf"])
    doc.modelspace().add_line((3.6, 4.5), (5.0, 6.4),
                              dxfattribs={"layer": "ARQ-PAREDES"})
    result = audit_apartment_components(doc)
    assert not result["ok"]
    assert any("collides with wall" in e for e in result["errors"])


def test_adoption_fails_for_wrong_geometry():
    doc = ezdxf.new()
    doc.layers.new("ARQ-MOBILIARIO")
    ent = doc.modelspace().add_lwpolyline(
        [(0, 0), (1, 0), (1, 1), (0, 1)], close=True,
        dxfattribs={"layer": "ARQ-MOBILIARIO"})
    with pytest.raises(ValueError, match="does not match"):
        adopt_component(doc, ent, "bed_double", (0, 0), unit_id="AP01")
    assert not ent.has_xdata("MCP_CAD")


def test_upper_unit_furniture_repositioned_out_of_door_swing(v6_files):
    doc = ezdxf.readfile(v6_files["dxf"])
    for e in doc.modelspace().query("LWPOLYLINE"):
        if not e.has_xdata("MCP_CAD"):
            continue
        info = read_component(e)
        if info["unit_id"] not in ("AP03", "AP04"):
            continue
        ymin = min(p[1] for p in e.get_points("xy"))
        if info["kind"] == "dining_table":
            assert ymin == pytest.approx(15.45)
        if info["kind"] == "washbasin_existing":
            assert ymin == pytest.approx(18.55)
