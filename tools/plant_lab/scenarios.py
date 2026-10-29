"""Deterministic supported programs and adversarial plant/DXF cases."""
from __future__ import annotations

from copy import deepcopy
from itertools import product

from mcp_cad_cloud.planta_gerador import ErroPrograma, gerar_modelo
from test_layout_compacto import CASA


def _build_valid_scenarios() -> list[dict]:
    candidates = product(
        (16.0, 17.0, 18.0, 19.0, 20.0),
        (8.0, 9.0, 10.0),
        (4.0, 5.0, 6.0),
        (11.0, 12.0, 13.0),
        (9.0, 10.0, 11.0),
        (4.0, 4.5, 5.0, 5.5, 6.0),
    )
    candidates = tuple(candidates)
    widths = (8.7, 8.8, 8.9, 9.0, 9.1)
    setbacks = ((0.4, 2.0, 1.0), (0.5, 3.0, 2.0), (0.7, 4.0, 3.0))
    scenarios = []
    for width in widths:
        accepted_for_width = 0
        for areas in candidates:
            program = deepcopy(CASA)
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
                gerar_modelo(program)
            except ErroPrograma:
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
    if len(scenarios) < 30:
        raise RuntimeError(f"Scenario corpus found only {len(scenarios)} supported programs")
    return scenarios[:30]


VALID_SCENARIOS = _build_valid_scenarios()


def _invalid_programs() -> list[dict]:
    cases = []

    def add(case_id, mutate):
        program = deepcopy(CASA)
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
    {"id": "mcp-natural-language-basic", "valid_scenario": VALID_SCENARIOS[0]},
    {"id": "mcp-natural-language-compact-variation", "valid_scenario": VALID_SCENARIOS[13]},
]
