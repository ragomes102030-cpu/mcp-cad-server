"""Parametric views for a compact detached residence licensing package.

Views are geometric studies derived from the existing 2D model and explicit
vertical inputs. They are not a permit approval or a substitute for review.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, isfinite, radians, sin, tan
import re
import unicodedata

from mcp_cad_cloud.arquitetura_requisitos import ProjectContext, RequirementResult


class ArchitecturePackageError(ValueError):
    """Raised when the supplied project cannot support the requested views."""


@dataclass(frozen=True)
class BuildingEnvelope:
    floor_level_m: float
    wall_height_m: float
    door_head_m: float
    window_sill_m: float
    window_head_m: float
    roof_type: str
    roof_pitch_degrees: float
    roof_overhang_m: float
    ridge_axis: str


@dataclass(frozen=True)
class Segment:
    x1: float
    y1: float
    x2: float
    y2: float
    layer: str
    source_id: str


@dataclass(frozen=True)
class ViewLabel:
    text: str
    x: float
    y: float
    source_id: str


@dataclass(frozen=True)
class ViewGeometry:
    view_id: str
    kind: str
    unit: str
    bounds: tuple[float, float, float, float]
    segments: tuple[Segment, ...]
    labels: tuple[ViewLabel, ...]
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class ArchitecturePackage:
    source_plan: dict
    project_context: ProjectContext
    envelope: BuildingEnvelope
    views: tuple[ViewGeometry, ...]
    requirement_results: tuple[RequirementResult, ...] = ()
    readiness: str = "review_required"
    limitations: tuple[str, ...] = (
        "NBR e código de obras municipal ainda não avaliados por requisitos rastreáveis.",
        "Conjunto geométrico para revisão profissional; não representa aprovação de licenciamento.",
        "Alturas e cobertura derivam somente dos valores explícitos fornecidos no contexto.",
        "Áreas anotadas derivam do modelo de projeto, não de medição independente das faces DXF.",
    )


def _normalized_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return re.sub(r"[^a-z0-9]+", "", "".join(
        char for char in decomposed if not unicodedata.combining(char)
    ))


def _finite(name: str, value: float | None) -> float:
    if value is None:
        raise ArchitecturePackageError(f"Altura/dimensão obrigatória ausente: {name}.")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ArchitecturePackageError(f"Valor inválido para {name}.") from exc
    if not isfinite(number):
        raise ArchitecturePackageError(f"Valor inválido para {name}.")
    return number


def _validate_inputs(model: dict, context: ProjectContext, envelope: BuildingEnvelope):
    if not isinstance(model, dict) or model.get("estrategia") != "compacto_2quartos":
        raise ArchitecturePackageError("Apenas o programa compacto de dois quartos é suportado.")
    if context.storeys != 1:
        raise ArchitecturePackageError("Esta versão de arquitetura suporta um pavimento.")
    if context.typology != "compacto_2quartos":
        raise ArchitecturePackageError("Tipologia incompatível com o programa compacto suportado.")

    summary = model.get("resumo_geometria") or {}
    width = _finite("largura da edificação", summary.get("largura"))
    depth = _finite("profundidade da edificação", summary.get("profundidade"))
    lot_width = _finite("largura do lote", context.lot_width_m)
    lot_depth = _finite("profundidade do lote", context.lot_depth_m)
    if lot_width <= 0 or lot_depth <= 0:
        raise ArchitecturePackageError("Dimensões do terreno devem ser positivas.")

    terrain = model.get("terreno")
    if not isinstance(terrain, (tuple, list)) or len(terrain) != 4:
        raise ArchitecturePackageError("Geometria do terreno ausente ou inválida.")
    x1, y1, x2, y2 = (_finite("coordenada do terreno", value) for value in terrain)
    if (abs((x2 - x1) - lot_width) > 1e-5
            or abs((y2 - y1) - lot_depth) > 1e-5):
        raise ArchitecturePackageError("Dimensões do contexto divergem do terreno gerado.")
    if x1 > 0 or y1 > 0 or x2 < width or y2 < depth:
        raise ArchitecturePackageError("Edificação fora dos limites do terreno informado.")

    requested = [_normalized_name(name) for name in context.requested_rooms]
    model_rooms = [_normalized_name(room.get("nome", "")) for room in model.get("ambientes", [])]
    if (len(requested) != 6 or len(requested) != len(set(requested))
            or any(name not in model_rooms for name in requested)):
        raise ArchitecturePackageError("Programa solicitado diverge dos ambientes gerados.")
    core = {
        "sala": any(name.startswith("sala") or name.startswith("estar") for name in requested),
        "cozinha": any("cozinha" in name for name in requested),
        "lavanderia": any("servico" in name or "lavanderia" in name for name in requested),
        "banheiro": any("banheiro" in name for name in requested),
        "quartos": sum("quarto" in name and "banheiro" not in name for name in requested),
    }
    if not all((core["sala"], core["cozinha"], core["lavanderia"], core["banheiro"],
                core["quartos"] == 2)):
        raise ArchitecturePackageError("Programa incompatível: exige sala, cozinha, lavanderia, banheiro e dois quartos.")

    floor = _finite("nível de piso", envelope.floor_level_m)
    wall_height = _finite("altura de parede", envelope.wall_height_m)
    door_head = _finite("altura superior de porta", envelope.door_head_m)
    window_sill = _finite("altura de peitoril", envelope.window_sill_m)
    window_head = _finite("altura superior de janela", envelope.window_head_m)
    pitch = _finite("inclinação do telhado", envelope.roof_pitch_degrees)
    overhang = _finite("beiral", envelope.roof_overhang_m)
    if wall_height <= floor:
        raise ArchitecturePackageError("Altura de parede deve ficar acima do nível do piso.")
    if not floor < door_head <= wall_height:
        raise ArchitecturePackageError("Altura superior de porta incompatível com as paredes.")
    if not floor <= window_sill < window_head <= wall_height:
        raise ArchitecturePackageError("Alturas de peitoril/janela incompatíveis com as paredes.")
    if envelope.roof_type != "gable":
        raise ArchitecturePackageError("A geometria paramétrica desta versão suporta cobertura de duas águas.")
    if not 0 < pitch < 60:
        raise ArchitecturePackageError("Inclinação de cobertura deve estar entre 0 e 60 graus.")
    if overhang < 0:
        raise ArchitecturePackageError("Beiral não pode ser negativo.")
    if envelope.ridge_axis not in {"x", "y"}:
        raise ArchitecturePackageError("Eixo da cumeeira deve ser x ou y.")

    for door in model.get("portas", []):
        if len(door) != 4 or _finite("porta", door[3]) <= 0:
            raise ArchitecturePackageError("Abertura de porta inválida no programa.")
        if not (-1e-5 <= door[0] <= width + 1e-5
                and -1e-5 <= door[1] <= depth + 1e-5):
            raise ArchitecturePackageError("Abertura de porta fora do perímetro da edificação.")
    for window in model.get("janelas", []):
        if len(window) != 4:
            raise ArchitecturePackageError("Abertura de janela inválida no programa.")
        x_start, y_start, x_end, y_end = window
        if (abs(y_start - y_end) > 1e-5 or x_end <= x_start
                or x_start < -1e-5 or x_end > width + 1e-5
                or y_start < -1e-5 or y_start > depth + 1e-5):
            raise ArchitecturePackageError("Geometria de janela incompatível com o perímetro suportado.")
    return width, depth, (x1, y1, x2, y2), floor, wall_height, door_head, window_sill, window_head


def _make_view(view_id: str, kind: str, segments: list[Segment],
               labels: list[ViewLabel] | None = None) -> ViewGeometry:
    if not segments:
        raise ArchitecturePackageError(f"Vista arquitetônica vazia: {view_id}.")
    xs = [point for seg in segments for point in (seg.x1, seg.x2)]
    ys = [point for seg in segments for point in (seg.y1, seg.y2)]
    # Include label extents in the viewport bounds. Text is plotted at about
    # 3.2 mm on A3 at 1:50; 0.10 m per character is a conservative width.
    for label in labels or ():
        xs.extend((label.x, label.x + 0.10 * len(label.text)))
        ys.extend((label.y - 0.08, label.y + 0.16))
    sources = tuple(dict.fromkeys(seg.source_id for seg in segments))
    return ViewGeometry(
        view_id=view_id,
        kind=kind,
        unit="m",
        bounds=(min(xs), min(ys), max(xs), max(ys)),
        segments=tuple(segments),
        labels=tuple(labels or ()),
        source_ids=sources,
    )


def _segment(target: list[Segment], x1: float, y1: float, x2: float, y2: float,
             layer: str, source_id: str):
    if abs(x1 - x2) + abs(y1 - y2) > 1e-9:
        target.append(Segment(float(x1), float(y1), float(x2), float(y2), layer, source_id))


def _rect(target: list[Segment], x1: float, y1: float, x2: float, y2: float,
          layer: str, source_id: str):
    _segment(target, x1, y1, x2, y1, layer, source_id)
    _segment(target, x2, y1, x2, y2, layer, source_id)
    _segment(target, x2, y2, x1, y2, layer, source_id)
    _segment(target, x1, y2, x1, y1, layer, source_id)


def _wall_faces(target: list[Segment], wall: tuple[float, ...],
                thickness: float, source_id: str):
    """Draw both wall faces and end jambs from an orthogonal wall axis."""
    x1, y1, x2, y2 = (float(value) for value in wall)
    half = thickness / 2
    if abs(y2-y1) <= 1e-8:
        left, right = sorted((x1, x2))
        _segment(target, left, y1-half, right, y1-half,
                 "PAREDES", source_id)
        _segment(target, left, y1+half, right, y1+half,
                 "PAREDES", f"{source_id}:face:1")
        _segment(target, left, y1-half, left, y1+half,
                 "PAREDES", f"{source_id}:end:0")
        _segment(target, right, y1-half, right, y1+half,
                 "PAREDES", f"{source_id}:end:1")
    elif abs(x2-x1) <= 1e-8:
        bottom, top = sorted((y1, y2))
        _segment(target, x1-half, bottom, x1-half, top,
                 "PAREDES", source_id)
        _segment(target, x1+half, bottom, x1+half, top,
                 "PAREDES", f"{source_id}:face:1")
        _segment(target, x1-half, bottom, x1+half, bottom,
                 "PAREDES", f"{source_id}:end:0")
        _segment(target, x1-half, top, x1+half, top,
                 "PAREDES", f"{source_id}:end:1")
    else:
        raise ArchitecturePackageError(
            "A planta arquitetônica exige eixos de parede ortogonais nesta versão.")


def _opening_axis(model: dict, x: float, y: float, width: float) -> str:
    """Infer whether a door opening lies on a horizontal or vertical wall."""
    horizontal = vertical = 0
    for wall in model.get("paredes", []):
        x1, y1, x2, y2 = (float(value) for value in wall)
        if abs(y2-y1) <= 1e-8 and abs(y-y1) <= 0.16:
            left, right = sorted((x1, x2))
            if min(abs(left-x), abs(right-x), abs(left-(x+width)),
                   abs(right-(x+width))) <= 0.16:
                horizontal += 1
        elif abs(x2-x1) <= 1e-8 and abs(x-x1) <= 0.16:
            bottom, top = sorted((y1, y2))
            if min(abs(bottom-y), abs(top-y), abs(bottom-(y+width)),
                   abs(top-(y+width))) <= 0.16:
                vertical += 1
    return "horizontal" if horizontal >= vertical else "vertical"


def _floor_plan(model: dict) -> ViewGeometry:
    segments: list[Segment] = []
    width = _finite("largura da planta", model.get("resumo_geometria", {}).get("largura"))
    depth = _finite("profundidade da planta", model.get("resumo_geometria", {}).get("profundidade"))
    thickness = _finite("espessura de parede", model.get("espessura_parede"))
    if thickness <= 0:
        raise ArchitecturePackageError("Espessura de parede deve ser positiva.")
    for index, wall in enumerate(model["paredes"]):
        _wall_faces(segments, wall, thickness, f"wall:{index}")
    leaves = model.get("portas_folhas", [])
    if len(leaves) != len(model.get("portas", [])):
        raise ArchitecturePackageError("Orientação explícita das folhas das portas ausente.")
    for index, (door, leaf_angle) in enumerate(zip(model["portas"], leaves)):
        x, y, _wall_angle, width = door
        angle = radians(_finite("orientação de folha de porta", leaf_angle))
        _segment(segments, x, y, x + width * cos(angle), y + width * sin(angle),
                 "ESQUADRIA-PORTA", f"door:{index}:leaf")
        # Show the conventional quarter swing from the closed wall axis to
        # the modeled open leaf. Eight chords keep the geometry portable to
        # lightweight DXF consumers while retaining stable audit IDs.
        arc_start = angle - radians(90)
        for part in range(8):
            a0 = arc_start + radians(90) * part / 8
            a1 = arc_start + radians(90) * (part + 1) / 8
            _segment(segments,
                     x + width * cos(a0), y + width * sin(a0),
                     x + width * cos(a1), y + width * sin(a1),
                     "ESQUADRIA-PORTA", f"door:{index}:swing:{part:02d}")
    for index, window in enumerate(model["janelas"]):
        x1, y1, x2, y2 = window
        offset = 0.035
        _segment(segments, x1, y1 - offset, x2, y2 - offset,
                 "ESQUADRIA-JANELA", f"window:{index}:line:1")
        _segment(segments, x1, y1 + offset, x2, y2 + offset,
                 "ESQUADRIA-JANELA", f"window:{index}:line:2")
    for index, furniture in enumerate(model.get("moveis", [])):
        if len(furniture) != 4:
            raise ArchitecturePackageError("Mobiliário inválido no programa.")
        x1, y1, x2, y2 = (_finite("mobiliário", value) for value in furniture)
        if x2 <= x1 or y2 <= y1:
            raise ArchitecturePackageError("Dimensões de mobiliário inválidas.")
        _rect(segments, x1, y1, x2, y2, "MOBILIARIO", f"furniture:{index}")

    areas = {room.get("nome"): room.get("area") for room in model.get("cotas_ambientes", [])}
    labels: list[ViewLabel] = []
    for index, room in enumerate(model["ambientes"]):
        x = room.get("texto_x", (room["x1"] + room["x2"]) / 2)
        y = room.get("texto_y", (room["y1"] + room["y2"]) / 2)
        name_key = _normalized_name(room["nome"])
        # The template furnishes some rooms densely. Move the label into the
        # known clear zone so it does not print over the bed, sofa or fixtures.
        if name_key.startswith("sala") or name_key.startswith("estar"):
            x, y = room["x2"] - 0.80, room["y2"] - 0.80
        elif name_key == "quarto1":
            x, y = room["x2"] - 0.65, room["y1"] + 0.56 * (room["y2"] - room["y1"])
        elif name_key == "quarto2":
            x, y = (room["x1"] + room["x2"]) / 2, room["y1"] + 0.45
        elif "banheiro" in name_key:
            x, y = room["x2"] - 0.68, room["y2"] - 0.63
        labels.append(ViewLabel(room["nome"], x, y, f"room:{index}"))
        area = areas.get(room["nome"])
        if area is not None:
            labels.append(ViewLabel(f"{float(area):.2f} m²", x, y - 0.25,
                                    f"room-area:{index}"))
    # Opening IDs sit just inside the footprint, near their modeled opening.
    # The complete schedule below carries the corresponding clear model width.
    for index, (x, y, _wall_angle, door_width) in enumerate(model["portas"]):
        axis = _opening_axis(model, float(x), float(y), float(door_width))
        if axis == "horizontal":
            tag_x = float(x) + float(door_width) / 2
            tag_y = float(y) + (0.38 if float(y) < depth / 2 else -0.38)
        else:
            tag_x = float(x) + (0.38 if float(x) < width / 2 else -0.38)
            tag_y = float(y) + float(door_width) / 2
        labels.append(ViewLabel(f"P{index + 1:02d}", tag_x, tag_y,
                                f"opening-tag:door:{index}"))
    for index, (x1, y1, x2, y2) in enumerate(model["janelas"]):
        labels.append(ViewLabel(f"J{index + 1:02d}", (x1 + x2) / 2,
                                y1 + (0.48 if y1 < depth / 2 else -0.48),
                                f"opening-tag:window:{index}"))

    # Compact drawing schedule, positioned to the right of the footprint.
    # Room dimensions/areas are copied from cotas_ambientes and are explicitly
    # model values; they are not independently measured clear-face dimensions.
    schedule_x = _finite("largura da planta", model.get("resumo_geometria", {}).get("largura")) + 0.65
    schedule_y = _finite("profundidade da planta", model.get("resumo_geometria", {}).get("profundidade")) - 0.10
    row = 0.30
    labels.append(ViewLabel("AMBIENTES | DIMENSÕES E ÁREAS", schedule_x, schedule_y,
                            "schedule:rooms:title"))
    for index, room in enumerate(model.get("cotas_ambientes", [])):
        schedule_y -= row
        labels.append(ViewLabel(
            f"{room['nome']} | {float(room['largura']):.2f} x "
            f"{float(room['profundidade']):.2f} m | {float(room['area']):.2f} m²",
            schedule_x, schedule_y, f"schedule:room:{index}"))
    schedule_y -= row * 1.25
    labels.append(ViewLabel("PORTAS | VÃOS (m)", schedule_x, schedule_y,
                            "schedule:doors:title"))
    for index, door in enumerate(model.get("portas", [])):
        schedule_y -= row
        labels.append(ViewLabel(f"P{index + 1:02d} | {float(door[3]):.2f}",
                                schedule_x, schedule_y, f"schedule:door:{index}"))
    schedule_y -= row * 1.25
    labels.append(ViewLabel("JANELAS | VÃOS (m)", schedule_x, schedule_y,
                            "schedule:windows:title"))
    for index, window in enumerate(model.get("janelas", [])):
        schedule_y -= row
        labels.append(ViewLabel(f"J{index + 1:02d} | {abs(float(window[2]) - float(window[0])):.2f}",
                                schedule_x, schedule_y, f"schedule:window:{index}"))
    width = _finite("largura da planta", model.get("resumo_geometria", {}).get("largura"))
    depth = _finite("profundidade da planta", model.get("resumo_geometria", {}).get("profundidade"))
    # Overall external dimension strings are explicit drawing geometry with
    # stable source IDs, so serialization audits can detect missing cotas.
    offset = 0.65
    tick = 0.12
    for source, x1, y1, x2, y2 in (
        ("dimension:overall:width", 0.0, depth + offset, width, depth + offset),
        ("dimension:overall:width", -tick, depth + offset - tick, tick, depth + offset + tick),
        ("dimension:overall:width", width - tick, depth + offset - tick, width + tick, depth + offset + tick),
        ("dimension:overall:depth", -offset, 0.0, -offset, depth),
        ("dimension:overall:depth", -offset - tick, -tick, -offset + tick, tick),
        ("dimension:overall:depth", -offset - tick, depth - tick, -offset + tick, depth + tick),
    ):
        _segment(segments, x1, y1, x2, y2, "COTAS", source)
    labels.extend((
        ViewLabel(f"{width:.2f} m", width / 2, depth + offset + 0.08,
                  "dimension-label:overall:width"),
        ViewLabel(f"{depth:.2f} m", -offset - 0.10, depth / 2,
                  "dimension-label:overall:depth"),
    ))
    return _make_view("ARQ-PLANTA", "planta_baixa", segments, labels)


def _site_plan(width: float, depth: float, terrain: tuple[float, float, float, float]) -> ViewGeometry:
    x1, y1, x2, y2 = terrain
    segments: list[Segment] = []
    _rect(segments, x1, y1, x2, y2, "LOTE", "site:parcel")
    _rect(segments, 0.0, 0.0, width, depth, "PROJECAO", "site:building-footprint")
    for index, (sx, sy, ex, ey) in enumerate((
        (x1, 0.0, 0.0, 0.0), (width, 0.0, x2, 0.0),
        (0.0, y1, 0.0, 0.0), (0.0, depth, 0.0, y2),
    )):
        _segment(segments, sx, sy, ex, ey, "AFASTAMENTOS-GEOMETRICOS", f"site:setback:{index}")
    return _make_view("ARQ-IMPLANTACAO", "implantacao", segments)


def _roof_plan(width: float, depth: float, envelope: BuildingEnvelope) -> ViewGeometry:
    b = envelope.roof_overhang_m
    segments: list[Segment] = []
    _rect(segments, -b, -b, width + b, depth + b, "COBERTURA", "roof:eaves-outline")
    if envelope.ridge_axis == "x":
        _segment(segments, -b, depth / 2, width + b, depth / 2,
                 "CUMEEIRA", "roof:ridge")
    else:
        _segment(segments, width / 2, -b, width / 2, depth + b,
                 "CUMEEIRA", "roof:ridge")
    return _make_view("ARQ-COBERTURA", "planta_cobertura", segments)


def _facade(view_id: str, side: str, width: float, depth: float,
            model: dict, envelope: BuildingEnvelope,
            door_head: float, window_sill: float, window_head: float) -> ViewGeometry:
    along_x = side in {"frontal", "fundos"}
    span = width if along_x else depth
    boundary = 0.0 if side in {"frontal", "lateral-esq"} else (depth if along_x else width)
    roof_pitch = radians(envelope.roof_pitch_degrees)
    slope_span = depth if envelope.ridge_axis == "x" else width
    rise = slope_span * 0.5 * tan(roof_pitch)
    wall_top = envelope.floor_level_m + envelope.wall_height_m
    ridge = wall_top + rise
    segments: list[Segment] = []
    facade_id = f"facade:{side}"
    _rect(segments, 0.0, envelope.floor_level_m, span, wall_top,
          "FACHADA-PAREDE", facade_id)
    _segment(segments, -envelope.roof_overhang_m, wall_top,
             span + envelope.roof_overhang_m, wall_top, "BEIRAL", facade_id)

    # Elevation of the roof silhouette depends on whether the ridge runs toward
    # this facade or across it.
    ridge_visible = (along_x and envelope.ridge_axis == "y") or (
        not along_x and envelope.ridge_axis == "x")
    left_eave = -envelope.roof_overhang_m
    right_eave = span + envelope.roof_overhang_m
    if ridge_visible:
        _segment(segments, left_eave, wall_top, span / 2, ridge,
                 "COBERTURA", f"roof:{side}:left-plane")
        _segment(segments, span / 2, ridge, right_eave, wall_top,
                 "COBERTURA", f"roof:{side}:right-plane")
    # When the ridge runs parallel to this facade, the projected roof edge is
    # the eaves line already drawn above. Adding a second line at ridge height
    # here created a detached, physically misleading roof profile.

    if along_x:
        coord = boundary
        for index, window in enumerate(model["janelas"]):
            x1, y1, x2, y2 = window
            if abs(y1 - y2) < 1e-5 and abs(y1 - coord) <= 0.10:
                _rect(segments, x1, envelope.floor_level_m + window_sill,
                      x2, envelope.floor_level_m + window_head,
                      "ESQUADRIA-JANELA", f"window:{side}:{index}")
        for index, door in enumerate(model["portas"]):
            x, y, _angle, door_width = door
            if abs(y - coord) <= 0.10:
                _rect(segments, x, envelope.floor_level_m, x + door_width,
                      envelope.floor_level_m + door_head,
                      "ESQUADRIA-PORTA", f"door:{side}:{index}")
    else:
        coord = boundary
        for index, door in enumerate(model["portas"]):
            x, y, _angle, door_width = door
            if abs(x - coord) <= 0.10:
                _rect(segments, y, envelope.floor_level_m, y + door_width,
                      envelope.floor_level_m + door_head,
                      "ESQUADRIA-PORTA", f"door:{side}:{index}")

    return _make_view(view_id, f"fachada_{side}", segments)


def _section(view_id: str, axis: str, width: float, depth: float, model: dict,
             envelope: BuildingEnvelope, floor: float, wall_height: float,
             door_head: float, window_sill: float, window_head: float) -> ViewGeometry:
    """Build a schematic section through intersected plan walls and openings."""
    along_x = axis == "x"
    cut = depth / 2 if along_x else width / 2
    distance = width if along_x else depth
    wall_top = floor + wall_height
    segments: list[Segment] = []
    _segment(segments, 0, floor, distance, floor, "CORTE-PISO", f"section:{axis}:floor")

    intersected_walls: list[tuple[float, str]] = [(0.0, f"section:{axis}:exterior:start"),
                                                   (distance, f"section:{axis}:exterior:end")]
    for index, wall in enumerate(model["paredes"]):
        x1, y1, x2, y2 = wall
        if along_x and abs(x1 - x2) < 1e-5 and min(y1, y2) <= cut <= max(y1, y2):
            intersected_walls.append((x1, f"section:{axis}:wall:{index}"))
        elif not along_x and abs(y1 - y2) < 1e-5 and min(x1, x2) <= cut <= max(x1, x2):
            intersected_walls.append((y1, f"section:{axis}:wall:{index}"))

    for index, room in enumerate(model.get("ambientes", [])):
        if along_x and room["y1"] - 1e-5 <= cut <= room["y2"] + 1e-5:
            intersected_walls.extend((
                (room["x1"], f"section:{axis}:room:{index}:left"),
                (room["x2"], f"section:{axis}:room:{index}:right"),
            ))
        elif not along_x and room["x1"] - 1e-5 <= cut <= room["x2"] + 1e-5:
            intersected_walls.extend((
                (room["y1"], f"section:{axis}:room:{index}:front"),
                (room["y2"], f"section:{axis}:room:{index}:rear"),
            ))

    seen_positions: set[float] = set()
    for location, source in intersected_walls:
        rounded = round(location, 6)
        if rounded in seen_positions:
            continue
        seen_positions.add(rounded)
        _segment(segments, location, floor, location, wall_top, "CORTE-PAREDE", source)

    if envelope.ridge_axis == ("x" if along_x else "y"):
        ridge_height = wall_top + (distance / 2 + envelope.roof_overhang_m) * tan(
            radians(envelope.roof_pitch_degrees))
        _segment(segments, 0, ridge_height, distance, ridge_height,
                 "CORTE-COBERTURA", f"section:{axis}:ridge-run")
        # In a section running along the ridge, the cut crosses both gable
        # end walls. Raise those two end-wall profiles to meet the ridge line;
        # leaving them at eaves height made the roof appear suspended.
        for side, position in (("start", 0.0), ("end", distance)):
            _segment(segments, position, wall_top, position, ridge_height,
                     "CORTE-PAREDE", f"section:{axis}:gable-{side}")
    else:
        roof_span = distance + 2 * envelope.roof_overhang_m
        half = roof_span / 2
        ridge_height = wall_top + half * tan(radians(envelope.roof_pitch_degrees))
        _segment(segments, -envelope.roof_overhang_m, wall_top,
                 distance / 2, ridge_height, "CORTE-COBERTURA",
                 f"section:{axis}:roof-left")
        _segment(segments, distance / 2, ridge_height,
                 distance + envelope.roof_overhang_m, wall_top,
                 "CORTE-COBERTURA", f"section:{axis}:roof-right")

    # Openings are shown only when the cut line passes through the opening.
    for index, door in enumerate(model["portas"]):
        x, y, _angle, door_width = door
        position = x if along_x else y
        fixed = y if along_x else x
        if abs(fixed - cut) <= 0.10:
            _rect(segments, position, floor, position + door_width,
                  floor + door_head, "CORTE-PORTA", f"section:{axis}:door:{index}")
    for index, window in enumerate(model["janelas"]):
        x1, y1, x2, y2 = window
        if along_x and abs(y1 - y2) < 1e-5 and abs(y1 - cut) <= 0.10:
            _rect(segments, x1, floor + window_sill, x2, floor + window_head,
                  "CORTE-JANELA", f"section:{axis}:window:{index}")
        elif not along_x and abs(x2 - x1) < 1e-5 and abs(x1 - cut) <= 0.10:
            _rect(segments, y1, floor + window_sill, y2, floor + window_head,
                  "CORTE-JANELA", f"section:{axis}:window:{index}")

    return _make_view(view_id, f"corte_{axis}", segments)


def generate_architecture_package(
    model: dict,
    context: ProjectContext,
    envelope: BuildingEnvelope,
) -> ArchitecturePackage:
    """Derive licensing views from a validated compact plan and vertical data."""
    (width, depth, terrain, floor, wall_height, door_head,
     window_sill, window_head) = _validate_inputs(model, context, envelope)
    views = [
        _site_plan(width, depth, terrain),
        _floor_plan(model),
        _roof_plan(width, depth, envelope),
        _section("ARQ-CORTE-A", "y", width, depth, model, envelope, floor,
                 wall_height, door_head, window_sill, window_head),
        _section("ARQ-CORTE-B", "x", width, depth, model, envelope, floor,
                 wall_height, door_head, window_sill, window_head),
    ]
    views.extend([
        _facade("ARQ-FACHADA-FRONTAL", "frontal", width, depth, model,
                envelope, door_head, window_sill, window_head),
        _facade("ARQ-FACHADA-FUNDOS", "fundos", width, depth, model,
                envelope, door_head, window_sill, window_head),
        _facade("ARQ-FACHADA-LATERAL-ESQ", "lateral-esq", width, depth, model,
                envelope, door_head, window_sill, window_head),
        _facade("ARQ-FACHADA-LATERAL-DIR", "lateral-dir", width, depth, model,
                envelope, door_head, window_sill, window_head),
    ])
    return ArchitecturePackage(
        source_plan=model,
        project_context=context,
        envelope=envelope,
        views=tuple(views),
    )
