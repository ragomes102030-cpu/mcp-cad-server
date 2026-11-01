"""Export a real CAD-based architectural study PDF and DXF."""
from pathlib import Path
import ezdxf
from mcp_cad_cloud.multifamiliar_arch_v2 import generate_multifamily_architectural_v2


def test_architectural_v2_export(tmp_path):
    files = generate_multifamily_architectural_v2(tmp_path)
    assert files["status"] == "architectural_study_not_code_approved"
    assert Path(files["pdf"]).read_bytes().startswith(b"%PDF-")
    doc = ezdxf.readfile(files["dxf"])
    assert not doc.audit().has_errors
    m = doc.modelspace()
    assert len(m.query("ARC")) >= 12
    assert len(m.query("LINE")) >= 100
    assert len(m.query("TEXT")) >= 25
