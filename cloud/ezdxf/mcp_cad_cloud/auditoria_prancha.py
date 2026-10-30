"""Independent checks over serialized, reopened licensing-sheet DXFs."""
from __future__ import annotations

from collections import Counter
from math import isfinite


def _source_id(entity) -> str | None:
    if not entity.has_xdata("MCP_CAD"):
        return None
    values = entity.get_xdata("MCP_CAD")
    return str(values[0].value) if values else None


def _entity_points(entity):
    try:
        from ezdxf import bbox
        extents = bbox.extents([entity], fast=True)
        if extents.has_data:
            return (extents.extmin, extents.extmax)
    except Exception:
        # Fall back to explicit coordinates for entity types whose extent
        # implementation is unavailable in this ezdxf version.
        pass
    kind = entity.dxftype()
    if kind == "LINE":
        return (entity.dxf.start, entity.dxf.end)
    if kind in {"TEXT", "INSERT", "POINT"}:
        return (entity.dxf.insert if kind != "POINT" else entity.dxf.location,)
    if kind == "LWPOLYLINE":
        return tuple(entity.vertices())
    return ()


def audit_sheet_document(doc, spec, package) -> dict:
    """Check a reopened sheet against declared package geometry and metadata."""
    errors: list[dict] = []

    def error(code: str, message: str):
        errors.append({"code": code, "message": message})

    if int(doc.header.get("$INSUNITS", 0)) != 4:
        error("units-not-mm", "DXF da prancha não está em milímetros.")
    paper_sizes = {"A0": (1189.0, 841.0), "A1": (841.0, 594.0),
                   "A2": (594.0, 420.0), "A3": (420.0, 297.0),
                   "A4": (297.0, 210.0)}
    paper = paper_sizes.get(spec.paper_format.upper())
    if paper is None:
        error("paper-format-invalid", "Formato de prancha desconhecido.")
        width = height = 0.0
    else:
        width, height = paper
        if spec.orientation == "portrait":
            width, height = height, width

    msp = doc.modelspace()
    entities = list(msp)
    source_ids = Counter(_source_id(entity) for entity in entities if _source_id(entity))
    expected_sources = Counter()
    expected_lines: dict[str, list[tuple]] = {}
    expected_labels: dict[str, list[tuple]] = {}

    def line_signature(start, end):
        # DXF sheets are in millimetres. Normalize direction and round only
        # sub-micron serialization noise; 0.01-mm changes must be visible.
        p = lambda v: (round(float(v[0]), 4), round(float(v[1]), 4))
        return tuple(sorted((p(start), p(end))))

    def label_signature(value, point):
        return (str(value)[:180],
                (round(float(point[0]), 4), round(float(point[1]), 4)))

    views = {view.view_id: view for view in package.views}
    for viewport in spec.viewports:
        view = views.get(viewport.view_id)
        if view is None:
            error("view-missing", f"Vista declarada não está no pacote: {viewport.view_id}.")
            continue
        min_x, min_y, max_x, max_y = view.bounds
        factor = 1000.0 / float(spec.scale)
        drawing_width = (max_x - min_x) * factor
        drawing_height = (max_y - min_y) * factor
        origin_x = (viewport.x_mm + (viewport.width_mm - drawing_width) / 2
                    - min_x * factor)
        origin_y = (viewport.y_mm + (viewport.height_mm - drawing_height) / 2
                    - min_y * factor)
        for segment in view.segments:
            expected_sources[segment.source_id] += 1
            start = (origin_x + segment.x1 * factor,
                     origin_y + segment.y1 * factor)
            end = (origin_x + segment.x2 * factor,
                   origin_y + segment.y2 * factor)
            expected_lines.setdefault(segment.source_id, []).append(
                (segment.layer, line_signature(start, end)))
        for label in view.labels:
            expected_sources[label.source_id] += 1
            point = (origin_x + label.x * factor,
                     origin_y + label.y * factor)
            expected_labels.setdefault(label.source_id, []).append(
                label_signature(label.text, point))
        expected_sources[f"sheet:{spec.sheet_id}:view-title:{view.view_id}"] += 1

    for source, count in expected_sources.items():
        if source_ids[source] < count:
            error("source-entity-missing", f"Entidade de origem ausente: {source}.")
        elif source_ids[source] > count:
            error("source-entity-extra", f"Entidade de origem duplicada: {source}.")

    # Compare physical, reopened DXF coordinates/layers/text at declared
    # viewport scale. XDATA presence alone does not prove that a view matches.
    entities_by_source: dict[str, list] = {}
    for entity in entities:
        source = _source_id(entity)
        if source in expected_lines or source in expected_labels:
            entities_by_source.setdefault(source, []).append(entity)
    for source, wanted in expected_lines.items():
        found = entities_by_source.get(source, [])
        if any(entity.dxftype() != "LINE" for entity in found):
            error("source-type-mismatch", f"Linha esperada substituída: {source}.")
            continue
        wanted_layers = Counter(layer for layer, _ in wanted)
        actual_layers = Counter(entity.dxf.layer for entity in found)
        if wanted_layers != actual_layers:
            error("source-layer-mismatch", f"Camada da entidade diverge: {source}.")
        actual_segments = Counter(
            line_signature(entity.dxf.start, entity.dxf.end) for entity in found)
        wanted_segments = Counter(signature for _, signature in wanted)
        if actual_segments != wanted_segments:
            error("source-geometry-mismatch",
                  f"Geometria ou escala real diverge da vista: {source}.")
    for source, wanted in expected_labels.items():
        found = entities_by_source.get(source, [])
        if any(entity.dxftype() != "TEXT" for entity in found):
            error("source-type-mismatch", f"Rótulo esperado substituído: {source}.")
            continue
        actual_labels = Counter(
            label_signature(entity.dxf.text, entity.dxf.insert) for entity in found)
        if Counter(wanted) != actual_labels:
            error("source-label-mismatch",
                  f"Texto ou posição do rótulo diverge da vista: {source}.")

    frame_id = f"sheet:{spec.sheet_id}:frame"
    title_id = f"sheet:{spec.sheet_id}:title-block"
    if source_ids[frame_id] != 4:
        error("sheet-frame-invalid", "Moldura da prancha incompleta ou ausente.")
    if source_ids[title_id] != 4:
        error("title-block-invalid", "Contorno do carimbo incompleto ou ausente.")

    required_labels = ("PROJETO:", "CONTRATANTE:", "RESPONSÁVEL TÉCNICO:",
                       "REGISTRO:", f"PRANCHA: {spec.sheet_id}", "ESCALA:")
    text_values = [entity.dxf.text for entity in msp.query("TEXT")]
    for label in required_labels:
        if not any(label in value for value in text_values):
            error("title-field-missing", f"Campo obrigatório ausente: {label}.")
    expected_scale = f"ESCALA: 1:{float(spec.scale):g} |"
    scale_rows = [value for value in text_values if value.startswith("ESCALA:")]
    if len(scale_rows) != 1 or not scale_rows[0].startswith(expected_scale):
        error("sheet-scale-mismatch",
              f"Escala do carimbo diverge da geometria/viewport: {spec.sheet_id}.")

    if width <= 0 or height <= 0:
        bounds = (0.0, 0.0, 0.0, 0.0)
    else:
        bounds = (0.0, 0.0, width, height)
    min_x, min_y, max_x, max_y = bounds
    checked = 0
    for entity in entities:
        for point in _entity_points(entity):
            x, y = float(point.x), float(point.y)
            checked += 1
            if not isfinite(x) or not isfinite(y) or x < min_x - 1e-5 or y < min_y - 1e-5 or x > max_x + 1e-5 or y > max_y + 1e-5:
                error("entity-outside-sheet", f"Entidade {entity.dxftype()} fora dos limites da folha.")
                break

    return {
        "ok": not errors,
        "sheet_id": spec.sheet_id,
        "errors": errors,
        "source_entities_checked": sum(expected_sources.values()),
        "source_segments_checked": sum(len(value) for value in expected_lines.values()),
        "source_labels_checked": sum(len(value) for value in expected_labels.values()),
        "entity_points_checked": checked,
        "source_id_counts": dict(source_ids),
    }
