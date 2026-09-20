# Layer E Release Decoupling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make theme release verdicts depend on Layers A–D while retaining agent compatibility as a separately validated, instruction-bound project status.

**Architecture:** `release.py` becomes strictly theme/package focused and tolerates historical Layer E evidence without counting it. A new `agent_compatibility.py` module validates shared runtime smoke and evaluation evidence once per instruction revision, and a small CLI renders the standalone report. Existing evidence is retained unchanged.

**Tech Stack:** Python 3 standard library, `unittest`, JSON Schema validation already present in `lib/theme_factory`, Bash wrappers, Markdown generated sections.

**Spec:** `docs/superpowers/specs/2026-09-20-release-gates-and-theme-uniqueness-design.md`

## Global Constraints

- APEX remains 26.1.x, Universal Theme 42, Iris only.
- Theme release layers are exactly A, B, C, and D.
- Agent compatibility is `PASS`, `FAIL`, or `UNVERIFIED` and never changes a theme verdict.
- Historical Layer E evidence must remain readable and must not be deleted or rewritten.
- Scenario 11 product coverage moves to Layer D/package tests; its evaluation history remains intact.
- No import, Chrome session, external agent run, or destructive evidence cleanup is part of this implementation plan.

## Review Focus

- A legacy manifest containing Layer E `FAIL` must still yield `VERIFIED` when A–D pass; Task 1 pins this.
- A missing D check must remain `UNVERIFIED` even when legacy E passes; Task 1 pins this.
- Instruction changes must invalidate standalone agent compatibility without invalidating theme evidence; Task 3 pins this.
- Unavailable agent CLIs must report `UNVERIFIED`, not `FAIL` and not affect catalog themes; Task 4 pins this.
- Existing nested per-theme evidence directories must still load without migration; Task 2 pins this.

---

### Task 1: Define the A–D release contract

**Files:**
- Modify: `tests/test_release_report.py`
- Modify: `lib/theme_factory/release.py`

**Interfaces:**
- Consumes: existing `release_verdict(layers: dict[str, str]) -> str`.
- Produces: `THEME_RELEASE_LAYERS: tuple[str, ...] = ("A", "B", "C", "D")`; `THEME_EVIDENCE_CHECKS: dict[str, str]`; unchanged `release_verdict` signature with A–D semantics.

- [ ] **Step 1: Add failing verdict tests**

Add these cases to `tests/test_release_report.py`:

```python
def test_release_verdict_requires_only_a_through_d(self):
    self.assertEqual(
        release_verdict({name: "PASS" for name in "ABCD"}),
        "VERIFIED",
    )

def test_legacy_layer_e_failure_does_not_change_theme_verdict(self):
    layers = {name: "PASS" for name in "ABCD"}
    layers["E"] = "FAIL"
    self.assertEqual(release_verdict(layers), "VERIFIED")

def test_missing_layer_d_is_unverified_even_when_legacy_e_passes(self):
    self.assertEqual(
        release_verdict({"A": "PASS", "B": "PASS", "C": "PASS", "E": "PASS"}),
        "UNVERIFIED",
    )
```

- [ ] **Step 2: Run the focused tests and confirm the old contract fails**

Run: `python3 -m unittest tests.test_release_report.ReleaseVerdictTests -v`

Expected: the first two tests fail because `release_verdict` currently requires E; the third passes.

- [ ] **Step 3: Implement the explicit A–D constants**

In `lib/theme_factory/release.py`, replace the mixed layer constants with:

```python
THEME_RELEASE_LAYERS = ("A", "B", "C", "D")
THEME_LAYER_DESCRIPTIONS = {
    "A": "Repository source",
    "B": "Package artifact",
    "C": "Database installation",
    "D": "Browser runtime",
}
LEGACY_EVIDENCE_LAYERS = {"E"}
THEME_EVIDENCE_CHECKS = {
    "C": "database_installation",
    "D": "browser_runtime_matrix",
}
```

Implement `release_verdict` by iterating `THEME_RELEASE_LAYERS`. Keep its precedence: any required `FAIL` returns `FAIL`; a missing or non-`PASS` required layer returns `UNVERIFIED`; otherwise return `VERIFIED`.

- [ ] **Step 4: Run the focused test module**

Run: `python3 -m unittest tests.test_release_report -v`

Expected: verdict tests pass; tests that explicitly expect a current Layer E report may still fail and will be migrated in later tasks.

- [ ] **Step 5: Commit the contract change**

```bash
git add lib/theme_factory/release.py tests/test_release_report.py
git commit -m "refactor: define theme release as layers a through d"
```

### Task 2: Preserve legacy Layer E evidence without counting it

**Files:**
- Modify: `lib/theme_factory/release.py`
- Modify: `tests/test_release_report.py`
- Test fixture: `.agents/evaluations/runtime/2026-09-17-release-linen/evidence.json`

**Interfaces:**
- Consumes: `load_evidence(evidence_dir, theme_name, expected_git_commit=None, expected_package_sha256=None) -> list[dict[str, Any]]`.
- Produces: the same return type; current A–D checks are validated, legacy E checks are returned with `legacy: True` but are not required.

- [ ] **Step 1: Add legacy compatibility tests**

Add tests that copy a schema-version-1 evidence manifest into a temporary directory and assert:

```python
items = load_evidence(temp_root, "linen")
legacy = [item for item in items if item["layer"] == "E"]
self.assertEqual(len(legacy), 1)
self.assertTrue(legacy[0]["legacy"])
self.assertFalse(any(
    item["layer"] == "E" and item["path"] == "missing"
    for item in items
))
```

Add a second fixture with only C and D checks and assert `load_evidence` does not synthesize a missing E check.

- [ ] **Step 2: Run the tests and confirm the missing-E assertion fails**

Run: `python3 -m unittest tests.test_release_report -v`

Expected: FAIL because `REQUIRED_EVIDENCE_CHECKS` currently synthesizes `agent_behavior_matrix`.

- [ ] **Step 3: Make evidence parsing backward compatible**

In `load_evidence`:

- accept layers in `THEME_LAYER_DESCRIPTIONS` or `LEGACY_EVIDENCE_LAYERS`;
- validate PASS/FAIL A–D artifacts through `_validate_evidence_artifact`;
- continue validating legacy E artifacts through the existing E branch during this task; Task 3 moves that branch without changing its accepted historical shape;
- add `legacy: layer in LEGACY_EVIDENCE_LAYERS` to each returned item;
- synthesize missing checks only from `THEME_EVIDENCE_CHECKS`.

Do not change artifact bytes or move evidence directories.

- [ ] **Step 4: Run release and catalog tests**

Run: `python3 -m unittest tests.test_release_report tests.test_theme_catalog -v`

Expected: PASS except for catalog column expectations intentionally addressed in Task 5.

- [ ] **Step 5: Commit legacy parsing support**

```bash
git add lib/theme_factory/release.py tests/test_release_report.py
git commit -m "fix: tolerate historical layer e release evidence"
```

### Task 3: Extract standalone agent compatibility validation

**Files:**
- Create: `lib/theme_factory/agent_compatibility.py`
- Create: `tests/test_agent_compatibility.py`
- Modify: `lib/theme_factory/release.py`
- Modify: `tests/test_gitstate.py`

**Interfaces:**
- Consumes: `instruction_equivalent(left: str, right: str, cwd: Path | None = None) -> bool`, `validate_evidence_schema`, and existing raw agent artifacts.
- Produces:
  - `AgentCompatibilityResult(status: str, instruction_commit: str | None, runtimes: tuple[str, ...], scenarios: tuple[str, ...], failures: tuple[str, ...], evidence_path: Path | None)`.
  - `validate_agent_behavior_artifact(path: Path, evidence_dir: Path, expected_instruction_commit: str | None) -> AgentCompatibilityResult`.
  - `latest_agent_compatibility(evidence_root: Path, expected_instruction_commit: str | None) -> AgentCompatibilityResult`.

- [ ] **Step 1: Write fixture-driven tests for the new API**

Create `tests/test_agent_compatibility.py` with a helper
`write_fixture(*, runtimes=("codex", "claude", "antigravity"), runtime_statuses=None, scenarios=("04", "05", "09", "14"), instruction_commit="a" * 40, include_package_sha=False) -> Path`. The helper writes one raw JSON file per runtime/scenario, computes each SHA-256, writes the aggregate artifact, and returns its path. Use it in these tests:

```python
def test_pass_requires_all_supported_runtimes(self):
    path = self.write_fixture()
    result = validate_agent_behavior_artifact(path, path.parent, "a" * 40)
    self.assertEqual(result.status, "PASS")
    self.assertEqual(result.runtimes, ("antigravity", "claude", "codex"))

def test_environmental_unavailability_is_unverified(self):
    path = self.write_fixture(runtime_statuses={"antigravity": "UNVERIFIED"})
    result = validate_agent_behavior_artifact(path, path.parent, "a" * 40)
    self.assertEqual(result.status, "UNVERIFIED")

def test_instruction_change_invalidates_evidence(self):
    path = self.write_fixture(instruction_commit="a" * 40)
    result = validate_agent_behavior_artifact(path, path.parent, "b" * 40)
    self.assertEqual(result.status, "UNVERIFIED")

def test_theme_package_sha_is_not_part_of_agent_identity(self):
    path = self.write_fixture(include_package_sha=False)
    self.assertNotIn("packageSha256", json.loads(path.read_text()))
    self.assertEqual(
        validate_agent_behavior_artifact(path, path.parent, "a" * 40).status,
        "PASS",
    )

def test_scenario_11_is_not_required_by_project_compatibility(self):
    path = self.write_fixture(scenarios=("04", "05", "09", "14"))
    result = validate_agent_behavior_artifact(path, path.parent, "a" * 40)
    self.assertEqual(result.scenarios, ("04", "05", "09", "14"))
    self.assertEqual(result.status, "PASS")
```

The valid fixture must reference raw runtime records for exactly `codex`, `claude`, and `antigravity`, scenarios `04`, `05`, `09`, and `14`, and zero pending findings.

- [ ] **Step 2: Run the new tests and confirm import failure**

Run: `python3 -m unittest tests.test_agent_compatibility -v`

Expected: FAIL because `lib.theme_factory.agent_compatibility` does not exist.

- [ ] **Step 3: Implement the compatibility module**

Move the E-specific artifact validation out of `_validate_evidence_artifact`. Validate:

- schema version and `evidenceType: "agent-compatibility"`;
- a 40-character `instructionCommit`;
- `instruction_equivalent(expected, actual)`;
- exactly the three supported runtime names;
- scenarios `04`, `05`, `09`, and `14`, each with digest-bound raw evidence;
- `pendingFindings == 0` for `PASS`;
- runtime environmental `UNVERIFIED` propagates to aggregate `UNVERIFIED`;
- a well-formed behavioral mismatch returns `FAIL`; malformed schema, path traversal, or digest mismatch raises `PackageError`.

Keep a compatibility adapter named `validate_legacy_layer_e_artifact(...)` that reads the old theme-bound shape, ignores its package binding for the standalone result, and permits scenario 11 as extra historical evidence.

- [ ] **Step 4: Remove E-only imports and comments from `release.py`**

`release.py` must no longer import `instruction_equivalent`. Its legacy E branch calls `validate_legacy_layer_e_artifact` and marks the returned check legacy; A–D binding continues to use `source_equivalent` and package SHA-256.

- [ ] **Step 5: Update git-state tests**

Move assertions about instruction-bound invalidation from `tests/test_gitstate.py` to `tests/test_agent_compatibility.py`. Retain `instruction_equivalent` unit tests in `tests/test_gitstate.py`; remove comments that claim `release.py` is the direct consumer.

- [ ] **Step 6: Run focused validation**

Run: `python3 -m unittest tests.test_agent_compatibility tests.test_gitstate tests.test_release_report -v`

Expected: PASS.

- [ ] **Step 7: Commit the extraction**

```bash
git add lib/theme_factory/agent_compatibility.py lib/theme_factory/release.py tests/test_agent_compatibility.py tests/test_gitstate.py tests/test_release_report.py
git commit -m "feat: report agent compatibility independently"
```

### Task 4: Add a standalone compatibility command and report

**Files:**
- Create: `tools/agent_compatibility_report.py`
- Create: `scripts/agent-compatibility-check.sh`
- Modify: `docs/AGENT_COMPATIBILITY.md`
- Create: `tests/test_agent_compatibility_cli.py`
- Modify: `tests/run-offline.sh`

**Interfaces:**
- Consumes: `latest_agent_compatibility(...)` from Task 3.
- Produces: CLI exit `0` for PASS, `1` for FAIL, `2` for UNVERIFIED; `--check` verifies the generated section without writing.

- [ ] **Step 1: Write CLI tests**

Create subprocess tests that invoke the tool with a temporary evidence root and documentation file. Assert:

- PASS renders a single row per runtime and exits `0`;
- a missing runtime renders `UNVERIFIED` and exits `2`;
- a behavioral failure exits `1`;
- `--check` reports drift and does not modify the file;
- no theme name or package SHA is required.
- `--migrate-legacy PATH --output PATH` writes a standalone artifact containing runtimes and scenarios 04/05/09/14 while omitting the old theme, package SHA, and scenario 11 fields.

- [ ] **Step 2: Run the CLI tests and confirm failure**

Run: `python3 -m unittest tests.test_agent_compatibility_cli -v`

Expected: FAIL because the CLI and wrapper do not exist.

- [ ] **Step 3: Implement the CLI and wrapper**

The Python command accepts validation/report arguments:

```text
--evidence-root PATH
--documentation PATH
--expected-instruction-commit SHA
--check
```

It also accepts a mutually exclusive migration mode:

```text
--migrate-legacy PATH
--output PATH
```

Migration reads one existing `agent_behavior_matrix.json`, verifies its digest-bound raw references first, copies the referenced runtime and scenario 04/05/09/14 JSON bytes into a self-contained `raw/` directory, and writes a new `evidenceType: "agent-compatibility"` artifact under `.agents/evaluations/agent-compatibility/<date>/compatibility.json`. It omits scenario 11 and removes theme/package identity. It never edits the source artifact or its raw files.

The Bash wrapper resolves the repository root and executes the module without starting any agent runtime. It validates existing evidence only.

Use generated markers `<!-- @generated:agent-compatibility:start -->` and `<!-- @generated:agent-compatibility:end -->` in `docs/AGENT_COMPATIBILITY.md` so explanatory prose remains handwritten.

- [ ] **Step 4: Document trigger semantics**

State explicitly that model-backed smokes run only after changes to `AGENTS.md`, `.agents/rules/**`, `.agents/skills/**`, on a scheduled compatibility run, or by explicit maintainer request. Theme CSS, package, font, and preview changes do not trigger them.

- [ ] **Step 5: Migrate one historical artifact into the standalone store**

Run:

```bash
python3 tools/agent_compatibility_report.py \
  --migrate-legacy .agents/evaluations/runtime/2026-09-17-release-linen/agent_behavior_matrix.json \
  --output .agents/evaluations/agent-compatibility/2026-09-17/compatibility.json
```

Expected: the new artifact validates against its copied, byte-identical raw evidence, omits package/theme identity and scenario 11, leaves the historical source tree unchanged, and reports `UNVERIFIED` rather than falsely `PASS` if the current instruction surface has changed.

- [ ] **Step 6: Register read-only validation in the offline suite**

Add `scripts/agent-compatibility-check.sh --check` to `tests/run-offline.sh`. The offline suite must accept exit `2` as a documented `UNVERIFIED` compatibility signal and fail only on malformed evidence or generated-document drift; it must not claim external runtimes passed.

- [ ] **Step 7: Run the tests**

Run: `python3 -m unittest tests.test_agent_compatibility tests.test_agent_compatibility_cli -v && scripts/check-agent-layout.sh`

Expected: all unit tests PASS and layout output ends with `status=PASS`.

- [ ] **Step 8: Commit the standalone command**

```bash
git add tools/agent_compatibility_report.py scripts/agent-compatibility-check.sh docs/AGENT_COMPATIBILITY.md tests/test_agent_compatibility_cli.py tests/run-offline.sh .agents/evaluations/agent-compatibility
git commit -m "feat: add standalone agent compatibility report"
```

### Task 5: Remove Layer E from theme catalog and release reports

**Files:**
- Modify: `lib/theme_factory/catalog.py`
- Modify: `lib/theme_factory/release.py`
- Modify: `tests/test_theme_catalog.py`
- Modify: `tests/test_release_report.py`
- Modify: `tests/live/RELEASE-MATRIX.md`

**Interfaces:**
- Consumes: `THEME_RELEASE_LAYERS` from Task 1.
- Produces: A–D-only Markdown tables and missing-layer explanations.

- [ ] **Step 1: Add exact rendering tests**

Assert the release header is:

```text
| Theme | A | B | C | D | Verdict |
```

Assert a catalog entry with A–C pass and D unverified reports `layers not current: D`, and a legacy E failure is absent from the reason.

- [ ] **Step 2: Run catalog/report tests and confirm failure**

Run: `python3 -m unittest tests.test_theme_catalog tests.test_release_report -v`

Expected: FAIL on the existing E column and `"ABCDE"` missing-layer scan.

- [ ] **Step 3: Render from `THEME_RELEASE_LAYERS`**

Replace hard-coded layer strings in `catalog.py` and report rendering with `THEME_RELEASE_LAYERS`. Do not duplicate `("A", "B", "C", "D")` in renderers.

Update the generated block in `tests/live/RELEASE-MATRIX.md`; retain historical prose outside the generated block, but label any old A–E tables as historical evidence.

- [ ] **Step 4: Run focused tests and generated checks**

Run: `python3 -m unittest tests.test_theme_catalog tests.test_release_report -v && scripts/theme.sh catalog --check`

Expected: PASS and no catalog drift.

- [ ] **Step 5: Commit report changes**

```bash
git add lib/theme_factory/catalog.py lib/theme_factory/release.py tests/test_theme_catalog.py tests/test_release_report.py tests/live/RELEASE-MATRIX.md
git commit -m "docs: render theme releases with layers a through d"
```

### Task 6: Update release orchestration and public documentation

**Files:**
- Modify: `scripts/release-check.sh`
- Modify: `tools/release_batch.py`
- Modify: `tests/test_release_batch.py`
- Modify: `README.md`
- Modify: `docs/PROJECT.md`
- Modify: `docs/THEME_FACTORY_IMPLEMENTATION_AND_CHROME_MCP_REPORT.md`
- Modify: `docs/superpowers/specs/2026-09-15-theme-factory-verification-design.md`

**Interfaces:**
- Consumes: A–D release contract and standalone compatibility command.
- Produces: release commands that never search for or generate Layer E evidence.

- [ ] **Step 1: Add orchestration regression tests**

In `tests/test_release_batch.py`, assert a batch can complete with only C/D artifacts and that command construction never includes `agent_behavior_matrix`, agent-smoke paths, or agent runtime names.

- [ ] **Step 2: Run the batch tests and confirm old assumptions fail**

Run: `python3 -m unittest tests.test_release_batch -v`

Expected: at least one assertion fails while Layer E remains mentioned by release orchestration or fixtures.

- [ ] **Step 3: Remove theme-bound agent work from release commands**

Make `scripts/release-check.sh` build/verify the package, load C/D evidence, render A–D, and return success only for A–D `VERIFIED`. Ensure `tools/release_batch.py` resumes only C and D work and never duplicates shared agent evidence into per-theme directories.

- [ ] **Step 4: Update current documentation**

Replace statements that “every layer A–E must pass” with the A–D contract. Add a short cross-link to `docs/AGENT_COMPATIBILITY.md`. In older design/report documents, preserve historical facts but prepend a migration note pointing to the 2026-09-20 design.

- [ ] **Step 5: Run focused and offline checks**

Run: `python3 -m unittest tests.test_release_batch tests.test_release_report tests.test_theme_catalog -v && tests/run-offline.sh`

Expected: PASS; standalone agent compatibility is allowed to state `UNVERIFIED`, but no theme fails for that reason.

- [ ] **Step 6: Commit orchestration and docs**

```bash
git add scripts/release-check.sh tools/release_batch.py tests/test_release_batch.py README.md docs/PROJECT.md docs/THEME_FACTORY_IMPLEMENTATION_AND_CHROME_MCP_REPORT.md docs/superpowers/specs/2026-09-15-theme-factory-verification-design.md
git commit -m "refactor: decouple agent checks from theme releases"
```

### Task 7: Final migration verification

**Files:**
- Modify: generated sections in `README.md`, `sample-themes/README.md`, `docs/DESIGN_SYSTEM.md`, `tests/live/RELEASE-MATRIX.md`

**Interfaces:**
- Consumes: completed Tasks 1–6.
- Produces: evidence that all historical packages and current reports behave under the new contract.

- [ ] **Step 1: Run the release-report command against an existing A–D-complete theme**

Run: `scripts/release-check.sh carbon-volt --evidence-dir .agents/evaluations/runtime/2026-09-19-release-carbon-volt`

Expected: exit `0`; report contains A–D only and verdict `VERIFIED`.

- [ ] **Step 2: Run against a directory containing historical E evidence**

Run: `scripts/release-check.sh linen --evidence-dir .agents/evaluations/runtime/2026-09-17-release-linen`

Expected: exit depends only on current A–D source/package binding; no parse error occurs because E is present.

- [ ] **Step 3: Regenerate and check catalogs**

Run: `scripts/theme.sh catalog --write && scripts/theme.sh catalog --check`

Expected: first command writes only expected generated sections; second exits `0`.

- [ ] **Step 4: Run the complete offline suite**

Run: `tests/run-offline.sh`

Expected: exit `0`.

- [ ] **Step 5: Inspect the diff for accidental evidence changes**

Run: `git status --short && git diff --stat && git diff -- .agents/evaluations/runtime tests/agent-smoke/runs`

Expected: no changes under historical evidence or smoke-run directories.

- [ ] **Step 6: Commit generated migration output**

```bash
git add README.md sample-themes/README.md docs/DESIGN_SYSTEM.md tests/live/RELEASE-MATRIX.md
git commit -m "chore: regenerate a-d release catalog"
```

If regeneration produces no diff, record that fact in the execution notes and do not create an empty commit.
