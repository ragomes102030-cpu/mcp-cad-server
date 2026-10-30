"""Cross-view physical dimension invariants for the 2-bedroom pilot."""
from math import tan, radians

from test_prancha_licenciamento import package as package_fixture


def test_roof_ridge_agrees_across_gable_facade_and_both_sections():
    package = package_fixture.__wrapped__()
    views = {view.view_id: view for view in package.views}
    facade = views["ARQ-FACHADA-LATERAL-ESQ"]
    perpendicular = views["ARQ-CORTE-A"]
    along_ridge = views["ARQ-CORTE-B"]

    facade_peaks = [
        max(segment.y1, segment.y2)
        for segment in facade.segments if segment.layer == "COBERTURA"
    ]
    perp_peaks = [
        max(segment.y1, segment.y2)
        for segment in perpendicular.segments
        if segment.layer == "CORTE-COBERTURA"
    ]
    ridge_run = [
        segment for segment in along_ridge.segments
        if segment.source_id == "section:x:ridge-run"
    ]
    assert len(facade_peaks) == 2
    assert perp_peaks
    assert len(ridge_run) == 1

    # One actual roof peak must be geometrically identical in every view.
    assert abs(max(facade_peaks) - max(perp_peaks)) <= 0.001
    assert abs(max(facade_peaks) - ridge_run[0].y1) <= 0.001


def test_roof_plan_and_implantation_footprints_derive_from_one_envelope():
    package = package_fixture.__wrapped__()
    model = package.source_plan
    width = model["resumo_geometria"]["largura"]
    depth = model["resumo_geometria"]["profundidade"]
    overhang = package.envelope.roof_overhang_m
    views = {view.view_id: view for view in package.views}
    def bounds(segments):
        xs = [v for s in segments for v in (s.x1, s.x2)]
        ys = [v for s in segments for v in (s.y1, s.y2)]
        return min(xs), min(ys), max(xs), max(ys)

    site = [s for s in views["ARQ-IMPLANTACAO"].segments
            if s.source_id == "site:building-footprint"]
    roof = [s for s in views["ARQ-COBERTURA"].segments
            if s.source_id == "roof:eaves-outline"]
    assert bounds(site) == (0.0, 0.0, width, depth)
    assert bounds(roof) == (-overhang, -overhang,
                            width + overhang, depth + overhang)
