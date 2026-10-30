# Residential Architecture Licensing Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the compact two-bedroom generator into a traceable architectural licensing package with configurable municipal profiles and evidence-based requirement results.

**Architecture:** Keep the existing deterministic layout engine intact as the first floor-plan source. Add a separate project-context and requirement-evaluation layer, then extend the architectural model into coordinated sheets and views. Every deliverable is serialized and independently inspected; unresolved rules remain `not_testable` instead of being treated as compliant.

**Tech Stack:** Python, ezdxf, matplotlib, pytest, current FastMCP workflow and CI.

**Spec:** `docs/superpowers/specs/2026-10-29-normative-residential-architecture-design.md`

## Global Constraints

- Initial typology is the existing compact, single-story, two-bedroom detached residence.
- Deliverable stage is architectural documentation for licensing; municipality remains a project configuration and no city-specific approval is claimed.
- Each rule carries its standard edition, status/source/date, applicability, result, evidence and limitations.
- Results are `passou`, `falhou`, `não testável` or `não aplicável`.
- No requirement is marked as passing without a current source and an independently testable criterion.
- Do not copy or redistribute protected normative text.
- No electrical, hydraulic, sanitary, structural, fire, gas, HVAC or landscaping design in this phase.
- No permit, code-compliance or construction-readiness claim is made by the generated files.

## Review Focus

- Missing or stale municipal profile must leave local checks `não testável`; test when no city/profile is supplied.
- Unsupported building/program requests must fail with no partial drawing; test one unsupported second floor and one unsupported room request.
- Vertical data missing from the existing 2D model must not produce fabricated elevations/sections; test missing wall/opening/roof heights.
- A licensing sheet must preserve geometry and dimensions across DXF serialization; test reopened DXF and deliberate sheet mutations.
- Normative catalog status changing after a snapshot must invalidate the source review date; test stale catalog metadata.

---

## File Map

- Create `cloud/ezdxf/mcp_cad_cloud/arquitetura_requisitos.py`: immutable project context, municipal profile, requirement record, applicability and result contracts.
- Create `cloud/ezdxf/mcp_cad_cloud/projeto_arquitetonico.py`: architectural package model and deterministic views derived from the existing compact layout plus explicit vertical inputs.
- Modify `cloud/ezdxf/mcp_cad_cloud/prancha_dxf.py`: multi-sheet composition, title block and view framing while preserving current one-sheet callers.
- Modify `cloud/ezdxf/mcp_cad_cloud/projeto_automatico.py`: optional new package workflow that serializes, reopens, audits and exports each sheet; legacy tool contract remains compatible.
- Create `cloud/ezdxf/mcp_cad_cloud/auditoria_prancha.py`: independent entity-level checks of serialized licensing sheets.
- Modify `cloud/ezdxf/mcp_cad_cloud/tools_verified.py` and `test_mcp_tool_discovery.py`: expose the licensing package as a separate MCP tool.
- Create `cloud/ezdxf/tests/test_arquitetura_requisitos.py`, `test_projeto_arquitetonico.py`, and `test_prancha_licenciamento.py`: requirement behavior, view generation, serialization and adversarial coverage.
- Modify `cloud/ezdxf/tests/test_one_prompt_residence.py` only for backward-compatibility assertions if the shared renderer changes.
- Modify `tools/plant_lab/scenarios.py` and the plant-lab report only after the new package API is stable; keep the original 30/22/2 benchmark measures separate from licensing-package coverage.
- Modify `.github/workflows/cloud-regressions.yml` only when a deterministic licensing-package corpus can run in CI and publish bounded artifacts.

## Task 1 [x]: Establish project and requirement result contracts

**Files:**
- Create: `cloud/ezdxf/mcp_cad_cloud/arquitetura_requisitos.py`
- Test: `cloud/ezdxf/tests/test_arquitetura_requisitos.py`

**Interfaces:**
- `ProjectContext`: typed fields for project name, use, typology, municipality, state, storeys, lot dimensions, requested rooms, stage and source-profile revision.
- `RequirementRecord`: stable ID, standard designation/edition, catalog status URL, checked date, applicability description, evaluator ID, evidence expectations and limitations.
- `RequirementResult`: requirement ID, status enum (`passou`, `falhou`, `não testável`, `não aplicável`), reason, evidence references and review metadata.
- `evaluate_applicability(project: ProjectContext, requirement: RequirementRecord) -> RequirementResult`: missing context yields `não testável`; a false applicability predicate yields `não aplicável`; only a registered evaluator with current source metadata may yield `passou`/`falhou`.
- Municipal profile JSON schema is versioned and requires city/UF, source URL, retrieval date, profile revision and a reviewer field; unreviewed parameters cannot pass.

- [ ] **Step 1: Write failing tests** for all four statuses, missing city, missing standard edition/source, stale catalog review, and unreviewed municipal profile.
- [ ] **Step 2: Run the new tests** with `PYTHONPATH=cloud/ezdxf; python -m pytest cloud/ezdxf/tests/test_arquitetura_requisitos.py -q`; confirm behavior fails because the module/contracts do not exist.
- [ ] **Step 3: Implement the minimal enums and immutable dataclasses** in `arquitetura_requisitos.py`; do not add detailed NBR criteria in this task.
- [ ] **Step 4: Run targeted and existing contract tests**; all statuses must remain distinguishable and missing/stale data must fail closed.
- [ ] **Step 5: Commit** as `feat(cad): add traceable architecture requirement contracts`.

## Task 2 [x]: Add a parametric architectural package model

**Files:**
- Create: `cloud/ezdxf/mcp_cad_cloud/projeto_arquitetonico.py`
- Test: `cloud/ezdxf/tests/test_projeto_arquitetonico.py`
- Read: `cloud/ezdxf/mcp_cad_cloud/planta_gerador.py`, `planta_layout_compacto.py`, `validar_modelo.py`

**Interfaces:**
- `BuildingEnvelope`: explicit floor, ceiling, wall-top, sill, head, parapet and roof pitch/eave inputs in meters.
- `ArchitecturePackage`: source plan, project context, generated sheets/views and requirement results.
- `generate_architecture_package(model: dict, context: ProjectContext, envelope: BuildingEnvelope) -> ArchitecturePackage`: unsupported/missing envelope data raises a typed error before drawing creation.
- First views: dimensioned floor plan from the existing compact model, site/implantation view from explicit lot/recuos, roof plan from explicit roof geometry, and two orthogonal sections plus facades from the vertical envelope.

- [ ] **Step 1: Write failing tests** for valid package creation, missing heights, contradictory openings, unsupported storeys, mismatched lot/context and stable geometry across repeat runs.
- [ ] **Step 2: Run targeted tests** and verify expected failures are assertion failures for missing interfaces.
- [ ] **Step 3: Implement package validation and view geometry** in `projeto_arquitetonico.py`; leave the existing floor-plan engine behavior unchanged.
- [ ] **Step 4: Verify** every generated view has declared units, coordinate bounds, source entity IDs and no unsignaled default height/roof assumptions.
- [ ] **Step 5: Commit** as `feat(cad): model licensing views for compact residences`.

## Task 3 [x]: Compose licensing sheets and an editable title block

**Files:**
- Modify: `cloud/ezdxf/mcp_cad_cloud/prancha_dxf.py`
- Test: `cloud/ezdxf/tests/test_prancha_licenciamento.py`

**Interfaces:**
- `SheetSpec`: paper format, orientation, scale, margins, sheet ID and ordered viewports.
- `ViewportSpec`: view ID and paper position/size in millimeters.
- `TitleBlockData`: project, municipality, owner, designer/registration as user-supplied values, content, sheet number, scale, issue date and revision.
- `SheetDrawing`: sheet ID, `SheetSpec`, title-block rows and actual ezdxf document.
- `compose_licensing_sheets(package: ArchitecturePackage, sheets: list[SheetSpec], title_block: TitleBlockData) -> list[SheetDrawing]`: missing identity fields remain visibly pending; it never invents professional names, license numbers or signatures.
- `renderizar_folha(sheet: SheetDrawing) -> tuple[bytes, bytes]`: one PDF page and PNG rendered from the composed/reopened DXF document.

- [ ] **Step 1: Write failing tests** for required labels, blank author identity, duplicate sheet IDs, clipping/overlap, scale metadata and multi-sheet DXF output.
- [ ] **Step 2: Run targeted tests** and confirm the renderer lacks multi-sheet/title-block support.
- [ ] **Step 3: Add modular sheet composition** to `prancha_dxf.py` without changing the current A3 legacy renderer's output contract.
- [ ] **Step 4: Reopen each DXF and render PDF/PNG**; assert extents, sheet IDs, expected title-block text and page count.
- [ ] **Step 5: Inspect visual samples** for plan, section, facade and implantation at actual print scale.
- [ ] **Step 6: Commit** as `feat(cad): compose architectural licensing sheets`.

## Task 4 [x]: Connect requirement evaluation and fail-closed exports

**Files:**
- Create: `cloud/ezdxf/mcp_cad_cloud/auditoria_prancha.py`
- Modify: `cloud/ezdxf/mcp_cad_cloud/projeto_automatico.py`
- Modify: `cloud/ezdxf/mcp_cad_cloud/tools_verified.py`
- Test: `cloud/ezdxf/tests/test_auditoria_prancha.py`
- Test: `cloud/ezdxf/tests/test_prancha_licenciamento.py`
- Test: `cloud/ezdxf/tests/test_mcp_tool_discovery.py`

**Interfaces:**
- `audit_sheet_document(doc, spec: SheetSpec) -> dict` independently checks units, sheet/frame extents, required title fields, source XDATA and entity bounds against a reopened DXF.
- `evaluate_package(package: ArchitecturePackage, requirements, applicability_rules, evaluators) -> list[RequirementResult]` uses only evaluator IDs present in the reviewed registry.
- `export_licensing_package(programa, contexto, envelope, folhas, carimbo, requirements, applicability_rules, evaluators) -> dict` serializes/reopens every sheet, returns a ZIP containing per-sheet DXF/PDF/PNG plus JSON/Markdown report, and fails before publishing downloads on geometry/audit failures.
- Public tool `projetar_pacote_licenciamento(...)` is separate from the existing `projetar_residencia(...)` contract; direct PDF/PNG links show sheet 1 while the ZIP carries every sheet.
- `licensing_readiness` is `blocked`, `review_required` or `ready_for_professional_review`; it never uses `approved`, `compliant` or equivalent.

- [ ] **Step 1: Write failing tests** showing that one failed applicable rule blocks readiness, while missing/stale/unsupported rules stay `não testável` and cannot be counted as passed.
- [ ] **Step 2: Verify RED** on the targeted new tests.
- [ ] **Step 3: Implement independent serialized-sheet auditing**, then package evaluation, per-sheet DXF/PDF/PNG ZIP, report assembly and short-lived downloads; retain the legacy `projetar_residencia` response fields.
- [ ] **Step 4: Test positive and adversarial DXF edits** (remove dimension, mutate sheet ID, move viewport outside sheet) against the reopened document.
- [ ] **Step 5: Expose the new high-level tool** and test direct discovery/call plus existing one-prompt and HTTP download regressions for API compatibility.
- [ ] **Step 6: Commit** as `feat(cad): audit licensing package evidence`.

## Task 5 [x]: Register verified normative sources and municipal profile inputs

**Files:**
- Create: `cloud/ezdxf/mcp_cad_cloud/normas_arquitetura.json`
- Create: `cloud/ezdxf/tests/test_normas_arquitetura.py`
- Modify: `cloud/ezdxf/README.md`

- [ ] **Step 1: Confirm each candidate standard's current designation, edition and status** directly in the ABNT catalog; store only bibliographic metadata, permitted links and review date, not copied standard text.
- [ ] **Step 2: Add contract tests** that reject missing editions, invalid status dates, duplicate IDs, stale reviews and municipal data without official-source metadata.
- [ ] **Step 3: Add only requirements whose source text has been lawfully reviewed** and whose criterion can be stated and independently tested. Otherwise register the item as `não testável` with a clear reason.
- [ ] **Step 4: Document** how to configure a municipality profile and how to report uncovered local rules; do not ship a profile that implies validation for an unselected city.
- [ ] **Step 5: Commit** as `feat(cad): register reviewed architectural standards`.

## Task 6 [x]: Build the licensing scenario corpus and CI evidence

**Files:**
- Create: `cloud/ezdxf/tests/test_licensing_package_corpus.py`
- Modify: `.github/workflows/cloud-regressions.yml`
- Modify: `tools/plant_lab/runner.py` only if the package corpus can reuse its artifact/report contract without conflating coverage.

- [ ] **Step 1: Define deterministic cases** for lot widths/depths, setbacks, orientation, two-bedroom supported programs, entry/room openings, vertical envelopes and missing-context adversarial inputs.
- [ ] **Step 2: Add failing acceptance assertions** for unsupported requirements remaining `não testável`, invalid geometries failing before export, and all valid outputs reopening cleanly.
- [ ] **Step 3: Implement the smallest corpus runner** with per-case IDs, status counts, warning-code distribution, report JSON/Markdown and sample PDF/PNG contact sheet.
- [ ] **Step 4: Run targeted corpus, full cloud tests and `git diff --check`**; record all warning and inconclusive cases.
- [ ] **Step 5: Add CI artifact upload** for reports and visual samples with a 30-day retention, without external deployment or protected credentials.
- [ ] **Step 6: Commit** as `test(cad): add licensing package regression corpus`.

## Verification and release gate

- Each implementation task uses TDD: the named test fails for the intended missing behavior before production code is added.
- After Task 6, run `PYTHONPATH=cloud/ezdxf; MCP_CAD_PROFILE=full; python -m pytest cloud/ezdxf/tests -q` and the licensing corpus.
- Open all representative PDF/PNG sheets and inspect at actual sheet scale; verify DXFs by `ezdxf.readfile()` plus independent entity-level checks.
- Review branch diff, report failures/warnings and CI artifacts; keep PR open for user review.
- Merge/deploy is outside this plan unless separately authorized after all gates pass.


## Implementation outcome (2026-10-29)

- Tasks 1–4 implemented: traceable requirement contracts, licensing views/sheets, reopened-DXF audit, fail-closed ZIP export, HTTP/MCP exposure, and four default A3 sheets covering nine views.
- Task 5 registers nine candidate requirement records. Only the NBR 9050 catalog ficha is confirmed “Em Vigor”; no criteria were copied or implemented, and all nine results remain `não testável`. Municipal profile remains unset/configurable.
- Task 6 adds 30 accepted variants and 10 adversarial package cases, real ezdxf reopen/audits, independent geometry checks, visual samples/contact sheet, warning counts, and a 30-day CI artifact. The original plant corpus remains 30 valid/22 adversarial/2 tool-handler cases.
- Root causes found and fixed: the social-zone checker rejected the compact layout’s 0.475 m open floor strip without testing its actual obstacles; the kitchen counter left only 0.20 m beside the laundry-door approach. The counter was shifted inward, and the checker now validates the real sample path up to its explicit geometric pilot tolerance.
- The circulation comparator now correctly returns no proposal when the baseline is already clear. The plant-lab report treats that evidenced no-op as success and preserves the original PNG.
- Follow-up visual defect: the floor-plan view showed each wall centerline as one stroke. It now derives two parallel wall faces at the model thickness and transverse end/jamb lines; the reopened-sheet audit detects if either face is removed. The regenerated 30+10 licensing corpus passed, and the representative plan was visually inspected.
- Final full-suite/corpus runs and CI state are recorded in the PR review; no merge or deployment is authorized by this plan.
