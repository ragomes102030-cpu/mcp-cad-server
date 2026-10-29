from copy import deepcopy
import importlib
import importlib.util

import pytest

from mcp_cad_cloud.planta_gerador import gerar_modelo
from test_layout_compacto import CASA


@pytest.fixture
def api():
    module = "mcp_cad_cloud.projeto_arquitetonico"
    assert importlib.util.find_spec(module) is not None, f"missing production module: {module}"
    return importlib.import_module(module)


def context(requirement_api, **changes):
    values = {
        "project_name": "Casa compacta",
        "use": "residencial_unifamiliar",
        "typology": "compacto_2quartos",
        "municipality": None,
        "state": None,
        "storeys": 1,
        "lot_width_m": 10.0,
        "lot_depth_m": 20.0,
        "requested_rooms": ("Sala de estar", "Cozinha", "Área de serviço",
                            "Quarto 1", "Quarto 2", "Banheiro social"),
        "stage": "licenciamento",
        "municipal_profile_revision": None,
    }
    values.update(changes)
    return requirement_api.ProjectContext(**values)


def envelope(api, **changes):
    values = {
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
    values.update(changes)
    return api.BuildingEnvelope(**values)


def generate(api, **changes):
    requirement_api = importlib.import_module("mcp_cad_cloud.arquitetura_requisitos")
    model = gerar_modelo(deepcopy(CASA))
    return api.generate_architecture_package(
        model,
        context(requirement_api, **changes.pop("context_changes", {})),
        envelope(api, **changes),
    )


def test_compact_house_produces_all_licensing_views_with_sources(api):
    package = generate(api)

    by_id = {view.view_id: view for view in package.views}
    assert {
        "ARQ-IMPLANTACAO", "ARQ-PLANTA", "ARQ-COBERTURA", "ARQ-CORTE-A",
        "ARQ-CORTE-B", "ARQ-FACHADA-FRONTAL", "ARQ-FACHADA-FUNDOS",
        "ARQ-FACHADA-LATERAL-ESQ", "ARQ-FACHADA-LATERAL-DIR",
    } <= set(by_id)
    assert all(view.unit == "m" and view.segments for view in package.views)
    assert all(view.source_ids for view in package.views)
    floor_plan = by_id["ARQ-PLANTA"]
    assert sum(segment.layer == "ESQUADRIA-PORTA" for segment in floor_plan.segments) == len(package.source_plan["portas"])
    assert sum(segment.layer == "ESQUADRIA-JANELA" for segment in floor_plan.segments) == 2 * len(package.source_plan["janelas"])
    assert sum(segment.layer == "MOBILIARIO" for segment in floor_plan.segments) == 4 * len(package.source_plan["moveis"])
    assert package.readiness == "review_required"
    assert any("NBR" in limitation for limitation in package.limitations)
    assert any("municip" in limitation.lower() for limitation in package.limitations)


def test_missing_wall_opening_or_roof_height_is_rejected(api):
    for changes in (
        {"wall_height_m": None},
        {"door_head_m": None},
        {"window_sill_m": None},
        {"window_head_m": None},
        {"roof_pitch_degrees": None},
    ):
        with pytest.raises(api.ArchitecturePackageError):
            generate(api, **changes)


def test_contradictory_opening_heights_are_rejected(api):
    with pytest.raises(api.ArchitecturePackageError, match="janela"):
        generate(api, window_sill_m=2.4, window_head_m=2.2)


def test_second_storey_and_unsupported_room_program_are_rejected(api):
    with pytest.raises(api.ArchitecturePackageError, match="pavimento"):
        generate(api, context_changes={"storeys": 2})
    with pytest.raises(api.ArchitecturePackageError, match="Programa"):
        generate(api, context_changes={
            "requested_rooms": ("Sala de estar", "Cozinha", "Quarto 1")
        })


def test_context_lot_dimensions_must_match_generated_site(api):
    with pytest.raises(api.ArchitecturePackageError, match="terreno"):
        generate(api, context_changes={"lot_width_m": 12.0})


def test_two_orthogonal_sections_and_opening_views_are_deterministic(api):
    first = generate(api)
    second = generate(api)

    first_by_id = {view.view_id: view for view in first.views}
    second_by_id = {view.view_id: view for view in second.views}
    assert first_by_id["ARQ-CORTE-A"] == second_by_id["ARQ-CORTE-A"]
    assert first_by_id["ARQ-CORTE-B"] == second_by_id["ARQ-CORTE-B"]
    assert len(first_by_id["ARQ-CORTE-A"].segments) >= 6
    assert len(first_by_id["ARQ-CORTE-B"].segments) >= 6
    assert any(segment.layer == "ESQUADRIA-JANELA"
               for segment in first_by_id["ARQ-FACHADA-FRONTAL"].segments)


def test_parallel_ridge_facades_do_not_show_a_detached_roof_profile(api):
    package = generate(api)
    views = {view.view_id: view for view in package.views}
    for view_id in ("ARQ-FACHADA-FRONTAL", "ARQ-FACHADA-FUNDOS"):
        view = views[view_id]
        roof = [segment for segment in view.segments if segment.layer == "COBERTURA"]
        assert roof == [], f"roof profile floats above this eave elevation: {roof}"
        eaves = [segment for segment in view.segments if segment.layer == "BEIRAL"]
        assert len(eaves) == 1
        assert eaves[0].y1 == eaves[0].y2 == package.envelope.wall_height_m


def test_ridge_parallel_section_connects_roof_to_gable_end_walls(api):
    package = generate(api)
    section = next(view for view in package.views if view.view_id == "ARQ-CORTE-B")
    gable_walls = [segment for segment in section.segments
                   if segment.source_id.startswith("section:x:gable-")]
    roof = next(segment for segment in section.segments
                if segment.source_id == "section:x:ridge-run")

    assert len(gable_walls) == 2
    assert {segment.x1 for segment in gable_walls} == {roof.x1, roof.x2}
    assert all(segment.y1 == package.envelope.wall_height_m for segment in gable_walls)
    assert all(segment.y2 == roof.y1 for segment in gable_walls)


def test_room_labels_are_moved_clear_of_known_bed_and_fixture_footprints(api):
    package = generate(api)
    floor = next(view for view in package.views if view.view_id == "ARQ-PLANTA")
    labels = {label.source_id: label for label in floor.labels}

    assert labels["room:0"].x > 3.0  # living-room label clears the sofa
    assert labels["room:3"].x > 2.4  # bedroom-1 label clears the bed
    assert labels["room:4"].y < 6.0  # bedroom-2 label uses the open band below furniture
    assert labels["room:5"].x > 5.0 and labels["room:5"].y > 7.5

