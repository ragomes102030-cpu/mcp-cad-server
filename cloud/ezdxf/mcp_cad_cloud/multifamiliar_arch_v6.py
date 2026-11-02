"""Revision 06: preserve V5 geometry and adopt its verified furniture as CAD components.

The PDF is rendered from the saved DXF modelspace, not redrawn by hand.
Preliminary study only: no fire, accessibility, permit or normative approval.
"""
from __future__ import annotations

import json
from collections import Counter
from math import cos, radians, sin
from pathlib import Path

from .components import CATALOG, adopt_component, footprint, read_component
from .multifamiliar_arch_v4 import _room_program
from .multifamiliar_arch_v5 import audit_functional_v5, design_stair, generate_multifamily_v5


class ComponentIntegrationError(ValueError):
    pass


def _expected_components(room):
    x0, y0, x1, y1 = room.rect
    if room.kind in ("quarto1", "quarto2"):
        return [("bed_double", (x0 + .60, y0 + .65 + (.80 if room.uid in ("AP03", "AP04") else 0)), "CAMA")]
    if room.kind == "sala_cozinha":
        return [("dining_table", (x0 + 5.30, (y0 + y1) / 2 - .70), "MESA")]
    if room.kind == "banheiro":
        return [
            ("washbasin_existing", (x0 + 1.18, y0 + .40), "LAV."),
            ("shower_existing", (x0 + .22, y0 + 1.55), "BOX"),
        ]
    return []


def _find_footprint(doc, kind, origin, tolerance=.015):
    from math import hypot
    expected = footprint(CATALOG[kind], origin)
    candidates = []
    for entity in doc.modelspace().query("LWPOLYLINE"):
        if entity.dxf.layer not in {"ARQ-MOBILIARIO", "ARQ-DETALHES"} or not entity.closed:
            continue
        points = list(entity.get_points("xy"))
        if len(points) != 4:
            continue
        if all(any(hypot(x-ex, y-ey) <= tolerance for x, y in points)
               for ex, ey in expected):
            candidates.append(entity)
    if len(candidates) != 1:
        raise ComponentIntegrationError(
            f"Expected exactly one existing {kind} at {origin}, found {len(candidates)}")
    return candidates[0]



def _relocate_upper_beds(doc):
    """Fix four existing upper-unit bed/door swing collisions without moving walls."""
    moved = 0
    for room in _room_program():
        if room.uid not in ("AP03", "AP04") or room.kind not in ("quarto1", "quarto2"):
            continue
        x0, y0, _, _ = room.rect
        bed = _find_footprint(doc, "bed_double", (x0 + .60, y0 + .65))
        # Pillow is a separate schematic polyline inside the original bed.
        pillows = []
        for entity in doc.modelspace().query("LWPOLYLINE"):
            if entity.dxf.layer != "ARQ-MOBILIARIO" or not entity.closed:
                continue
            pts = list(entity.get_points("xy"))
            if len(pts) != 4:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if (abs(min(xs) - (x0 + .71)) < .01
                    and abs(max(xs) - (x0 + 1.89)) < .01
                    and abs(min(ys) - (y0 + 2.15)) < .01
                    and abs(max(ys) - (y0 + 2.46)) < .01):
                pillows.append(entity)
        if len(pillows) != 1:
            raise ComponentIntegrationError(
                f"{room.uid}/{room.kind}: missing or ambiguous pillow geometry")
        for entity in (bed, pillows[0]):
            entity.set_points([(x, y + .80) for x, y in entity.get_points("xy")],
                              format="xy")
            moved += 1
    if moved != 8:
        raise ComponentIntegrationError(f"Expected eight corrected entities, got {moved}")
    return moved


def adopt_apartment_components(doc):
    """Adopt 20 real existing CAD shapes; never overwrite the baseline walls/doors."""
    m = doc.modelspace()
    _relocate_upper_beds(doc)
    if "ARQ-COMPONENTES-ROTULOS" not in doc.layers:
        doc.layers.new("ARQ-COMPONENTES-ROTULOS", dxfattribs={"color": 8})
    items = []
    for room in _room_program():
        for kind, origin, label in _expected_components(room):
            entity = _find_footprint(doc, kind, origin)
            adopt_component(doc, entity, kind, origin, unit_id=room.uid)
            # Text is additional semantic annotation, not substitute CAD geometry.
            m.add_text(label, dxfattribs={
                "insert": (origin[0] + .08, origin[1] + .12),
                "height": .16, "layer": "ARQ-COMPONENTES-ROTULOS"})
            items.append({"unit": room.uid, "room": room.kind,
                          "kind": kind, "handle": entity.dxf.handle})
    return items


def audit_apartment_components(doc):
    """Validate unit ownership, room fit, wall/door intersections and circulation."""
    from shapely.geometry import LineString, Polygon, box
    m = doc.modelspace()
    errors = []
    room_lookup = {(r.uid, r.kind): r for r in _room_program()}
    found = []
    wall_lines = []
    for e in m.query("LWPOLYLINE LINE"):
        if e.dxf.layer != "ARQ-PAREDES":
            continue
        if e.dxftype() == "LINE":
            pts = [(e.dxf.start.x, e.dxf.start.y),
                   (e.dxf.end.x, e.dxf.end.y)]
        else:
            pts = list(e.get_points("xy"))
            if e.closed and pts:
                pts.append(pts[0])
        if len(pts) >= 2:
            wall_lines.append(LineString(pts))
    door_sweeps = []
    for arc in m.query("ARC"):
        if arc.dxf.layer != "ARQ-PORTAS":
            continue
        a, b = float(arc.dxf.start_angle), float(arc.dxf.end_angle)
        if b < a:
            b += 360
        cx, cy = arc.dxf.center.x, arc.dxf.center.y
        radius = float(arc.dxf.radius)
        pts = [(cx + radius * cos(radians(a + (b-a)*i/30)),
                cy + radius * sin(radians(a + (b-a)*i/30))) for i in range(31)]
        door_sweeps.append(LineString(pts).buffer(.02))
    for e in m.query("LWPOLYLINE"):
        if not e.has_xdata("MCP_CAD"):
            continue
        try:
            meta = read_component(e)
        except (ValueError, KeyError) as exc:
            errors.append(f"Invalid component metadata: {exc}")
            continue
        points = list(e.get_points("xy"))
        if len(points) != 4:
            errors.append("Component has non-rectangular footprint")
            continue
        polygon = Polygon(points)
        uid = meta["unit_id"]
        expected_rooms = [r for (unit, _), r in room_lookup.items() if unit == uid
                          and box(*r.rect).covers(polygon)]
        if len(expected_rooms) != 1:
            errors.append(f"{uid}: component outside exactly one room")
        if any(polygon.intersects(wall) for wall in wall_lines):
            errors.append(f"{uid}: component collides with wall")
        if any(polygon.intersects(sweep) for sweep in door_sweeps):
            errors.append(f"{uid}: component collides with door swing")
        origin = (min(p[0] for p in points), min(p[1] for p in points))
        expected = Polygon(footprint(CATALOG[meta["kind"]], origin))
        if polygon.symmetric_difference(expected).area > .0001:
            errors.append(f"{uid}: metadata differs from CAD footprint")
        found.append((uid, meta["kind"], polygon))
    for i, (uid, kind, polygon) in enumerate(found):
        for uid2, kind2, polygon2 in found[i+1:]:
            if polygon.intersection(polygon2).area > .0001:
                errors.append(f"Components overlap: {uid}/{kind} and {uid2}/{kind2}")
    counts = Counter(uid for uid, _, _ in found)
    for uid in ("AP01", "AP02", "AP03", "AP04"):
        if counts[uid] != 5:
            errors.append(f"{uid}: expected five semantic components, got {counts[uid]}")
    if len(found) != 20:
        errors.append(f"Expected 20 components, got {len(found)}")
    functional = audit_functional_v5(doc, design_stair())
    if not functional["ok"]:
        errors.extend(functional["errors"])
    if doc.audit().has_errors:
        errors.append("DXF internal audit failed")
    return {
        "ok": not errors, "errors": errors, "components": len(found),
        "per_apartment": dict(counts), "functional_routes": functional["routes"],
        "doors": len([a for a in m.query("ARC") if a.dxf.layer == "ARQ-PORTAS"]),
        "window_segments": len([e for e in m.query("LINE")
                                if e.dxf.layer == "ARQ-JANELAS"]),
        "dxf_audit_errors": len(doc.audit().errors),
        "warnings": ["No normative, accessibility, fire or permit compliance assessment.",
                     "Furniture clearances not certified; existing V5 footprints preserved."],
    }


def _render_a3(doc, pdf_path, count):
    import matplotlib
    matplotlib.use("Agg", force=True)
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    from matplotlib.backends.backend_pdf import PdfPages
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.properties import LayoutProperties
    m = doc.modelspace()
    props = LayoutProperties.from_layout(m)
    props.set_colors("#FFFFFF", "#18212B")
    with PdfPages(pdf_path) as output:
        for idx in (0, 1):
            fig = Figure(figsize=(420/25.4, 297/25.4), facecolor="white")
            ax = fig.add_axes([16/420, 43/297, 265/420, 220/297])
            ax.set_axis_off()
            Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(
                m, finalize=False, layout_properties=props)
            if idx == 0:
                ax.set_xlim(-.5625, 32.5625)
                ax.set_ylim(-.75, 26.75)
            else:
                ax.set_xlim(25.8, 31.6)
                ax.set_ylim(9.5, 16.5)
            ax.set_aspect("equal", adjustable="box")
            fig.add_artist(Rectangle((8/420, 8/297), 404/420, 281/297,
                fill=False, transform=fig.transFigure, edgecolor="#263948", linewidth=1))
            fig.add_artist(Line2D((294/420, 294/420), (8/297, 289/297),
                transform=fig.transFigure, color="#263948", linewidth=.8))
            def title(value, x, y, size=8, bold=False):
                fig.text(x/420, y/297, value, fontsize=size,
                         weight="bold" if bold else "normal", color="#1B2936")
            title("MCP CAD CLOUD", 299, 276, 13, True)
            title("MULTIFAMILIAR | REVISAO 06", 299, 263, 8.5, True)
            title("COMPONENTES PARAMETRICOS", 299, 247, 8.5, True)
            if idx == 0:
                title("ARQ-01 | PAVIMENTO MOBILIADO", 299, 228, 8.5, True)
                title("4 APARTAMENTOS / 20 AMBIENTES", 299, 212)
                title(f"{count} COMPONENTES COM XDATA", 299, 195, 8, True)
                title("CAMAS / MESAS / LAVATORIOS / BOXES", 299, 180, 7.2)
                title("PAREDES / PORTAS / ROTAS AUDITADAS", 299, 161, 7.2)
            else:
                title("ARQ-02 | DETALHE DE ESCADA", 299, 228, 8.5, True)
                title("18 ESPELHOS / 2 LANCES", 299, 212)
                title("DESNIVEL DE TESTE: 3,00 m", 299, 195)
                title("ACESSO / SEGURANCA A CONFERIR", 299, 173, 7.5, True)
            title("SEM VERIFICACAO NORMATIVA", 299, 106, 8, True)
            title("TERRENO HIPOTETICO / NORTE ILUSTRATIVO", 299, 87, 7)
            title("ESCALA DE IMPRESSAO NAO GARANTIDA", 299, 70, 7)
            title("NAO UTILIZAR PARA EXECUCAO", 299, 31, 8.5, True)
            title(f"ARQ-0{idx+1} | REV 06 | COTAS EM METROS", 19, 25, 8)
            output.savefig(fig)
            fig.clear()


def generate_multifamily_v6(output_dir):
    """Build V5 through the real CAD generator, adopt components and export A3."""
    import ezdxf
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = generate_multifamily_v5(out / "base_v5")
    if base["status"] != "functional_preliminary_checks_passed_not_normative":
        raise ComponentIntegrationError("V5 baseline not approved for functional study")
    doc = ezdxf.readfile(base["dxf"])
    adopted = adopt_apartment_components(doc)
    report = audit_apartment_components(doc)
    report["adopted"] = adopted
    report["upper_bed_and_pillow_entities_relocated"] = 8
    report["scope"] = "architectural preliminary study only"
    report_path = out / "auditoria_componentes_v6.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if not report["ok"]:
        raise ComponentIntegrationError("; ".join(report["errors"]))
    for name in list(doc.layouts.names()):
        if name.startswith("ARQ-0"):
            doc.layouts.delete(name)
    for name, center, height in (("ARQ-01 A3 REV06", (16, 13), 27.5),
                                 ("ARQ-02 A3 ESCADA REV06", (28.7, 13), 7.0)):
        sheet = doc.layouts.new(name)
        sheet.page_setup(size=(420, 297), margins=(8, 8, 8, 8), units="mm")
        sheet.add_viewport(center=(149, 148), size=(265, 220),
                           view_center_point=center, view_height=height, status=2)
        sheet.add_text(name, dxfattribs={
            "insert": (298, 275), "height": 4, "layer": "ARQ-TEXTOS"})
    dxf = out / "multifamiliar_componentes_v6.dxf"
    pdf = out / "multifamiliar_componentes_v6_A3.pdf"
    doc.saveas(dxf)
    _render_a3(doc, pdf, len(adopted))
    if not pdf.read_bytes().startswith(b"%PDF-"):
        raise ComponentIntegrationError("PDF A3 was not generated")
    report["pdf_a3_pages"] = 2
    report["pdf_bytes"] = pdf.stat().st_size
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "components_preliminarily_audited_not_normative",
            "pdf": str(pdf), "dxf": str(dxf), "audit": str(report_path)}


if __name__ == "__main__":
    import sys
    print(json.dumps(generate_multifamily_v6(
        sys.argv[1] if len(sys.argv) > 1 else "."), indent=2))
