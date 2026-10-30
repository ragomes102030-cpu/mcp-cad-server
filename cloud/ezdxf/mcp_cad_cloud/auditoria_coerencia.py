"""Cross-view architectural coherence gate for the compact-house pilot.

This is a geometric consistency check, not a municipal or NBR compliance
engine. It compares separate view geometries with one common source model.
"""
from __future__ import annotations

from collections import Counter
from math import radians, tan


def _edge(x1, y1, x2, y2):
    a = (round(float(x1), 5), round(float(y1), 5))
    b = (round(float(x2), 5), round(float(y2), 5))
    return tuple(sorted((a, b)))


def _rectangle_edges(bounds):
    x1, y1, x2, y2 = bounds
    return Counter(_edge(*p) for p in (
        (x1, y1, x2, y1),
        (x2, y1, x2, y2),
        (x2, y2, x1, y2),
        (x1, y2, x1, y1),
    ))


def _segments_for(view, source):
    return [part for part in view.segments if part.source_id == source]


def _same_rectangle(view, source, bounds):
    segments = _segments_for(view, source)
    found = Counter(_edge(s.x1, s.y1, s.x2, s.y2) for s in segments)
    return found == _rectangle_edges(bounds)


def audit_architecture_coherence(package) -> dict:
    """Reject incompatible elevations, footprints or projected openings.

    Requires all nine views of the currently supported one-storey pilot.
    Geometry comes from independent projection comparisons, not DXF XDATA
    presence. The serialized sheet auditor separately checks physical lines.
    """
    errors = []

    def fail(code, view, source):
        errors.append({"code": code, "view_id": view, "source_id": source})

    views = {view.view_id: view for view in package.views}
    required = (
        "ARQ-PLANTA", "ARQ-IMPLANTACAO", "ARQ-COBERTURA",
        "ARQ-CORTE-A", "ARQ-CORTE-B", "ARQ-FACHADA-FRONTAL",
        "ARQ-FACHADA-FUNDOS", "ARQ-FACHADA-LATERAL-ESQ",
        "ARQ-FACHADA-LATERAL-DIR",
    )
    for view_id in required:
        if view_id not in views:
            fail("view-missing", view_id, "view")
    if errors:
        return {"ok": False, "status": "blocked", "errors": errors,
                "checked": {"views": len(views)}, "normative_approval": False}

    model = package.source_plan
    env = package.envelope
    width = float(model["resumo_geometria"]["largura"])
    depth = float(model["resumo_geometria"]["profundidade"])
    overhang = float(env.roof_overhang_m)
    floor = float(env.floor_level_m)
    wall_top = floor + float(env.wall_height_m)

    for view_id, source, bounds in (
        ("ARQ-IMPLANTACAO", "site:building-footprint", (0, 0, width, depth)),
        ("ARQ-COBERTURA", "roof:eaves-outline",
         (-overhang, -overhang, width + overhang, depth + overhang)),
    ):
        if not _same_rectangle(views[view_id], source, bounds):
            fail("footprint-mismatch", view_id, source)

    facade_specs = (
        ("frontal", "ARQ-FACHADA-FRONTAL", width, 0.0, "y"),
        ("fundos", "ARQ-FACHADA-FUNDOS", width, depth, "y"),
        ("lateral-esq", "ARQ-FACHADA-LATERAL-ESQ", depth, 0.0, "x"),
        ("lateral-dir", "ARQ-FACHADA-LATERAL-DIR", depth, width, "x"),
    )
    opening_checks = 0
    for side, view_id, span, boundary, fixed_axis in facade_specs:
        facade = views[view_id]
        if not _same_rectangle(
            facade, f"facade:{side}", (0, floor, span, wall_top)
        ):
            fail("facade-envelope-mismatch", view_id, f"facade:{side}")

        for index, (x1, y1, x2, y2) in enumerate(model["janelas"]):
            source = f"window:{side}:{index}"
            if fixed_axis == "y":
                visible = abs(y2-y1) < 1e-5 and abs(y1-boundary) <= 0.10
                bounds = (x1, floor + env.window_sill_m,
                          x2, floor + env.window_head_m)
            else:
                visible = abs(x2-x1) < 1e-5 and abs(x1-boundary) <= 0.10
                bounds = (y1, floor + env.window_sill_m,
                          y2, floor + env.window_head_m)
            if visible:
                opening_checks += 1
                if not _same_rectangle(facade, source, bounds):
                    fail("facade-window-mismatch", view_id, source)
            elif _segments_for(facade, source):
                fail("facade-unexpected-window", view_id, source)

        for index, (x, y, _angle, door_width) in enumerate(model["portas"]):
            source = f"door:{side}:{index}"
            visible = abs((y if fixed_axis == "y" else x) - boundary) <= 0.10
            start = x if fixed_axis == "y" else y
            if visible:
                opening_checks += 1
                if not _same_rectangle(
                    facade, source,
                    (start, floor, start + door_width,
                     floor + env.door_head_m)
                ):
                    fail("facade-door-mismatch", view_id, source)
            elif _segments_for(facade, source):
                fail("facade-unexpected-door", view_id, source)

    transverse_span = depth if env.ridge_axis == "x" else width
    ridge_height = wall_top + (
        transverse_span / 2 + overhang
    ) * tan(radians(env.roof_pitch_degrees))
    gables = ("ARQ-FACHADA-LATERAL-ESQ", "ARQ-FACHADA-LATERAL-DIR") if env.ridge_axis == "x" else (
        "ARQ-FACHADA-FRONTAL", "ARQ-FACHADA-FUNDOS"
    )
    for view_id in gables:
        edges = [s for s in views[view_id].segments if s.layer == "COBERTURA"]
        if len(edges) != 2 or abs(
            max((max(s.y1, s.y2) for s in edges), default=-1) - ridge_height
        ) > 1e-4:
            fail("roof-ridge-mismatch", view_id, "roof:ridge")

    # ARQ-CORTE-B is X and ARQ-CORTE-A is Y in the supported package.
    parallel_section = "ARQ-CORTE-B" if env.ridge_axis == "x" else "ARQ-CORTE-A"
    perpendicular_section = "ARQ-CORTE-A" if env.ridge_axis == "x" else "ARQ-CORTE-B"
    parallel_axis = env.ridge_axis
    run = _segments_for(views[parallel_section], f"section:{parallel_axis}:ridge-run")
    if len(run) != 1 or abs(run[0].y1 - ridge_height) > 1e-4 or abs(run[0].y2 - ridge_height) > 1e-4:
        fail("roof-ridge-mismatch", parallel_section,
             f"section:{parallel_axis}:ridge-run")
    perp_edges = [s for s in views[perpendicular_section].segments
                  if s.layer == "CORTE-COBERTURA"]
    if len(perp_edges) != 2 or abs(
        max((max(s.y1, s.y2) for s in perp_edges), default=-1) - ridge_height
    ) > 1e-4:
        fail("roof-ridge-mismatch", perpendicular_section, "section:roof")

    return {
        "ok": not errors,
        "status": "review_required" if not errors else "blocked",
        "errors": errors,
        "checked": {
            "views": len(views),
            "projected_facade_openings": opening_checks,
            "footprints": 2,
            "facade_envelopes": 4,
            "roof_profiles": 4,
        },
        "geometry": {
            "width_m": width,
            "depth_m": depth,
            "roof_ridge_elevation_m": round(ridge_height, 4),
        },
        "normative_approval": False,
        "limitations": [
            "Conferência de coerência geométrica; não certifica NBR nem Código de Obras.",
            "Não confere visualmente textos sobrepostos nem espaços de circulação.",
        ],
    }
