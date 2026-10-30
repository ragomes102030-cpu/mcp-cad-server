"""Independent checks of entities read back from a serialized plant DXF."""
from copy import deepcopy

import ezdxf
import pytest

from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.backend import _ensure, reset_drawing, test_session as _test_session
from mcp_cad_cloud.planta_gerador import gerar_modelo
from test_layout_compacto import CASA


@pytest.fixture
def reopened_drawing(tmp_path):
    program = deepcopy(CASA)
    model = gerar_modelo(program)
    with _test_session("plant-lab-independent-geometry"):
        reset_drawing()
        preview = cad.planta_criar_validada(
            programa=program, modo="preview", template="programa_sob_medida")
        assert preview["ok"], preview
        created = cad.planta_criar_validada(
            programa=program, modo="desenhar", template="programa_sob_medida",
            preview_token=preview["preview_token"])
        assert created["ok"], created
        path = tmp_path / "reopened-plant.dxf"
        _ensure().saveas(path)
    doc = ezdxf.readfile(path)
    contract = {
        "terrain_bounds": (-0.5, -3.0, 9.5, 17.0),
        "expected_doors": 5,
        "expected_window_pairs": 6,
        "expected_room_areas_m2": [18.0, 9.0, 5.0, 12.0, 10.0, 5.0],
    }
    return doc, contract


def test_independent_evaluator_accepts_real_reopened_plant(reopened_drawing):
    from tools.plant_lab.independent_geometry import evaluate_reopened_dxf

    doc, contract = reopened_drawing
    assert evaluate_reopened_dxf(doc, contract) == []


def test_independent_evaluator_detects_removed_door_arc(reopened_drawing):
    from tools.plant_lab.independent_geometry import evaluate_reopened_dxf

    doc, contract = reopened_drawing
    doc.modelspace().delete_entity(next(iter(doc.modelspace().query(
        'ARC[layer=="PORTAS"]'))))

    issues = evaluate_reopened_dxf(doc, contract)

    assert "door-count-mismatch" in {issue["code"] for issue in issues}


def test_independent_evaluator_detects_window_pair_disagreement(reopened_drawing):
    from tools.plant_lab.independent_geometry import evaluate_reopened_dxf

    doc, contract = reopened_drawing
    window = next(iter(doc.modelspace().query('LINE[layer=="JANELAS"]')))
    window.dxf.start = (float(window.dxf.start.x) + 0.20,
                        float(window.dxf.start.y), 0.0)

    issues = evaluate_reopened_dxf(doc, contract)

    assert "window-pair-mismatch" in {issue["code"] for issue in issues}


def test_independent_evaluator_detects_furniture_outside_lot(reopened_drawing):
    from tools.plant_lab.independent_geometry import evaluate_reopened_dxf

    doc, contract = reopened_drawing
    furniture = next(iter(doc.modelspace().query(
        'LWPOLYLINE[layer=="MOBILIARIO"]')))
    furniture.transform(ezdxf.math.Matrix44.translate(20, 0, 0))

    issues = evaluate_reopened_dxf(doc, contract)

    assert "furniture-outside-lot" in {issue["code"] for issue in issues}


def test_independent_evaluator_detects_overlapping_furniture(reopened_drawing):
    from tools.plant_lab.independent_geometry import evaluate_reopened_dxf

    doc, contract = reopened_drawing
    furniture = list(doc.modelspace().query('LWPOLYLINE[layer=="MOBILIARIO"]'))
    furniture[1].set_points(furniture[0].get_points("xy"), format="xy")

    issues = evaluate_reopened_dxf(doc, contract)

    assert "furniture-overlap" in {issue["code"] for issue in issues}


def test_independent_evaluator_detects_room_area_annotation_mismatch(reopened_drawing):
    from tools.plant_lab.independent_geometry import evaluate_reopened_dxf

    doc, contract = reopened_drawing
    label = next(iter(doc.modelspace().query('TEXT[layer=="COTAS_INT"]')))
    label.dxf.text = "99.00 x 99.00 m"

    issues = evaluate_reopened_dxf(doc, contract)

    assert "room-area-label-mismatch" in {issue["code"] for issue in issues}
