"""DXF-backed A3 concept sheet for the multifamily pilot.

This is NOT an architectural approval drawing. Stair, wall thickness,
interior doors, circulation and regulatory compliance remain unresolved.
"""
from __future__ import annotations

import io
from pathlib import Path

from .multifamiliar_partition import build_partitioned_four_apartment_floor
from .multifamiliar_acceptance import audit_multifamily_architecture


def generate_multifamily_preview(output_dir: str | Path) -> dict[str, str]:
    """Export a real DXF and a PDF rendered from that DXF's modelspace."""
    import ezdxf
    import matplotlib
    matplotlib.use("Agg", force=True)
    from matplotlib.figure import Figure
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.properties import LayoutProperties

    model = build_partitioned_four_apartment_floor()
    architectural_audit = audit_multifamily_architecture(model)
    if architectural_audit['ok']:
        raise RuntimeError('Concept export unexpectedly passed strict architectural gate')
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2013")
    for name, color in (("PAREDES", 7), ("AMBIENTES", 8), ("ABERTURAS", 4),
                        ("TEXTOS", 2), ("RESERVAS", 1)):
        doc.layers.new(name, dxfattribs={"color": color})
    msp = doc.modelspace()
    for wall in model.walls:
        g = wall.geometry
        start = (g["x"], g["y"])
        end = (g["x"] + (g["length"] if wall.metadata["axis"] == "horizontal" else 0),
               g["y"] + (g["length"] if wall.metadata["axis"] == "vertical" else 0))
        msp.add_line(start, end, dxfattribs={"layer": "PAREDES"})
    for room in model.rooms:
        if room.id == "stair-reservation":
            layer = "RESERVAS"
        elif room.id == "common-corridor":
            layer = "AMBIENTES"
        else:
            layer = "AMBIENTES"
        g = room.geometry
        x, y, w, h = (g[k] for k in ("x", "y", "width", "depth"))
        msp.add_lwpolyline([(x,y),(x+w,y),(x+w,y+h),(x,y+h)], close=True,
                           dxfattribs={"layer":layer})
        label = room.id.replace("-", " ")[:25]
        msp.add_text(label, dxfattribs={"height":.20,"insert":(x+.18,y+h/2),
                                       "layer":"TEXTOS"})
    for opening in model.openings:
        g = opening.geometry
        msp.add_line((g["x"],g["y"]), (g["x"]+g["width"],g["y"]),
                     dxfattribs={"layer":"ABERTURAS"})
    audit = doc.audit()
    if audit.has_errors:
        raise RuntimeError("DXF audit failed: " + str(len(audit.errors)))
    dxf_path = out / "multifamiliar_preliminar.dxf"
    pdf_path = out / "multifamiliar_preliminar_A3.pdf"
    doc.saveas(dxf_path)

    fig = Figure(figsize=(420/25.4,297/25.4), facecolor="white")
    ax = fig.add_axes([.07,.17,.86,.70])
    ax.set_axis_off()
    props = LayoutProperties.from_layout(msp)
    props.set_colors("#FFFFFF", "#101820")
    Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(
        msp, finalize=False, layout_properties=props)
    ax.set_xlim(-1,model.lot["width"]+1)
    ax.set_ylim(-1,model.lot["depth"]+1)
    ax.set_aspect("equal", adjustable="box")
    fig.text(.07,.92,"MCP CAD CLOUD  |  PAVIMENTO MULTIFAMILIAR",
             fontsize=16,weight="bold")
    fig.text(.07,.885,"4 unidades | estudo preliminar | dimensoes em metros",fontsize=10)
    fig.text(.07,.09,"A3 / SEM ESCALA GARANTIDA | NAO APROVADO PARA EXECUCAO",
             fontsize=9,weight="bold")
    fig.text(.07,.065,"Escada reservada, sem detalhamento; portas e paredes esquematicas.",
             fontsize=8)
    fig.savefig(pdf_path,format="pdf")
    fig.clear()
    if not pdf_path.read_bytes().startswith(b"%PDF-"):
        raise RuntimeError("PDF export failed")
    return {"dxf":str(dxf_path),"pdf":str(pdf_path),
            "status":"concept_preview_not_validated",
            "architectural_audit":architectural_audit}
