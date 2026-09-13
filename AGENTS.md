# APEX Theme Factory — agent instructions

You are the Oracle APEX design-engineering agent defined in **docs/AGENT_SPEC.md**. Read it first.
Then read **docs/PROJECT.md** for the target app, URL, connection and hard constraints.

Non-negotiables
- APEX 26.1.4, Universal Theme, theme style **Iris only** (light). Never switch styles or use Theme Roller.
- Runtime truth = Chrome DevTools MCP against the user's running Chrome (`--autoConnect`); see docs/CHROME_DEVTOOLS_MCP.md.
- Declarative source = `applications/ut/` (APEXLang, app 102, workspace DEMO) via SQLcl `docker-demo`; see docs/APEXLANG_ROUNDTRIP.md. Import only when the user asks.
- Appearance = `static-files/css` (shared foundation + `--app-*` vocabulary aliasing Iris) plus theme packages in `sample-themes/<name>/css` scoped to `html.app-theme-<name>`; interaction = Alpine in `static-files/js/components`. Assemble with `scripts/sync-static.sh` before `apex-import`; default theme via `scripts/apply-theme.sh`.

Skills live in `.agents/skills/` (router: `design-to-apex`). Knowledge, findings and evaluations are in `.agents/`.
Component registry: docs/COMPONENTS.md. Tokens and conventions: docs/DESIGN_SYSTEM.md.
