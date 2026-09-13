# Chrome DevTools MCP — install & usage

`chrome-devtools-mcp` (Google, https://github.com/ChromeDevTools/chrome-devtools-mcp) gives agents
Puppeteer/CDP access to Chrome: pages, snapshots, screenshots, `evaluate_script`, console,
network, emulation, performance traces.

In this project it connects to **the user's already-running Chrome** (not a throw-away profile)
so it sees the APEX Builder session, cookies and the logged-in app.

## How the connection works

Chrome ≥ 144 exposes a user-consented remote-debugging endpoint:

1. In Chrome open `chrome://inspect/#remote-debugging` and enable **Allow remote debugging for this browser**.
   (Verified on this machine: `~/.config/google-chrome/Local State` → `"remote_debugging":{"user-enabled":true}`,
   `~/.config/google-chrome/DevToolsActivePort` → port `9222`.)
2. Start the server with `--autoConnect`. It reads `DevToolsActivePort` from the stable-channel
   profile and attaches. No `--remote-debugging-port` flag on Chrome is needed.
3. The **first** tool call after start can take 20–40 s (Chrome may show a consent prompt).
   Later calls are fast. Don't treat a slow first `list_pages` as a failure.

`http://127.0.0.1:9222/json/version` returns an empty body in this mode — that is expected; the
endpoint is gated, not broken.

## Global installation (done 2026-09-13)

```bash
npm i -g chrome-devtools-mcp@latest          # binary: chrome-devtools-mcp (v1.9.0 at install time)
```

| Client | Config location | Server name | Command |
|---|---|---|---|
| Claude Code | `~/.claude.json` (user scope) via `claude mcp add --scope user chrome-devtools -- npx -y chrome-devtools-mcp@latest --autoConnect` | `chrome-devtools` | `npx -y chrome-devtools-mcp@latest --autoConnect` |
| Codex | `~/.codex/config.toml` `[mcp_servers.chrome-devtools]` via `codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --autoConnect` | `chrome-devtools` | same |
| Antigravity | `~/.gemini/config/mcp_config.json` → `mcpServers.chrome-devtools-mcp` (pre-existing) | `chrome-devtools-mcp` | `npx -y chrome-devtools-mcp@latest --auto-connect` |

Re-run the `add` commands (or edit the files) to reinstall on another machine. Backups of the
Codex config are kept next to it as `config.toml.bak-<timestamp>`.

## Tool cheat-sheet (v1.9)

All page-scoped tools require `pageId` (from `list_pages`) because `--pageIdRouting` is on by default.

| Need | Tool |
|---|---|
| Find the APEX tab | `list_pages` → pick the `localhost:8181/ords/r/demo/ut/...` entry |
| Open / reload a page | `navigate_page {pageId, url}` / `navigate_page {pageId, type:"reload"}` |
| Accessibility tree with uids | `take_snapshot {pageId}` |
| Screenshot (whole page / element) | `take_screenshot {pageId, fullPage?, uid?}` |
| Runtime DOM / computed CSS / apex.env | `evaluate_script {pageId, function:"() => ..."}` |
| Console errors | `list_console_messages {pageId}` |
| Network failures | `list_network_requests {pageId}` |
| Responsive check | `resize_page {pageId, width, height}` or `emulate {pageId, ...}` |
| Click / type | `click {pageId, uid}` / `fill {pageId, uid, value}` |

### `evaluate_script` snippets for APEX

```js
// identify page + theme
() => ({ app: apex.env.APP_ID, page: apex.env.APP_PAGE_ID, v: apex.env.APEX_VERSION,
         body: document.body.className })

// which region owns an element, and its Static ID
() => { const el = document.querySelector('.t-Region'); const r = el.closest('.t-Region');
        return { id: r.id, classes: r.className, staticId: r.dataset.regionId ?? r.id }; }

// winning computed values for a selector
() => { const cs = getComputedStyle(document.querySelector('.t-Region-header'));
        return ['padding','background-color','border-radius','box-shadow'].map(p => [p, cs.getPropertyValue(p)]); }

// read Iris design tokens
() => Object.fromEntries(['--ut-palette-primary','--ut-border-radius-lg','--ut-shadow-md']
        .map(n => [n, getComputedStyle(document.documentElement).getPropertyValue(n).trim()]))

// prototype a CSS change (temporary — must be moved to static-files/css afterwards)
() => { const s = document.createElement('style'); s.id = 'proto'; s.textContent = '.app-x{padding:1rem}';
        document.head.append(s); return 'ok'; }
```

## Rules for this project (spec §13–14, §47, §49)

- DevTools is for **inspect, prototype, verify** — never the place where a change lives.
- After every significant change: reload → `list_console_messages` → screenshot → compare → fix source.
- Test refreshable regions after refresh (spec §32) and at ≥ 3 viewport widths (spec §45).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `list_pages` hangs > 60 s | Remote debugging toggle off in `chrome://inspect/#remote-debugging`, or Chrome not running. Check `DevToolsActivePort` exists. |
| Connects to an empty browser | `--autoConnect` missing → it launched its own profile. Fix the client config. |
| `Required at pageId` | Pass `pageId` from `list_pages` on every page-scoped call. |
| Wrong Chrome channel | Add `--channel=beta|dev|canary` to match the running Chrome. |
