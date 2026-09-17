---
trigger: always_on
description: Mandatory Oracle APEX Theme Factory architecture and safety boundaries.
---

# APEX Theme Factory workspace rule

- Read `docs/AGENT_SPEC.md`, `docs/PROJECT.md`, and `.agents/knowledge/pitfalls.md` before theme, runtime, or import work.
- Target only APEX 26.1.x, Universal Theme 42, and the Iris light style. Never switch styles or use Theme Roller.
- Runtime truth comes from Chrome DevTools via the `chrome-devtools-mcp` server attached to the user's running Chrome.
- Reach it only through the project daemon: `python3 tools/chrome_devtools_client.py <tool> '<json-args>'`. Never call a
  `chrome-devtools` MCP tool directly and never start a second daemon — both trigger a Chrome consent prompt the user
  may not be present to accept, and the second instance can wedge the approved session.
- Declarative source is `applications/ut/` in APEXLang. Import only when the user asks.
- Appearance belongs in shared `static-files/css` plus scoped `sample-themes/<name>/css`; interaction belongs in `static-files/js/components`.
- Portable packages contain one theme. Custom fonts must be package-local licensed WOFF2 files; external font URLs are forbidden.
- Use `.agents/skills/design-to-apex/SKILL.md` as the design-work router and load only the focused skills it names.
