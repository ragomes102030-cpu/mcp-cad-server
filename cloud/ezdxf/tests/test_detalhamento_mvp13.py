"""Regression: opening dimensions and independent annotation overlap diagnostics."""
from dataclasses import replace

from mcp_cad_cloud.auditoria_legibilidade import auditar_legibilidade_vista
from mcp_cad_cloud.projeto_arquitetonico import Segment, ViewGeometry, ViewLabel
from test_prancha_licenciamento import package as package_fixture


def test_opening_schedule_exposes_vertical_dimensions_from_same_envelope():
    package = package_fixture.__wrapped__()
    floor = next(view for view in package.views if view.view_id == "ARQ-PLANTA")
    labels = {item.source_id: item.text for item in floor.labels}
    for index, door in enumerate(package.source_plan["portas"]):
        text = labels[f"schedule:door:{index}"]
        assert f"L={door[3]:.2f}" in text, text
        assert "H=2.10" in text, text
    for index, window in enumerate(package.source_plan["janelas"]):
        text = labels[f"schedule:window:{index}"]
        assert "H=1.30" in text, text
        assert "P=0.90" in text, text


def test_vertical_window_reports_real_span_not_zero():
    from copy import deepcopy
    from mcp_cad_cloud.projeto_arquitetonico import _floor_plan
    package = package_fixture.__wrapped__()
    model = deepcopy(package.source_plan)
    model["janelas"][0] = (0.0, 2.0, 0.0, 3.2)
    floor = _floor_plan(model, package.envelope)
    label = next(x.text for x in floor.labels
                 if x.source_id == "schedule:window:0")
    assert "L=1.20" in label, label


def test_legibility_detects_text_on_top_of_furniture():
    view = ViewGeometry(
        view_id="ARQ-PLANTA", kind="planta_baixa", unit="m",
        bounds=(0.0, 0.0, 3.0, 3.0),
        segments=tuple([
            Segment(0.5, 0.5, 1.5, 0.5, "MOBILIARIO", "furniture:0"),
            Segment(1.5, 0.5, 1.5, 1.5, "MOBILIARIO", "furniture:0"),
            Segment(1.5, 1.5, 0.5, 1.5, "MOBILIARIO", "furniture:0"),
            Segment(0.5, 1.5, 0.5, 0.5, "MOBILIARIO", "furniture:0"),
        ]),
        labels=(ViewLabel("Quarto 1", 1.0, 1.0, "room:1"),),
        source_ids=("furniture:0",),
    )
    result = auditar_legibilidade_vista(view, 50)
    assert result["status"] == "review_required"
    assert any(x["code"] == "label-furniture-overlap" for x in result["warnings"])
    assert result["warnings"][0]["source_id"] == "room:1"


def test_default_package_legibility_reports_provenance_and_no_normative_approval():
    package = package_fixture.__wrapped__()
    floor = next(view for view in package.views if view.view_id == "ARQ-PLANTA")
    result = auditar_legibilidade_vista(floor, 50)
    assert result["checked_labels"] > 12
    assert result["normative_approval"] is False
    assert result["method"] == "estimated-text-bounds"


def test_compact_plan_window_ids_do_not_overlap_furniture():
    # Regression from the 10 x 20 pilot: J02 used to sit over the kitchen worktop.
    package = package_fixture.__wrapped__()
    floor = next(view for view in package.views if view.view_id == "ARQ-PLANTA")
    audit = auditar_legibilidade_vista(floor, 50)
    warnings = [item for item in audit["warnings"]
                if item["code"] == "label-furniture-overlap"]
    assert not warnings, warnings
    # Put external facade identifiers outside rooms, where they do not
    # compete with equipment, beds or internal room labels.
    for label in floor.labels:
        if label.source_id.startswith("opening-tag:window:"):
            assert label.y < 0 or label.y > package.source_plan["resumo_geometria"]["profundidade"]
