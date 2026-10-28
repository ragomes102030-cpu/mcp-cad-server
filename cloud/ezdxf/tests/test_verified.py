"""Headless CAD smoke regression: actual entities and DXF roundtrip."""
import base64
import io
import tempfile
import zipfile
import ezdxf
from mcp_cad_cloud import tools_verified as cad

def test_create_export_roundtrip():
    assert cad.new_drawing("QA")["ok"]
    assert cad.layer_create("PAREDES", 1)["created"]
    line = cad.draw_line([0, 0], [4, 0], "PAREDES")
    assert line["ok"] and line["handle"]
    assert cad.draw_rectangle([0, 0], [8, 10], "PAREDES")["ok"]
    assert cad.draw_circle([1, 1], 0.4)["ok"]
    assert cad.draw_arc([4, 2], 0.8, 0, 90)["ok"]
    assert cad.draw_text("Sala", [2, 2], 0.2)["ok"]
    assert cad.dim_aligned([0, 0], [8, 0], 0.4)["ok"]
    before = cad.inspect_drawing()
    assert before["entities"] == 6
    assert before["by_type"]["DIMENSION"] == 1
    assert cad.drawing_audit()["ok"]
    result = cad.export_dxf(incluir_base64=True)
    assert result["ok"]
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(result["data_base64"]))) as z:
        dxf_bytes = z.read("desenho.dxf")
    handle, filename = tempfile.mkstemp(suffix=".dxf")
    try:
        with open(handle, "wb", closefd=False) as exported:
            exported.write(dxf_bytes)
        doc = ezdxf.readfile(filename)
    finally:
        import os
        os.close(handle)
        os.unlink(filename)
    assert len(doc.modelspace()) == before["entities"]
    assert doc.header["$INSUNITS"] == 6
    assert sum(1 for e in doc.modelspace() if e.dxftype() == "LINE") == 1
    assert cad.erase(line["handle"], False)["preview"]
    assert cad.inspect_drawing()["entities"] == before["entities"]
    assert cad.erase(line["handle"], True)["deleted"]
    assert cad.inspect_drawing()["entities"] == before["entities"] - 1

def test_invalid_inputs_do_not_mutate():
    cad.new_drawing("validation")
    assert cad.draw_circle([0, 0], -1)["ok"] is False
    assert cad.draw_rectangle([10, 10], [5, 5])["ok"] is False
    assert cad.draw_line([0, 0], [float("nan"), 1])["ok"] is False
    assert cad.draw_line([0, 0], [2, 2], "UNKNOWN")["ok"] is False
    assert cad.inspect_drawing()["entities"] == 0

def test_no_fake_success_stubs():
    forbidden = {"command_line", "script", "plot_pdf", "drawing_export_dwg",
                 "system_run_command", "move_entity"}
    assert forbidden.isdisjoint(set(cad.TOOLS))
    assert len(cad.TOOLS) == len(set(cad.TOOLS))
    assert all(callable(getattr(cad, n)) for n in cad.TOOLS)
