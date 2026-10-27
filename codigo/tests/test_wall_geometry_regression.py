from copy import deepcopy

from cad_mcp.planta_assistida import build_assisted_model
from cad_mcp.validar_modelo import validar


def _walls_on(model, axis_value, horizontal=True):
    result = []
    for x1, y1, x2, y2 in model["paredes"]:
        if horizontal and abs(y1 - axis_value) < 1e-9 and abs(y2 - axis_value) < 1e-9:
            result.append((min(x1, x2), max(x1, x2)))
        if not horizontal and abs(x1 - axis_value) < 1e-9 and abs(x2 - axis_value) < 1e-9:
            result.append((min(y1, y2), max(y1, y2)))
    return result


def test_assisted_template_has_front_and_back_dimension_chains():
    model = build_assisted_model()

    front = {(x1, x2) for x1, x2, y, _ in model["cotas_h"] if y < 0}
    back = {(x1, x2) for x1, x2, y, _ in model["cotas_h"] if y > 11}

    assert front >= {(0, 5), (5, 8.6), (8.6, 12), (0, 12)}
    assert back >= {(0, 4.6), (4.6, 8.6), (8.6, 12), (0, 12)}


def test_assisted_template_cuts_external_window_openings_from_walls():
    model = build_assisted_model()

    front_walls = _walls_on(model, 0.0, horizontal=True)
    right_walls = _walls_on(model, 12.0, horizontal=False)

    for start, end in ((2.2, 4.2), (5.9, 7.3), (9.4, 10.6)):
        assert not any(a < end - 0.01 and b > start + 0.01 for a, b in front_walls)
    for start, end in ((3.2, 4.2), (7.5, 9.5)):
        assert not any(a < end - 0.01 and b > start + 0.01 for a, b in right_walls)


def test_validator_rejects_overlapping_wall_axes():
    model = build_assisted_model()
    broken = deepcopy(model)
    broken["paredes"].append(tuple(broken["paredes"][0]))

    result = validar(broken)

    assert any(p["chave"] == "parede-duplicada" for p in result["erros"])


def test_validator_rejects_door_leaf_crossing_another_wall():
    model = build_assisted_model()
    broken = deepcopy(model)
    # A folha da porta da sala desce a partir de (2,20; 5,00). Esta parede
    # artificial cruza a folha e deve ser apontada antes do AutoCAD.
    broken["paredes"].append((2.2, 4.0, 2.2, 4.9))

    result = validar(broken)

    assert any(p["chave"] == "porta-colide-parede" for p in result["erros"])

