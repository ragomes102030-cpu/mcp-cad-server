"""Deterministic regression corpus for the compact-residence sheet pipeline."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
from math import ceil
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[2]
CLOUD = ROOT / "cloud" / "ezdxf"
TESTS = CLOUD / "tests"
for entry in (str(CLOUD), str(TESTS)):
    if entry not in __import__("sys").path:
        __import__("sys").path.insert(0, entry)

from mcp_cad_cloud.arquitetura_requisitos import ProjectContext
from mcp_cad_cloud import backend
from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud.auditoria_circulacao import auditar_circulacao
from mcp_cad_cloud.auditoria_geometrica import auditar_dxf_serializado
from mcp_cad_cloud.auditoria_prancha import audit_sheet_document
from mcp_cad_cloud.normas_arquitetura import load_requirement_records
from mcp_cad_cloud.planta_gerador import ErroPrograma, gerar_modelo
from mcp_cad_cloud.projeto_arquitetonico import (
    ArchitecturePackageError, BuildingEnvelope, generate_architecture_package,
)
from mcp_cad_cloud.projeto_automatico import evaluate_package
from mcp_cad_cloud.prancha_dxf import (
    SheetCompositionError, SheetSpec, TitleBlockData, ViewportSpec,
    compose_licensing_sheets, renderizar_folha,
)
from tools.plant_lab.scenarios import VALID_SCENARIOS
from tools.plant_lab.independent_geometry import evaluate_reopened_dxf


ROOMS = ("Sala de estar", "Cozinha", "Área de serviço", "Quarto 1",
         "Quarto 2", "Banheiro social")
_ENVELOPE = {
    "floor_level_m": 0.0, "wall_height_m": 2.8, "door_head_m": 2.1,
    "window_sill_m": 0.9, "window_head_m": 2.2, "roof_type": "gable",
    "roof_pitch_degrees": 25.0, "roof_overhang_m": 0.45, "ridge_axis": "x",
}
_SHEET_MUTATIONS = ("delete-dimension", "wrong-sheet-id", "insert-outside-circle")


def build_scenarios() -> list[dict]:
    """Use only compact programs already accepted by the strict 2D validator."""
    selected = VALID_SCENARIOS[:30]
    if len(selected) < 30:
        raise RuntimeError(f"expected at least 30 supported scenarios, got {len(selected)}")
    return [deepcopy(item) for item in selected]


def _context(program: dict, model: dict) -> ProjectContext:
    terrain = model["terreno"]
    return ProjectContext(
        project_name="Residência compacta - laboratório",
        use="residencial_unifamiliar", typology="compacto_2quartos",
        municipality=None, state=None, storeys=1,
        lot_width_m=terrain[2] - terrain[0],
        lot_depth_m=terrain[3] - terrain[1],
        requested_rooms=tuple(item["nome"] for item in program["ambientes"]),
        stage="licenciamento",
    )


def _envelope(index: int) -> BuildingEnvelope:
    values = dict(_ENVELOPE)
    values["roof_pitch_degrees"] = (20.0, 25.0, 30.0)[index % 3]
    values["roof_overhang_m"] = (0.30, 0.45, 0.60)[index % 3]
    return BuildingEnvelope(**values)


def _scale_for(view, viewport_width_mm=220.0, viewport_height_mm=200.0) -> float:
    min_x, min_y, max_x, max_y = view.bounds
    required = max((max_x - min_x) * 1000 / viewport_width_mm,
                   (max_y - min_y) * 1000 / viewport_height_mm)
    return max(50.0, ceil(required / 25.0) * 25.0)


def _compose(package, view_id: str, sheet_id: str):
    view = next(item for item in package.views if item.view_id == view_id)
    scale = _scale_for(view)
    spec = SheetSpec("A3", "landscape", scale, 10.0, sheet_id,
                     (ViewportSpec(view_id, 20, 70, 220, 200),))
    title = TitleBlockData(package.project_context.project_name,
                           package.project_context.municipality,
                           package.project_context.state, None, None, None,
                           "2026-10-29", "R00")
    return compose_licensing_sheets(package, [spec], title)[0]


def _roundtrip(sheet):
    stream = io.StringIO()
    sheet.document.write(stream)
    raw = stream.getvalue().encode("utf-8")
    reopened = ezdxf.read(io.StringIO(raw.decode("utf-8")))
    audit = audit_sheet_document(reopened, sheet.spec, _CURRENT_PACKAGE[0])
    structural = reopened.audit()
    return raw, reopened, audit, structural


_CURRENT_PACKAGE = [None]


def _functional_checks(program: dict, package) -> list[str]:
    errors: list[str] = []
    model = package.source_plan
    expected_names = {item["nome"] for item in program["ambientes"]}
    generated_names = {item["nome"] for item in model["ambientes"]}
    if not expected_names <= generated_names:
        errors.append("briefing-room-fidelity-mismatch")
    if len(model.get("portas", ())) != 5:
        errors.append("supported-door-count-mismatch")
    if len(model.get("janelas", ())) != 6:
        errors.append("supported-window-count-mismatch")
    floor = next(view for view in package.views if view.kind == "planta_baixa")
    labels = {label.source_id for label in floor.labels}
    for index in range(len(program["ambientes"])):
        if f"room-area:{index}" not in labels:
            errors.append(f"room-area-label-missing:{index}")
        if f"schedule:room:{index}" not in labels:
            errors.append(f"room-dimensions-schedule-missing:{index}")
    for index in range(len(model.get("portas", ()))):
        if f"opening-tag:door:{index}" not in labels or f"schedule:door:{index}" not in labels:
            errors.append(f"door-identification-or-schedule-missing:{index}")
        if sum(segment.source_id.startswith(f"door:{index}:swing:")
               for segment in floor.segments) != 8:
            errors.append(f"door-swing-symbol-invalid:{index}")
    for index in range(len(model.get("janelas", ()))):
        if f"opening-tag:window:{index}" not in labels or f"schedule:window:{index}" not in labels:
            errors.append(f"window-identification-or-schedule-missing:{index}")
    for source_id in ("schedule:rooms:title", "schedule:doors:title",
                      "schedule:windows:title"):
        if source_id not in labels:
            errors.append(f"opening-or-room-schedule-title-missing:{source_id}")
    if "dimension-label:overall:width" not in labels or "dimension-label:overall:depth" not in labels:
        errors.append("external-dimensions-missing")
    return errors


def _mutate_sheet(doc, mutation: str):
    msp = doc.modelspace()
    if mutation == "delete-dimension":
        entity = next(item for item in msp.query("LINE")
                      if item.has_xdata("MCP_CAD")
                      and item.get_xdata("MCP_CAD")[0].value == "dimension:overall:width")
        msp.delete_entity(entity)
    elif mutation == "wrong-sheet-id":
        entity = next(item for item in msp.query("TEXT")
                      if item.dxf.text.startswith("PRANCHA: ARQ-"))
        entity.dxf.text = entity.dxf.text.replace("ARQ-01", "ARQ-99")
    elif mutation == "insert-outside-circle":
        msp.add_circle((450.0, 300.0), 10.0)
    else:
        raise ValueError(f"unknown sheet mutation: {mutation}")


def _contact_sheet(paths: list[Path], target: Path):
    import matplotlib
    matplotlib.use("Agg", force=True)
    from matplotlib.figure import Figure
    from matplotlib import image as mpimg

    fig = Figure(figsize=(18, 12), facecolor="white")
    for index, path in enumerate(paths):
        ax = fig.add_subplot(3, 3, index + 1)
        ax.imshow(mpimg.imread(path))
        ax.set_title(path.stem, fontsize=9)
        ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(target, format="png", dpi=110, facecolor="white")
    fig.clear()


def run_corpus(output_dir: str | Path, *, valid_limit: int | None = None) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dxf").mkdir(exist_ok=True)
    (out / "visuals").mkdir(exist_ok=True)
    all_scenarios = build_scenarios()
    scenarios = all_scenarios[:valid_limit] if valid_limit else all_scenarios
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "compact_two_bedroom_licensing_package_regression_not_code_approval",
        "valid_scenario_count": len(scenarios),
        "full_valid_scenario_count": len(all_scenarios),
        "adversarial_scenario_count": 7 + len(_SHEET_MUTATIONS),
        "valid_scenarios": [], "adversarial_scenarios": [],
        "coverage": {"view_types": {}, "requirements": {}, "warnings": {}},
    }
    image_paths: list[Path] = []
    requirements = load_requirement_records()
    for index, scenario in enumerate(scenarios):
        item = {"id": scenario["id"], "status": "failed", "errors": []}
        try:
            program = deepcopy(scenario["program"])
            with backend.test_session("licensing-corpus-" + scenario["id"]):
                backend.reset_drawing()
                preview = cad.planta_criar_validada(
                    programa=program, modo="preview", template="programa_sob_medida")
                if not preview.get("ok") or not preview.get("validacao", {}).get("ok"):
                    raise AssertionError(f"strict preview rejected: {preview}")
                drawn = cad.planta_criar_validada(
                    programa=program, modo="desenhar", template="programa_sob_medida",
                    preview_token=preview["preview_token"], nome=scenario["id"])
                if not drawn.get("ok"):
                    raise AssertionError(f"real DXF drawing failed: {drawn}")
                model = preview["modelo"]
                document = backend._ensure()
                production_geometry = auditar_dxf_serializado(model, document)
                circulation = auditar_circulacao(model, document)
                source_path = out / "dxf" / f"{scenario['id']}-source.dxf"
                document.saveas(source_path)
                reopened_source = ezdxf.readfile(source_path)
                structural_source = reopened_source.audit()
                independent_source = evaluate_reopened_dxf(reopened_source, scenario)
                item["source_plan_audits"] = {
                    "production_geometry_ok": production_geometry.get("ok"),
                    "production_circulation_ok": circulation.get("ok"),
                    "circulation_warnings": circulation.get("avisos", []),
                    "door_count": len(model.get("portas", ())),
                    "window_geometry_count": len(model.get("janelas", ())),
                    "furniture_count": len(model.get("moveis", ())),
                    "connected_rooms": (circulation.get("metricas") or {}).get(
                        "ambientes_conectados"),
                    "ezdxf_errors": len(structural_source.errors),
                    "independent_errors": independent_source,
                }
                for warning in (circulation.get("avisos") or ()):
                    code = warning.get("chave", "circulation-warning-unclassified")
                    report["coverage"]["warnings"][code] = (
                        report["coverage"]["warnings"].get(code, 0) + 1)
                if not production_geometry.get("ok"):
                    item["errors"].append("production-plan-geometry-audit-failed")
                if not circulation.get("ok"):
                    item["errors"].append("production-circulation-audit-failed")
                if structural_source.has_errors:
                    item["errors"].append("source-dxf-ezdxf-audit-failed")
                if independent_source:
                    item["errors"].append("source-dxf-independent-geometry-failed")
                if index >= 3:
                    source_path.unlink(missing_ok=True)
            package = generate_architecture_package(model, _context(program, model),
                                                   _envelope(index))
            _CURRENT_PACKAGE[0] = package
            item["functional_errors"] = _functional_checks(program, package)
            evaluation = evaluate_package(package, requirements, {}, {})
            item["licensing_readiness"] = evaluation["licensing_readiness"]
            item["requirement_statuses"] = [result.status.value for result in evaluation["results"]]
            if evaluation["licensing_readiness"] != "review_required":
                item["errors"].append("unverified-requirement-readiness-not-conservative")
            if any(status != "não testável" for status in item["requirement_statuses"]):
                item["errors"].append("unreviewed-standard-counted-as-verified")
            for status in item["requirement_statuses"]:
                report["coverage"]["requirements"][status] = (
                    report["coverage"]["requirements"].get(status, 0) + 1)
            if item["requirement_statuses"]:
                key = "normative-criteria-not-tested"
                report["coverage"]["warnings"][key] = report["coverage"]["warnings"].get(key, 0) + 1
            if package.project_context.municipality is None:
                key = "municipality-profile-not-configured"
                report["coverage"]["warnings"][key] = report["coverage"]["warnings"].get(key, 0) + 1
            item["errors"].extend(item["functional_errors"])
            if index == 0:
                selected_views = [view.view_id for view in package.views]
            else:
                selected_views = ["ARQ-PLANTA", package.views[(index % 8) + 1].view_id]
            dxf_records = []
            for sheet_index, view_id in enumerate(selected_views):
                view_kind = next(view.kind for view in package.views if view.view_id == view_id)
                report["coverage"]["view_types"][view_kind] = report["coverage"]["view_types"].get(view_kind, 0) + 1
                sheet_id = "ARQ-01" if sheet_index == 0 else "ARQ-02"
                sheet = _compose(package, view_id, sheet_id)
                raw, reopened, audit, structural = _roundtrip(sheet)
                if not audit["ok"]:
                    item["errors"].extend(f"{issue['code']}:{issue['message']}" for issue in audit["errors"])
                if structural.has_errors:
                    item["errors"].append("ezdxf-structural-audit-failed")
                dxf_record = {"sheet": sheet_id, "view_id": view_id,
                              "sha256": hashlib.sha256(raw).hexdigest(),
                              "bytes": len(raw), "entity_count": len(list(reopened.modelspace())),
                              "audit_errors": audit["errors"]}
                dxf_records.append(dxf_record)
                if index < 3:
                    (out / "dxf" / f"{scenario['id']}-{sheet_id}.dxf").write_bytes(raw)
                if index == 0:
                    reopened_sheet = type(sheet)(sheet.sheet_id, sheet.spec,
                                                 sheet.title_block_rows, reopened)
                    pdf, png = renderizar_folha(reopened_sheet)
                    if not pdf.startswith(b"%PDF-") or not png.startswith(bytes.fromhex("89504e470d0a1a0a")):
                        item["errors"].append("invalid-render-signature")
                    stem = view_id.lower().replace("arq-", "")
                    png_path = out / "visuals" / f"{stem}.png"
                    (out / "visuals" / f"{stem}.pdf").write_bytes(pdf)
                    png_path.write_bytes(png)
                    image_paths.append(png_path)
            item["sheets"] = dxf_records
            if not item["errors"]:
                item["status"] = "passed"
        except Exception as exc:
            item["errors"].append(f"{type(exc).__name__}: {exc}")
        report["valid_scenarios"].append(item)

    base_program = deepcopy(scenarios[0]["program"])
    base_model = gerar_modelo(base_program)
    base_context = _context(base_program, base_model)
    _CURRENT_PACKAGE[0] = generate_architecture_package(
        base_model, base_context, _envelope(0))
    adversarial_specs = [
        ("second-storey-unsupported", "input", {"storeys": 2}),
        ("missing-city-remains-unverified", "requirement", {}),
        ("non-finite-wall-height", "envelope", {"wall_height_m": float("nan")}),
        ("door-head-above-wall", "envelope", {"door_head_m": 3.0}),
        ("context-lot-mismatch", "context", {"lot_width_m": 11.0}),
        ("missing-room", "context", {"requested_rooms": base_context.requested_rooms[:-1]}),
        ("title-project-mismatch", "title", {"project_name": "Outra residência"}),
    ]
    for case_id, category, mutation in adversarial_specs:
        item = {"id": case_id, "status": "failed", "errors": []}
        try:
            if category == "requirement":
                evaluation = evaluate_package(_CURRENT_PACKAGE[0], requirements, {}, {})
                if evaluation["licensing_readiness"] == "review_required" and all(
                    result.status.value == "não testável" for result in evaluation["results"]
                ):
                    item["status"] = "passed"
                else:
                    item["errors"].append("unconfigured-city-requirement-was-not-held-pending")
            elif category == "input":
                context_values = dict(base_context.__dict__)
                context_values.update(mutation)
                generate_architecture_package(base_model, ProjectContext(**context_values), _envelope(0))
                item["errors"].append("unsupported-second-storey-was-accepted")
            elif category == "context":
                context_values = dict(base_context.__dict__)
                context_values.update(mutation)
                generate_architecture_package(base_model, ProjectContext(**context_values), _envelope(0))
                item["errors"].append("mismatched-project-context-was-accepted")
            elif category == "envelope":
                envelope_values = dict(_ENVELOPE)
                envelope_values.update(mutation)
                generate_architecture_package(base_model, base_context,
                                              BuildingEnvelope(**envelope_values))
                item["errors"].append("invalid-vertical-envelope-was-accepted")
            elif category == "title":
                title = TitleBlockData(mutation["project_name"], None, None, None,
                                       None, None, "2026-10-29", "R00")
                spec = SheetSpec("A3", "landscape", 50, 10, "ARQ-01",
                                 (ViewportSpec("ARQ-PLANTA", 20, 70, 220, 200),))
                compose_licensing_sheets(_CURRENT_PACKAGE[0], [spec], title)
                item["errors"].append("title-context-mismatch-was-accepted")
            if not item["errors"]:
                item["status"] = "passed"
        except (ArchitecturePackageError, ErroPrograma, SheetCompositionError, ValueError) as exc:
            item["expected_rejection"] = str(exc)
            item["status"] = "passed"
        report["adversarial_scenarios"].append(item)

    # Mutate reopened documents to prove independent detection of corrupt sheets.
    package = _CURRENT_PACKAGE[0]
    clean_sheet = _compose(package, "ARQ-PLANTA", "ARQ-01")
    stream = io.StringIO(); clean_sheet.document.write(stream)
    clean = ezdxf.read(io.StringIO(stream.getvalue()))
    for mutation in _SHEET_MUTATIONS:
        item = {"id": f"sheet-mutation-{mutation}", "status": "failed", "errors": []}
        doc = ezdxf.read(io.StringIO(stream.getvalue()))
        try:
            _mutate_sheet(doc, mutation)
            result = audit_sheet_document(doc, clean_sheet.spec, package)
            codes = {issue["code"] for issue in result["errors"]}
            expected = "source-entity-missing" if mutation == "delete-dimension" else (
                "title-field-missing" if mutation == "wrong-sheet-id" else "entity-outside-sheet")
            if expected in codes:
                item.update(status="passed", detected_codes=sorted(codes))
            else:
                item["errors"].append(f"expected {expected}, detected {sorted(codes)}")
        except Exception as exc:
            item["errors"].append(f"{type(exc).__name__}: {exc}")
        report["adversarial_scenarios"].append(item)

    all_items = report["valid_scenarios"] + report["adversarial_scenarios"]
    report["summary"] = {
        "valid_passed": sum(item["status"] == "passed" for item in report["valid_scenarios"]),
        "valid_failed": sum(item["status"] != "passed" for item in report["valid_scenarios"]),
        "adversarial_passed": sum(item["status"] == "passed" for item in report["adversarial_scenarios"]),
        "adversarial_failed": sum(item["status"] != "passed" for item in report["adversarial_scenarios"]),
        "total_passed": sum(item["status"] == "passed" for item in all_items),
        "total_failed": sum(item["status"] != "passed" for item in all_items),
    }
    report["requirements"] = {
        "candidate_count": len(requirements),
        "criteria_implemented": 0,
        "limitations": ["lista não exaustiva", "nenhum critério NBR revisado com texto autorizado"]
    }
    report["coverage"]["requirements"] = {"não testável": len(requirements)}
    _contact_sheet(image_paths[:9], out / "contact-sheet.png")
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Corpus de regressão do pacote arquitetônico", "",
        f"- Cenários válidos: {report['summary']['valid_passed']}/{len(scenarios)}",
        f"- Casos adversariais detectados: {report['summary']['adversarial_passed']}/{len(report['adversarial_scenarios'])}",
        f"- Falhas: {report['summary']['total_failed']}",
        "- Resultado não certifica conformidade normativa ou aprovação de prefeitura.",
        "", "## Cobertura das vistas", "",
    ]
    lines.extend(f"- {kind}: {count}" for kind, count in sorted(report["coverage"]["view_types"].items()))
    lines.extend(["", "## Falhas e inconclusivos", ""])
    failed = [item for item in all_items if item["status"] != "passed"]
    lines.extend(f"- {item['id']}: {'; '.join(item['errors'])}" for item in failed)
    if not failed:
        lines.append("- Nenhuma falha neste corpus determinístico.")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
