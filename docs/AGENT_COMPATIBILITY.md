# Agent Compatibility Matrix and Smoke Contracts

This document records the discovery paths, runtime boundaries, offline validation commands, smoke harness contracts, and latest verification results for the three supported agent runtimes: **OpenAI Codex**, **Claude Code**, and **Google Antigravity**.

## 1. Supported Discovery Paths

| Runtime | Instruction Entry | Skills Discovery | Chrome DevTools MCP Tool |
|---|---|---|---|
| **Codex** | `AGENTS.md` (canonical root instructions) | `.agents/skills/` (native read) | `chrome-devtools` |
| **Claude Code** | `CLAUDE.md` (symlink to `AGENTS.md`) | `.claude/skills/<name>` (symlinks to `.agents/skills/`) | `chrome-devtools` |
| **Antigravity** | `.agents/rules/apex-theme-factory.md` (always-on rule) | `.agents/skills/` (native; `.agent/skills` legacy symlink) | `chrome-devtools-mcp` |

- Canonical skills reside in `.agents/skills/<name>/SKILL.md`.
- Router skill for design implementation: `.agents/skills/design-to-apex/SKILL.md`.
- Supported boundary: **APEX 26.1.x / Universal Theme 42 / Iris**.
- Application import authorization: **Explicit user confirmation required**; never import without a direct user request.
- Changes during inspection: **None** (`wouldEdit: false`).

## 2. Structural Layout Verification

Run the offline structural verifier to confirm entry files, symlinks, rules, and skill metadata across all runtimes without network or model access:

```bash
scripts/check-agent-layout.sh
```

Expected output:
```text
AGENT_LAYOUT status=PASS skills=20 claude_links=20 errors=0
```

## 3. Smoke Test Harness

The smoke runner executes the runtime in read-only / plan mode with a neutral prompt (`tests/agent-smoke/readiness-prompt.md`) and validates the returned JSON against `tests/agent-smoke/result.schema.json`.

```bash
python3 tools/agent_smoke.py <codex|claude|antigravity> [--date YYYY-MM-DD]
```

### Exit and Status Semantics

- **`0` (PASS):** Runtime completed successfully, produced valid JSON conforming to the schema, identified the expected entry file and Chrome tool, and respected all safety boundaries.
- **`1` (FAIL):** Runtime executed but returned incorrect paths, wrong boundary, attempted edits, or produced invalid output.
- **`2` (UNVERIFIED):** Runtime CLI is not installed, unauthenticated, out of quota, or timed out. This is not a failure of repository compatibility, but indicates that environment prerequisites were not met.

### Nature of Evidence

When a CLI does not expose its internal loader telemetry, the recorded result serves as **behavioral evidence** that the agent discovered and respects the project boundaries when given a neutral readiness prompt.

## 4. Latest Smoke Results

| Runtime | CLI version | Checked at (UTC) | Structural | Behavioral | Evidence |
|---|---|---|---|---|---|
| Codex | codex-cli 0.154.0 | 2026-09-17 | PASS | PASS | `tests/agent-smoke/runs/2026-09-17/codex.md` |
| Claude Code | 2.1.273 | 2026-09-17 | PASS | PASS | `tests/agent-smoke/runs/2026-09-17/claude.md` |
| Antigravity | 1.2.5 | 2026-09-17 | PASS | PASS | `tests/agent-smoke/runs/2026-09-17/antigravity.md` |

**All three PASS as of 2026-09-17** — the first round in which every runtime was green, which is what let
Layer E reach PASS in the release reports.

Why they were re-run that day rather than reused from 2026-09-16: these smokes measure what a runtime does
after reading `AGENTS.md`, `.agents/rules/*.md` and the skills — all Markdown, which `last_source_commit()`
treats as *non*-source. Adding the Chrome-daemon rule to those files therefore changed the thing under test
without invalidating any binding automatically, so the re-run was done by hand. Treat any edit under
`AGENTS.md`, `.agents/rules/` or `.agents/skills/` the same way (`.agents/knowledge/pitfalls.md` §5.x).

Earlier records are kept for history: `tests/agent-smoke/runs/2026-09-16/` (Claude Code `UNVERIFIED` —
headless `claude -p` could not authenticate, OAuth session expired; Antigravity 1.2.4 `UNVERIFIED` on a later
attempt — provider returned `503 No capacity`, confirmed environmental by a control run against the previous
schema) and `tests/agent-smoke/runs/2026-09-15/` (Claude Code "not installed", Antigravity "timed out" — both
environmental).

### Harness notes

- `tests/agent-smoke/result.schema.json` must stay free of a `$schema` dialect pointer: `claude --json-schema` rejects `https://json-schema.org/draft/2020-12/schema` outright. A CLI rejecting the schema is classified `FAIL` (harness defect), never `UNVERIFIED`.
- Absolute paths inside the repository are normalised to repo-relative form before comparison; paths outside the repository fail.
- The worktree guard compares `git status` before and after the run. Do not edit the repository while a smoke runs — the guard cannot tell a model's edit from yours.
