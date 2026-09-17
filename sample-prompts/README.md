# Sample prompts

Starter prompts for driving this project with an agent CLI (Claude Code, Codex, Antigravity — they are written
runtime-agnostically). Copy one, fill in the `<< … >>` placeholders, and paste it as your first message.

They are starting points, not incantations: edit them freely. What they encode is the handful of things this
project has learned the hard way — measure before you write, name the layer a fix belongs in, and never let a
missing check become a pass.

## Which one

| Prompt | Use when | Blast radius |
|---|---|---|
| [`init.md`](init.md) | Starting a session and you want the workspace checked before touching anything | read-only |
| [`install-theme.md`](install-theme.md) | Putting a packaged theme into your own APEX app | database, gated on your go-ahead |
| [`uninstall-theme.md`](uninstall-theme.md) | Removing a theme, or rolling back to the pre-install backup | database, gated on your go-ahead |
| [`new-theme-from-design.md`](new-theme-from-design.md) | Turning a Figma / screenshot / written direction into a theme package | edits `sample-themes/<name>/`, builds a ZIP |
| [`restyle-component.md`](restyle-component.md) | Changing how one Universal Theme component looks | edits theme CSS |
| [`harden-dark-theme.md`](harden-dark-theme.md) | A dark package looks right at rest but breaks in selection, charts or dialogs | edits theme CSS |
| [`accessibility-audit.md`](accessibility-audit.md) | Checking AA contrast properly, including driven states | read-only |
| [`diagnose-runtime.md`](diagnose-runtime.md) | Something in the running app is wrong and you want the mechanism, not a workaround | read-only, then a proposal |
| [`release-verify.md`](release-verify.md) | Deciding whether a package can honestly ship | read-only |

## What they have in common

Each prompt states four things up front, and it is worth keeping that shape if you write your own:

1. **The boundary** — APEX 26.1.x, Universal Theme 42, theme style Iris only.
2. **The blast radius** — read-only, edits source, or needs your authorization before a database write. Stated
   explicitly so the agent asks instead of assuming.
3. **Browser access through the project daemon**
   (`python3 tools/chrome_devtools_client.py <tool> '<json-args>'`), never a direct MCP call — Chrome's
   debugging consent is per connection, so a direct call raises a prompt only the person at the machine can
   accept, and unattended work stops there.
4. **Measure, don't guess** — and report what was *not* covered. Several prompts require the count of nodes
   scanned alongside any "0 failures", because a scan that reached nothing looks exactly like a clean result.

## Related

- `AGENTS.md` — the always-on rules every runtime loads.
- `.agents/skills/design-to-apex/SKILL.md` — the router that design work goes through.
- `.agents/knowledge/pitfalls.md` — every trap met so far, with the fix. Worth reading before theme work.
- `README.md` (repo root) — the install / uninstall / build guides these prompts drive.
