from datetime import date
import importlib
import importlib.util

import pytest


@pytest.fixture
def api():
    module = "mcp_cad_cloud.arquitetura_requisitos"
    assert importlib.util.find_spec(module) is not None, f"missing production module: {module}"
    return importlib.import_module(module)


def context(api, **changes):
    values = {
        "project_name": "Casa compacta",
        "use": "residencial_unifamiliar",
        "typology": "compacto_2quartos",
        "municipality": "Fortaleza",
        "state": "CE",
        "storeys": 1,
        "lot_width_m": 10.0,
        "lot_depth_m": 25.0,
        "requested_rooms": ("sala", "cozinha", "quarto", "quarto", "banheiro"),
        "stage": "licenciamento",
        "municipal_profile_revision": "2026-01",
    }
    values.update(changes)
    return api.ProjectContext(**values)


def requirement(api, **changes):
    values = {
        "requirement_id": "doc.plan.dimensioning",
        "standard": "ABNT NBR 6492",
        "edition": "2021",
        "catalog_status": "Em Vigor",
        "source_url": "https://www.abntcatalogo.com.br/",
        "catalog_checked_at": date(2026, 10, 1),
        "applicability_rule_id": "always",
        "evaluator_id": "dimensioning_v1",
        "review_interval_days": 365,
    }
    values.update(changes)
    return api.RequirementRecord(**values)


def evaluator(_project):
    return True, "Dimensões documentadas", ("sheet:ARQ-01/entity:42",)


def test_current_applicable_requirement_returns_pass_and_evidence(api):
    result = api.evaluate_applicability(
        context(api), requirement(api),
        applicability_rules={"always": lambda _project: True},
        evaluators={"dimensioning_v1": evaluator},
        as_of=date(2026, 10, 29),
    )

    assert result.status is api.RequirementStatus.PASSED
    assert result.requirement_id == "doc.plan.dimensioning"
    assert result.evidence == ("sheet:ARQ-01/entity:42",)


def test_missing_municipality_makes_local_requirement_not_testable(api):
    result = api.evaluate_applicability(
        context(api, municipality=None, state=None, municipal_profile_revision=None),
        requirement(api, applicability_rule_id="municipal_profile"),
        applicability_rules={"municipal_profile": lambda project: (
            None if not project.municipality or not project.state
            or not project.municipal_profile_revision else True
        )},
        evaluators={"dimensioning_v1": evaluator},
        as_of=date(2026, 10, 29),
    )

    assert result.status is api.RequirementStatus.NOT_TESTABLE
    assert "municip" in result.reason.lower()


def test_requirement_outside_its_applicability_is_not_applicable(api):
    result = api.evaluate_applicability(
        context(api), requirement(api, applicability_rule_id="multistory_only"),
        applicability_rules={"multistory_only": lambda project: project.storeys > 1},
        evaluators={"dimensioning_v1": evaluator},
        as_of=date(2026, 10, 29),
    )

    assert result.status is api.RequirementStatus.NOT_APPLICABLE


def test_failed_registered_evaluator_returns_failed_with_reason(api):
    result = api.evaluate_applicability(
        context(api), requirement(api),
        applicability_rules={"always": lambda _project: True},
        evaluators={"dimensioning_v1": lambda _project: (
            False, "Cota ausente", ("sheet:ARQ-01",)
        )},
        as_of=date(2026, 10, 29),
    )

    assert result.status is api.RequirementStatus.FAILED
    assert result.reason == "Cota ausente"
    assert result.evidence == ("sheet:ARQ-01",)


def test_missing_normative_source_or_edition_stays_not_testable(api):
    for incomplete in (
        requirement(api, source_url="", catalog_status="Em Vigor"),
        requirement(api, edition="", catalog_status="Em Vigor"),
        requirement(api, catalog_status="Cancelada"),
    ):
        result = api.evaluate_applicability(
            context(api), incomplete,
            applicability_rules={"always": lambda _project: True},
            evaluators={"dimensioning_v1": evaluator},
            as_of=date(2026, 10, 29),
        )
        assert result.status is api.RequirementStatus.NOT_TESTABLE


def test_stale_catalog_review_stays_not_testable(api):
    result = api.evaluate_applicability(
        context(api), requirement(api, catalog_checked_at=date(2024, 1, 1)),
        applicability_rules={"always": lambda _project: True},
        evaluators={"dimensioning_v1": evaluator},
        as_of=date(2026, 10, 29),
    )

    assert result.status is api.RequirementStatus.NOT_TESTABLE
    assert "atualiza" in result.reason.lower() or "revis" in result.reason.lower()


def test_unregistered_applicability_or_evaluator_stays_not_testable(api):
    result = api.evaluate_applicability(
        context(api), requirement(api, applicability_rule_id="unknown", evaluator_id="unknown"),
        applicability_rules={}, evaluators={}, as_of=date(2026, 10, 29),
    )

    assert result.status is api.RequirementStatus.NOT_TESTABLE


def test_unreviewed_or_mismatched_municipal_profile_is_rejected(api):
    profile = api.MunicipalProfile(
        schema_version=1,
        municipality="Fortaleza",
        state="CE",
        source_url="https://www.fortaleza.ce.gov.br/",
        retrieved_at=date(2026, 10, 1),
        revision="2026-01",
        reviewer="",
    )

    assert api.validate_municipal_profile(profile, context(api))
    assert api.validate_municipal_profile(
        api.MunicipalProfile(
            schema_version=1,
            municipality="Recife",
            state="PE",
            source_url="https://www.recife.pe.gov.br/",
            retrieved_at=date(2026, 10, 1),
            revision="2026-01",
            reviewer="Arquiteto revisor",
        ),
        context(api),
    )


def test_reviewed_municipal_profile_matches_project(api):
    profile = api.MunicipalProfile(
        schema_version=1,
        municipality="Fortaleza",
        state="CE",
        source_url="https://www.fortaleza.ce.gov.br/",
        retrieved_at=date(2026, 10, 1),
        revision="2026-01",
        reviewer="Arquiteto revisor",
    )

    assert api.validate_municipal_profile(profile, context(api)) == ()
