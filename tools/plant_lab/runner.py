"""End-to-end local plant generation lab; writes evidence without touching originals."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys
import time
import traceback
from urllib.parse import urlparse

import ezdxf

ROOT = Path(__file__).resolve().parents[2]
CLOUD = ROOT / "cloud" / "ezdxf"
TESTS = CLOUD / "tests"
for path in (str(CLOUD), str(TESTS)):
    if path not in sys.path:
        sys.path.insert(0, path)

from mcp_cad_cloud import tools_verified as cad
from mcp_cad_cloud import backend, downloads
from mcp_cad_cloud.auditoria_circulacao import auditar_circulacao
from mcp_cad_cloud.auditoria_geometrica import auditar_dxf_serializado
from mcp_cad_cloud.prancha_dxf import renderizar_prancha
from tools.plant_lab.independent_geometry import evaluate_reopened_dxf
from tools.plant_lab.scenarios import ADVERSARIAL_SCENARIOS, MCP_SCENARIOS, VALID_SCENARIOS
from tools.plant_lab.sensitivity import measure_route_widths


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _entity_sha256(doc) -> str:
    """Stable digest of DXF modelspace entities, excluding random handles/metadata."""
    payload = []
    for entity in doc.modelspace():
        attrs = entity.dxf.all_existing_dxf_attribs()
        attrs.pop("handle", None)
        attrs.pop("owner", None)
        payload.append({"type": entity.dxftype(), "attributes": attrs})
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), default=repr).encode("utf-8")
    return _sha(canonical)


def _write_visuals(doc, scenario, directory, geometry):
    pdf, png = renderizar_prancha(doc, scenario["id"], geometry)
    directory.mkdir(parents=True, exist_ok=True)
    pdf_path, png_path = directory / f"{scenario['id']}.pdf", directory / f"{scenario['id']}.png"
    pdf_path.write_bytes(pdf)
    png_path.write_bytes(png)
    if not pdf.startswith(b"%PDF-") or not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("rendered PDF/PNG does not have a valid file signature")
    return {"pdf_path": str(pdf_path), "png_path": str(png_path),
            "pdf_sha256": _sha(pdf), "png_sha256": _sha(png),
            "pdf_bytes": len(pdf), "png_bytes": len(png)}


def _build_case(scenario, out):
    started = time.perf_counter()
    result = {"id": scenario["id"], "status": "failed", "errors": []}
    try:
        with backend.test_session("plant-lab-" + scenario["id"]):
            backend.reset_drawing()
            preview = cad.planta_criar_validada(programa=scenario["program"],
                modo="preview", template="programa_sob_medida")
            if not preview.get("ok") or not preview.get("validacao", {}).get("ok"):
                raise AssertionError(f"preview rejected: {preview}")
            drawn = cad.planta_criar_validada(programa=scenario["program"],
                modo="desenhar", template="programa_sob_medida",
                preview_token=preview["preview_token"], nome=scenario["id"])
            if not drawn.get("ok"):
                raise AssertionError(f"draw rejected: {drawn}")
            ez_audit = cad.drawing_audit()
            model = preview["modelo"]
            geom = auditar_dxf_serializado(model, backend._ensure())
            circulation = auditar_circulacao(model, backend._ensure())
            path = out / "dxf" / f"{scenario['id']}.dxf"
            path.parent.mkdir(parents=True, exist_ok=True)
            backend._ensure().saveas(path)
            reopened = ezdxf.readfile(path)
            auditor = reopened.audit()
            independent = evaluate_reopened_dxf(reopened, scenario)
            sensitivity = measure_route_widths(reopened)
            result.update({"dxf_path": str(path), "sha256": _sha(path.read_bytes()),
                "entity_sha256": _entity_sha256(reopened),
                "ezdxf_audit": {"ok": not auditor.has_errors, "errors": len(auditor.errors),
                                "fixes": len(auditor.fixes)},
                "production_geometry": geom, "production_circulation": circulation,
                "independent_errors": independent, "route_sensitivity": sensitivity,
                "entity_count": len(reopened.modelspace()),
                "duration_seconds": round(time.perf_counter() - started, 3)})
            failures = []
            if not ez_audit.get("ok") or ez_audit.get("errors"):
                failures.append("pre-save ezdxf audit reported errors")
            if auditor.has_errors:
                failures.append("reopened ezdxf audit reported errors")
            if not geom.get("ok"):
                failures.append("production geometric audit failed")
            if not circulation.get("ok"):
                failures.append("production circulation audit failed")
            if independent:
                failures.append("independent DXF evaluator found errors")
            if scenario.get("render"):
                result["visuals"] = _write_visuals(backend._ensure(), scenario,
                    out / "visuals", preview["resumo_geometria"])
            result["status"] = "passed" if not failures else "failed"
            result["errors"] = failures
    except Exception as exc:
        result["errors"] = [f"{type(exc).__name__}: {exc}"]
        result["traceback"] = traceback.format_exc(limit=8)
    result.setdefault("duration_seconds", round(time.perf_counter() - started, 3))
    return result


def _mutate(doc, mutation):
    msp = doc.modelspace()
    if mutation == "remove-door-arc":
        msp.delete_entity(next(iter(msp.query('ARC[layer=="PORTAS"]'))))
    elif mutation == "break-door-leaf":
        next(iter(msp.query('LINE[layer=="PORTAS"]'))).dxf.start = (999, 999, 0)
    elif mutation in ("shift-window-line", "remove-window-line"):
        item = next(iter(msp.query('LINE[layer=="JANELAS"]')))
        if mutation == "remove-window-line":
            msp.delete_entity(item)
        else:
            item.dxf.start = (item.dxf.start.x + 0.23, item.dxf.start.y, 0)
    elif mutation == "furniture-outside-lot":
        item = next(iter(msp.query('LWPOLYLINE[layer=="MOBILIARIO"]')))
        item.translate(100, 0, 0)
    elif mutation == "overlap-furniture":
        items = list(msp.query('LWPOLYLINE[layer=="MOBILIARIO"]'))
        points = list(items[0].get_points("xy"))
        items[1].set_points(points, format="xy")
    elif mutation == "change-lot-bounds":
        item = next(iter(msp.query('LWPOLYLINE[layer=="TERRENO"]')))
        points = list(item.get_points("xy"))
        points[-1] = (points[-1][0] + 1, points[-1][1])
        item.set_points(points, format="xy")
    elif mutation == "wrong-dxf-units":
        doc.header["$INSUNITS"] = 0
    elif mutation == "diagonal-wall":
        item = next(iter(msp.query('LINE[layer=="PAREDES"]')))
        item.dxf.end = (item.dxf.end.x + 0.3, item.dxf.end.y + 0.2, 0)
    elif mutation == "break-room-area-label":
        item = next(iter(msp.query('TEXT[layer=="COTAS_INT"]')))
        item.dxf.text = "999 x 999 m"
    else:
        raise ValueError(f"unknown DXF mutation: {mutation}")


def _adversarial(scenarios, valid_cases, out):
    base = next((case for case in valid_cases if case.get("dxf_path")), None)
    results = []
    for scenario in scenarios:
        item = {"id": scenario["id"], "kind": scenario["kind"], "status": "failed", "errors": []}
        try:
            if scenario["kind"] == "invalid_program":
                with backend.test_session("plant-lab-" + scenario["id"]):
                    backend.reset_drawing()
                    before = len(backend._ensure().modelspace())
                    response = cad.planta_criar_validada(programa=scenario["program"],
                        modo="preview", template="programa_sob_medida")
                    after = len(backend._ensure().modelspace())
                item.update({"rejected": not response.get("ok"), "entities_before": before,
                             "entities_after": after})
                if response.get("ok") or before != after:
                    item["errors"].append("invalid input was accepted or changed drawing")
                else:
                    item["status"] = "passed"
            else:
                if not base:
                    raise RuntimeError("no valid DXF is available for mutations")
                doc = ezdxf.readfile(base["dxf_path"])
                _mutate(doc, scenario["mutation"])
                reference = next(s for s in VALID_SCENARIOS if s["id"] == base["id"])
                issues = evaluate_reopened_dxf(doc, reference)
                detected = [issue["code"] for issue in issues]
                item.update({"mutation": scenario["mutation"], "detected_codes": detected})
                if scenario["expected_code"] in detected:
                    item["status"] = "passed"
                else:
                    item["errors"].append(f"expected {scenario['expected_code']}, detected {detected}")
        except Exception as exc:
            item["errors"].append(f"{type(exc).__name__}: {exc}")
        results.append(item)
    return results


def _mcp_cases(scenarios, out):
    results = []
    for entry in scenarios:
        scenario = entry["valid_scenario"]
        item = {"id": entry["id"], "transport": "direct_tool_handler",
                "status": "failed", "errors": []}
        try:
            with backend.test_session("plant-lab-" + entry["id"]):
                backend.reset_drawing()
                response = cad.projetar_residencia(
                    pedido=scenario["briefing"], nome=entry["id"])
                if not response.get("ok"):
                    raise AssertionError(f"one-call MCP tool returned failure: {response}")
                path = out / "mcp" / f"{entry['id']}.dxf"
                path.parent.mkdir(parents=True, exist_ok=True)
                backend._ensure().saveas(path)
                reopened = ezdxf.readfile(path)
                auditor = reopened.audit()
                independent = evaluate_reopened_dxf(reopened, scenario)
                item.update({"dxf_path": str(path), "sha256": _sha(path.read_bytes()),
                    "ezdxf_errors": len(auditor.errors), "independent_errors": independent,
                    "production_geometry_ok": response.get("auditoria_geometrica", {}).get("ok"),
                    "production_circulation_ok": response.get("auditoria_circulacao", {}).get("ok"),
                    "files": {kind: {"sha256": response["arquivos"][f"sha256_{kind}"],
                                     "bytes": len(downloads.retrieve(
                                         _token_from_url(response["arquivos"][f"{kind}_url"]), kind)[0])}
                              for kind in ("dxf", "pdf", "png")}})
                if (auditor.has_errors or independent
                    or not item["production_geometry_ok"]
                    or not item["production_circulation_ok"]):
                    item["errors"].append("DXF or one-call audit failed after reopen")
                else:
                    item["status"] = "passed"
        except Exception as exc:
            item["errors"].append(f"{type(exc).__name__}: {exc}")
            item["traceback"] = traceback.format_exc(limit=8)
        results.append(item)
    return results


def _token_from_url(url):
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) != 3 or parts[0] != "downloads":
        raise ValueError(f"unexpected short-lived export URL: {url}")
    return parts[1]


def _circulation_comparison(out):
    case = {"id": "circulation-original-vs-proposal", "status": "failed", "errors": []}
    request = ("Residência térrea de dois quartos, sala, cozinha, lavanderia e banheiro "
               "em lote de 10 x 20 m.")
    try:
        with backend.test_session("plant-lab-circulation-comparison"):
            backend.reset_drawing()
            response = cad.propor_melhoria_circulacao(request)
            case["mode"] = response.get("modo")
            case["candidates_evaluated"] = response.get("candidatas_avaliadas", 0)
            case["original_unchanged"] = response.get("alteracoes_aplicadas_ao_original") is False
            case["proposal_available"] = response.get("alternativa_disponivel") is True
            if not response.get("ok"):
                raise AssertionError(f"circulation comparison failed: {response}")
            if not case["original_unchanged"]:
                raise AssertionError("circulation proposal modified the original drawing")
            original_files = response["original"]["arquivos"]
            proposed_files = response.get("proposta", {}).get("arquivos")
            if not proposed_files:
                case["errors"].append("tool produced no circulation proposal to compare")
                return case
            visual_dir = out / "visuals"
            visual_dir.mkdir(parents=True, exist_ok=True)
            images = {}
            for label, files in (("original", original_files), ("proposal", proposed_files)):
                token = _token_from_url(files["png_url"])
                retrieved = downloads.retrieve(token, "png")
                if not retrieved:
                    raise RuntimeError(f"local short-lived {label} PNG could not be retrieved")
                payload = retrieved[0]
                if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError(f"{label} PNG signature is invalid")
                path = visual_dir / f"circulation-{label}.png"
                path.write_bytes(payload)
                images[label] = path
            from PIL import Image, ImageDraw
            original_image = Image.open(images["original"]).convert("RGB")
            proposal_image = Image.open(images["proposal"]).convert("RGB")
            width = max(original_image.width, proposal_image.width)
            height = max(original_image.height, proposal_image.height)
            comparison = Image.new("RGB", (width * 2, height + 42), "white")
            draw = ImageDraw.Draw(comparison)
            draw.text((12, 12), "ORIGINAL", fill="black")
            draw.text((width + 12, 12), "PROPOSTA NAO APLICADA", fill="black")
            original_image.thumbnail((width - 12, height - 12))
            proposal_image.thumbnail((width - 12, height - 12))
            comparison.paste(original_image, (0, 42))
            comparison.paste(proposal_image, (width, 42))
            comparison_path = visual_dir / "circulation-comparison.png"
            comparison.save(comparison_path)
            case.update({"status": "passed", "comparison_png": str(comparison_path),
                "original_png": str(images["original"]), "proposal_png": str(images["proposal"]),
                "proposal": {key: value for key, value in response["proposta"].items()
                             if key != "arquivos"}})
    except Exception as exc:
        case["errors"].append(f"{type(exc).__name__}: {exc}")
        case["traceback"] = traceback.format_exc(limit=8)
    return case


def _contact_sheet(valid_cases, out):
    paths = [case["visuals"]["png_path"] for case in valid_cases if case.get("visuals")]
    if not paths:
        return None
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    columns = 4
    rows = (len(paths) + columns - 1) // columns
    figure, axes = plt.subplots(rows, columns, figsize=(16, 4 * rows), squeeze=False)
    for axis, path in zip(axes.flat, paths):
        axis.imshow(mpimg.imread(path))
        axis.set_title(Path(path).stem)
        axis.axis("off")
    for axis in axes.flat[len(paths):]:
        axis.axis("off")
    target = out / "visuals" / "contact-sheet.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(target, dpi=120)
    plt.close(figure)
    return str(target)


def _markdown(report):
    lines = ["# Plant generation lab", "", f"Generated: {report['generated_at']}", "",
        "## Summary", "", f"- Overall: **{'PASS' if report['ok'] else 'FAIL'}**",
        f"- Valid scenarios: {report['summary']['valid_passed']}/{report['summary']['valid_total']} passed",
        f"- Adversarial scenarios: {report['summary']['adversarial_passed']}/{report['summary']['adversarial_total']} passed",
        f"- MCP tool-handler scenarios: {report['summary']['mcp_passed']}/{report['summary']['mcp_total']} passed", "",
        f"- Production circulation warnings: {report['summary']['circulation_warnings']} (recorded, non-blocking)",
        f"- Warning codes: {', '.join(f'{key}={count}' for key, count in report['summary']['circulation_warning_codes'].items()) or 'none'}",
        f"- Disconnected rooms: {report['summary']['disconnected_rooms']}", "",
        "### Independent route sensitivity (approximate)", "",
        "| Grid | Estimated cases | Inconclusive | Min width | Max width |",
        "|---:|---:|---:|---:|---:|"]
    for grid, values in report["route_sensitivity_summary"].items():
        minimum = "—" if values["minimum_m"] is None else f"{values['minimum_m']:.3f} m"
        maximum = "—" if values["maximum_m"] is None else f"{values['maximum_m']:.3f} m"
        lines.append(f"| {float(grid):.2f} m | {values['estimated']} | {values['inconclusive']} | {minimum} | {maximum} |")
    lines += ["",
        "## Failures", ""]
    failures = [case for key in ("valid_cases", "adversarial_cases", "mcp_cases")
                for case in report[key] if case["status"] != "passed"]
    if report.get("circulation_comparison") and report["circulation_comparison"]["status"] != "passed":
        failures.append(report["circulation_comparison"])
    if failures:
        for case in failures:
            lines.append(f"- **{case['id']}**: {'; '.join(case.get('errors', []))}")
    else:
        lines.append("None.")
    lines += ["", "## Evidence", "", "DXF files are serialized and reopened with ezdxf before independent geometry evaluation.",
        "Circulation widths are approximate grid estimates and do not establish accessibility or legal compliance.",
        "Room-area checks compare dimension labels because the DXF does not encode closed room polygons.", ""]
    return "\n".join(lines)


def run_lab(output_dir: Path, valid_scenarios=None, adversarial_scenarios=None, mcp_scenarios=None) -> dict:
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    valid_scenarios = VALID_SCENARIOS if valid_scenarios is None else valid_scenarios
    adversarial_scenarios = ADVERSARIAL_SCENARIOS if adversarial_scenarios is None else adversarial_scenarios
    mcp_scenarios = MCP_SCENARIOS if mcp_scenarios is None else mcp_scenarios
    valid = [_build_case(scenario, out) for scenario in valid_scenarios]
    adversarial = _adversarial(adversarial_scenarios, valid, out)
    mcp = _mcp_cases(mcp_scenarios, out)
    circulation = _circulation_comparison(out) if mcp_scenarios is None or len(mcp_scenarios) else None
    contact_sheet = _contact_sheet(valid, out)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "output_dir": str(out),
        "valid_cases": valid, "adversarial_cases": adversarial, "mcp_cases": mcp,
        "circulation_comparison": circulation, "contact_sheet": contact_sheet,
        "limitations": ["Room areas are annotation consistency checks, not measured boundary areas.",
            "Route widths are grid estimates; no legal/accessibility compliance is asserted."]}
    report["summary"] = {
        "valid_total": len(valid), "valid_passed": sum(c["status"] == "passed" for c in valid),
        "adversarial_total": len(adversarial), "adversarial_passed": sum(c["status"] == "passed" for c in adversarial),
        "mcp_total": len(mcp), "mcp_passed": sum(c["status"] == "passed" for c in mcp),
        "valid_failed": sum(c["status"] != "passed" for c in valid),
        "adversarial_failed": sum(c["status"] != "passed" for c in adversarial),
        "mcp_failed": sum(c["status"] != "passed" for c in mcp)}
    report["summary"]["circulation_warnings"] = sum(
        len(case.get("production_circulation", {}).get("avisos", [])) for case in valid)
    report["summary"]["circulation_warning_codes"] = dict(Counter(
        warning.get("chave", "unknown")
        for case in valid
        for warning in case.get("production_circulation", {}).get("avisos", [])))
    report["summary"]["circulation_errors"] = sum(
        len(case.get("production_circulation", {}).get("erros", [])) for case in valid)
    report["summary"]["disconnected_rooms"] = sum(
        sum(not room.get("conectado", False)
            for room in case.get("production_circulation", {}).get("metricas", {}).get("ambientes", []))
        for case in valid)
    report["route_sensitivity_summary"] = {}
    for grid in (0.05, 0.10, 0.15):
        values = [measurement["width_m"]
            for case in valid
            for measurement in case.get("route_sensitivity", {}).get("measurements", [])
            if measurement.get("grid_m") == grid and measurement.get("width_m") is not None]
        inconclusive = sum(1 for case in valid
            for measurement in case.get("route_sensitivity", {}).get("measurements", [])
            if measurement.get("grid_m") == grid and measurement.get("width_m") is None)
        report["route_sensitivity_summary"][f"{grid:.2f}"] = {
            "estimated": len(values), "inconclusive": inconclusive,
            "minimum_m": min(values) if values else None,
            "maximum_m": max(values) if values else None,
        }
    report["ok"] = (report["summary"]["valid_passed"] == len(valid)
                     and report["summary"]["adversarial_passed"] == len(adversarial)
                     and report["summary"]["mcp_passed"] == len(mcp)
                     and (circulation is None or circulation["status"] == "passed"))
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    (out / "report.md").write_text(_markdown(report), encoding="utf-8")
    return report
