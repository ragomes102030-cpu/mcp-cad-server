from copy import deepcopy
from datetime import date
import importlib
import importlib.util
import json
import zipfile
import io
from urllib.parse import urlparse

import pytest

from mcp_cad_cloud.arquitetura_requisitos import ProjectContext, RequirementRecord
from test_layout_compacto import CASA
from test_prancha_licenciamento import (
    api as sheet_api_fixture,
    package as package_fixture,
    spec,
    title_block,
)


def load_api():
    module = "mcp_cad_cloud.projeto_automatico"
    assert importlib.util.find_spec(module) is not None
    api = importlib.import_module(module)
    assert hasattr(api, "evaluate_package"), "missing production interface: evaluate_package"
    assert hasattr(api, "export_licensing_package"), "missing production interface: export_licensing_package"
    return api


def requirement(**changes):
    values = {
        "requirement_id": "arq-documentacao-demo",
        "standard": "ABNT NBR 6492",
        "edition": "2021",
        "catalog_status": "Em Vigor",
        "source_url": "https://www.abntcatalogo.com.br/",
        "catalog_checked_at": date.today(),
        "applicability_rule_id": "always",
        "evaluator_id": "dimension-check",
        "review_interval_days": 365,
    }
    values.update(changes)
    return RequirementRecord(**values)


def passing_evaluator(_project):
    return True, "Cotas externas conferidas", ("sheet:ARQ-01/entity:19",)


def test_no_verified_requirement_registry_stays_under_professional_review():
    api = load_api()
    package = package_fixture.__wrapped__()

    evaluation = api.evaluate_package(package, [], {}, {})

    assert evaluation["licensing_readiness"] == "review_required"
    assert evaluation["results"] == ()
    assert "requisito" in evaluation["reason"].lower()


def test_failed_applicable_requirement_blocks_package():
    api = load_api()
    package = package_fixture.__wrapped__()
    failed = lambda _project: (False, "A cota está ausente", ("sheet:ARQ-01",))

    evaluation = api.evaluate_package(
        package, [requirement()], {"always": lambda _project: True},
        {"dimension-check": failed},
    )

    assert evaluation["licensing_readiness"] == "blocked"
    assert evaluation["results"][0].status.value == "falhou"


def test_stale_unknown_or_unverified_requirement_never_counts_as_pass():
    api = load_api()
    package = package_fixture.__wrapped__()
    stale = requirement(catalog_checked_at=date(2020, 1, 1))
    unknown = requirement(requirement_id="municipal-code", applicability_rule_id="city")

    evaluation = api.evaluate_package(
        package, [stale, unknown], {"always": lambda _project: True},
        {"dimension-check": passing_evaluator},
    )

    assert evaluation["licensing_readiness"] == "review_required"
    assert all(item.status.value == "não testável" for item in evaluation["results"])


def test_current_applicable_requirements_ready_only_for_professional_review():
    api = load_api()
    package = package_fixture.__wrapped__()

    evaluation = api.evaluate_package(
        package, [requirement()], {"always": lambda _project: True},
        {"dimension-check": passing_evaluator},
    )

    assert evaluation["licensing_readiness"] == "ready_for_professional_review"
    assert "aprova" not in evaluation["licensing_readiness"]
    assert evaluation["results"][0].status.value == "passou"


def test_export_reopens_all_sheets_and_bundles_auditable_files():
    api = load_api()
    sheet_api = sheet_api_fixture.__wrapped__()
    context = {
        "project_name": "Casa compacta",
        "use": "residencial_unifamiliar",
        "typology": "compacto_2quartos",
        "municipality": None,
        "state": None,
        "storeys": 1,
        "lot_width_m": 10.0,
        "lot_depth_m": 20.0,
        "requested_rooms": ["Sala de estar", "Cozinha", "Área de serviço",
                            "Quarto 1", "Quarto 2", "Banheiro social"],
        "stage": "licenciamento",
    }
    envelope = {
        "floor_level_m": 0.0,
        "wall_height_m": 2.8,
        "door_head_m": 2.1,
        "window_sill_m": 0.9,
        "window_head_m": 2.2,
        "roof_type": "gable",
        "roof_pitch_degrees": 25.0,
        "roof_overhang_m": 0.45,
        "ridge_axis": "x",
    }
    sheets = [
        {
            "paper_format": "A3", "orientation": "landscape", "scale": 50,
            "margin_mm": 10, "sheet_id": "ARQ-01",
            "viewports": [{"view_id": "ARQ-PLANTA", "x_mm": 20, "y_mm": 70,
                           "width_mm": 380, "height_mm": 200}],
        },
        {
            "paper_format": "A3", "orientation": "landscape", "scale": 100,
            "margin_mm": 10, "sheet_id": "ARQ-02",
            "viewports": [{"view_id": "ARQ-COBERTURA", "x_mm": 20, "y_mm": 70,
                           "width_mm": 220, "height_mm": 200}],
        },
    ]
    block = {
        "project_name": "Casa compacta", "municipality": None, "state": None,
        "owner": "", "designer": "", "professional_registration": "",
        "issue_date": "2026-10-29", "revision": "R00",
    }

    result = api.export_licensing_package(
        deepcopy(CASA), context, envelope, sheets, block,
        requirements=[], applicability_rules={}, evaluators={},
    )

    assert result["ok"] is True, result
    assert result["licensing_readiness"] == "review_required"
    assert len(result["auditorias_folhas"]) == 2
    assert all(item["ok"] for item in result["auditorias_folhas"])
    token = urlparse(result["arquivos"]["dxf_url"]).path.split("/")[-2]
    downloaded = importlib.import_module("mcp_cad_cloud.downloads").retrieve(token, "zip")
    assert downloaded is not None
    archive = zipfile.ZipFile(io.BytesIO(downloaded[0]))
    names = set(archive.namelist())
    assert {"ARQ-01.dxf", "ARQ-02.dxf", "ARQ-01.pdf", "ARQ-02.pdf",
            "ARQ-01.png", "ARQ-02.png", "report.json", "report.md"} <= names
    report_text = archive.read("report.json").decode("utf-8")
    report = json.loads(report_text)
    assert report["licensing_readiness"] == "review_required"
    assert "https://" not in report_text

