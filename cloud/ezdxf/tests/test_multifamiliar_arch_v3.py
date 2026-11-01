"""Regressions: structural wall union, circulation, openings, A3 title block."""
import json
from pathlib import Path

import ezdxf
import pytest
from shapely.geometry import LineString, Point, box
from mcp_cad_cloud.multifamiliar_arch_v3 import (
    _build_geometry, audit_multifamily_internal, generate_multifamily_v3,
    ArchitecturalValidationError, STAIR,
)


def test_clean_wall_material_and_uninterrupted_shared_corridor():
    material, raw, openings, spaces = _build_geometry()
    assert material.is_valid
    assert material.geom_type in {"Polygon", "MultiPolygon"}
    assert not material.intersects(LineString([(3.25, 13), (26.85, 13)]))
    audit = audit_multifamily_internal(material, raw, openings, spaces)
    assert audit["ok"]
    assert audit["corridor_clear_width_m"] == pytest.approx(2.0)


def test_circulation_cross_wall_regression_rejected():
    material, raw, openings, spaces = _build_geometry()
    obstruction = box(14.91, 12.1, 15.09, 13.9)
    report = audit_multifamily_internal(
        material.union(obstruction), raw.union(obstruction), openings, spaces
    )
    assert report["ok"] is False
    assert any("corredor" in problem.lower() for problem in report["errors"])


def test_all_apartments_have_unblocked_internal_access_and_exterior_windows():
    material, raw, openings, spaces = _build_geometry()
    for uid in ("AP01", "AP02", "AP03", "AP04"):
        doors = [op for op in openings if op.type == "door" and op.unit == uid]
        assert len(doors) == 5
        assert len([op for op in openings if op.type == "window" and op.unit == uid]) == 5
        for op in doors:
            assert op.axis == "h"
            mid = Point((op.start + op.end) / 2, op.wall_coord)
            assert raw.covers(mid)
            assert material.distance(mid) > .01, op.id
            door_leaf = LineString([
                (op.start, op.wall_coord + .12 * op.side),
                (op.start, op.wall_coord + (op.width - .04) * op.side),
            ])
            assert not material.intersects(door_leaf), op.id
    for op in openings:
        if op.type == "window" and op.axis == "v" and op.wall_coord == 27:
            assert op.end <= STAIR[1] or op.start >= STAIR[3]


def test_cad_dxfs_and_pdf_a3_rendered_from_same_architectural_model(tmp_path):
    files = generate_multifamily_v3(tmp_path)
    dxf, pdf = Path(files["dxf"]), Path(files["pdf"])
    doc = ezdxf.readfile(dxf)
    assert not doc.audit().has_errors
    assert "ARQ-01 A3" in doc.layouts
    sheet = doc.layouts.get("ARQ-01 A3")
    assert len([v for v in sheet.query("VIEWPORT") if v.dxf.id != 1]) == 1
    assert any("CARIMBO" in e.dxf.text for e in sheet.query("TEXT"))
    assert len(doc.modelspace().query("ARC")) == 21
    assert len(doc.modelspace().query("LWPOLYLINE")) >= 20
    fitz = pytest.importorskip('fitz', reason='PDF page checks run in dedicated A3 workflow')
    with fitz.open(pdf) as document:
        assert len(document) == 1
        page = document[0]
        assert page.rect.width == pytest.approx(420 / 25.4 * 72, abs=1)
        assert page.rect.height == pytest.approx(297 / 25.4 * 72, abs=1)
        assert all(part in page.get_text() for part in ("REVISAO 03", "TERRENO", "NAO UTILIZAR"))
    audit = json.loads(Path(files["audit"]).read_text())
    assert audit["ok"] and not audit["errors"]
    assert audit["doors"] == 21
    assert audit["windows"] == 20
    assert audit["dxf_audit_errors"] == 0
