from datetime import date
import importlib
import importlib.util
import json

import pytest


def api():
    module = "mcp_cad_cloud.normas_arquitetura"
    assert importlib.util.find_spec(module) is not None, f"missing module: {module}"
    return importlib.import_module(module)


def test_catalogue_registry_is_explicit_non_exhaustive_and_fail_closed():
    registry_api = api()
    registry = registry_api.load_registry()
    assert registry["schema_version"] == 1
    assert registry["scope"] == "candidate_standards_not_exhaustive"
    entries = {entry["id"]: entry for entry in registry["standards"]}
    known = entries["nbr-9050-2020-corr-2021"]
    assert known["catalog_status"] == "Em Vigor"
    assert known["catalog_checked_at"] == "2026-10-29"
    assert known["evaluator_id"] is None
    assert known["criteria_reviewed"] is False
    assert entries["nbr-6492-2021"]["catalog_status"] == "Não confirmado"
    assert all(item["evaluator_id"] is None for item in entries.values())


def test_loaded_candidates_never_pass_without_lawfully_reviewed_criteria():
    from mcp_cad_cloud.arquitetura_requisitos import (
        ProjectContext, RequirementStatus, evaluate_applicability,
    )

    registry_api = api()
    records = registry_api.load_requirement_records()
    context = ProjectContext("Casa", "residencial", "compacto_2quartos", None,
                             None, 1, 10, 20, (), "licenciamento")
    results = [evaluate_applicability(
        context, item, applicability_rules={}, evaluators={}) for item in records]
    assert results
    assert all(item.status is RequirementStatus.NOT_TESTABLE for item in results)


@pytest.mark.parametrize("mutation", [
    lambda payload: payload["standards"].append(payload["standards"][0]),
    lambda payload: payload["standards"][0].update(source_url="http://insecure.test/norm"),
    lambda payload: payload["standards"][0].update(catalog_checked_at="2099-01-01"),
    lambda payload: payload["standards"][0].update(catalog_checked_at="2020-01-01"),
    lambda payload: payload["standards"][0].update(criteria_reviewed=True),
])
def test_invalid_or_unreviewed_registry_metadata_is_rejected(tmp_path, mutation):
    registry_api = api()
    payload = registry_api.load_registry()
    mutation(payload)
    target = tmp_path / "registry.json"
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        registry_api.validate_registry(payload, as_of=date.today())
