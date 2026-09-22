# Uniqueness and CI Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the theme identity-collision rule, make the generated uniqueness report accurately describe and enforce that rule, and align hosted CI with the decoupled Layers A-D release model.

**Architecture:** Keep `lib/theme_factory/fingerprint.py` as the single source of truth for similarity thresholds, and have the report renderer import those constants instead of duplicating numeric policy in prose. Add the committed uniqueness report check to the shared offline gate used by both GitHub workflows, then regenerate the report only after every source-affecting commit so its `last_source_commit()` binding remains stable.

**Tech Stack:** Python 3.12+, `unittest`, Bash with `set -euo pipefail`, GitHub Actions YAML, generated Markdown.

**Spec:** `docs/superpowers/specs/2026-09-20-release-gates-and-theme-uniqueness-design.md`

## Global Constraints

- APEX remains 26.1.x, Universal Theme 42, style Iris only; this remediation does not alter application metadata or theme presentation.
- `IDENTITY_COLLISION` is an error when geometry, rhythm, typography treatment, interaction, and responsive strategy all match and average palette Delta E is strictly below `20`.
- Font-family equality and matching component-profile count are report dimensions, not prerequisites for `IDENTITY_COLLISION`.
- `STRUCTURAL_RECOLOR` remains CSS similarity `>= 0.98` with at least five matching profiles.
- `PROFILE_COLLISION` remains CSS similarity `>= 0.92` with at least five matching profiles.
- `STRUCTURAL_SIMILARITY` remains warning-only at CSS similarity `>= 0.85` when no error rule applies.
- All theme discovery remains dynamic; do not introduce an eight-theme shortlist.
- Theme release verdicts depend on Layers A-D only. Agent compatibility remains a separate project-level verdict and must not be described as Layer E in hosted theme CI.
- The generated report remains bound to `last_source_commit()`. Commit every non-Markdown source change before regenerating `docs/generated/theme-uniqueness-report.md`.
- Do not push the temporary source commit that precedes report regeneration by itself; push only after the report-only follow-up commit and final verification pass.
- No APEX import, SQLcl mutation, or Chrome runtime capture is authorized by this plan. Current Layers B-D remain `UNVERIFIED` until the user explicitly requests a release-evidence refresh.

## Review Focus

- A pair with all five explicit identity axes matching, different fonts, zero matching profiles, and Delta E `19.99` must still be an `IDENTITY_COLLISION`; Task 1 pins this directly.
- Delta E exactly `20.0` must not cross the strict-below-20 identity threshold; Task 1 pins the boundary.
- A difference in any explicit identity axis must prevent `IDENTITY_COLLISION`, even when the palette is very close; Task 1 pins a false-axis case.
- Human-readable report policy must use the exact classifier constants and must not resurrect the old `< 12`, font-match, or seven-profile requirements; Task 2 pins the rendered policy line.
- Both hosted workflows must state that Layers C-D are absent while describing agent compatibility as a separate verdict; Task 3 pins positive and negative wording checks.

---

## File Map

- Modify `lib/theme_factory/fingerprint.py`: define public threshold constants and correct `classify_similarity()`.
- Modify `tests/test_theme_fingerprint.py`: directly test the identity rule, its strict boundary, and an axis mismatch.
- Modify `lib/theme_factory/uniqueness_report.py`: render threshold prose from classifier constants.
- Modify `tests/test_uniqueness_report.py`: lock report policy wording and the shared offline-gate command.
- Modify `tests/run-common-offline.sh`: reject a stale committed uniqueness report in every common CI run.
- Modify `.github/workflows/verify.yml`: describe the Layers C-D runtime boundary and separate agent compatibility verdict.
- Modify `.github/workflows/nightly.yml`: use the same release-model terminology.
- Modify `tests/test_changed_themes.py`: parse both workflows and reject the obsolete `Layers C-E` phrase.
- Regenerate `docs/generated/theme-uniqueness-report.md`: bind the current 28-pair matrix to the final source commit.

---

### Task 1: Make the identity-collision classifier match the approved specification

**Files:**
- Modify: `tests/test_theme_fingerprint.py:7-13,145-168`
- Modify: `lib/theme_factory/fingerprint.py:13-29,388-414`

**Interfaces:**
- Consumes: `SimilarityReport` and `classify_similarity(report: SimilarityReport) -> tuple[str, str]`.
- Produces: named threshold constants and an identity rule based only on the five explicit axes plus palette distance.

- [x] **Step 1: Import the direct classifier interface in the test module**

Add `SimilarityReport` and `classify_similarity` to the existing import from `lib.theme_factory.fingerprint`:

```python
from lib.theme_factory.fingerprint import (
    SimilarityReport,
    check_uniqueness,
    classify_similarity,
    compare_fingerprints,
    delta_e_1976,
    fingerprint_theme,
)
```

- [x] **Step 2: Write focused failing tests for the approved identity rule**

Add this helper and these tests to `ThemeFingerprintTests`:

```python
    def similarity_report(self, **overrides) -> SimilarityReport:
        values = {
            "candidate": "candidate",
            "nearest_theme": "existing",
            "css_similarity": 0.10,
            "palette_delta_e": 19.99,
            "matching_profiles": (),
            "font_match": False,
            "geometry_match": True,
            "rhythm_match": True,
            "typography_match": True,
            "interaction_match": True,
            "responsive_match": True,
        }
        values.update(overrides)
        return SimilarityReport(**values)

    def test_identity_collision_uses_explicit_axes_not_font_or_profiles(self):
        self.assertEqual(
            classify_similarity(self.similarity_report()),
            ("error", "IDENTITY_COLLISION"),
        )

    def test_identity_collision_palette_threshold_is_strictly_below_twenty(self):
        self.assertEqual(
            classify_similarity(self.similarity_report(palette_delta_e=20.0)),
            ("PASS", "PASS"),
        )

    def test_identity_collision_requires_every_explicit_axis(self):
        self.assertEqual(
            classify_similarity(self.similarity_report(interaction_match=False)),
            ("PASS", "PASS"),
        )
```

- [x] **Step 3: Run the focused tests and verify the missing collision is exposed**

Run:

```bash
python3 -m unittest \
  tests.test_theme_fingerprint.ThemeFingerprintTests.test_identity_collision_uses_explicit_axes_not_font_or_profiles \
  tests.test_theme_fingerprint.ThemeFingerprintTests.test_identity_collision_palette_threshold_is_strictly_below_twenty \
  tests.test_theme_fingerprint.ThemeFingerprintTests.test_identity_collision_requires_every_explicit_axis -v
```

Expected: the first test fails because the current classifier returns `IDENTITY_SIMILARITY`; the two boundary tests pass.

- [x] **Step 4: Add named classifier thresholds**

Add these module constants below `SEMANTIC_TOKENS` in `lib/theme_factory/fingerprint.py`:

```python
STRUCTURAL_RECOLOR_CSS_THRESHOLD = 0.98
PROFILE_COLLISION_CSS_THRESHOLD = 0.92
STRUCTURAL_SIMILARITY_CSS_THRESHOLD = 0.85
ERROR_PROFILE_MATCH_THRESHOLD = 5
IDENTITY_COLLISION_DELTA_E_THRESHOLD = 20.0
```

- [x] **Step 5: Replace classifier literals and remove the extra identity prerequisites**

Implement `classify_similarity()` as:

```python
def classify_similarity(report: SimilarityReport) -> tuple[str, str]:
    """Return the highest-priority finding for a pair."""

    profile_count = len(report.matching_profiles)
    if (
        report.css_similarity >= STRUCTURAL_RECOLOR_CSS_THRESHOLD
        and profile_count >= ERROR_PROFILE_MATCH_THRESHOLD
    ):
        return "error", "STRUCTURAL_RECOLOR"
    if (
        report.css_similarity >= PROFILE_COLLISION_CSS_THRESHOLD
        and profile_count >= ERROR_PROFILE_MATCH_THRESHOLD
    ):
        return "error", "PROFILE_COLLISION"
    if (
        report.geometry_match
        and report.rhythm_match
        and report.typography_match
        and report.interaction_match
        and report.responsive_match
        and report.palette_delta_e < IDENTITY_COLLISION_DELTA_E_THRESHOLD
    ):
        return "error", "IDENTITY_COLLISION"
    if report.css_similarity >= STRUCTURAL_SIMILARITY_CSS_THRESHOLD:
        return "warning", "STRUCTURAL_SIMILARITY"
    if profile_count >= ERROR_PROFILE_MATCH_THRESHOLD:
        return "warning", "PROFILE_SIMILARITY"
    if (
        report.font_match
        and report.geometry_match
        and report.palette_delta_e < IDENTITY_COLLISION_DELTA_E_THRESHOLD
    ):
        return "warning", "IDENTITY_SIMILARITY"
    return "PASS", "PASS"
```

- [x] **Step 6: Run all fingerprint tests**

Run: `python3 -m unittest tests.test_theme_fingerprint -v`

Expected: all fingerprint tests pass, including the new different-font/zero-profile collision case.

- [x] **Step 7: Commit the classifier correction**

```bash
git add lib/theme_factory/fingerprint.py tests/test_theme_fingerprint.py
git commit -m "fix: enforce explicit theme identity collision axes"
```

---

### Task 2: Derive report policy text from classifier constants

**Files:**
- Modify: `lib/theme_factory/uniqueness_report.py:10-17,54-68`
- Modify: `tests/test_uniqueness_report.py:28-43`

**Interfaces:**
- Consumes: the five public threshold constants introduced by Task 1.
- Produces: `render_uniqueness_report(...) -> str` whose policy summary cannot silently retain obsolete numeric thresholds.

- [x] **Step 1: Write a failing report-contract test**

Extend `test_markdown_explains_all_similarity_dimensions` with exact policy assertions:

```python
        self.assertIn("structural recolor CSS ≥ 0.98 with ≥ 5 matching profiles", report)
        self.assertIn("profile collision CSS ≥ 0.92 with ≥ 5 matching profiles", report)
        self.assertIn(
            "identity collision requires matching geometry, rhythm, typography treatment, "
            "interaction, and responsive strategy with palette Delta E < 20",
            report,
        )
        self.assertIn("CSS similarity ≥ 0.85", report)
        self.assertNotIn("Delta E < 12", report)
        self.assertNotIn("requires all seven profiles", report)
```

- [x] **Step 2: Run the report test and verify the stale prose fails**

Run:

```bash
python3 -m unittest \
  tests.test_uniqueness_report.UniquenessReportTests.test_markdown_explains_all_similarity_dimensions -v
```

Expected: FAIL because the renderer still says all seven profiles and Delta E `< 12`.

- [x] **Step 3: Import classifier constants into the report renderer**

Extend the existing import from `lib.theme_factory.fingerprint`:

```python
from lib.theme_factory.fingerprint import (
    ERROR_PROFILE_MATCH_THRESHOLD,
    IDENTITY_COLLISION_DELTA_E_THRESHOLD,
    PROFILE_COLLISION_CSS_THRESHOLD,
    STRUCTURAL_RECOLOR_CSS_THRESHOLD,
    STRUCTURAL_SIMILARITY_CSS_THRESHOLD,
    SimilarityReport,
    classify_similarity,
    compare_fingerprints,
    fingerprint_theme,
)
```

- [x] **Step 4: Render accurate policy text from those constants**

Replace the two threshold lines in `render_uniqueness_report()` with:

```python
        "- Error thresholds: "
        f"structural recolor CSS ≥ {STRUCTURAL_RECOLOR_CSS_THRESHOLD:g} with "
        f"≥ {ERROR_PROFILE_MATCH_THRESHOLD} matching profiles; "
        f"profile collision CSS ≥ {PROFILE_COLLISION_CSS_THRESHOLD:g} with "
        f"≥ {ERROR_PROFILE_MATCH_THRESHOLD} matching profiles; "
        "identity collision requires matching geometry, rhythm, typography treatment, "
        "interaction, and responsive strategy with palette Delta E "
        f"< {IDENTITY_COLLISION_DELTA_E_THRESHOLD:g}.",
        f"- Warning threshold: CSS similarity ≥ {STRUCTURAL_SIMILARITY_CSS_THRESHOLD:g} "
        "when no error rule applies.",
```

- [x] **Step 5: Run the complete report and classifier test modules**

Run:

```bash
python3 -m unittest tests.test_theme_fingerprint tests.test_uniqueness_report -v
```

Expected: all tests pass. Do not regenerate the committed report yet; later source commits would immediately invalidate its source binding.

- [x] **Step 6: Commit the report-policy correction**

```bash
git add lib/theme_factory/uniqueness_report.py tests/test_uniqueness_report.py
git commit -m "fix: derive uniqueness report policy from classifier"
```

---

### Task 3: Enforce report freshness and correct hosted release terminology

**Files:**
- Modify: `tests/test_uniqueness_report.py:45-61`
- Modify: `tests/test_changed_themes.py:127-141`
- Modify: `tests/run-common-offline.sh:15-18`
- Modify: `.github/workflows/verify.yml:23-31`
- Modify: `.github/workflows/nightly.yml:38-41`

**Interfaces:**
- Consumes: `python3 -m lib.theme_factory.uniqueness_report ... --check`, which is read-only and exits `1` on drift.
- Produces: a shared common gate that rejects report drift and workflow summaries consistent with the Layers A-D model.

- [x] **Step 1: Add a failing test that requires the common gate command**

Add this method to `UniquenessReportTests`:

```python
    def test_common_offline_gate_checks_committed_report(self):
        script = (Path("tests/run-common-offline.sh")).read_text(encoding="utf-8")
        self.assertIn(
            "python3 -m lib.theme_factory.uniqueness_report "
            "--repo-root . --output docs/generated/theme-uniqueness-report.md --check",
            script,
        )
```

- [x] **Step 2: Replace the stale workflow assertion with positive and negative release-model checks**

In `CiTierContractTests.test_workflows_parse_and_keep_live_layers_out_of_hosted_ci`, replace the `Layers C-E` assertion with:

```python
        for workflow in (verify, nightly):
            self.assertIn("Layers C-D", workflow)
            self.assertIn("Agent compatibility has a separate project-level verdict", workflow)
            self.assertNotIn("Layers C-E", workflow)
```

Keep the YAML parsing, changed-theme selection, no-Chrome, and no-import assertions already in that test.

- [x] **Step 3: Run the two targeted tests and verify they fail for the intended reasons**

Run:

```bash
python3 -m unittest \
  tests.test_uniqueness_report.UniquenessReportTests.test_common_offline_gate_checks_committed_report \
  tests.test_changed_themes.CiTierContractTests.test_workflows_parse_and_keep_live_layers_out_of_hosted_ci -v
```

Expected: FAIL because the common script lacks the report check and both workflows still say `Layers C-E`.

- [x] **Step 4: Add the report check to the common offline gate**

Insert this command after the unit suite and before `scripts/check-agent-layout.sh` in `tests/run-common-offline.sh`:

```bash
python3 -m lib.theme_factory.uniqueness_report --repo-root . --output docs/generated/theme-uniqueness-report.md --check
```

- [x] **Step 5: Correct the push/PR workflow summary**

Replace the summary command in `.github/workflows/verify.yml` with:

```yaml
      - name: State live-evidence boundary
        if: always()
        run: echo 'Layers C-D are UNVERIFIED — run the local release workflow with SQLcl and the approved Chrome daemon. Agent compatibility has a separate project-level verdict.' >> "$GITHUB_STEP_SUMMARY"
```

- [x] **Step 6: Correct the nightly workflow summary**

Replace the summary command in `.github/workflows/nightly.yml` with:

```yaml
      - name: State hosted-runner boundary
        if: always()
        run: echo 'Offline/package checks only. No database import, Chrome session, or Layers C-D verification ran. Agent compatibility has a separate project-level verdict.' >> "$GITHUB_STEP_SUMMARY"
```

- [x] **Step 7: Run the focused contract tests**

Run:

```bash
python3 -m unittest tests.test_uniqueness_report tests.test_changed_themes -v
```

Expected: the test modules pass. Do not run `tests/run-common-offline.sh` yet: the newly enforced gate must correctly report drift until Task 4 regenerates the committed report.

- [x] **Step 8: Commit every remaining source-affecting change**

```bash
git add \
  tests/test_uniqueness_report.py \
  tests/test_changed_themes.py \
  tests/run-common-offline.sh \
  .github/workflows/verify.yml \
  .github/workflows/nightly.yml
git commit -m "ci: enforce uniqueness report freshness"
```

Expected: this commit is intentionally followed immediately by Task 4 and must not be pushed alone.

---

### Task 4: Regenerate the source-bound report and close offline verification

**Files:**
- Regenerate: `docs/generated/theme-uniqueness-report.md`
- Update tracking only: `docs/superpowers/plans/2026-09-22-uniqueness-ci-review-remediation.md`

**Interfaces:**
- Consumes: the committed classifier, renderer, shared gate, and workflow changes from Tasks 1-3.
- Produces: a 28-pair report bound to the final source commit and a repository where the shared push/nightly gate passes.

- [x] **Step 1: Confirm there are no uncommitted non-Markdown source changes**

Run:

```bash
git status --short
git diff --name-only -- ':!**/*.md'
```

Expected: the second command prints nothing. The plan Markdown itself may still be modified as checkboxes are tracked.

- [x] **Step 2: Regenerate the uniqueness report after the final source commit**

Run:

```bash
python3 -m lib.theme_factory.uniqueness_report \
  --repo-root . \
  --output docs/generated/theme-uniqueness-report.md
```

Expected: `THEME_UNIQUENESS_REPORT status=PASS rows=28`.

- [x] **Step 3: Verify report freshness, row count, and absence of error-level pairs**

Run:

```bash
python3 -m lib.theme_factory.uniqueness_report \
  --repo-root . \
  --output docs/generated/theme-uniqueness-report.md \
  --check
test "$(rg -c '^\| `[^`]+` \| `[^`]+` \|' docs/generated/theme-uniqueness-report.md)" -eq 28
! rg '\| error \|' docs/generated/theme-uniqueness-report.md
```

Expected: the check reports `PASS`, the row-count assertion exits `0`, and no error row is found. Warning rows remain visible for human review.

- [x] **Step 4: Run the focused remediation suite**

Run:

```bash
python3 -m unittest \
  tests.test_theme_fingerprint \
  tests.test_uniqueness_report \
  tests.test_changed_themes -v
```

Expected: all focused tests pass.

- [x] **Step 5: Run the complete common offline suite through the real CI entry point**

Run: `tests/run-common-offline.sh`

Expected: all unit tests pass, the committed report check reports `PASS`, agent layout passes, and the script ends with `COMMON_OFFLINE_CHECKS status=PASS`.

- [x] **Step 6: Run repository package verification**

Run: `tests/run-package-offline.sh`

Expected: all package tests pass and all discovered themes build and verify successfully.

- [x] **Step 7: Run the remaining generated-state and compatibility checks**

Run:

```bash
scripts/theme.sh catalog --check
scripts/theme.sh inspect-iris --check
scripts/agent-compatibility-check.sh --check
```

Expected: catalog and Iris inventory are current, and the standalone agent compatibility verdict is `PASS`.

- [x] **Step 8: Commit the generated report as a report-only follow-up**

```bash
git add \
  docs/generated/theme-uniqueness-report.md \
  docs/superpowers/plans/2026-09-22-uniqueness-ci-review-remediation.md
git diff --cached --name-only
git commit -m "docs: refresh theme uniqueness report"
```

Expected: the staged list contains Markdown only. Because Markdown is excluded by `last_source_commit()`, this commit does not invalidate the report binding.

- [x] **Step 9: Re-run the report check and inspect final repository state**

Run:

```bash
python3 -m lib.theme_factory.uniqueness_report \
  --repo-root . \
  --output docs/generated/theme-uniqueness-report.md \
  --check
git status --short --branch
```

Expected: report status is `PASS` and the working tree is clean. Do not claim Layers B-D are verified; this plan changes offline policy and CI only.

---

## Post-Plan Release Checkpoint

The selected review findings are closed when Task 4 passes. The authoritative release matrix may still show Layers B-D as `UNVERIFIED` because its retained browser evidence is bound to an older source identity. That is not silently repaired by offline tests.

After the user explicitly authorizes an app import and runtime evidence refresh, start a separate execution using `apexlang-roundtrip`, `chrome-devtools-mcp`, `apex-visual-comparison`, `apex-responsive-design`, `apex-accessibility`, and `apex-design-review`. Follow `docs/APEXLANG_ROUNDTRIP.md` and `tests/live/CAPTURE-RUNTIME-EVIDENCE.md`, use only `python3 tools/chrome_devtools_client.py ...` for runtime truth, verify all eight themes at `1440`, `1024`, `768`, and `375` pixels, and then rebuild `tests/live/RELEASE-MATRIX.md` through the release tooling. Do not convert this checkpoint into an import merely because the offline remediation succeeds.
