# Agent Runtime Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Codex, Claude Code, and Google Antigravity reliably discover the same Theme Factory constraints and skills, with deterministic layout checks and dated read-only behavioral smoke evidence.

**Architecture:** `AGENTS.md` remains the concise canonical instruction source, Claude resolves it through `CLAUDE.md`, and Antigravity receives an always-active workspace rule under `.agents/rules/`. Canonical skills stay in `.agents/skills/` with runtime-specific symlinks. Offline structure validation is separate from authenticated model smoke tests so CI never consumes quota or overclaims behavioral compatibility.

**Tech Stack:** Bash, Python 3.10+ standard library, JSON Schema, Codex CLI, Claude Code CLI, Antigravity `agy` CLI.

**Spec:** `docs/superpowers/specs/2026-09-15-agent-runtime-compatibility-design.md`

## Global Constraints

- Canonical project instructions remain `AGENTS.md`; do not duplicate `docs/AGENT_SPEC.md` into runtime entry files.
- Canonical skills remain `.agents/skills/<name>/SKILL.md`.
- `CLAUDE.md` must resolve to `AGENTS.md`; `.claude/skills/<name>` must resolve to the matching canonical skill.
- Antigravity must have an always-active `.agents/rules/apex-theme-factory.md` under 12,000 characters.
- `.agent/skills` remains a documented legacy compatibility symlink only.
- All runtimes must state the APEX 26.1.x / Universal Theme 42 / Iris-only boundary and explicit import authorization rule.
- Theme fonts, when used, are package-local licensed WOFF2 assets; external font URLs are forbidden.
- Live smokes use read-only/plan permissions, make no database or Chrome calls, and never use a permission-bypass flag.
- CI runs structure tests only; authentication/quota failures are `UNVERIFIED`, not `FAIL`.
- An executor must read `AGENTS.md`, `docs/PROJECT.md`, `.agents/knowledge/pitfalls.md`, and this plan's spec before Task 1.

## File Map

| Path | Responsibility |
|---|---|
| `scripts/check-agent-layout.sh` | Fast structural verifier for entry files, rules, skills, and symlinks. |
| `tests/test_agent_layout.py` | Isolated positive/negative tests for the structural verifier. |
| `.agents/rules/apex-theme-factory.md` | Antigravity always-active workspace constraints. |
| `.agents/README.md` | Canonical and legacy discovery-path documentation. |
| `sample-prompts/init.md` | Idempotent read-only session-readiness prompt. |
| `docs/AGENT_COMPATIBILITY.md` | Runtime matrix, commands, evidence limits, and latest smoke versions. |
| `tests/agent-smoke/readiness-prompt.md` | Common neutral behavioral prompt. |
| `tests/agent-smoke/result.schema.json` | Strict cross-runtime JSON result contract. |
| `tools/agent_smoke.py` | Quota-consuming smoke runner, parser, redactor, and result writer. |
| `tests/agent-smoke/runs/2026-09-15/` | First dated, redacted runtime results; later releases use their UTC run date. |

---

### Task 1: Structural Agent-Layout Verifier

**Files:**
- Create: `scripts/check-agent-layout.sh`
- Create: `tests/test_agent_layout.py`

**Interfaces:**
- Consumes: repository root passed as optional argument, defaulting to the parent of `scripts/`.
- Produces: one final line `AGENT_LAYOUT status=PASS skills=<count> claude_links=<count> errors=0` or `status=FAIL ...`; nonzero exit on failure.

- [ ] **Step 1: Write failing isolated layout tests**

```python
# tests/test_agent_layout.py
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class AgentLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / ".agents/skills/design-to-apex").mkdir(parents=True)
        (self.tmp / ".agents/rules").mkdir(parents=True)
        (self.tmp / ".claude/skills").mkdir(parents=True)
        (self.tmp / ".agent").mkdir(parents=True)
        (self.tmp / "scripts").mkdir()
        shutil.copy("scripts/check-agent-layout.sh", self.tmp / "scripts/check-agent-layout.sh")

    def run_check(self):
        return subprocess.run(
            ["bash", str(self.tmp / "scripts/check-agent-layout.sh"), str(self.tmp)],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_valid_layout_passes(self):
        (self.tmp / "AGENTS.md").write_text("# Rules\nAPEX 26.1.x / Universal Theme 42 / Iris only\n", encoding="utf-8")
        os.symlink("AGENTS.md", self.tmp / "CLAUDE.md")
        (self.tmp / ".agents/rules/apex-theme-factory.md").write_text("# Rule\n", encoding="utf-8")
        skill = self.tmp / ".agents/skills/design-to-apex/SKILL.md"
        skill.write_text("---\nname: design-to-apex\ndescription: route design work\n---\n", encoding="utf-8")
        os.symlink("../../.agents/skills/design-to-apex", self.tmp / ".claude/skills/design-to-apex")
        os.symlink("../.agents/skills", self.tmp / ".agent/skills")
        (self.tmp / ".agents/README.md").write_text(".agents/skills .claude/skills .agent/skills .agents/rules\n", encoding="utf-8")
        (self.tmp / "sample-prompts").mkdir()
        (self.tmp / "sample-prompts/init.md").write_text("Inspect only; stop before edits.\n", encoding="utf-8")
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AGENT_LAYOUT status=PASS", result.stdout)
```

Add negative tests for missing/broken `CLAUDE.md`, oversized `AGENTS.md`, missing/oversized Antigravity rule, missing `trigger: always_on` rule frontmatter, missing skill YAML delimiter/name/description, duplicate skill names, directory/name mismatch, missing Claude link, wrong Claude target, wrong legacy target, documentation path drift, and forbidden initialization commands.

- [ ] **Step 2: Add an initial executable stub and verify the tests fail meaningfully**

```bash
#!/usr/bin/env bash
set -euo pipefail
echo "AGENT_LAYOUT status=FAIL skills=0 claude_links=0 errors=1"
exit 1
```

Run: `python3 -m unittest tests.test_agent_layout -v`

Expected: positive layout test fails while negative cases detect the stub's generic failure.

- [ ] **Step 3: Implement exact structural checks**

Use `readlink -f` for symlink targets, `wc -c` for byte limits, and sorted `find "$root/.agents/skills" -mindepth 2 -maxdepth 2 -name SKILL.md`. Parse frontmatter with an embedded Python standard-library script that requires the first and closing `---`, one `name:`, one non-empty `description:`, unique names, and `name == parent directory`. Parse the Antigravity rule separately and require first-line YAML frontmatter containing exactly `trigger: always_on` plus a non-empty `description`.

Scan `sample-prompts/init.md` case-insensitively for these forbidden patterns:

```text
git init
git commit
apex import
apex-import.sh
dangerously-skip-permissions
dangerously-bypass-approvals-and-sandbox
rm -rf
```

Collect every error, print it as `ERROR path={repository-relative-path} message={specific-message}`, then print the one summary line. Do not exit on the first mismatch.

- [ ] **Step 4: Run isolated and real-repository checks**

Run: `python3 -m unittest tests.test_agent_layout -v`

Expected: all isolated tests pass.

Run: `scripts/check-agent-layout.sh`

Expected: fail specifically because `.agents/rules/apex-theme-factory.md` is missing and `sample-prompts/init.md` still contains repository initialization/commit instructions.

- [ ] **Step 5: Commit the verifier before repairing the layout**

```bash
git add scripts/check-agent-layout.sh tests/test_agent_layout.py
git commit -m "test: validate agent discovery layout"
```

---

### Task 2: Canonical Runtime Instructions, Symlinks, and Antigravity Rule

**Files:**
- Modify: `AGENTS.md`
- Verify: `CLAUDE.md`
- Create: `.agents/rules/apex-theme-factory.md`
- Modify: `.agents/README.md`
- Verify/repair: `.claude/skills/*`
- Verify/repair: `.agent/skills`
- Modify: `tests/test_agent_layout.py`

**Interfaces:**
- Consumes: the path contract from Task 1.
- Produces: identical project boundaries discoverable through each runtime's canonical entry points.

- [ ] **Step 1: Add failing assertions for the full project contract**

Extend `tests/test_agent_layout.py` so the real repository check requires all of these phrases in the canonical entry and Antigravity rule: `APEX 26.1.x`, `Universal Theme 42`, `Iris`, `Chrome DevTools`, `Import only when the user asks`, `sample-themes/<name>`, `WOFF2`, and `external font URLs`.

```python
REQUIRED_PROJECT_PHRASES = (
    "APEX 26.1.x", "Universal Theme 42", "Iris", "Chrome DevTools",
    "Import only when the user asks", "sample-themes/<name>", "WOFF2",
    "external font URLs",
)

def assert_contract(testcase, text: str) -> None:
    for phrase in REQUIRED_PROJECT_PHRASES:
        testcase.assertIn(phrase, text)
```

Run: `python3 -m unittest tests.test_agent_layout -v`

Expected: fail because the Antigravity rule does not exist and the root instructions do not yet contain the font rule.

- [ ] **Step 2: Keep `AGENTS.md` concise while adding the font/package rule**

Add one non-negotiable bullet:

```markdown
- Portable theme assets stay inside `sample-themes/<name>/`: custom fonts are optional licensed WOFF2 files, external font URLs are forbidden, and every built ZIP contains exactly one theme.
```

Do not paste sections from `docs/AGENT_SPEC.md`; keep the existing links to detailed docs and skills.

- [ ] **Step 3: Create the Antigravity always-active rule**

The rule must include this complete operational core:

```markdown
---
trigger: always_on
description: Mandatory Oracle APEX Theme Factory architecture and safety boundaries.
---

# APEX Theme Factory workspace rule

- Read `docs/AGENT_SPEC.md`, `docs/PROJECT.md`, and `.agents/knowledge/pitfalls.md` before theme, runtime, or import work.
- Target only APEX 26.1.x, Universal Theme 42, and the Iris light style. Never switch styles or use Theme Roller.
- Runtime truth comes from the `chrome-devtools-mcp` server attached to the user's running Chrome.
- Declarative source is `applications/ut/` in APEXLang. Import only when the user explicitly asks.
- Appearance belongs in shared `static-files/css` plus scoped `sample-themes/<name>/css`; interaction belongs in `static-files/js/components`.
- Portable packages contain one theme. Custom fonts must be package-local licensed WOFF2 files; external font URLs are forbidden.
- Use `.agents/skills/design-to-apex/SKILL.md` as the design-work router and load only the focused skills it names.
```

- [ ] **Step 4: Repair and verify symlinks without replacing valid links**

For every directory under `.agents/skills/`, require `.claude/skills/<name>` to be a relative symlink to `../../.agents/skills/<name>`. Require `CLAUDE.md -> AGENTS.md` and `.agent/skills -> ../.agents/skills`. If an unexpected regular file occupies a required path, stop and report it instead of deleting it.

```bash
test -L CLAUDE.md && test "$(readlink CLAUDE.md)" = "AGENTS.md"
test -L .agent/skills && test "$(readlink .agent/skills)" = "../.agents/skills"
for skill in .agents/skills/*; do
  name="${skill##*/}"
  link=".claude/skills/$name"
  if [[ -e "$link" && ! -L "$link" ]]; then
    echo "refusing to replace non-symlink: $link" >&2
    exit 1
  fi
  [[ -L "$link" ]] || ln -s "../../.agents/skills/$name" "$link"
  [[ "$(readlink "$link")" = "../../.agents/skills/$name" ]]
done
```

- [ ] **Step 5: Correct `.agents/README.md` discovery documentation**

Replace the runtime table with separate instruction and skill columns. Codex uses `AGENTS.md` plus `.agents/skills`; Claude uses `CLAUDE.md` plus `.claude/skills`; Antigravity uses `.agents/rules/apex-theme-factory.md` plus `.agents/skills`; `.agent/skills` is labeled legacy only.

- [ ] **Step 6: Run the structural verifier**

Run: `python3 -m unittest tests.test_agent_layout -v && scripts/check-agent-layout.sh`

Expected: the unit suite passes; the repository check now fails only on the stale initialization prompt handled in Task 3.

- [ ] **Step 7: Commit runtime discovery layout**

```bash
git add AGENTS.md .agents/rules/apex-theme-factory.md .agents/README.md .claude/skills .agent/skills CLAUDE.md tests/test_agent_layout.py
git commit -m "feat: align codex claude and antigravity discovery"
```

---

### Task 3: Idempotent Session-Readiness Prompt

**Files:**
- Modify: `sample-prompts/init.md`
- Modify: `tests/test_agent_layout.py`

**Interfaces:**
- Consumes: canonical instruction and skill paths from Task 2.
- Produces: one safe prompt that reports project readiness and stops before changes.

- [ ] **Step 1: Add a failing prompt-content test**

```python
def test_init_prompt_requests_evidence_and_stops(self):
    text = Path("sample-prompts/init.md").read_text(encoding="utf-8")
    for phrase in ("git status", "apex-validate.sh", "APEX_VERSION", "apex-theme-iris", "stop"):
        self.assertIn(phrase, text)
```

Run: `python3 -m unittest tests.test_agent_layout.AgentLayoutTests.test_init_prompt_requests_evidence_and_stops -v`

Expected: fail because the current prompt emphasizes initialization and does not use the final readiness contract.

- [ ] **Step 2: Replace the stale prompt completely**

The new prompt tells an agent to read instructions, report relevant skills, run `git status --short --branch`, run `scripts/apex-validate.sh` while explicitly acknowledging that it connects through the saved SQLcl connection, inspect the running APEX tab through the runtime-specific Chrome DevTools server, report app ID/alias/APEX version/Iris class, compare referenced assets with source, and stop before editing/importing/committing. It must never claim the folder is not a repository.

Replace the file with this exact prompt:

```markdown
Prepare this APEX Theme Factory workspace for a design session without changing it.

1. Read `AGENTS.md`, `docs/AGENT_SPEC.md`, `docs/PROJECT.md`, and `.agents/knowledge/pitfalls.md`; report the focused skills relevant to the requested work.
2. Run `git status --short --branch` and report existing changes without modifying them.
3. Run `scripts/apex-validate.sh`; state that this validation uses the configured saved SQLcl connection and report its real result.
4. Through this runtime's configured Chrome DevTools server, inspect the already-running APEX tab and report application ID, alias, APEX version, and the Iris theme class. Do not navigate or mutate the application.
5. Compare the page's referenced CSS and JavaScript assets with `static-files/` and report any drift.
6. Stop before editing files, importing APEXLang, committing, or changing browser/database state.

If a required runtime is unavailable, report that part as UNVERIFIED and continue with the remaining read-only checks.
```

- [ ] **Step 3: Run prompt and structural tests**

Run: `python3 -m unittest tests.test_agent_layout -v && scripts/check-agent-layout.sh`

Expected: both pass with `AGENT_LAYOUT status=PASS skills=20 claude_links=20 errors=0` unless the canonical skill count has intentionally changed; the test must derive the count rather than hard-code 20.

- [ ] **Step 4: Commit the readiness prompt**

```bash
git add sample-prompts/init.md tests/test_agent_layout.py
git commit -m "docs: make agent readiness prompt idempotent"
```

---

### Task 4: Cross-Runtime Smoke Contract and Harness

**Files:**
- Create: `tests/agent-smoke/readiness-prompt.md`
- Create: `tests/agent-smoke/result.schema.json`
- Create: `tools/agent_smoke.py`
- Create: `tests/test_agent_smoke.py`
- Create: `docs/AGENT_COMPATIBILITY.md`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: runtime name `codex|claude|antigravity`, repository root, and optional output date.
- Produces: `tests/agent-smoke/runs/{UTC-date}/{runtime}.json` plus `{runtime}.md`, and exit `0` PASS, `1` behavioral FAIL, `2` UNVERIFIED environment/auth/quota.

- [ ] **Step 1: Write the strict JSON schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["runtime", "instructionEntry", "routerSkill", "apexBoundary", "runtimeTruthTool", "importRequiresUserRequest", "wouldEdit"],
  "properties": {
    "runtime": {"enum": ["codex", "claude", "antigravity"]},
    "instructionEntry": {"type": "string", "minLength": 1},
    "routerSkill": {"const": ".agents/skills/design-to-apex/SKILL.md"},
    "apexBoundary": {"const": "APEX 26.1.x / Universal Theme 42 / Iris"},
    "runtimeTruthTool": {"type": "string", "minLength": 1},
    "importRequiresUserRequest": {"const": true},
    "wouldEdit": {"const": false}
  }
}
```

- [ ] **Step 2: Write a neutral read-only readiness prompt**

Ask the runtime to inspect project instruction/skill discovery, return only the schema object, state the exact APEX boundary, identify the configured Chrome runtime-truth server without calling it, confirm import authorization, and make no edits, commits, database calls, browser calls, or network calls. Do not tell it which entry file or router path it should find.

Use this exact neutral prompt:

```markdown
Inspect this repository's agent instructions and skill discovery paths. Return only one JSON object matching the supplied schema. Report the instruction entry you actually discovered, the design-work router skill you actually discovered, the exact supported APEX/theme/style boundary, and the configured Chrome runtime-truth server name. Confirm whether an application import requires an explicit user request and whether you would edit anything for this inspection. Do not edit files, commit, call a database, call a browser tool, or access the network.
```

- [ ] **Step 3: Write failing harness tests with fake runtime executables**

```python
# tests/test_agent_smoke.py
import json
import tempfile
import unittest
from pathlib import Path

from tools.agent_smoke import classify_result


class AgentSmokeTests(unittest.TestCase):
    def test_authentication_failure_is_unverified(self):
        verdict = classify_result("codex", 1, "authentication required", "")
        self.assertEqual(verdict.status, "UNVERIFIED")

    def test_wrong_boundary_is_fail(self):
        payload = {"runtime": "codex", "instructionEntry": "AGENTS.md", "routerSkill": ".agents/skills/design-to-apex/SKILL.md", "apexBoundary": "APEX 24", "runtimeTruthTool": "chrome-devtools", "importRequiresUserRequest": True, "wouldEdit": False}
        verdict = classify_result("codex", 0, "", json.dumps(payload))
        self.assertEqual(verdict.status, "FAIL")
```

Add cases for malformed JSON, extra prose, runtime mismatch, wrong entry path, wrong Chrome server name, quota/timeout, redaction of home paths/tokens/session IDs, and valid results for all three runtimes.

- [ ] **Step 4: Run the smoke harness tests and verify failure**

Run: `python3 -m unittest tests.test_agent_smoke -v`

Expected: import failure for `tools.agent_smoke`.

- [ ] **Step 5: Implement runtime command construction without a shell**

```python
COMMANDS = {
    "codex": lambda prompt, schema: [
        "codex", "exec", "--ephemeral", "--sandbox", "read-only",
        "--output-schema", str(schema), "-",
    ],
    "claude": lambda prompt, schema: [
        "claude", "-p", "--permission-mode", "plan", "--no-session-persistence",
        "--output-format", "json", "--json-schema", schema.read_text(encoding="utf-8"), prompt,
    ],
    "antigravity": lambda prompt, schema: [
        "agy", "-p", "--mode", "plan", "--sandbox", "--output-format", "json",
        "--json-schema", str(schema), prompt,
    ],
}
```

For Codex, pass the prompt through stdin because the final `-` requests stdin. For Claude and Antigravity, pass it as the final argument. Capture stdout/stderr, version, exit code, and elapsed time. Extract Codex's stdout as the schema object. For Claude and Antigravity JSON output, parse the outer result envelope and prefer its `structured_output` object; if only a `result` string exists, parse that string as JSON and reject extra prose. Never use `shell=True`, permission bypass flags, model overrides, or user configuration mutations.

- [ ] **Step 6: Implement validation, redaction, and worktree guard**

Snapshot `git status --porcelain=v1` and `git diff --binary` before the run; after the run, allow only new files inside the requested dated run directory. Parse a single JSON object, apply the schema's required/const checks in standard-library code, and enforce runtime-specific entries:

```python
EXPECTED = {
    "codex": ("AGENTS.md", "chrome-devtools"),
    "claude": ("CLAUDE.md", "chrome-devtools"),
    "antigravity": (".agents/rules/apex-theme-factory.md", "chrome-devtools-mcp"),
}
```

Replace absolute home paths with `<HOME>`, UUID/session-like values with `<SESSION>`, and values on lines containing `token`, `secret`, `password`, or `authorization` with `<REDACTED>` before writing evidence.

- [ ] **Step 7: Document compatibility and evidence limits**

`docs/AGENT_COMPATIBILITY.md` must include canonical paths, offline check command, smoke command `python3 tools/agent_smoke.py <runtime>`, expected JSON fields, exit/status semantics, the fact that results are behavioral evidence rather than loader telemetry when a CLI cannot expose loader internals, and a table whose latest-version/result cells begin `UNVERIFIED — run the release smoke` until Task 5.

- [ ] **Step 8: Run offline tests**

Run: `python3 -m unittest tests.test_agent_layout tests.test_agent_smoke -v && scripts/check-agent-layout.sh`

Expected: all tests and the structural check pass without invoking any model.

- [ ] **Step 9: Commit the smoke framework**

```bash
git add tests/agent-smoke/readiness-prompt.md tests/agent-smoke/result.schema.json tools/agent_smoke.py tests/test_agent_smoke.py docs/AGENT_COMPATIBILITY.md .gitignore
git commit -m "test: add read-only agent compatibility smokes"
```

---

### Task 5: Run and Record Live Codex, Claude, and Antigravity Smokes

**Files:**
- Create: `tests/agent-smoke/runs/2026-09-15/codex.json`
- Create: `tests/agent-smoke/runs/2026-09-15/codex.md`
- Create: `tests/agent-smoke/runs/2026-09-15/claude.json`
- Create: `tests/agent-smoke/runs/2026-09-15/claude.md`
- Create: `tests/agent-smoke/runs/2026-09-15/antigravity.json`
- Create: `tests/agent-smoke/runs/2026-09-15/antigravity.md`
- Modify: `docs/AGENT_COMPATIBILITY.md`

**Interfaces:**
- Consumes: authenticated local CLI sessions and the Task 4 harness.
- Produces: three independent dated PASS/FAIL/UNVERIFIED records; one runtime never substitutes for another.

- [ ] **Step 1: Confirm the worktree and CLI versions before spending quota**

Run: `git status --short && codex --version && claude --version && agy --version`

Expected: clean worktree and three version strings. If a CLI is missing, record that runtime as `UNVERIFIED` and continue with the others.

- [ ] **Step 2: Run Codex in read-only ephemeral mode**

Run: `python3 tools/agent_smoke.py codex --date 2026-09-15`

Expected: exit 0 and a result whose instruction entry is `AGENTS.md`, router is `.agents/skills/design-to-apex/SKILL.md`, runtime tool is `chrome-devtools`, import authorization is true, and wouldEdit is false. Authentication/quota exit 2 remains `UNVERIFIED`.

- [ ] **Step 3: Run Claude Code in plan mode**

Run: `python3 tools/agent_smoke.py claude --date 2026-09-15`

Expected: exit 0 and `CLAUDE.md`/router/`chrome-devtools`/true/false fields; authentication/quota exit 2 remains `UNVERIFIED`.

- [ ] **Step 4: Run Antigravity in sandboxed plan mode**

Run: `python3 tools/agent_smoke.py antigravity --date 2026-09-15`

Expected: exit 0 and `.agents/rules/apex-theme-factory.md`/router/`chrome-devtools-mcp`/true/false fields; authentication/quota exit 2 remains `UNVERIFIED`.

- [ ] **Step 5: Verify the repository was not modified by any model**

Run: `git status --short`

Expected: only the six expected run artifacts and the compatibility-document update are present. Any other path is a smoke `FAIL`; inspect and revert only the smoke-created path after preserving evidence.

- [ ] **Step 6: Update the compatibility matrix from recorded evidence**

For each runtime, copy its exact CLI version, UTC date, status, and evidence path into `docs/AGENT_COMPATIBILITY.md`. Do not turn `UNVERIFIED` into PASS based on another runtime or the structural verifier.

Use one row per runtime with this fixed column order:

```markdown
| Runtime | CLI version | Checked at (UTC) | Structural | Behavioral | Evidence |
|---|---|---|---|---|---|
| Codex | recorded by harness | recorded by harness | PASS | PASS/FAIL/UNVERIFIED | `tests/agent-smoke/runs/2026-09-15/codex.md` |
| Claude Code | recorded by harness | recorded by harness | PASS | PASS/FAIL/UNVERIFIED | `tests/agent-smoke/runs/2026-09-15/claude.md` |
| Antigravity | recorded by harness | recorded by harness | PASS | PASS/FAIL/UNVERIFIED | `tests/agent-smoke/runs/2026-09-15/antigravity.md` |
```

- [ ] **Step 7: Re-run structural checks and commit dated evidence**

Run: `python3 -m unittest tests.test_agent_layout tests.test_agent_smoke -v && scripts/check-agent-layout.sh`

Expected: all offline checks pass.

```bash
git add tests/agent-smoke/runs docs/AGENT_COMPATIBILITY.md
git commit -m "test: record agent compatibility smokes"
```

## Plan Acceptance

- `scripts/check-agent-layout.sh` passes and reports the derived canonical skill/link counts.
- Codex, Claude Code, and Antigravity each resolve the intended instruction entry and shared router.
- The initialization prompt is safe on an existing repository and stops before changes.
- Smoke commands contain no permission bypass and leave no model-created worktree changes.
- Dated behavioral evidence is stored separately per runtime with explicit PASS/FAIL/UNVERIFIED status.
- A structural pass is never presented as proof that an authenticated model actually loaded the files.
