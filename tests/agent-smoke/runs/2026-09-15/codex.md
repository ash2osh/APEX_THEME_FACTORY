# Agent Compatibility Smoke: codex

- **Status:** PASS
- **CLI Version:** codex-cli 0.149.1
- **Run Date (UTC):** 2026-09-15
- **Verdict Message:** All assertions passed

## Result Payload

```json
{
  "runtime": "codex",
  "instructionEntry": "AGENTS.md",
  "routerSkill": ".agents/skills/design-to-apex/SKILL.md",
  "apexBoundary": "APEX 26.1.x / Universal Theme 42 / Iris",
  "runtimeTruthTool": "chrome-devtools",
  "importRequiresUserRequest": true,
  "wouldEdit": false
}
```

## Raw Execution Output (Redacted)

### Standard Output
```text
{"runtime":"codex","instructionEntry":"AGENTS.md","routerSkill":".agents/skills/design-to-apex/SKILL.md","apexBoundary":"APEX 26.1.x / Universal Theme 42 / Iris","runtimeTruthTool":"chrome-devtools","importRequiresUserRequest":true,"wouldEdit":false}
```

### Standard Error
```text
OpenAI Codex v0.149.1
--------
workdir: <HOME>/projects/APEX_THEME_FACTORY
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: <SESSION>
--------
user
Inspect this repository's agent instructions and skill discovery paths. Return only one JSON object matching the supplied schema. Report the instruction entry you actually discovered, the design-work router skill you actually discovered, the exact supported APEX/theme/style boundary, and the configured Chrome runtime-truth server name. Confirm whether an application import requires an explicit user request and whether you would edit anything for this inspection. Do not edit files, commit, call a database, call a browser tool, or access the network.

exec
/bin/bash -lc "sed -n '1,240p' <HOME>/.codex/plugins/cache/openai-curated-remote/superpowers/6.3.0/skills/using-superpowers/SKILL.md" in <HOME>/projects/APEX_THEME_FACTORY
 succeeded in 0ms:
---
name: using-superpowers
description: Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## The Rule

**Invoke relevant or requested skills BEFORE any response or action** — including clarifying questions, exploring the codebase, or checking files. If it turns out wrong for the situation, you don't have to use it.

**Before entering plan mode:** if you haven't already brainstormed, invoke the brainstorming skill first.

Then announce 
```
