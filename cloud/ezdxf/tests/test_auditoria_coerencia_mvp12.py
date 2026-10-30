"""Semantic cross-sheet audits: reject inconsistent plan-derived views."""
from dataclasses import replace

from mcp_cad_cloud.auditoria_coerencia import audit_architecture_coherence
from test_prancha_licenciamento import package as package_fixture
from test_projeto_arquitetonico import (
    api as architecture_api_fixture,
    generate as generate_architecture_fixture,
)


def _mutate(package, view_id, predicate, **changes):
    rebuilt = []
    for view in package.views:
        if view.view_id != view_id:
            rebuilt.append(view)
            continue
        segments = list(view.segments)
        for index, segment in enumerate(segments):
            if predicate(segment):
                segments[index] = replace(segment, **changes)
                break
        else:
            raise AssertionError(f"No source matched in view {view_id}")
        rebuilt.append(replace(view, segments=tuple(segments)))
    return replace(package, views=tuple(rebuilt))


def _codes(result):
    return {item["code"] for item in result["errors"]}


def test_generated_cross_view_geometry_is_coherent_and_not_normative_approval():
    package = package_fixture.__wrapped__()
    audit = audit_architecture_coherence(package)
    assert audit["ok"], audit
    assert audit["status"] == "review_required"
    assert audit["normative_approval"] is False
    assert audit["checked"]["views"] == 9
    assert audit["checked"]["projected_facade_openings"] > 0


def test_moving_site_building_footprint_blocks_package():
    package = package_fixture.__wrapped__()
    bad = _mutate(
        package, "ARQ-IMPLANTACAO",
        lambda part: part.source_id == "site:building-footprint",
        x1=0.40,
    )
    assert "footprint-mismatch" in _codes(audit_architecture_coherence(bad))


def test_moving_roof_eave_blocks_package():
    package = package_fixture.__wrapped__()
    bad = _mutate(
        package, "ARQ-COBERTURA",
        lambda part: part.source_id == "roof:eaves-outline",
        x1=-0.15,
    )
    assert "footprint-mismatch" in _codes(audit_architecture_coherence(bad))


def test_moving_window_in_facade_blocks_package():
    package = package_fixture.__wrapped__()
    bad = _mutate(
        package, "ARQ-FACHADA-FRONTAL",
        lambda part: part.source_id.startswith("window:frontal:"),
        x1=1.50,
    )
    assert "facade-window-mismatch" in _codes(audit_architecture_coherence(bad))


def test_changed_roof_peak_in_section_blocks_package():
    package = package_fixture.__wrapped__()
    bad = _mutate(
        package, "ARQ-CORTE-B",
        lambda part: part.source_id == "section:x:ridge-run",
        y1=8.00,
    )
    assert "roof-ridge-mismatch" in _codes(audit_architecture_coherence(bad))


def test_ridge_axis_y_is_also_cross_view_consistent():
    api = architecture_api_fixture.__wrapped__()
    package = generate_architecture_fixture(api, ridge_axis="y")
    audit = audit_architecture_coherence(package)
    assert audit["ok"], audit
    assert audit["checked"]["roof_profiles"] == 4
