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

- [x] Write tests for valid serialized DXF, out-of-lot geometry, missing/shifted door and window geometry, furniture overlap, and requested area label consistency.
- [x] Run the targeted tests RED because the evaluator was missing, then implement it from reopened DXF entities and explicit tolerances.
- [x] Re-run the targeted tests GREEN; intentional mutations report named issue codes.

### Task 2: Scenario corpus and circulation sensitivity

**Files:**
- Create: `tools/plant_lab/scenarios.py`
- Create: `tools/plant_lab/sensitivity.py`
- Create: `cloud/ezdxf/tests/test_plant_lab_scenarios.py`

**Interfaces:**
- `VALID_SCENARIOS` contains at least 30 deterministic supported programs, each with stable `id`, program, and render selection flag.
- `ADVERSARIAL_SCENARIOS` contains at least 20 stable cases split between expected input rejection and controlled DXF corruption.
- `measure_route_widths(doc, scenario, steps=(0.05, 0.10, 0.15)) -> dict` independently measures approximate connectivity/clearance sensitivity from reopened DXF geometry.

- [x] Write count, unique-ID, valid scenario, adversarial rejection/no-mutation, DXF mutation detection, and grid-sensitivity tests.
- [x] Run targeted tests RED before implementing the corpus/evaluator.
- [x] Probe generator and strict preview compatibility; only strict-valid supported programs count as valid. Unsupported suites and other requirements remain adversarial.
- [x] Implement 5/10/15 cm test-only measurements, labelled approximate and separate from the fixed 10 cm production audit.
- [x] Targeted tests pass; the full lab reports 30 valid and 22 adversarial cases.

### Task 3: Runner, reports, and visual inspection artifacts

**Files:**
- Create: `tools/plant_lab/runner.py`
- Create: `tools/run_plant_lab.py`
- Create: `cloud/ezdxf/tests/test_plant_lab_runner.py`

**Interfaces:**
- `run_lab(output_dir: Path) -> dict` returns stable aggregate counts, per-scenario diagnostics, timings, file hashes, and artifact paths.
- CLI writes `report.json`, `report.md`, DXFs for valid scenarios, and selected real-flow PDF/PNG samples/contact sheet beneath `out/plant-lab/`.

- [x] Test report schema, hashes, expected-mutation failures, and a non-zero CLI exit on required failure.
- [x] Confirm the runner import test failed before implementation; later regressions reproduce the width-specific furniture/door collision before the fix.
- [x] Implement isolated sessions, DXF save/reopen/audit, production and independent checks, fidelity labels, and visible per-case failures.
- [x] Render compact layout samples plus the circulation original/proposal comparison and contact sheet.
- [x] Inspect the contact sheet, a 9.2 m plan, and the circulation comparison; fix the width-dependent collision with a regression.
- [x] Full runner passed 30/30 valid, 22/22 adversarial and 2/2 natural-language tool-handler cases, including the 9.2 m regression scenario.

### Task 4: CI and usage documentation

**Files:**
- Modify: `.github/workflows/cloud-regressions.yml`
- Create: `cloud/ezdxf/tests/test_plant_lab_http_smoke.py`
- Modify: `cloud/ezdxf/README.md`

**Interfaces:**
- CI runs the lab CLI after pytest and uploads `out/plant-lab/` with a fixed artifact name and bounded retention.
- MCP/HTTP smoke exercises one supported natural-language request and confirms tool response plus real returned DXF/PDF/PNG validity without relying on a deployed service.

- [x] Add HTTP smoke assertions for initialize/tools/list/tools/call and valid DXF/PDF/PNG downloads with DXF round-trip.
- [x] Exercise public MCP initialization and tool listing plus malformed/unsupported requests in existing isolated coverage.
- [x] Add lab execution/artifact upload while retaining the existing preview artifact.
- [x] Document local invocation, scenarios, outputs and explicit legal/measurement limits.
- [x] Focused HTTP smoke passes; workflow and docs reviewed.

### Task 5: Full regression, review, and PR

**Files:**
- Review all changed files from Tasks 1–4.
- Create a PR against `cloud/ezdxf` after evidence is complete.

- [x] Run the full cloud suite after the final original-integrity regression: 138 passed, one Authlib deprecation warning.
- [x] Run the CLI with natural-language-only tool-handler cases; 29 shared cases across full runs had identical entity hashes, and the same-scenario regression test passes. Inspect the contact sheet, 9.2 m sample and circulation comparison.
- [x] Confirm the original dirty checkout remains on `cloud/ezdxf` with its pre-existing edits/untracked outputs; all work is isolated in `codex/plant-lab-20261029`.
- [x] Fix reproduced generator/layout defects with failing regressions, then rerun the full lab and suite.
- [x] Review changed code, CI, and report outputs for claims, weakened checks, token URLs and nondeterminism. The report has no short-lived download URLs; architectural/legal limits and 59 circulation warnings remain visible.
- [ ] Commit the branch, push it, open a PR against `cloud/ezdxf`, and attach the PR. Do not merge or deploy in this plan.
