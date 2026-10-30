"""Measured, collision-aware interior dimensions for compact floor plans.

Use room clear-face bounds without silently shortening a dimension. Full-length
horizontal/vertical lines are drawn only where door swings, furniture and text
permit them. Record any omission rather than inventing a clear placement.

This is a graphic preflight, NOT an accessibility or code-compliance check.
"""
from __future__ import annotations

from math import isfinite

from mcp_cad_cloud.auditoria_legibilidade import _label_box


def _overlap(a, b, clearance=0.0):
    return (min(a[2], b[2]) - max(a[0], b[0]) > -clearance and
            min(a[3], b[3]) - max(a[1], b[1]) > -clearance)


def _room_box(room):
    values = tuple(float(room[key]) for key in ("x1", "y1", "x2", "y2"))
    x1, y1, x2, y2 = values
    if not all(map(isfinite, values)) or x2 <= x1 or y2 <= y1:
        raise ValueError("Ambiente sem dimensoes positivas e finitas")
    return values


def _candidates(index, room, axis, blocked, obstacles, door_boxes, ViewLabel):
    x1, y1, x2, y2 = _room_box(room)
    length = x2 - x1 if axis == "width" else y2 - y1
    text = f"{length:.2f} m"
    height = 0.16  # model metres at 1:50; matches A3 annotation estimate
    text_width = len(text) * height * 0.53
    extent = y2 - y1 if axis == "width" else x2 - x1
    choices = []
    for step in range(17, int((extent - 0.17) * 100), 3):
        pos = (y1 if axis == "width" else x1) + step / 100
        line = (x1, pos - .010, x2, pos + .010) if axis == "width" else (
            pos - .010, y1, pos + .010, y2)
        if any(_overlap(line, box, .020) for box in obstacles + blocked):
            continue
        if any(_overlap(line, box, .008) for box in door_boxes):
            continue
        for side in (1, -1):
            if axis == "width":
                label_y = pos + (.14 if side == 1 else -.17)
                options = ((x1 + step / 100) for step in range(
                    6, int((x2 - x1 - text_width - .06) * 100), 6))
                label_locations = ((xx, label_y) for xx in options)
            else:
                label_x = pos + (.13 if side == 1 else -text_width - .13)
                options = ((y1 + step / 100) for step in range(
                    6, int((y2 - y1 - .15) * 100), 6))
                label_locations = ((label_x, yy) for yy in options)
            for lx, ly in label_locations:
                label = ViewLabel(
                    text, lx, ly, f"dimension-label:room:{index}:{axis}")
                rect = _label_box(label, 50)
                if (rect[0] < x1 + .035 or rect[2] > x2 - .035 or
                        rect[1] < y1 + .035 or rect[3] > y2 - .035):
                    continue
                if any(_overlap(rect, box, .018) for box in obstacles + blocked):
                    continue
                if any(_overlap(rect, box, .018) for box in door_boxes):
                    continue
                boundary = min(pos - (y1 if axis == "width" else x1),
                               (y2 if axis == "width" else x2) - pos)
                center_penalty = (abs(lx + text_width/2 - (x1+x2)/2)
                                  if axis == "width" else
                                  abs(ly - (y1+y2)/2))
                choices.append((boundary + .25 * center_penalty, pos,
                                label, line, rect))
    return sorted(choices, key=lambda entry: entry[0])


def _emit(segments, labels, Segment, chosen, room, index, axis, blocked):
    _, pos, label, _, rect = chosen
    x1, y1, x2, y2 = _room_box(room)
    source = f"dimension:room:{index}:{axis}"
    if axis == "width":
        segments.append(Segment(x1, pos, x2, pos, "COTAS-INTERIOR", source))
        ends = ((x1, pos), (x2, pos))
    else:
        segments.append(Segment(pos, y1, pos, y2, "COTAS-INTERIOR", source))
        ends = ((pos, y1), (pos, y2))
    for x, y in ends:
        segments.append(Segment(x-.045, y-.045, x+.045, y+.045,
                                "COTAS-INTERIOR", source))
    labels.append(label)
    blocked.append(rect)


def adicionar_cotas_internas(segments, labels, model, Segment, ViewLabel):
    """Place two measured axes per room where unobstructed.

    Pair-search for the congested rooms prevents a width label from making
    an otherwise possible vertical label impossible. Vertical and horizontal
    dimension baselines inherently cross geometrically inside a rectangle;
    their *labels* are protected from both baselines.
    """
    furniture = [tuple(map(float, item)) for item in model.get("moveis", [])
                 if len(item) == 4]
    doors = [
        (min(s.x1, s.x2), min(s.y1, s.y2),
         max(s.x1, s.x2), max(s.y1, s.y2))
        for s in segments if s.layer == "ESQUADRIA-PORTA"
    ]
    prefixes = ("room:", "room-area:", "opening-tag:", "dimension-label:")
    blocked = [_label_box(label, 50) for label in labels
               if label.source_id.startswith(prefixes)]
    rooms = model.get("ambientes", [])
    for room in rooms:
        _room_box(room)  # reject invalid geometry before producing any cotas

    # Constrained rooms first: the bathroom and laundry have far fewer
    # safe placements than the open living room.
    rankings = []
    for index, room in enumerate(rooms):
        width = _candidates(index, room, "width", blocked, furniture,
                            doors, ViewLabel)
        depth = _candidates(index, room, "depth", blocked, furniture,
                            doors, ViewLabel)
        rankings.append((min(len(width), len(depth)), index))
    omitted = {"width": [], "depth": []}

    for _, index in sorted(rankings):
        room = rooms[index]
        width = _candidates(index, room, "width", blocked, furniture,
                            doors, ViewLabel)
        depth = _candidates(index, room, "depth", blocked, furniture,
                            doors, ViewLabel)
        best_pair = None
        for w in width[:450]:
            for d in depth[:450]:
                if (_overlap(w[4], d[4], .012) or
                        _overlap(w[4], d[3], .010) or
                        _overlap(d[4], w[3], .010)):
                    continue
                score = w[0] + d[0]
                if best_pair is None or score < best_pair[0]:
                    best_pair = (score, w, d)
            if best_pair and w[0] > best_pair[0]:
                break
        if best_pair:
            _emit(segments, labels, Segment, best_pair[1], room,
                  index, "width", blocked)
            _emit(segments, labels, Segment, best_pair[2], room,
                  index, "depth", blocked)
        else:
            # A requested dimension is not silently fabricated just to
            # achieve 100% graphic coverage.
            for axis in ("width", "depth"):
                options = _candidates(index, room, axis, blocked, furniture,
                                      doors, ViewLabel)
                if options:
                    _emit(segments, labels, Segment, options[0], room,
                          index, axis, blocked)
                else:
                    omitted[axis].append(index)
    return omitted


def adicionar_profundidades_auxiliares(segments, labels, model, omitted,
                                     Segment, ViewLabel):
    """Draw true-scale vertical reference rails outside the footprint.

    The rails preserve the original model Y ordinates. They are annotated
    as auxiliary, *without* fictitious witness lines across other rooms.
    If an unobstructed rail or a separate legend cannot fit, leave a
    dimension omitted; the room schedule remains the numeric source.
    """
    indices = [int(i) for i in omitted.get("depth", [])]
    if not indices:
        return []
    room_data = model.get("ambientes", [])
    width = float(model["resumo_geometria"]["largura"])
    depth = float(model["resumo_geometria"]["profundidade"])
    scheduled = [label for label in labels
                 if label.source_id.startswith("schedule:")]
    if not scheduled:
        return []
    # Reserve a quiet strip immediately between the right exterior wall
    # and the table at width + 0.65 m. No oblique room-to-rail extension
    # crosses another apartment/room.
    rail_x = width + .28
    header_y = min(label.y for label in scheduled) - .30
    legend_ys = [header_y - .30 * (i + 1) for i in range(len(indices))]
    if (header_y > depth - .20 or
            not legend_ys or min(legend_ys) < .35):
        return []

    original_labels = [_label_box(item, 50) for item in labels
                       if item.source_id.startswith(
                           ("room:", "room-area:", "opening-tag:",
                            "dimension-label:", "schedule:"))]
    rail_boxes = []
    result = []
    for idx, row_y in zip(indices, legend_ys):
        if not (0 <= idx < len(room_data)):
            continue
        _, y1, _, y2 = _room_box(room_data[idx])
        rail = (rail_x - .05, y1, rail_x + .05, y2)
        if y1 < 0 or y2 > depth:
            continue
        if any(_overlap(rail, old, .035) for old in rail_boxes):
            continue
        # The textual room name is essential: the rail is a proportional
        # reference and is intentionally NOT shown as an in-situ wall cota.
        tag = f"AUX D{idx + 1:02d} {room_data[idx]['nome']} {y2-y1:.2f} m"
        label = ViewLabel(tag, width + .65, row_y,
                          f"dimension-label:room:{idx}:depth:aux")
        label_box = _label_box(label, 50)
        if any(_overlap(label_box, other, .025)
               for other in original_labels):
            continue
        original_labels.append(label_box)
        rail_boxes.append(rail)
        source = f"dimension:room:{idx}:depth:aux"
        segments.append(Segment(rail_x, y1, rail_x, y2,
                                "COTAS-AUXILIAR", source))
        for y in (y1, y2):
            segments.append(Segment(rail_x-.045, y-.045,
                                    rail_x+.045, y+.045,
                                    "COTAS-AUXILIAR", source))
        labels.append(label)
        result.append(idx)
    if result:
        labels.append(ViewLabel("COTAS AUX. - REFERENCIA SEM CHAMADA",
                                width+.65, header_y, "aux-depth:legend"))
    return result
