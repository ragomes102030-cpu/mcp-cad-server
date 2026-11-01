"""Smoke test real DXF-backed PDF export for multifamily concept."""
import ezdxf

from mcp_cad_cloud.multifamiliar_export import generate_multifamily_preview


def test_multifamily_preview_exports_real_dxf_and_a3_pdf(tmp_path):
    result = generate_multifamily_preview(tmp_path)
    assert result["status"] == "concept_preview_not_validated"
    from pathlib import Path
    pdf = Path(result["pdf"])
    dxf = Path(result["dxf"])
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert pdf.stat().st_size > 1000
    doc = ezdxf.readfile(dxf)
    assert not doc.audit().has_errors
    assert len(doc.modelspace()) > 30
