"""Render an actual ezdxf drawing as a simple A3 architectural sheet and PNG.

The exported PDF is a conceptual graphic sheet, not a legal/executive project.
PDF and PNG are rendered from the same live DXF document that is exported.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from math import isfinite
from typing import Any

_A3_INCH = (420 / 25.4, 297 / 25.4)


def renderizar_prancha(doc, titulo: str, geometria: dict) -> tuple[bytes, bytes]:
    import matplotlib
    matplotlib.use("Agg", force=True)
    from matplotlib.figure import Figure
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.properties import LayoutProperties

    fig = Figure(figsize=_A3_INCH, facecolor="white")
    ax = fig.add_axes([0.06, 0.14, 0.64, 0.75])
    ax.set_axis_off()
    props = LayoutProperties.from_layout(doc.modelspace())
    props.set_colors("#FFFFFF", "#101820")
    Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(
        doc.modelspace(),
        finalize=False,
        layout_properties=props,
        filter_func=lambda e: e.dxf.get("layer", "0") != "TERRENO",
    )
    # A3 landscape; view of building at approximately 1:50.
    # The separate terrain outline remains in DXF but is omitted from this
    # enlarged building-focused sheet.
    cx = float(geometria["largura"]) / 2
    cy = float(geometria["profundidade"]) / 2
    span_x = 420 * 0.64 / 20  # 1:50, meters visible on this axis
    span_y = 297 * 0.75 / 20
    ax.set_xlim(cx - span_x / 2, cx + span_x / 2)
    ax.set_ylim(cy - span_y / 2, cy + span_y / 2)
    ax.set_aspect("equal", adjustable="box")

    fig.text(.06, .945, "MCP CAD CLOUD  /  PLANTA BAIXA 2D",
             fontsize=19, weight="bold", color="#142b3b")
    fig.text(.06, .91, titulo[:90], fontsize=12, color="#445563")
    fig.text(.74, .83, "QUADRO TECNICO", fontsize=12,
             color="#142b3b", weight="bold")
    fig.text(.74, .775, "TIPO: estudo preliminar", fontsize=10, color="#142b3b")
    fig.text(.74, .74, "PAVIMENTOS: 1 (terreo)", fontsize=10, color="#142b3b")
    fig.text(.74, .69,
             f"DIMENSOES: {geometria['largura']:.2f} x {geometria['profundidade']:.2f} m",
             fontsize=10, color="#142b3b")
    fig.text(.74, .65,
             f"PROJECAO: {geometria['area_construida']:.2f} m2",
             fontsize=10, color="#142b3b")
    fig.text(.74, .61,
             f"AREA MAPEADA: {geometria['area_util_total']:.2f} m2",
             fontsize=10, color="#142b3b")
    fig.text(.74, .54, "ESCALA GRAFICA: aprox. 1:50",
             fontsize=9, color="#445563")
    fig.text(.74, .49, "Arquivo DXF disponivel para", fontsize=9, color="#445563")
    fig.text(.74, .47, "medicao e edicao CAD.", fontsize=9, color="#445563")
    fig.text(.06, .07,
             "ESTUDO CONCEITUAL - SEM APROVACAO NORMATIVA OU URBANISTICA.",
             fontsize=10, weight="bold", color="#984d36")
    fig.text(.06, .044,
             "Cotas e geometria derivadas de entidades reais DXF. Conferir antes de executar.",
             fontsize=9, color="#445563")

    pdf = io.BytesIO()
    png = io.BytesIO()
    try:
        fig.savefig(pdf, format="pdf", facecolor="white")
        fig.savefig(png, format="png", dpi=140, facecolor="white")
    finally:
        fig.clear()
    pdf_bytes, png_bytes = pdf.getvalue(), png.getvalue()
    if not pdf_bytes.startswith(b"%PDF-") or not png_bytes.startswith(bytes.fromhex("89504e470d0a1a0a")):
        raise RuntimeError("Falha ao renderizar PDF/PNG a partir do DXF")
    return pdf_bytes, png_bytes


class SheetCompositionError(ValueError):
    """Raised when a requested sheet cannot represent its views safely."""


_PAPER_MM = {
    "A0": (1189.0, 841.0),
    "A1": (841.0, 594.0),
    "A2": (594.0, 420.0),
    "A3": (420.0, 297.0),
    "A4": (297.0, 210.0),
}
_TITLE_BLOCK_HEIGHT_MM = 52.0


@dataclass(frozen=True)
class ViewportSpec:
    view_id: str
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float


@dataclass(frozen=True)
class SheetSpec:
    paper_format: str
    orientation: str
    scale: float
    margin_mm: float
    sheet_id: str
    viewports: tuple[ViewportSpec, ...]


@dataclass(frozen=True)
class TitleBlockData:
    project_name: str
    municipality: str | None
    state: str | None
    owner: str | None
    designer: str | None
    professional_registration: str | None
    issue_date: str | None
    revision: str | None


@dataclass(frozen=True)
class SheetDrawing:
    sheet_id: str
    spec: SheetSpec
    title_block_rows: tuple[str, ...]
    document: Any


def _paper_dimensions(spec: SheetSpec) -> tuple[float, float]:
    paper = _PAPER_MM.get(spec.paper_format.upper())
    if paper is None:
        raise SheetCompositionError("Formato de folha deve ser A0, A1, A2, A3 ou A4.")
    if spec.orientation not in {"landscape", "portrait"}:
        raise SheetCompositionError("Orientação da folha deve ser landscape ou portrait.")
    width, height = paper
    return (width, height) if spec.orientation == "landscape" else (height, width)


def _display(value: str | None) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else "PENDENTE"


def _add_sheet_text(msp, x: float, y: float, text: str, height: float,
                    layer: str, source_id: str | None = None):
    entity = msp.add_text(
        text[:180],
        dxfattribs={
            "height": height,
            "insert": (x, y),
            "layer": layer,
            "lineweight": 35,
            "true_color": 0x101820,
        },
    )
    if source_id:
        entity.set_xdata("MCP_CAD", [(1000, source_id)])
    return entity


def _add_sheet_rect(msp, x1: float, y1: float, x2: float, y2: float,
                    layer: str, source_id: str):
    points = ((x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1))
    for start, end in zip(points, points[1:]):
        line = msp.add_line(start, end, dxfattribs={"layer": layer})
        line.set_xdata("MCP_CAD", [(1000, source_id)])


def _title_rows(data: TitleBlockData, spec: SheetSpec,
                view_ids: tuple[str, ...]) -> tuple[str, ...]:
    municipality = _display(data.municipality)
    state = _display(data.state) if municipality != "PENDENTE" else "PENDENTE"
    return (
        f"PROJETO: {_display(data.project_name)} | MUNICÍPIO: {municipality} / {state}",
        f"CONTRATANTE: {_display(data.owner)}",
        f"RESPONSÁVEL TÉCNICO: {_display(data.designer)}",
        f"REGISTRO: {_display(data.professional_registration)}",
        f"PRANCHA: {spec.sheet_id} | CONTEÚDO: {', '.join(view_ids)}",
        f"ESCALA: 1:{spec.scale:g} | DATA: {_display(data.issue_date)} | REVISÃO: {_display(data.revision)}",
        "DOCUMENTO PARA REVISÃO PROFISSIONAL; REQUISITOS NORMATIVOS/LOCAIS PODEM ESTAR PENDENTES",
    )


def compose_licensing_sheets(package, sheets: list[SheetSpec],
                             title_block: TitleBlockData) -> list[SheetDrawing]:
    """Create editable DXFs for each sheet at the requested declared scale."""
    import ezdxf

    if not sheets:
        raise SheetCompositionError("Informe ao menos uma folha.")
    if not title_block.project_name.strip():
        raise SheetCompositionError("Nome do projeto obrigatório no carimbo.")
    if title_block.project_name.strip() != package.project_context.project_name.strip():
        raise SheetCompositionError("Projeto do carimbo diverge do contexto arquitetônico.")
    view_map = {view.view_id: view for view in package.views}
    ids = [sheet.sheet_id.strip() for sheet in sheets]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise SheetCompositionError("IDs de prancha ausentes ou duplicados.")

    composed: list[SheetDrawing] = []
    for spec in sheets:
        paper_width, paper_height = _paper_dimensions(spec)
        try:
            scale = float(spec.scale)
            margin = float(spec.margin_mm)
        except (TypeError, ValueError, OverflowError) as exc:
            raise SheetCompositionError("Escala e margem da folha inválidas.") from exc
        if not isfinite(scale) or not isfinite(margin) or scale <= 0 or margin < 0:
            raise SheetCompositionError("Escala e margem da folha inválidas.")
        if not spec.viewports:
            raise SheetCompositionError(f"Nenhuma vista indicada para {spec.sheet_id}.")
        view_ids = tuple(viewport.view_id for viewport in spec.viewports)
        rows = _title_rows(title_block, spec, view_ids)
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = ezdxf.units.MM
        doc.appids.new("MCP_CAD")
        segment_layers = {
            segment.layer for viewport in spec.viewports
            if viewport.view_id in view_map
            for segment in view_map[viewport.view_id].segments
        }
        for layer_name, color in (
            ("FOLHA", 7), ("CARIMBO", 7), ("TITULOS-VISTAS", 5),
            ("PAREDES", 7), ("LOTE", 8), ("PROJECAO", 3),
            ("AFASTAMENTOS-GEOMETRICOS", 4), ("COBERTURA", 2),
            ("CUMEEIRA", 1), ("CORTE-PISO", 7), ("CORTE-PAREDE", 7),
            ("CORTE-COBERTURA", 2), ("CORTE-PORTA", 6), ("CORTE-JANELA", 5),
            ("ESQUADRIA-JANELA", 5), ("ESQUADRIA-PORTA", 6),
        ):
            if layer_name not in doc.layers:
                doc.layers.new(layer_name, dxfattribs={"color": color})
        for layer_name in sorted(segment_layers):
            if layer_name not in doc.layers:
                doc.layers.new(layer_name, dxfattribs={"color": 7})

        for index, first in enumerate(spec.viewports):
            for second in spec.viewports[index + 1:]:
                separated = (
                    first.x_mm + first.width_mm <= second.x_mm
                    or second.x_mm + second.width_mm <= first.x_mm
                    or first.y_mm + first.height_mm <= second.y_mm
                    or second.y_mm + second.height_mm <= first.y_mm
                )
                if not separated:
                    raise SheetCompositionError(
                        f"Viewports sobrepostos na folha {spec.sheet_id}."
                    )

        msp = doc.modelspace()
        _add_sheet_rect(msp, margin, margin, paper_width - margin,
                        paper_height - margin, "FOLHA", f"sheet:{spec.sheet_id}:frame")
        _add_sheet_rect(msp, margin, margin, paper_width - margin,
                        margin + _TITLE_BLOCK_HEIGHT_MM, "CARIMBO",
                        f"sheet:{spec.sheet_id}:title-block")
        row_top = margin + _TITLE_BLOCK_HEIGHT_MM - 5
        for index, text in enumerate(rows):
            _add_sheet_text(msp, margin + 3, row_top - 6.5 * index,
                            text, 3.0 if index < 6 else 2.4,
                            "CARIMBO", f"sheet:{spec.sheet_id}:title-row:{index}")

        for viewport in spec.viewports:
            view = view_map.get(viewport.view_id)
            if view is None:
                raise SheetCompositionError(f"Vista não encontrada: {viewport.view_id}.")
            try:
                viewport_values = tuple(float(value) for value in (
                    viewport.x_mm, viewport.y_mm,
                    viewport.width_mm, viewport.height_mm,
                ))
            except (TypeError, ValueError, OverflowError) as exc:
                raise SheetCompositionError("Viewport contém dimensão inválida.") from exc
            if not all(isfinite(value) for value in viewport_values):
                raise SheetCompositionError("Viewport contém dimensão inválida.")
            x_mm, y_mm, width_mm, height_mm = viewport_values
            if (width_mm <= 0 or height_mm <= 0
                    or x_mm < margin
                    or y_mm < margin + _TITLE_BLOCK_HEIGHT_MM
                    or x_mm + width_mm > paper_width - margin
                    or y_mm + height_mm > paper_height - margin):
                raise SheetCompositionError(f"Viewport fora da área útil da folha {spec.sheet_id}.")
            min_x, min_y, max_x, max_y = view.bounds
            factor = 1000.0 / scale
            drawing_width = (max_x - min_x) * factor
            drawing_height = (max_y - min_y) * factor
            if (drawing_width > width_mm + 1e-6
                    or drawing_height > height_mm + 1e-6):
                raise SheetCompositionError(
                    f"Vista {view.view_id} não cabe no viewport na escala 1:{scale:g}."
                )
            origin_x = x_mm + (width_mm - drawing_width) / 2 - min_x * factor
            origin_y = y_mm + (height_mm - drawing_height) / 2 - min_y * factor
            for segment in view.segments:
                line = msp.add_line(
                    (origin_x + segment.x1 * factor, origin_y + segment.y1 * factor),
                    (origin_x + segment.x2 * factor, origin_y + segment.y2 * factor),
                    dxfattribs={"layer": segment.layer},
                )
                line.set_xdata("MCP_CAD", [(1000, segment.source_id)])
            for label in view.labels:
                _add_sheet_text(
                    msp,
                    origin_x + label.x * factor,
                    origin_y + label.y * factor,
                    label.text,
                    max(3.0, min(4.0, 0.16 * factor)),
                    "PAREDES",
                    label.source_id,
                )
            _add_sheet_text(
                msp, x_mm, y_mm - 4.0,
                view.view_id, 3.0, "TITULOS-VISTAS",
                f"sheet:{spec.sheet_id}:view-title:{view.view_id}",
            )

        composed.append(SheetDrawing(spec.sheet_id, spec, rows, doc))
    return composed


def renderizar_folha(sheet: SheetDrawing) -> tuple[bytes, bytes]:
    """Render one composed DXF document to a single-page PDF and PNG."""
    import matplotlib
    matplotlib.use("Agg", force=True)
    from matplotlib.figure import Figure
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.properties import LayoutProperties

    paper_width, paper_height = _paper_dimensions(sheet.spec)
    fig = Figure(figsize=(paper_width / 25.4, paper_height / 25.4), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    properties = LayoutProperties.from_layout(sheet.document.modelspace())
    properties.set_colors("#FFFFFF", "#101820")
    Frontend(RenderContext(sheet.document), MatplotlibBackend(ax)).draw_layout(
        sheet.document.modelspace(), finalize=False,
        layout_properties=properties,
        filter_func=lambda entity: entity.dxftype() != "TEXT",
    )
    ax.set_xlim(0, paper_width)
    ax.set_ylim(0, paper_height)
    ax.set_aspect("equal", adjustable="box")
    for entity in sheet.document.modelspace().query("TEXT"):
        source = ""
        if entity.has_xdata("MCP_CAD"):
            tags = entity.get_xdata("MCP_CAD")
            source = str(tags[0].value) if tags else ""
        is_room_label = source.startswith(("room:", "room-area:"))
        height_pt = float(entity.dxf.height) * 72 / 25.4 * 1.15
        ax.text(
            float(entity.dxf.insert.x),
            float(entity.dxf.insert.y),
            entity.dxf.text,
            fontsize=max(6.0, height_pt),
            color="#101820",
            fontfamily="DejaVu Sans",
            fontweight="medium",
            rotation=float(entity.dxf.get("rotation", 0.0)),
            ha="center" if is_room_label else "left",
            va="center" if is_room_label else "baseline",
        )
    pdf = io.BytesIO()
    png = io.BytesIO()
    try:
        fig.savefig(pdf, format="pdf", facecolor="white")
        fig.savefig(png, format="png", dpi=150, facecolor="white")
    finally:
        fig.clear()
    pdf_bytes, png_bytes = pdf.getvalue(), png.getvalue()
    if (not pdf_bytes.startswith(b"%PDF-")
            or not png_bytes.startswith(bytes.fromhex("89504e470d0a1a0a"))):
        raise RuntimeError("Falha ao renderizar folha arquitetônica")
    return pdf_bytes, png_bytes
