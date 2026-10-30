"""Conservative room-width cotas for the compact pilot.

Dimensions are derived from the plan's clear-face room bounding boxes. When
the drawing is too crowded, omit the graphical dimension instead of placing
a false/illegible label. The room schedule remains the complete numeric record.
"""
from __future__ import annotations

from math import isfinite


def _overlap(a, b, clearance=0.0):
    return (min(a[2], b[2]) - max(a[0], b[0]) > -clearance and
            min(a[3], b[3]) - max(a[1], b[1]) > -clearance)


def adicionar_cotas_internas(segments, labels, model, Segment, ViewLabel):
    """Add measured horizontal interior dimension lines and labels.

    Returns source IDs of rooms that could not be annotated safely. No
    dimension is fabricated when an area is obstructed by furniture or text.
    """
    omitted = []
    furniture = [
        tuple(map(float, item)) for item in model.get("moveis", [])
        if len(item) == 4
    ]
    # Match the paper text footprint approximation used by the A3 renderer:
    # min(4, max(3, 160/scale)) mm at 1:50 -> 0.16 m text height.
    height = 0.16

    def annotation_box(label):
        width = max(0.10, len(label.text) * height * 0.53)
        centered = label.source_id.startswith(("room:", "room-area:"))
        left = label.x - width / 2 if centered else label.x
        return (left, label.y - height * 0.55,
                left + width, label.y + height * 0.65)

    label_boxes = [annotation_box(label) for label in labels
                   if label.source_id.startswith((
                       "room:", "room-area:", "opening-tag:",
                       "dimension-label:"
                   ))]
    for index, room in enumerate(model.get("ambientes", [])):
        x1, y1, x2, y2 = (
            float(room[k]) for k in ("x1", "y1", "x2", "y2"))
        if not all(map(isfinite, (x1, y1, x2, y2))) or x2 <= x1 or y2 <= y1:
            raise ValueError("Dimensões inválidas do ambiente para cotas internas")
        width = x2 - x1
        name = f"dimension:room:{index}:width"
        text = f"{width:.2f} m"
        estimated_text_width = len(text) * height * 0.53
        # Candidates closest to the horizontal room edges first, with
        # alternatives for furniture and interior annotation congestion.
        depths = (0.22, 0.36, 0.50, 0.68, 0.88)
        candidates = [
            y for offset in depths for y in (y1 + offset, y2 - offset)
            if y1 + 0.12 < y < y2 - 0.24
        ]
        placed = False
        for y in candidates:
            # The drawn line spans the actual clear-face width, without
            # trimming ends to change the measured length.
            line_box = (x1, y - .022, x2, y + .022)
            label_x = (x1 + x2 - estimated_text_width) / 2
            label_y = y + .11
            label_box = (label_x, label_y - .04,
                         label_x + estimated_text_width, label_y + height)
            if (label_box[0] < x1 + .05 or label_box[2] > x2 - .05
                    or label_box[3] > y2 - .06):
                continue
            if any(_overlap(box, obstacle, .03)
                   for obstacle in furniture
                   for box in (line_box, label_box)):
                continue
            if any(_overlap(label_box, box, .03) for box in label_boxes):
                continue
            # The line itself must not run through another annotation.
            if any(_overlap(line_box, box, .01) for box in label_boxes):
                continue
            segments.append(Segment(x1, y, x2, y, "COTAS-INTERIOR", name))
            for edge in (x1, x2):
                segments.append(Segment(edge - .045, y - .045,
                                        edge + .045, y + .045,
                                        "COTAS-INTERIOR", name))
            new_label = ViewLabel(text, label_x, label_y,
                                  f"dimension-label:room:{index}:width")
            labels.append(new_label)
            label_boxes.append(annotation_box(new_label))
            placed = True
            break
        if not placed:
            omitted.append(f"room:{index}")
    return omitted
