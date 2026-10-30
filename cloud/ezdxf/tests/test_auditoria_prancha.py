from copy import deepcopy
import importlib
import importlib.util
import io

import ezdxf
import pytest

from test_prancha_licenciamento import (
    api as sheet_api_fixture,
    package as package_fixture,
    spec,
    title_block,
)


def load_auditor():
    module = "mcp_cad_cloud.auditoria_prancha"
    assert importlib.util.find_spec(module) is not None, f"missing production module: {module}"
    return importlib.import_module(module)


def serialized_sheet():
    sheet_api = sheet_api_fixture.__wrapped__()
    package = package_fixture.__wrapped__()
    sheet = sheet_api.compose_licensing_sheets(
        package, [spec(sheet_api)], title_block(sheet_api)
    )[0]
    stream = io.StringIO()
    sheet.document.write(stream)
    reopened = ezdxf.read(io.StringIO(stream.getvalue()))
    return package, sheet.spec, reopened


def test_reopened_sheet_passes_independent_entity_audit():
    auditor = load_auditor()
    package, spec, doc = serialized_sheet()

    result = auditor.audit_sheet_document(doc, spec, package)

    assert result["ok"] is True, result
    assert result["errors"] == []
    assert result["source_entities_checked"] > 0
    assert result["sheet_id"] == "ARQ-01"


def test_missing_source_geometry_is_detected_after_serialization():
    auditor = load_auditor()
    package, spec, doc = serialized_sheet()
    entity = next(
        entity for entity in doc.modelspace().query("LINE")
        if entity.has_xdata("MCP_CAD")
        and entity.get_xdata("MCP_CAD")[0].value.startswith("wall:outline:")
    )
    doc.modelspace().delete_entity(entity)

    result = auditor.audit_sheet_document(doc, spec, package)

    assert result["ok"] is False
    assert "source-entity-missing" in {item["code"] for item in result["errors"]}


def test_missing_inner_partition_face_is_detected_after_serialization():
    auditor = load_auditor()
    package, spec, doc = serialized_sheet()
    floor_plan = next(view for view in package.views if view.view_id == "ARQ-PLANTA")
    expected_source = next(
        segment.source_id for segment in floor_plan.segments
        if segment.layer == "PAREDES"
        and abs(segment.y1-4.775) < 1e-8
        and abs(segment.y2-4.775) < 1e-8
    )
    entity = next(
        entity for entity in doc.modelspace().query("LINE")
        if entity.has_xdata("MCP_CAD")
        and entity.get_xdata("MCP_CAD")[0].value == expected_source
    )
    doc.modelspace().delete_entity(entity)

    result = auditor.audit_sheet_document(doc, spec, package)

    assert result["ok"] is False
    missing = [item["message"] for item in result["errors"]
               if item["code"] == "source-entity-missing"]
    assert any(expected_source in message for message in missing)


def test_missing_overall_dimension_is_detected_after_serialization():
    auditor = load_auditor()
    package, spec, doc = serialized_sheet()
    entity = next(
        entity for entity in doc.modelspace().query("LINE")
        if entity.has_xdata("MCP_CAD")
        and entity.get_xdata("MCP_CAD")[0].value == "dimension:overall:width"
    )
    doc.modelspace().delete_entity(entity)

    result = auditor.audit_sheet_document(doc, spec, package)

    assert result["ok"] is False
    assert "source-entity-missing" in {item["code"] for item in result["errors"]}


def test_wrong_units_and_out_of_sheet_geometry_are_detected():
    auditor = load_auditor()
    package, spec, doc = serialized_sheet()
    doc.header["$INSUNITS"] = ezdxf.units.M
    line = next(entity for entity in doc.modelspace().query("LINE")
                if entity.dxf.layer == "FOLHA")
    line.dxf.start = (-10.0, line.dxf.start.y, 0.0)

    result = auditor.audit_sheet_document(doc, spec, package)

    codes = {item["code"] for item in result["errors"]}
    assert {"units-not-mm", "entity-outside-sheet"} <= codes


def test_missing_title_block_field_is_detected():
    auditor = load_auditor()
    package, spec, doc = serialized_sheet()
    text = next(entity for entity in doc.modelspace().query("TEXT")
                if "RESPONSÁVEL TÉCNICO:" in entity.dxf.text)
    doc.modelspace().delete_entity(text)

    result = auditor.audit_sheet_document(doc, spec, package)

    assert result["ok"] is False
    assert "title-field-missing" in {item["code"] for item in result["errors"]}


def test_wrong_sheet_number_and_non_line_geometry_outside_bounds_are_detected():
    auditor = load_auditor()
    package, spec, doc = serialized_sheet()
    title = next(entity for entity in doc.modelspace().query("TEXT")
                 if entity.dxf.text.startswith("PRANCHA: ARQ-01"))
    title.dxf.text = title.dxf.text.replace("ARQ-01", "ARQ-99")
    doc.modelspace().add_circle((450.0, 300.0), 10.0)

    result = auditor.audit_sheet_document(doc, spec, package)

    codes = {item["code"] for item in result["errors"]}
    assert {"title-field-missing", "entity-outside-sheet"} <= codes

