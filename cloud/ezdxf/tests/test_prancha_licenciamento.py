from copy import deepcopy
from dataclasses import replace
import importlib
import importlib.util

import ezdxf
import pytest

from mcp_cad_cloud.arquitetura_requisitos import ProjectContext
from mcp_cad_cloud.planta_gerador import gerar_modelo
from test_layout_compacto import CASA


@pytest.fixture
def api():
    module = "mcp_cad_cloud.prancha_dxf"
    assert importlib.util.find_spec(module) is not None, f"missing production module interface: {module}"
    return importlib.import_module(module)


@pytest.fixture
def package():
    from mcp_cad_cloud.projeto_arquitetonico import (
        BuildingEnvelope,
        generate_architecture_package,
    )

    context = ProjectContext(
        project_name="Casa compacta",
        use="residencial_unifamiliar",
        typology="compacto_2quartos",
        municipality=None,
        state=None,
        storeys=1,
        lot_width_m=10.0,
        lot_depth_m=20.0,
        requested_rooms=("Sala de estar", "Cozinha", "Área de serviço",
                         "Quarto 1", "Quarto 2", "Banheiro social"),
        stage="licenciamento",
    )
    envelope = BuildingEnvelope(
        floor_level_m=0.0,
        wall_height_m=2.8,
        door_head_m=2.1,
        window_sill_m=0.9,
        window_head_m=2.2,
        roof_type="gable",
        roof_pitch_degrees=25.0,
        roof_overhang_m=0.45,
        ridge_axis="x",
    )
    return generate_architecture_package(gerar_modelo(deepcopy(CASA)), context, envelope)


def require_sheet_api(api):
    for symbol in ("SheetCompositionError", "ViewportSpec", "SheetSpec",
                   "TitleBlockData", "compose_licensing_sheets", "renderizar_folha"):
        assert hasattr(api, symbol), f"missing production interface: {symbol}"


def title_block(api, **changes):
    values = {
        "project_name": "Casa compacta",
        "municipality": None,
        "state": None,
        "owner": "Contratante de teste",
        "designer": None,
        "professional_registration": None,
        "issue_date": "2026-10-29",
        "revision": "R00",
    }
    values.update(changes)
    return api.TitleBlockData(**values)


def spec(api, sheet_id="ARQ-01", **changes):
    values = {
        "paper_format": "A3",
        "orientation": "landscape",
        "scale": 50,
        "margin_mm": 10.0,
        "sheet_id": sheet_id,
        "viewports": (api.ViewportSpec(
            view_id="ARQ-PLANTA", x_mm=20, y_mm=70, width_mm=220, height_mm=200,
        ),),
    }
    values.update(changes)
    return api.SheetSpec(**values)


def test_sheet_has_editable_pending_title_block_and_reopened_dxf(package, api, tmp_path):
    require_sheet_api(api)
    sheet = api.compose_licensing_sheets(
        package, [spec(api)], title_block(api)
    )[0]
    path = tmp_path / "ARQ-01.dxf"
    sheet.document.saveas(path)
    reopened = ezdxf.readfile(path)
    texts = [entity.dxf.text for entity in reopened.modelspace()
             if entity.dxftype() == "TEXT"]

    assert reopened.header["$INSUNITS"] == ezdxf.units.MM
    assert sheet.sheet_id == "ARQ-01"
    assert any(value.startswith("PROJETO: Casa compacta") for value in texts)
    assert any("MUNICÍPIO: PENDENTE" in value for value in texts)
    assert any("RESPONSÁVEL TÉCNICO: PENDENTE" in value for value in texts)
    assert any("REGISTRO: PENDENTE" in value for value in texts)
    assert any(entity.dxf.layer == "CARIMBO" for entity in reopened.modelspace())
    source_ids = {entity.get_xdata("MCP_CAD")[0].value
                  for entity in reopened.modelspace()
                  if entity.has_xdata("MCP_CAD")}
    assert "dimension:overall:width" in source_ids
    assert "dimension:overall:depth" in source_ids
    assert "dimension-label:overall:width" in source_ids
    assert all(entity.dxf.get("true_color") == 0x101820 for entity in reopened.modelspace()
               if entity.dxftype() == "TEXT")
    assert reopened.audit().has_errors is False


def test_multiple_unique_sheet_ids_create_separate_editable_drawings(package, api):
    require_sheet_api(api)
    first = spec(api, "ARQ-01")
    second = spec(api, "ARQ-02", viewports=(api.ViewportSpec(
        view_id="ARQ-COBERTURA", x_mm=20, y_mm=70, width_mm=220, height_mm=200,
    ),))

    sheets = api.compose_licensing_sheets(package, [first, second], title_block(api))

    assert [sheet.sheet_id for sheet in sheets] == ["ARQ-01", "ARQ-02"]
    assert sheets[0].document is not sheets[1].document


def test_duplicate_sheet_ids_and_unknown_views_are_rejected(package, api):
    require_sheet_api(api)
    with pytest.raises(api.SheetCompositionError, match="duplicad"):
        api.compose_licensing_sheets(
            package, [spec(api, "ARQ-01"), spec(api, "ARQ-01")], title_block(api)
        )
    broken = spec(api, "ARQ-02", viewports=(api.ViewportSpec(
        view_id="ARQ-NAO-EXISTE", x_mm=20, y_mm=70, width_mm=220, height_mm=200,
    ),))
    with pytest.raises(api.SheetCompositionError, match="Vista"):
        api.compose_licensing_sheets(package, [broken], title_block(api))


def test_viewport_that_cannot_fit_declared_scale_is_rejected(package, api):
    require_sheet_api(api)
    too_small = spec(api, viewports=(api.ViewportSpec(
        view_id="ARQ-PLANTA", x_mm=20, y_mm=70, width_mm=100, height_mm=100,
    ),))

    with pytest.raises(api.SheetCompositionError, match="escala"):
        api.compose_licensing_sheets(package, [too_small], title_block(api))


def test_overlapping_viewports_are_rejected(package, api):
    overlapping = spec(api, viewports=(
        api.ViewportSpec("ARQ-PLANTA", 20, 70, 220, 200),
        api.ViewportSpec("ARQ-COBERTURA", 200, 70, 200, 200),
    ))

    with pytest.raises(api.SheetCompositionError, match="sobrepostos"):
        api.compose_licensing_sheets(package, [overlapping], title_block(api))


def test_non_finite_scale_or_viewport_dimensions_are_rejected(package, api):
    invalid_scale = spec(api, scale=float("nan"))
    invalid_viewport = spec(api, viewports=(api.ViewportSpec(
        view_id="ARQ-PLANTA", x_mm=20, y_mm=70,
        width_mm=float("inf"), height_mm=200,
    ),))

    with pytest.raises(api.SheetCompositionError, match="Escala"):
        api.compose_licensing_sheets(package, [invalid_scale], title_block(api))
    with pytest.raises(api.SheetCompositionError, match="Viewport"):
        api.compose_licensing_sheets(package, [invalid_viewport], title_block(api))


def test_each_sheet_renders_pdf_png_from_reopened_dxf_document(package, api, tmp_path):
    require_sheet_api(api)
    sheet = api.compose_licensing_sheets(package, [spec(api)], title_block(api))[0]
    path = tmp_path / f"{sheet.sheet_id}.dxf"
    sheet.document.saveas(path)
    reopened_sheet = replace(sheet, document=ezdxf.readfile(path))
    pdf, png = api.renderizar_folha(reopened_sheet)

    assert pdf.startswith(b"%PDF-")
    assert png.startswith(bytes.fromhex("89504e470d0a1a0a"))

