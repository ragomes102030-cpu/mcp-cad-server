"""Preflight annotation-legibility diagnostics for the compact architecture pilot.

No claim of actual rendered glyph measurement is made: this is a bounded
geometric approximation based on the same text-height rule as the A3 renderer.
The PDF/PNG must still be reviewed at print size. Report warnings, not NBR
or municipal approvals.
"""
from __future__ import annotations

from collections import defaultdict
from math import isfinite


def _label_box(label, scale: float) -> tuple[float, float, float, float]:
    # The A3 exporter sets DXF height between 3 and 4 mm. Matplotlib paints
    # text at approximately this height with a variable-width font.
    height_mm = max(3.0, min(4.0, 160.0 / scale))
    height_m = height_mm * scale / 1000.0
    width_m = max(height_m * 0.40, len(label.text) * height_m * 0.53)
    centered = label.source_id.startswith(("room:", "room-area:"))
    left = float(label.x) - (width_m / 2 if centered else 0)
    bottom = float(label.y) - (height_m * 0.55 if centered else 0.20 * height_m)
    return (left, bottom, left + width_m, bottom + height_m)


def _overlap_area(a, b) -> float:
    dx = min(a[2], b[2]) - max(a[0], b[0])
    dy = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, dx) * max(0.0, dy)


def auditar_legibilidade_vista(view, scale: float) -> dict:
    """Flag significant model-coordinate text collisions in a drawing view.

    Source IDs are used for reproducible debugging, not for inferred legal
    compliance. Area thresholds avoid near-touching floating point noise.
    """
    scale = float(scale)
    if not isfinite(scale) or scale <= 0:
        raise ValueError("Escala da auditoria de legibilidade inválida")
    furniture = defaultdict(list)
    for segment in view.segments:
        if segment.layer == "MOBILIARIO" and segment.source_id.startswith("furniture:"):
            furniture[segment.source_id].extend(
                [(segment.x1, segment.y1), (segment.x2, segment.y2)]
            )
    obstacles = {}
    for source, points in furniture.items():
        if len(points) >= 8:
            x = [p[0] for p in points]
            y = [p[1] for p in points]
            obstacles[source] = (min(x), min(y), max(x), max(y))

    # Schedules are intentionally arranged in separate rows. Check only view
    # annotations where overlaying the drawing obscures design information.
    prefixes = ("room:", "room-area:", "opening-tag:", "dimension-label:")
    annotation = [(label, _label_box(label, scale))
                  for label in view.labels
                  if label.source_id.startswith(prefixes)]
    warnings = []
    for label, rect in annotation:
        for furniture_id, obstacle in sorted(obstacles.items()):
            if _overlap_area(rect, obstacle) > 0.003:
                warnings.append({
                    "code": "label-furniture-overlap",
                    "view_id": view.view_id,
                    "source_id": label.source_id,
                    "other_source_id": furniture_id,
                    "detail": "Texto potencialmente sobreposto ao mobiliário.",
                })
        # Some room labels and window/door tags are geometrically close.
        # The caller can use the stable IDs to reposition either annotation.
    for index, (first, box_a) in enumerate(annotation):
        for second, box_b in annotation[index + 1:]:
            if _overlap_area(box_a, box_b) <= 0.003:
                continue
            warnings.append({
                "code": "label-label-overlap",
                "view_id": view.view_id,
                "source_id": first.source_id,
                "other_source_id": second.source_id,
                "detail": "Caixas de texto estimadas se intersectam na prancha.",
            })

    return {
        "ok": not warnings,
        "status": "ok" if not warnings else "review_required",
        "method": "estimated-text-bounds",
        "view_id": view.view_id,
        "scale": scale,
        "checked_labels": len(annotation),
        "checked_furniture": len(obstacles),
        "warnings": warnings,
        "normative_approval": False,
        "limitations": [
            "Estimativa de caixas de texto sem medição tipográfica exata; revisar PDF/PNG em escala.",
            "Não confere acessibilidade, iluminação, ventilação ou requisitos municipais.",
        ],
    }
