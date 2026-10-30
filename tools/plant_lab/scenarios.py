"""Deterministic supported programs and adversarial plant/DXF cases."""
from __future__ import annotations

from copy import deepcopy
from itertools import product

from mcp_cad_cloud.planta_gerador import ErroPrograma, gerar_modelo
from mcp_cad_cloud.validar_modelo import validar

BASE_PROGRAM = {
    "largura": 9.0, "terreno_largura": 10.0, "terreno_profundidade": 20.0,
    "recuo_lateral": 0.5, "recuo_frente": 3.0, "recuo_fundo": 2.0,
    "ambientes": [
        {"nome": "Sala de estar", "area": 18.0},
        {"nome": "Cozinha", "area": 9.0},
        {"nome": "Área de serviço", "area": 5.0},
        {"nome": "Quarto 1", "area": 12.0},
        {"nome": "Quarto 2", "area": 10.0},
        {"nome": "Banheiro social", "area": 5.0},
    ],
}


def _build_valid_scenarios() -> list[dict]:
    candidates = product(
        (16.0, 16.5, 17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0),
        (8.0, 8.5, 9.0, 9.5, 10.0),
        (4.0, 4.5, 5.0, 5.5, 6.0),
        (11.0, 11.5, 12.0, 12.5, 13.0),
        (9.0, 9.5, 10.0, 10.5, 11.0),
        (4.0, 4.5, 5.0, 5.5, 6.0),
    )
    candidates = tuple(candidates)
    widths = (8.7, 8.8, 8.9, 9.0, 9.1, 9.2, 9.3)
    setbacks = ((0.4, 2.0, 1.0), (0.5, 3.0, 2.0), (0.7, 4.0, 3.0))
    scenarios = []
    for width in widths:
        accepted_for_width = 0
        for areas in candidates:
            program = deepcopy(BASE_PROGRAM)
            setback = setbacks[(len(scenarios) + accepted_for_width) % len(setbacks)]
            side, front, back = setback
            program.update(
                largura=width,
                terreno_largura=width + 2 * side + 0.4,
                terreno_profundidade=9.2 + front + back + 1.0,
                recuo_lateral=side,
                recuo_frente=front,
                recuo_fundo=back,
            )
            for room, area in zip(program["ambientes"], areas):
                room["area"] = area
            try:
                model = gerar_modelo(program)
            except ErroPrograma:
                continue
            # A generator-accepted program can still contain orphaned furniture.
            # Only count scenarios that pass the same strict model gate as preview.
            if not validar(model, estrito=True).get("ok"):
                continue
            index = len(scenarios) + 1
            lot_width = float(program["terreno_largura"])
            lot_depth = float(program["terreno_profundidade"])
            scenarios.append({
                "id": f"valid-{index:02d}-w{width:.1f}",
                "kind": "supported_program",
                "source": "structured",
                "program": program,
                "briefing": (
                    f"Residência térrea de dois quartos, sala, cozinha, lavanderia "
                    f"e banheiro em lote de {lot_width:.1f} x {lot_depth:.1f} m."
                ),
                "terrain_bounds": (-side, -front, -side + lot_width,
                                   -front + lot_depth),
                "expected_doors": 5,
                "expected_window_pairs": 6,
                "expected_room_areas_m2": [room["area"] for room in program["ambientes"]],
                "render": accepted_for_width in (0, 3),
            })
            accepted_for_width += 1
            if accepted_for_width == 6:
                break
    # Preserve a full end-to-end case at the width where the original suite
    # exposed a laundry-door/furniture collision.
    scenarios = scenarios[:30]
    if not any(abs(float(item["program"]["largura"]) - 9.2) < 1e-8
               for item in scenarios):
        program = deepcopy(BASE_PROGRAM)
        program.update(largura=9.2, terreno_largura=10.4, terreno_profundidade=20.0,
            recuo_lateral=0.5, recuo_frente=3.0, recuo_fundo=2.0)
        for room, area in zip(program["ambientes"], (16.0, 8.0, 4.0, 11.0, 11.0, 5.5)):
            room["area"] = area
        if validar(gerar_modelo(program), estrito=True).get("ok"):
            case = {
                "id": "valid-width-9.2", "kind": "supported_program",
                "source": "structured", "program": program,
                "briefing": "Residência de dois quartos no lote de 10,4 x 20,0 m.",
                "terrain_bounds": (-0.5, -3.0, 9.9, 17.0),
                "expected_doors": 5, "expected_window_pairs": 6,
                "expected_room_areas_m2": [room["area"] for room in program["ambientes"]],
                "render": True,
            }
            if len(scenarios) >= 30:
                scenarios[-1] = case
            else:
                scenarios.append(case)
    # The compact template supports fewer independent room-area combinations
    # than the raw Cartesian input space suggests. Add explicit terrain/recuo
    # variants of already verified room programs so lot placement is exercised
    # without pretending unsupported room schedules are valid.
    base_scenarios = list(scenarios)
    terrain_variants = ((0.35, 2.5, 1.5), (0.6, 3.5, 2.5), (0.8, 4.0, 3.0))
    variant_index = 0
    while len(scenarios) < 30:
        source = base_scenarios[variant_index % len(base_scenarios)]
        side, front, back = terrain_variants[variant_index % len(terrain_variants)]
        program = deepcopy(source["program"])
        house_width = float(program["largura"])
        house_depth = float(gerar_modelo(program)["resumo_geometria"]["profundidade"])
        program.update(recuo_lateral=side, recuo_frente=front, recuo_fundo=back,
            terreno_largura=house_width + 2 * side + 0.4,
            terreno_profundidade=house_depth + front + back + 1.0)
        if validar(gerar_modelo(program), estrito=True).get("ok"):
            variant_index += 1
            item = deepcopy(source)
            item.update(id=f"valid-terrain-{len(scenarios)+1:02d}", program=program,
                terrain_bounds=(-side, -front, -side + program["terreno_largura"],
                                -front + program["terreno_profundidade"]))
            scenarios.append(item)
        else:
            variant_index += 1
    return scenarios[:30]


VALID_SCENARIOS = _build_valid_scenarios()


def _invalid_programs() -> list[dict]:
    cases = []

    def add(case_id, mutate):
        program = deepcopy(BASE_PROGRAM)
        mutate(program)
        cases.append({"id": f"invalid-{case_id}", "kind": "invalid_program",
                      "program": program})

    add("third-bedroom", lambda p: p["ambientes"].append(
        {"nome": "Quarto 3", "area": 9.0}))
    add("suite-unsupported", lambda p: p["ambientes"].__setitem__(3,
        {"nome": "Suíte", "area": 12.0}))
    add("missing-bathroom", lambda p: (p.update(estrategia="compacto_2quartos"),
                                        p["ambientes"].pop(5)))
    add("duplicate-room", lambda p: p["ambientes"].__setitem__(4,
        {"nome": "Quarto 1", "area": 10.0}))
    add("nan-area", lambda p: p["ambientes"][0].update(area=float("nan")))
    add("infinite-area", lambda p: p["ambientes"][1].update(area=float("inf")))
    add("lot-too-narrow", lambda p: p.update(terreno_largura=9.1))
    add("unsupported-pool", lambda p: (p.update(estrategia="compacto_2quartos"),
                                        p["ambientes"].append(
                                            {"nome": "Piscina", "area": 10.0})))
    add("bedroom-impossible-area", lambda p: p["ambientes"][3].update(area=50.0))
    add("compact-width-too-small", lambda p: p.update(
        estrategia="compacto_2quartos", largura=8.5))
    add("too-few-rooms", lambda p: p.update(ambientes=[p["ambientes"][0]]))
    add("room-name-empty", lambda p: p["ambientes"][0].update(nome="  "))
    return cases


_DXF_MUTATIONS = (
    ("remove-door-arc", "door-count-mismatch"),
    ("break-door-leaf", "door-leaf-mismatch"),
    ("shift-window-line", "window-pair-mismatch"),
    ("remove-window-line", "window-pair-mismatch"),
    ("furniture-outside-lot", "furniture-outside-lot"),
    ("overlap-furniture", "furniture-overlap"),
    ("change-lot-bounds", "lot-bounds-mismatch"),
    ("wrong-dxf-units", "units-not-meters"),
    ("diagonal-wall", "wall-invalid-geometry"),
    ("break-room-area-label", "room-area-label-mismatch"),
)

ADVERSARIAL_SCENARIOS = _invalid_programs() + [
    {"id": f"mutation-{mutation}", "kind": "dxf_mutation",
     "mutation": mutation, "expected_code": expected_code}
    for mutation, expected_code in _DXF_MUTATIONS
]


MCP_SCENARIOS = [
    {"id": "mcp-natural-language-basic", "valid_scenario": {
        "program": deepcopy(BASE_PROGRAM),
        "briefing": "Residência térrea de dois quartos, sala, cozinha, lavanderia e banheiro em lote de 10 x 20 m.",
        "terrain_bounds": (-0.5, -3.0, 9.5, 17.0), "expected_doors": 5,
        "expected_window_pairs": 6,
        "expected_room_areas_m2": [room["area"] for room in BASE_PROGRAM["ambientes"]],
    }},
    {"id": "mcp-natural-language-larger-lot", "valid_scenario": {
        "program": {**deepcopy(BASE_PROGRAM), "terreno_largura": 11.0,
                    "terreno_profundidade": 22.0},
        "briefing": "Residência térrea de dois quartos, sala, cozinha, lavanderia e banheiro em lote de 11 x 22 m.",
        "terrain_bounds": (-0.5, -3.0, 10.5, 19.0), "expected_doors": 5,
        "expected_window_pairs": 6,
        "expected_room_areas_m2": [room["area"] for room in BASE_PROGRAM["ambientes"]],
    }},
]
