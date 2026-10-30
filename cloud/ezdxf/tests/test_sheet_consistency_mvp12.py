"""Mutation tests: geometrically plausible but incorrect sheets must fail closed.

These tests intentionally preserve XDATA IDs and sheet boundaries; the old
presence-only audit accepted the corruptions.
"""
import io

import ezdxf

from mcp_cad_cloud.auditoria_prancha import audit_sheet_document
from test_prancha_licenciamento import (
    api as sheet_api_fixture,
    package as package_fixture,
    spec,
    title_block,
)


def _reopened():
    api = sheet_api_fixture.__wrapped__()
    package = package_fixture.__wrapped__()
    sheet = api.compose_licensing_sheets(
        package, [spec(api)], title_block(api)
    )[0]
    stream = io.StringIO()
    sheet.document.write(stream)
    return package, sheet.spec, ezdxf.read(io.StringIO(stream.getvalue()))


def _by_source(doc, source_prefix, kind):
    return next(
        entity for entity in doc.modelspace()
        if entity.dxftype() == kind
        and entity.has_xdata("MCP_CAD")
        and str(entity.get_xdata("MCP_CAD")[0].value).startswith(source_prefix)
    )


def _codes(result):
    return {item["code"] for item in result["errors"]}


def test_valid_reopened_sheet_still_passes_strict_geometry():
    package, sheet, doc = _reopened()
    result = audit_sheet_document(doc, sheet, package)
    assert result["ok"], result


def test_wall_shift_with_same_source_id_is_rejected():
    package, sheet, doc = _reopened()
    entity = _by_source(doc, "wall:outline:", "LINE")
    start = entity.dxf.start
    end = entity.dxf.end
    entity.dxf.start = (start.x + 0.6, start.y, start.z)
    entity.dxf.end = (end.x + 0.6, end.y, end.z)
    result = audit_sheet_document(doc, sheet, package)
    assert "source-geometry-mismatch" in _codes(result)


def test_wall_wrong_layer_with_same_source_id_is_rejected():
    package, sheet, doc = _reopened()
    entity = _by_source(doc, "wall:outline:", "LINE")
    entity.dxf.layer = "LOTE"
    result = audit_sheet_document(doc, sheet, package)
    assert "source-layer-mismatch" in _codes(result)


def test_duplicate_wall_geometry_with_same_source_id_is_rejected():
    package, sheet, doc = _reopened()
    entity = _by_source(doc, "wall:outline:", "LINE")
    duplicated = doc.modelspace().add_line(
        entity.dxf.start, entity.dxf.end, dxfattribs={"layer": entity.dxf.layer}
    )
    duplicated.set_xdata("MCP_CAD", [
        (1000, entity.get_xdata("MCP_CAD")[0].value)
    ])
    result = audit_sheet_document(doc, sheet, package)
    assert "source-entity-extra" in _codes(result)


def test_scale_text_must_match_physical_viewport_scale():
    package, sheet, doc = _reopened()
    scale_text = next(entity for entity in doc.modelspace().query("TEXT")
                      if entity.dxf.text.startswith("ESCALA:"))
    scale_text.dxf.text = scale_text.dxf.text.replace("1:50", "1:75")
    result = audit_sheet_document(doc, sheet, package)
    assert "sheet-scale-mismatch" in _codes(result)


def test_altered_dimension_label_is_rejected_even_with_same_id():
    package, sheet, doc = _reopened()
    label = _by_source(doc, "dimension-label:", "TEXT")
    label.dxf.text = "999,99 m"
    result = audit_sheet_document(doc, sheet, package)
    assert "source-label-mismatch" in _codes(result)
