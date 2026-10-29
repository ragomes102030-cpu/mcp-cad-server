"""Render an actual ezdxf drawing as a simple A3 architectural sheet and PNG.

The exported PDF is a conceptual graphic sheet, not a legal/executive project.
PDF and PNG are rendered from the same live DXF document that is exported.
"""
from __future__ import annotations

import io

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
    if not pdf_bytes.startswith(b"%PDF-") or not png_bytes.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
        raise RuntimeError("Falha ao renderizar PDF/PNG a partir do DXF")
    return pdf_bytes, png_bytes
