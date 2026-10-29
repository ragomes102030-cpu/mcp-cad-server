import json

from tools.plant_lab.licensing_corpus import build_scenarios, run_corpus


def test_deterministic_scenario_catalog_has_thirty_supported_and_distinct_cases():
    scenarios = build_scenarios()
    assert len(scenarios) == 30
    assert len({item["id"] for item in scenarios}) == 30
    assert {item["kind"] for item in scenarios} == {"supported_program"}


def test_sampled_end_to_end_corpus_checks_drawings_views_and_adversarial_edits(tmp_path):
    report = run_corpus(tmp_path, valid_limit=3)

    assert report["summary"]["valid_passed"] == 3, report["valid_scenarios"]
    assert report["summary"]["valid_failed"] == 0
    assert report["summary"]["adversarial_passed"] == 10, report["adversarial_scenarios"]
    assert report["summary"]["adversarial_failed"] == 0
    assert report["requirements"]["criteria_implemented"] == 0
    assert report["coverage"]["view_types"]
    assert report["coverage"]["warnings"]["normative-criteria-not-tested"] == 3
    assert report["coverage"]["warnings"]["municipality-profile-not-configured"] == 3
    assert "passagem-estreita-estimada" not in report["coverage"]["warnings"]
    assert "sala-cozinha-integracao-nao-comprovada" not in report["coverage"]["warnings"]
    assert (tmp_path / "contact-sheet.png").is_file()
    saved = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert saved["summary"] == report["summary"]
