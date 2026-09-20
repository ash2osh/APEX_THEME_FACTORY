# Theme Factory Verification and Release Design

**Date:** 2026-09-15
**Status:** Approved for implementation planning
**Scope:** Automated tests, CI, runtime parity, design debt, agent evaluations, and consumer-app evidence

> **Migration note (2026-09-20):** This earlier design records the original A–E release contract. The current
> contract is defined by `docs/superpowers/specs/2026-09-20-release-gates-and-theme-uniqueness-design.md`:
> theme verdicts use Layers A–D, while agent compatibility is instruction-bound and reported separately in
> `docs/AGENT_COMPATIBILITY.md`. The historical Layer E requirements below remain useful evaluation history.

## 1. Purpose

Define the evidence required before the repository, an individual theme ZIP, or an agent workflow can be called verified. The release process must separate source validation, package validation, database installation proof, browser runtime proof, and cross-application portability proof.

## 2. Goals

- Add fast offline tests for every packaging and installer safety contract.
- Add CI that runs without Oracle credentials or a live APEX instance.
- Detect source/runtime drift, including missing application-level assets such as Alpine.
- Add one real Alpine component fixture inside a refreshable APEX region.
- Resolve the five ambiguous agent evaluations and all pending findings (currently seven documents) through valid evidence.
- Enforce the documented CSS token and selector rules.
- Complete Solarized Dark's live verification.
- Prove installation and uninstallation against two structurally different consumer applications.
- Publish a release report that states every unavailable or excluded check.

## 3. Evidence Layers

Every result uses one of `PASS`, `FAIL`, `UNVERIFIED`, or `NOT APPLICABLE`.

### Layer A: repository source

- shell syntax;
- JSON and schema validity;
- APEXLang validation;
- canonical skill structure;
- CSS policy checks;
- deterministic package build;
- clean source/export synchronization.

### Layer B: package artifact

- ZIP layout and checksums;
- no path traversal, absolute paths, symlinks, or duplicate archive names;
- self-contained CSS with no unresolved imports or undeclared shared tokens;
- optional custom fonts contain only declared WOFF2 faces, use package-prefixed family identifiers, and include every referenced license;
- installer/uninstaller dry-run behavior against fixtures;
- manual documentation completeness.

### Layer C: database installation

- exact-target preflight;
- fresh-export patch and validation;
- import into a disposable consumer application;
- idempotent reinstall;
- second package coexistence;
- switcher enable/disable transitions;
- uninstall and backup recovery;
- preservation of unrelated application components.

### Layer D: browser runtime

- expected app, page, APEX version, theme number/style, package class, CSS URL, and runtime URL;
- every declared font request, response MIME type, `document.fonts.check()` result, computed role family, and fallback behavior;
- console and network failures;
- visual states and contrast;
- responsive widths;
- keyboard behavior;
- report/grid/form/dialog lifecycle;
- Alpine initialization and refresh behavior.
- Font APEX icon family and glyph rendering before and after applying a custom-font package.

### Layer E: agent behavior

- valid neutral prompts;
- isolated baseline/current conditions where comparison is meaningful;
- all tools required by each Expected clause;
- full patches and evidence retained before cleanup;
- separate results for Codex, Claude Code, and Antigravity where runtime compatibility is claimed.

## 4. Offline Test Architecture

Tests use Python's standard-library `unittest` plus small Bash entry points. No package manager or third-party test dependency is introduced.

```text
tests/
├── run-offline.sh
├── fixtures/
│   ├── apexlang/minimal/
│   ├── apexlang/with-existing-assets/
│   ├── apexlang/no-global-page/
│   ├── apexlang/ambiguous-css-block/
│   ├── packages/invalid/
│   └── packages/custom-font/
├── test_manifest.py
├── test_css_bundle.py
├── test_package_archive.py
├── test_apexlang_patch.py
├── test_installer_cli.py
├── test_uninstaller_cli.py
├── test_agent_layout.py
└── test_css_policy.py
```

`tests/run-offline.sh` runs Bash syntax checks, all unit tests, a package build for every theme, and a second build comparison. It exits on the first command failure while preserving individual unittest diagnostics.

Installer tests use fake `sql` executables placed first on a test-specific `PATH`. Each fake records arguments and returns controlled export, query, validation, drift, or import results. Tests assert that no import command is issued on every refusal path.

## 5. CI

`.github/workflows/verify.yml` runs on pushes and pull requests with:

- checkout without credentials persisted;
- Python standard library only;
- `bash -n scripts/*.sh tests/*.sh`;
- `tests/run-offline.sh`;
- `git diff --exit-code` after generation to enforce committed generated artifacts where applicable;
- ZIP artifact upload for Linen and Solarized Dark on successful workflow runs.

CI does not connect to SQLcl, Oracle Database, localhost APEX, Chrome, or external model runtimes. Its summary labels those layers `UNVERIFIED` and links to the required local release command.

## 6. Source/Runtime Parity

`scripts/check-runtime-parity.sh` uses SQLcl read-only queries and Chrome DevTools evidence to compare:

- application ID and alias;
- APEX version and current Iris style;
- every Theme Factory static file path and content size;
- application CSS/JavaScript file URLs;
- `window.App`, `window.Alpine`, active theme class, installed registry, and switcher availability;
- console and failed network requests.

The script produces a dated JSON report under `.agents/evaluations/runtime/`. A missing referenced asset is `FAIL`; a repository asset that is intentionally not deployed is `NOT APPLICABLE` only when declared in the package manifest or static-sync exclusion list.

The first remediation must import the already-validated `application.apx` Alpine URL change into app 102 only after explicit user authorization, then confirm `window.Alpine.version === "3.17.2"`.

## 7. Alpine Lifecycle Fixture

The repository adds one minimal, non-business component named `themeFactoryDisclosure`:

- registered through `Alpine.data()` before Alpine starts;
- hosted inside a refreshable native APEX region on a dedicated factory evaluation page;
- mirrors its open/closed value to an APEX page item through `apex.item()`;
- initializes once;
- remains keyboard operable;
- reinitializes correctly when the owning region is replaced;
- does not call `Alpine.start()` after refresh;
- introduces no console errors or duplicate handlers.

Its contract is added to `docs/COMPONENTS.md`. Evaluation 04 is rewritten to exercise this actual component and region rather than a hypothetical fixture.

## 8. CSS Policy Remediation

The policy checker parses declarations rather than comments and enforces:

- every theme selector is scoped under its manifest class;
- no application-owned selector begins with Oracle-reserved namespaces;
- no literal color declaration occurs in `sample-themes/*/css/apex/*.css`;
- every literal needed by component CSS is declared in that theme's `tokens.css` or the shared foundation;
- `!important` appears only in the global `x-cloak` rule or beside a comment identifying the mirrored Iris rule;
- every used `--app-*` token is declared by the flattened package;
- package CSS contains no remote URL or unresolved local import.
- font-bearing packages contain no external font URL or data URL, every file has the `wOF2` signature, and every declared role has its documented fallback and license.

The five existing literal declarations in theme `css/apex` files move to semantic tokens without changing their computed runtime values.

## 9. Agent Evaluation Repair

The evaluation matrix is corrected in this order:

1. retain exact neutral prompts and full diffs/fixtures before worktree cleanup;
2. ensure each scenario's Expected clauses match the task actually given;
3. supply Chrome to scenarios requiring runtime evidence;
4. supply a real APEXLang fixture to lifecycle scenarios;
5. rerun scenarios 04, 05, 09, 11, and 14;
6. reclassify each pending finding only after its motivating scenario passes and regression scenarios remain green;
7. preserve `UNVERIFIED` when a required tool or environment is unavailable.

A baseline/current comparison is required only when testing whether a skill change is load-bearing. A straightforward current-behavior regression may pass without manufacturing a misleading baseline comparison.

## 10. Live Theme Verification

Each theme's release matrix covers pages representing:

- shell and navigation;
- standard, alert, and content regions;
- Cards and Content Row;
- forms and validation errors;
- Interactive Report;
- Interactive Grid, including edit, paging, sort, filter, selection, and refresh;
- modal dialog and drawer;
- menus, Popup LOV, date picker, and floating labels;
- Calendar and Oracle JET chart;
- documentation tables and code samples;
- loading, empty, error, hover, focus, selected, and disabled states.

Required viewports are `1440`, `1024`, `768`, and `375` CSS pixels. The standard contrast audit runs on every applicable page, supplemented by driven hover, empty, focus, menu, dialog, and validation states that resting-node inspection cannot see.

Package failures must be zero. Known Universal Theme demonstration failures are listed individually with plain-Iris comparison evidence; they are never silently excluded.

Solarized Dark may replace “NOT fully verified” with a dated Verified section only after the expanded page list in its current README, Calendar, JET charts, all four widths, console/network checks, and driven interactive states pass against the final packaged CSS.

## 11. Consumer-Application Portability Matrix

Live release tests provision two disposable applications in the DEMO workspace from committed APEXLang fixtures, selecting unused application IDs from a documented test-only range after collision checks:

### Minimal consumer

- Universal Theme 42 / Iris;
- no pre-existing Global Page;
- no custom application static files;
- side navigation and one standard page.

### Business consumer

- Universal Theme 42 / Iris;
- existing Global Page content;
- existing CSS and JavaScript URLs;
- side navigation and navigation bar;
- form, validation, Interactive Report, Interactive Grid, Cards, modal dialog, drawer, Calendar, and JET chart;
- unrelated static files and components whose identifiers and digests are captured before installation.

The matrix runs:

1. dry-run fixed Linen;
2. install fixed Linen;
3. reinstall Linen;
4. enable switcher;
5. install Solarized Dark from its separate ZIP;
6. switch among Linen, Solarized Dark, and Iris;
7. reload and open a dialog to verify namespaced browser persistence;
8. install the custom-font fixture, verify body/heading/mono faces and Font APEX isolation, then simulate a failed font request and verify the declared fallback;
9. uninstall the active package and verify fallback;
10. uninstall the final package and verify clean Iris;
11. restore the pre-test backup and compare application digests.

Disposable applications are deleted only through the release test's explicit cleanup command after their IDs are rechecked. Cleanup is never part of a generic offline test.

## 12. Release Report

`scripts/release-check.sh <theme-name>` produces `dist/<theme-name>/RELEASE-REPORT.md` containing:

- repository commit and dirty-state check;
- package version and checksum;
- results for Layers A-E;
- exact APEX/SQLcl/Chrome/agent versions;
- consumer application aliases and test IDs;
- pages, states, and widths exercised;
- console/network findings;
- remaining `UNVERIFIED` and `NOT APPLICABLE` items;
- rollback result;
- final release verdict.

The report refuses a `VERIFIED` verdict when any required layer is `FAIL` or `UNVERIFIED`.

## 13. Acceptance Criteria

- Offline CI passes from a clean checkout without Oracle or model credentials.
- Source/runtime parity reports no missing referenced asset.
- Alpine 3.17.2 loads once and the real fixture passes refresh and keyboard tests.
- All theme CSS policy violations are resolved without changing intended appearance.
- Scenarios 04, 05, 09, 11, and 14 have valid evidence-backed results.
- Pending findings are promoted or rejected only through the documented protocol.
- Linen and Solarized Dark pass the complete live matrix.
- Separate single-theme ZIPs install, coexist, switch, persist, uninstall, and restore successfully in both consumer fixtures.
- The custom-font fixture self-hosts licensed WOFF2 assets, loads all declared roles, falls back cleanly, and does not alter Font APEX icons.
- Release reports state coverage limits and never infer runtime success from source validation alone.
