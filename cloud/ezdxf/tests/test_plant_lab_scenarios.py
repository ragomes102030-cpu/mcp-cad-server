"""The plant lab's deterministic matrix matches declared generator support."""
from copy import deepcopy

import ezdxf
import pytest

from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.backend import _ensure, reset_drawing, test_session as _test_session
from mcp_cad_cloud.planta_gerador import ErroPrograma, gerar_modelo
from test_layout_compacto import CASA


def test_corpus_has_thirty_supported_programs_and_twenty_adversarial_cases():
    from tools.plant_lab.scenarios import VALID_SCENARIOS, ADVERSARIAL_SCENARIOS

    assert len(VALID_SCENARIOS) >= 30
    assert any(item["id"] == "valid-width-9.2" for item in VALID_SCENARIOS)
    assert len(ADVERSARIAL_SCENARIOS) >= 20
    ids = [item["id"] for item in (*VALID_SCENARIOS, *ADVERSARIAL_SCENARIOS)]
    assert len(ids) == len(set(ids))


def test_every_valid_scenario_generates_and_preserves_brief_areas():
    from tools.plant_lab.scenarios import VALID_SCENARIOS

    for scenario in VALID_SCENARIOS:
        model = gerar_modelo(scenario["program"])
        assert model["resumo_geometria"]["tipo"] == "compacto_2quartos", scenario["id"]
        assert scenario["expected_room_areas_m2"] == [
            room["area"] for room in scenario["program"]["ambientes"]
        ], scenario["id"]


def test_invalid_program_scenarios_are_rejected_by_generator():
    from tools.plant_lab.scenarios import ADVERSARIAL_SCENARIOS

    invalid_programs = [item for item in ADVERSARIAL_SCENARIOS
                        if item["kind"] == "invalid_program"]
    assert len(invalid_programs) >= 10
    for scenario in invalid_programs:
        try:
            gerar_modelo(scenario["program"])
        except ErroPrograma:
            continue
        raise AssertionError(f"{scenario['id']} was unexpectedly accepted")


def test_dxf_mutation_scenarios_name_expected_independent_failure():
    from tools.plant_lab.scenarios import ADVERSARIAL_SCENARIOS

    mutations = [item for item in ADVERSARIAL_SCENARIOS
                 if item["kind"] == "dxf_mutation"]
    assert len(mutations) >= 10
    assert all(item.get("mutation") and item.get("expected_code") for item in mutations)
    assert len({item["mutation"] for item in mutations}) == len(mutations)


@pytest.fixture
def reopened_reference_drawing(tmp_path):
    program = deepcopy(CASA)
    model = gerar_modelo(program)
    with _test_session("plant-lab-route-sensitivity"):
        reset_drawing()
        preview = cad.planta_criar_validada(
            programa=program, modo="preview", template="programa_sob_medida")
        assert preview["ok"], preview
        created = cad.planta_criar_validada(
            programa=program, modo="desenhar", template="programa_sob_medida",
            preview_token=preview["preview_token"])
        assert created["ok"], created
        path = tmp_path / "route-sensitivity.dxf"
        _ensure().saveas(path)
    return ezdxf.readfile(path), model


def test_route_width_sensitivity_reports_all_grid_sizes_as_approximate(reopened_reference_drawing):
    from tools.plant_lab.sensitivity import measure_route_widths

    doc, _model = reopened_reference_drawing
    report = measure_route_widths(doc, steps=(0.05, 0.10, 0.15))

    assert report["method"] == "independent_dxf_grid_approximation"
    assert [item["grid_m"] for item in report["measurements"]] == [0.05, 0.10, 0.15]
    assert all(item["approximate"] is True for item in report["measurements"])
    assert all(item["status"] == "estimated" and item["width_m"] >= 0
               for item in report["measurements"])
    assert len({item["width_m"] for item in report["measurements"]}) > 1
