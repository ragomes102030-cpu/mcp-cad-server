from pathlib import Path

import pytest

from tools.plant_lab import runner
from tools.plant_lab.scenarios import VALID_SCENARIOS, ADVERSARIAL_SCENARIOS
from tools.plant_lab.scenarios import MCP_SCENARIOS
from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.backend import reset_drawing, test_session as local_test_session
from test_layout_compacto import CASA
from tools import run_plant_lab


def test_runner_writes_auditable_report_and_reopened_dxf(tmp_path):
    scenario = dict(VALID_SCENARIOS[0], render=False)
    result = runner.run_lab(
        tmp_path,
        valid_scenarios=[scenario],
        adversarial_scenarios=[ADVERSARIAL_SCENARIOS[4]],
        mcp_scenarios=[],
    )

    assert result["summary"]["valid_passed"] == 1, result["valid_cases"]
    assert result["summary"]["adversarial_passed"] == 1, result["adversarial_cases"]
    assert result["summary"]["circulation_errors"] == 0
    assert sum(result["summary"]["circulation_warning_codes"].values()) == result["summary"]["circulation_warnings"]
    assert result["summary"]["disconnected_rooms"] == 0
    assert set(result["route_sensitivity_summary"]) == {"0.05", "0.10", "0.15"}
    assert (tmp_path / "report.json").is_file()
    assert (tmp_path / "report.md").is_file()
    case = result["valid_cases"][0]
    assert case["independent_errors"] == []
    assert case["sha256"]
    assert case["entity_sha256"]
    assert Path(case["dxf_path"]).is_file()


def test_runner_returns_failure_for_a_mutation_contract_regression(tmp_path):
    scenario = dict(VALID_SCENARIOS[0], render=False)
    mutation = next(item for item in ADVERSARIAL_SCENARIOS
                    if item.get("kind") == "dxf_mutation"
                    and item["mutation"] == "remove-door-arc")
    mutation = dict(mutation, expected_code="hallucinated-code")
    result = runner.run_lab(
        tmp_path,
        valid_scenarios=[scenario],
        adversarial_scenarios=[mutation],
        mcp_scenarios=[],
    )

    assert result["summary"]["adversarial_failed"] == 1
    assert not result["ok"]


def test_reference_compact_program_passes_real_preview_without_orphan_furniture():
    with local_test_session("plant-lab-baseline-preview"):
        reset_drawing()
        preview = cad.planta_criar_validada(
            programa=CASA, modo="preview", template="programa_sob_medida")

    assert preview["ok"], preview
    assert preview["validacao"]["ok"], preview["validacao"]


def test_width_9_2_compact_plan_has_no_laundry_door_furniture_collision(tmp_path):
    scenario = next(item for item in VALID_SCENARIOS if item["id"] == "valid-width-9.2")
    scenario = dict(scenario, render=False)
    case = runner._build_case(scenario, tmp_path)

    assert case["status"] == "passed", case.get("production_circulation")


def test_same_scenario_has_stable_entity_hash_and_verifiable_file_hash(tmp_path):
    scenario = dict(VALID_SCENARIOS[0], render=False)
    first = runner._build_case(scenario, tmp_path / "first")
    second = runner._build_case(scenario, tmp_path / "second")

    assert first["status"] == second["status"] == "passed"
    assert first["sha256"] != second["sha256"]
    assert first["entity_sha256"] == second["entity_sha256"]


def test_cli_returns_nonzero_when_lab_report_contains_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(run_plant_lab, "run_lab", lambda _output: {
        "ok": False,
        "output_dir": str(tmp_path),
        "summary": {"valid_passed": 1, "valid_total": 2,
                    "adversarial_passed": 1, "adversarial_total": 1,
                    "mcp_passed": 0, "mcp_total": 0},
    })

    assert run_plant_lab.main(["--output", str(tmp_path)]) == 1


def test_runner_natural_language_scenario_uses_default_program_flow(tmp_path):
    cases = runner._mcp_cases([MCP_SCENARIOS[0]], tmp_path)

    assert cases[0]["status"] == "passed", cases[0]
    assert cases[0]["production_geometry_ok"]
    assert cases[0]["production_circulation_ok"]
    assert all("url" not in key.casefold() for key in cases[0]["files"])


def test_circulation_comparison_fails_if_tool_claims_original_was_changed(tmp_path, monkeypatch):
    from io import BytesIO
    from PIL import Image
    from mcp_cad_cloud import downloads

    buffer = BytesIO()
    Image.new("RGB", (64, 64), "white").save(buffer, format="PNG")
    png = buffer.getvalue()
    token_url = "https://local.invalid/downloads/" + "A" * 43 + "/png"
    proposal = {"status": "for_review", "files": "omitted"}
    monkeypatch.setattr(downloads, "retrieve", lambda _token, _fmt: (png, "image/png", "plant.png"))
    monkeypatch.setattr(runner.cad, "propor_melhoria_circulacao", lambda _request: {
        "ok": True, "modo": "comparacao_sem_aplicacao",
        "alteracoes_aplicadas_ao_original": True, "candidatas_avaliadas": 1,
        "alternativa_disponivel": True,
        "original": {"arquivos": {"png_url": token_url}},
        "proposta": {**proposal, "arquivos": {"png_url": token_url}},
    })

    result = runner._circulation_comparison(tmp_path)

    assert result["status"] == "failed"
    assert result["original_unchanged"] is False
