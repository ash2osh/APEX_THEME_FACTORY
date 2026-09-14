# .agents — controlled knowledge for the APEX design agent

Structure required by [docs/AGENT_SPEC.md](../docs/AGENT_SPEC.md) §50–§62.

```text
.agents/
├── skills/        # reusable rules & techniques (SKILL.md each). Router: design-to-apex
│                  #   external: impeccable, web-design-guidelines (npx skills; skills-lock.json)
├── knowledge/     # verified reference facts (Iris tokens, UT DOM, runtime facts) + pitfalls.md (traps & fixes, by layer)
├── findings/      # discoveries awaiting review → pending / accepted / rejected
└── evaluations/   # regression scenarios the skills must pass
```

Exposure to agent runtimes (all point at `.agents/skills`):

| Runtime | Path |
|---|---|
| Codex | reads `.agents/skills/` natively |
| Claude Code | `.claude/skills/<name>` → symlink |
| Antigravity | `.agent/skills` → symlink |

## Lifecycle of a discovery (spec §58)

1. Write `findings/pending/<yyyy-mm-dd>-<slug>.md` from `findings/TEMPLATE.md`.
2. Classify (§51) and set confidence (§57). One page is weak evidence.
3. Add or update an evaluation scenario that fails under the old assumption.
4. Make the smallest skill/knowledge change. Re-run the evaluation.
5. Move the finding to `accepted/` (or `rejected/` with a reason).

Skills are not diaries (§59): observations go to `knowledge/`, page facts go to `docs/` or the
finding itself.
