"""Regressoes do motor arquitetonico da revisao 05."""
import json
from pathlib import Path

import ezdxf
import pytest

from mcp_cad_cloud.multifamiliar_arch_v4 import generate_multifamily_v4
from mcp_cad_cloud.multifamiliar_arch_v5 import (
    FunctionalValidationError,
    audit_functional_v5,
    correct_living_room_interferences,
    correct_stair_access_door,
    design_stair,
    generate_multifamily_v5,
)


@pytest.fixture(scope="module")
def baseline(tmp_path_factory):
    return Path(generate_multifamily_v4(tmp_path_factory.mktemp("baseline_v4"))["dxf"])


def test_stair_calculated_for_three_metres():
    stair = design_stair(3.0)
    assert stair.risers == 18
    assert stair.risers_per_flight == 9
    assert stair.treads_per_flight == 8
    assert stair.riser_height_m == pytest.approx(1 / 6, abs=0.00001)
    assert stair.comfort_2h_plus_p_m == pytest.approx(0.62333, abs=0.00001)


@pytest.mark.parametrize("height", (2.2, 2.5, 3.5, 4.1))
def test_reject_unsupported_floor_heights(height):
    with pytest.raises(FunctionalValidationError):
        design_stair(height)


def test_functional_qa_rejects_original_furniture_and_door(baseline):
    doc = ezdxf.readfile(baseline)
    report = audit_functional_v5(doc, design_stair())
    assert report["ok"] is False
    assert any("bloqueada" in e or "obstrui" in e for e in report["errors"])


def test_real_furniture_and_door_correction_passes(baseline):
    doc = ezdxf.readfile(baseline)
    changes = correct_living_room_interferences(doc)
    assert changes["removed_or_repositioned"] >= 4
    assert correct_stair_access_door(doc)
    report = audit_functional_v5(doc, design_stair())
    assert report["ok"], report["errors"]
    assert all(r["connected"] for r in report["routes"].values())


def test_missing_door_is_rejected(baseline):
    doc = ezdxf.readfile(baseline)
    correct_living_room_interferences(doc)
    correct_stair_access_door(doc)
    door = next(iter(doc.modelspace().query('ARC[layer=="ARQ-PORTAS"]')))
    doc.modelspace().delete_entity(door)
    report = audit_functional_v5(doc, design_stair())
    assert not report["ok"]


def test_rev05_dxfs_and_two_real_a3_pdf_pages(tmp_path, baseline):
    files = generate_multifamily_v5(tmp_path, base_dxf=baseline)
    assert files["status"] == "functional_preliminary_checks_passed_not_normative"
    dxf, pdf = Path(files["dxf"]), Path(files["pdf"])
    assert pdf.read_bytes().startswith(b"%PDF-")
    doc = ezdxf.readfile(dxf)
    assert not doc.audit().has_errors
    assert "ARQ-01 A3 REV05" in doc.layouts
    assert "ARQ-02 A3 ESCADA" in doc.layouts
    assert len([e for e in doc.modelspace().query("LINE")
                if e.dxf.layer == "ARQ-ESCADA-PISOS"]) == 16
    audit = json.loads(Path(files["audit"]).read_text())
    assert audit["ok"] and not audit["errors"]
    assert audit["pdf_a3_pages"] == 2
    assert audit["dxf_audit_errors"] == 0
    fitz = pytest.importorskip("fitz")
    with fitz.open(pdf) as pages:
        assert len(pages) == 2
        assert all(page.rect.width == pytest.approx(420 / 25.4 * 72, abs=1)
                   for page in pages)
        assert "REVISAO 05" in pages[0].get_text()
        assert "18 ESPELHOS" in pages[1].get_text()
