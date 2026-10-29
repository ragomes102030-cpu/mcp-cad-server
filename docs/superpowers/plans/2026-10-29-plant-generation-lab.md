# Plant Generation Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic 30-valid/20-adversarial plant generation laboratory with independent DXF checks, circulation sensitivity, reviewable visual artifacts, reports, and CI coverage.

**Architecture:** Keep scenario data, independent evaluation, and artifact/report generation in repository tooling and tests, outside the production MCP package. Generate and reopen real DXF files with `ezdxf`, use existing production auditors as separate evidence, and run targeted MCP/HTTP smoke coverage; CI uploads the lab report and visual samples.

**Tech Stack:** Python 3.10+, pytest, ezdxf, matplotlib, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-29-plant-generation-lab-design.md`

## Global Constraints

- At least 30 supported valid programs and 20 adversarial scenarios, with structured programs and natural-language MCP coverage reported separately.
- Production circulation uses a fixed 10 cm grid; 5/10/15 cm sensitivity measurements are independent test indicators.
- No legal or normative compliance claims; no subjective architectural score.
- No new production dependency; do not hide, downgrade, or silently accept failures.
- Work from production base `c77e87a1f8e2dea5710ac4010eb9de64fffd391a` on `codex/plant-lab-20261029`.

## Review Focus

- Near-limit plot dimensions and setbacks: confirm all accepted geometries fit the actual reopened plot. Test in scenario matrix and independent evaluator.
- Rounded areas and tolerance boundaries: compare requested areas with dimension labels in the reopened DXF using an explicit tolerance, and state that the file has no closed per-room polygons for direct physical area measurement. Test in evaluator and valid cases.
- Unsupported, duplicate, and non-finite program values: reject without mutating state or generating partial artifacts. Test in adversarial cases.
- Doors/windows/furniture tampering and false room connectivity: evaluator must detect removed/shifted openings, collisions, and window-as-route mutations. Test through controlled DXF mutations.
- Shared backend state and repeated runs: each scenario must reset/isolate drawings so order does not change results. Test deterministic full runner twice.

---

### Task 1: Independent DXF evaluator

**Files:**
- Create: `tools/plant_lab/independent_geometry.py`
- Create: `cloud/ezdxf/tests/test_plant_lab_geometry.py`

**Interfaces:**
- Produces `evaluate_reopened_dxf(doc, scenario) -> list[dict]`, where each issue has `code`, `severity`, and `detail`.
- Uses DXF entities and scenario requirements; does not use model summaries or production geometry auditors to compute its own checks.

- [ ] Write tests for valid serialized DXF, out-of-lot geometry, missing/shifted door and window geometry, furniture/room overlap, and measured-vs-requested room areas.
- [ ] Run `python -m pytest cloud/ezdxf/tests/test_plant_lab_geometry.py -q`; confirm tests fail because the evaluator is missing.
- [ ] Implement the independent evaluator using geometry derived from the reopened DXF entities and explicit tolerances.
- [ ] Re-run the targeted tests and confirm they pass; record issue codes for each intentional mutation.

### Task 2: Scenario corpus and circulation sensitivity

**Files:**
- Create: `tools/plant_lab/scenarios.py`
- Create: `tools/plant_lab/sensitivity.py`
- Create: `cloud/ezdxf/tests/test_plant_lab_scenarios.py`

**Interfaces:**
- `VALID_SCENARIOS` contains at least 30 deterministic supported programs, each with stable `id`, program, and render selection flag.
- `ADVERSARIAL_SCENARIOS` contains at least 20 stable cases split between expected input rejection and controlled DXF corruption.
- `measure_route_widths(doc, scenario, steps=(0.05, 0.10, 0.15)) -> dict` independently measures approximate connectivity/clearance sensitivity from reopened DXF geometry.

- [ ] Write count, unique-ID, deterministic-seed, valid scenario, adversarial rejection/no-mutation, DXF mutation detection, and grid-sensitivity tests.
- [ ] Run the targeted test file and confirm expected failures expose missing corpus/evaluator behavior.
- [ ] Implement supported program variants only after probing generator compatibility; classify unsupported briefs as adversarial instead of counting them as valid.
- [ ] Implement test-only multi-grid measurements and label all results approximate, separate from the fixed 10 cm production auditor.
- [ ] Re-run targeted tests and ensure all valid IDs generate and all adversarial cases produce their expected classification.

### Task 3: Runner, reports, and visual inspection artifacts

**Files:**
- Create: `tools/plant_lab/runner.py`
- Create: `tools/run_plant_lab.py`
- Create: `cloud/ezdxf/tests/test_plant_lab_runner.py`

**Interfaces:**
- `run_lab(output_dir: Path) -> dict` returns stable aggregate counts, per-scenario diagnostics, timings, file hashes, and artifact paths.
- CLI writes `report.json`, `report.md`, DXFs for valid scenarios, and selected real-flow PDF/PNG samples/contact sheet beneath `out/plant-lab/`.

- [ ] Test report schema, deterministic scenario classification, hashes, and that required failures return a non-zero CLI exit.
- [ ] Confirm tests fail before runner/report implementation.
- [ ] Implement isolation/reset, DXF write/read with `ezdxf.readfile`, `ezdxf.audit()`, production audit reporting, independent audit, fidelity checks, and per-scenario error capture.
- [ ] Render documented representative cases for each supported layout family plus original/proposal circulation comparison; assemble contact sheet.
- [ ] Run the runner locally, inspect the resulting contact sheet and selected PNG/PDF, and correct concrete rendering/generation defects with regression tests.
- [ ] Re-run runner tests and verify report totals match the corpus, with no discarded failures.

### Task 4: CI and usage documentation

**Files:**
- Modify: `.github/workflows/cloud-regressions.yml`
- Create: `cloud/ezdxf/tests/test_plant_lab_http_smoke.py`
- Modify: `cloud/ezdxf/README.md`

**Interfaces:**
- CI runs the lab CLI after pytest and uploads `out/plant-lab/` with a fixed artifact name and bounded retention.
- MCP/HTTP smoke exercises one supported natural-language request and confirms tool response plus real returned DXF/PDF/PNG validity without relying on a deployed service.

- [ ] Add HTTP smoke assertions for supported call, invalid request handling, and download signatures/round-trip DXF.
- [ ] Confirm the new smoke test fails for any absent/malformed contract before changing workflow/docs.
- [ ] Add lab execution and upload steps to existing workflow; keep existing preview artifact behavior intact.
- [ ] Document local invocation, scenario categories, output files, and explicit non-legal limitations.
- [ ] Run focused smoke and workflow configuration checks.

### Task 5: Full regression, review, and PR

**Files:**
- Review all changed files from Tasks 1–4.
- Create a PR against `cloud/ezdxf` after evidence is complete.

- [ ] Run the full existing cloud suite plus lab suite from repository root with `PYTHONPATH=cloud/ezdxf` and `MCP_CAD_PROFILE=full`.
- [ ] Run the CLI twice and compare stable report fields/hashes; inspect all visual samples.
- [ ] Confirm the original checkout's dirty files remain untouched and the worktree diff contains only scoped lab/product fixes.
- [ ] Fix any concrete defect only with a failing regression first; repeat affected checks and the full suite.
- [ ] Review changed files for unsupported quality/legal claims, accidental weakening of checks, artifacts containing secrets, and flaky nondeterminism.
- [ ] Commit the branch, push it, open a PR against `cloud/ezdxf`, and attach the PR. Do not merge or deploy in this plan.
