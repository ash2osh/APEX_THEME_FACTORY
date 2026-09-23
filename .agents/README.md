# .agents — knowledge for the APEX design agent

```text
.agents/
├── skills/        # reusable rules & techniques (SKILL.md each). Router: design-to-apex
│                  #   external: impeccable, web-design-guidelines (npx skills; skills-lock.json)
├── knowledge/     # verified reference facts (Iris tokens, UT DOM, runtime facts) + pitfalls.md (traps & fixes)
└── rules/         # Antigravity workspace rule
```

Exposure to agent runtimes:

| Runtime | Instructions / Rules | Skills Discovery |
|---|---|---|
| Codex | `AGENTS.md` | `.agents/skills/` (native) |
| Claude Code | `CLAUDE.md` (symlink to `AGENTS.md`) | `.claude/skills/<name>` (symlinks to `.agents/skills/`) |
| Antigravity | `.agents/rules/apex-theme-factory.md` (workspace rule) | `.agents/skills/` (native; `.agent/skills` legacy compatibility symlink only) |

When something surprises you, record it in `knowledge/pitfalls.md` (entry in its layer file, heading in the
index). Change a skill only when the lesson is reusable; skills hold rules, not a diary of discoveries.
