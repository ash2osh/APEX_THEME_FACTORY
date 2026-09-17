# Verification Integrity Defect Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or
> superpowers:subagent-driven-development) to implement this plan task-by-task. Steps use checkbox
> (`- [ ]`) syntax. Every task is TDD: write the failing test, watch it fail *for the right reason*,
> then implement.

**Goal:** Close the four open defects in this project's own verification system, plus two smaller ones,
so that a `VERIFIED` release report cannot overstate what was actually checked.

**Why these six together:** every one of them is the same class of bug — *the checker believes a claim it
never tested*. None of them is a defect in a theme; all of them weaken the evidence that themes are
correct. They are listed in the order they should be executed, which is not the order of severity: it is
the order that minimises live re-captures.

**Context:** found during the 2026-09-17 session while adding custom fonts to `solarized-dark`. Ten other
defects found the same day are already fixed (see `.agents/knowledge/pitfalls.md` and the commits between
`d9853b3` and `3a51d06`).

## Global Constraints

- **Source vs evidence ordering is mandatory** (`pitfalls.md` §5.x): commit all source → build packages →
  capture evidence touching nothing → commit evidence and Markdown only. Tasks 1–4 are *source* changes,
  so they must land **before** the re-capture in Task 7, not between captures.
- One live re-capture for the whole plan. Capturing twice is a 2-hour mistake, not a 1-hour one.
- No task may make a check pass by weakening it. If a fix reveals that existing evidence was optimistic,
  the correct outcome is a failing check and a re-capture, not an adjusted threshold.
- `jsonschema` is **not** installed and `pip` is PEP 668-managed on this machine. Task 1 must either
  vendor a minimal validator or add the dependency deliberately — decide before starting, do not
  `--break-system-packages`.
- Tasks 1–4 change `lib/` or `tools/`, so each invalidates the current release evidence. That is expected
  and is why they are batched.
- Do not edit `sample-themes/estate-slate*/` while another agent holds them (memory:
  concurrent-codex-and-runtime-etiquette). Task 6 is a decision, not an edit, until that is resolved.

## File Map

| Path | Responsibility | Task |
|---|---|---|
| `tests/live/runtime-evidence.schema.json` | The Layer D artifact contract — currently enforced nowhere. | 1 |
| `lib/theme_factory/evidence_schema.py` *(new)* | Minimal, dependency-free validator for that schema. | 1 |
| `lib/theme_factory/release.py` | Release gate; must validate artifacts, not just their keys. | 1, 2 |
| `lib/theme_factory/gitstate.py` | Source identity; must distinguish instruction Markdown from prose. | 3 |
| `tools/live_matrix.py`, `tools/browser_matrix.py` | Capture drivers; must re-check the tree as they go. | 4 |
| `scripts/sync-static.sh` | Static-file registration; `charSet` on binaries. | 5 |
| `.agents/evaluations/runtime/` | Where the re-captured evidence lands. | 7 |

---

## Task 1 — Enforce the runtime-evidence schema instead of documenting it

**Defect:** `tests/live/runtime-evidence.schema.json` requires each font entry to carry
`{role, family, weight, style, check, requestUrl, mimeType}` with `additionalProperties: false`. Until
2026-09-17 the emitter produced `{family, loaded}`. Nothing noticed, because the schema is referenced
only from `tests/live/CAPTURE-RUNTIME-EVIDENCE.md` — no code ever reads it. The emitter now matches by
hand, which is a coincidence waiting to lapse.

**Decision required before starting:** vendor a ~120-line validator (recommended — no dependency, and the
schema uses only `type`/`required`/`const`/`enum`/`pattern`/`additionalProperties`/`items`), or add
`jsonschema` to the project's dependencies and document how it is installed on a PEP 668 machine.

- [ ] Write `tests/test_evidence_schema.py`: a known-good artifact validates; one with a font entry
      missing `requestUrl` fails; one with an extra key fails; one with `viewportWidth: 1441` fails.
      Watch them fail — the module does not exist yet.
- [ ] Implement `lib/theme_factory/evidence_schema.py::validate(document, schema_path) -> list[str]`
      returning human-readable errors (empty list = valid). Support exactly the keywords the schema uses;
      raise on an unsupported keyword rather than silently ignoring it — an ignored keyword is how this
      defect started.
- [ ] Add a test asserting every artifact under `.agents/evaluations/runtime/*/raw/browser-*.json`
      validates. This is the property test that would have caught the original drift.
- [ ] Wire `validate()` into `_load_bound_raw_artifact` in `release.py` for Layer D artifacts.

**Acceptance:** deleting `requestUrl` from any captured artifact makes `scripts/release-check.sh` exit
non-zero with a message naming the file and the field.

## Task 2 — Make the release gate check font evidence, not just its presence

**Defect:** `_valid_browser_runtime_artifact` checks `isinstance(artifact.get("fonts"), list)` and
`artifact.get("fontsVerified") is True`. Both are satisfied by `"fonts": []` with `fontsVerified: true`,
so a hand-written or regressed artifact can claim verified fonts for a font-bearing package.

- [ ] Write the failing test: an artifact for a theme whose package declares 5 faces, but whose `fonts`
      array is empty, must be rejected. A second test: an entry with `check: false` must be rejected.
- [ ] Extend `_valid_browser_runtime_artifact` to take the expected face count (derive it from the
      package via `tools.browser_matrix.font_expectations`, or record `declaredFaceCount` in the artifact
      at capture time — prefer the latter, so the gate does not need the ZIP).
- [ ] Require every entry's `check` to be `true` when `fontsVerified` is `true`.

**Acceptance:** a `solarized-dark` artifact with fewer than 5 font entries fails the gate; `linen`, with
0 declared faces and an empty array, still passes.

## Task 3 — Stop treating instruction Markdown as non-source

**Defect:** `NON_SOURCE_PATHSPECS` excludes `**/*.md`. That is right for prose and evidence, and wrong for
Layer E, whose *subject* is Markdown: the agent smokes measure what a runtime does after reading
`AGENTS.md`, `.agents/rules/*.md` and `.agents/skills/**`. Editing those leaves Layer E's artifacts
claiming a binding they no longer have, and nothing detects it. On 2026-09-17 this was handled by
re-running all three smokes by hand — a procedure, not a fix.

- [ ] Write the failing test: `source_equivalent(a, b)` must be **False** when the only difference is
      `AGENTS.md`, `.agents/rules/x.md` or `.agents/skills/y/SKILL.md`, and still **True** when the only
      difference is `README.md`, `docs/*.md` or anything under the evidence root.
- [ ] Introduce `INSTRUCTION_PATHSPECS` and subtract them from the Markdown exclusion, e.g. exclude
      `**/*.md` but re-include `AGENTS.md`, `.agents/rules/**/*.md`, `.agents/skills/**/*.md`.
- [ ] Decide explicitly whether `CLAUDE.md` (a symlink to `AGENTS.md`) needs its own entry — test it.
- [ ] Update `pitfalls.md` §5.x: the manual re-run rule becomes "the tooling now catches this", and say
      what replaced it.

**Cost to know before starting:** this makes instruction edits invalidate Layers C and D as well as E,
because `source_equivalent` is shared. That is arguably over-strict — C and D do not depend on
instructions. If that is unacceptable, the alternative is a *separate* Layer-E-only binding, which is
more code but more honest. **Choose deliberately and record the choice in the commit message.**

## Task 4 — Re-check the working tree during a capture, not only at its start

**Defect:** `tools/live_matrix.py` checks `git status --porcelain` once per invocation (line ~358). A tree
that goes dirty mid-run passes the theme in flight and fails the next one — which is exactly what
happened on 2026-09-17 when re-running the agent smokes mid-pipeline wrote
`tests/agent-smoke/runs/*.json`. The new banner guard (`package_matches_source`) narrows this but does not
close it.

- [ ] Write the failing test: a capture whose tree goes dirty between two operations must abort.
- [ ] Extract the check into `gitstate.assert_clean_source(cwd)` and call it before **each** consumer's
      lifecycle and before each Layer D row, not once at startup.
- [ ] Make the failure message name the dirty paths, so the cause is obvious without re-running.

**Acceptance:** touching a tracked source file mid-capture aborts within one operation, naming the file.

## Task 5 — Stop writing `charSet` for binary static files

**Defect (minor, pre-existing):** `sync-static.sh` registers every file with `charSet: utf-8`, including
`.woff2` and `.jpg`. Harmless in practice — APEX ignores it for binaries — but it is a false statement in
generated source, and it will mislead the next person reading the export.

- [ ] Write the failing test over the generated `static-files.apx`: no `file` block whose `mimeType` is
      `font/woff2` or `image/*` may declare `charSet`.
- [ ] Emit `charSet` only for text types in the `sync_one` registration.
- [ ] Re-run `scripts/sync-static.sh` and `scripts/apex-validate.sh` — expect `Validation successful.`

**Note:** this changes `applications/ut/**`, which is source, so it belongs in this batch rather than
after the re-capture.

## Task 6 — Decide what happens to `estate-slate` / `estate-slate-dark`

**Not a code defect — an evidence gap.** Two font-bearing packages were committed in `a38076b` with no
Layer C/D/E evidence at all, and their `dist/` builds are stamped `0edc66a`, which the Task-4 guard now
refuses. They are also not in `tests/live/RELEASE-MATRIX.md` or the release pipeline, so nothing reports
them as unverified — they are simply invisible to the release system.

- [ ] Decide with the repository owner: (a) capture full evidence for them too — roughly doubles the
      pipeline to ~2 hours and needs two more consumer fixtures or serialised runs; (b) mark them
      explicitly `UNVERIFIED — not release candidates` in `sample-themes/README.md` and their own
      READMEs; or (c) move them out of `sample-themes/` until they are ready.
- [ ] Whichever is chosen, add a check that **every** directory in `sample-themes/` either has evidence or
      is explicitly marked unverified. Silence is the actual defect here.

## Task 7 — One re-capture, then verify

- [ ] Confirm the tree is clean and all of Tasks 1–5 are committed.
- [ ] Rebuild both packages; confirm `package_matches_source` is true for each.
- [ ] Run the Layer C/D pipeline, touching nothing until `PIPELINE_DONE`.
- [ ] Regenerate Layer E (all three smokes — Task 3 makes this mandatory after any instruction edit).
- [ ] `scripts/release-check.sh linen` and `solarized-dark`; both must exit 0.
- [ ] Update `tests/live/RELEASE-MATRIX.md` and the implementation report with the new commit.

## Plan Acceptance

- [ ] `bash tests/run-offline.sh` → `ALL_OFFLINE_CHECKS status=PASS`.
- [ ] Both release checks exit 0 with verdict `VERIFIED`.
- [ ] Each of Tasks 1–5 has at least one test that was demonstrated failing before its implementation.
- [ ] Deleting a required field from a captured artifact now fails the gate (Task 1 acceptance) — verify
      this by hand once, then restore the file.
- [ ] `pitfalls.md` §5.x no longer describes a manual procedure that the tooling now enforces.
- [ ] No `sample-themes/` package is silently unverified (Task 6).

## Explicitly out of scope

- Re-running scenario 11's 24-page app-102 sweep against the font-bearing build. That needs an
  `apex-import` of app 102, which only the repository owner may authorise, and it is tracked separately.
- Extending Layer D beyond the four widths, or app 102 beyond 24 of its 122 pages. The coverage bound is
  recorded in `.agents/findings/accepted/2026-09-14-solarized-dark-2page-coverage-gap.md` and is not what
  this plan is about.
