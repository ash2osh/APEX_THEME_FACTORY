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

### Contrast audit (run before calling any theme or restyle "verified")

Every visible text node vs its *blended* effective background (walks up through translucent layers), AA
thresholds (4.5:1, or 3:1 for ≥ 24 px / bold ≥ 18.66 px). Returns the failures with selector, colours, ratio.
Pass it as the `function` of `evaluate_script` after the page has settled (Cards/IG render asynchronously —
wait ~1.5 s or hook their events first). Expect Universal Theme's own `u-color-*` demo fills (p1304) to fail
under every style; anything else is yours.

```js
async () => {
  await new Promise(r => setTimeout(r, 1500));
  const parse = c => { const m = c.match(/[\d.]+/g); if (!m) return null; const [r,g,b,a] = m.map(Number); return { r, g, b, a: a === undefined ? 1 : a }; };
  const lum = ({r,g,b}) => { const f = v => { v /= 255; return v <= 0.03928 ? v/12.92 : ((v+0.055)/1.055)**2.4; }; return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b); };
  const blend = (t, u) => ({ r: t.r*t.a+u.r*(1-t.a), g: t.g*t.a+u.g*(1-t.a), b: t.b*t.a+u.b*(1-t.a), a: 1 });
  const bgOf = el => { let e = el, acc = null; while (e && e !== document.documentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && c.a > 0) { acc = acc ? blend(acc, c) : c; if (c.a >= 0.999) return acc; } e = e.parentElement; } const body = parse(getComputedStyle(document.body).backgroundColor); return acc ? blend(acc, body) : body; };
  const cr = (a, b) => { const la = lum(a), lb = lum(b); return (Math.max(la,lb)+0.05)/(Math.min(la,lb)+0.05); };
  const bad = [], seen = new Set(), w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
  while ((n = w.nextNode())) {
    const t = n.textContent.trim(); if (t.length < 2) continue;
    const el = n.parentElement; if (!el || el.closest('#apexDevToolbar, script, style, [aria-hidden="true"], .u-VisuallyHidden')) continue;
    const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') continue;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const fg = parse(cs.color); if (!fg) continue; const bg = bgOf(el); const ratio = cr(fg.a < 1 ? blend(fg, bg) : fg, bg);
    const size = parseFloat(cs.fontSize), weight = parseInt(cs.fontWeight) || 400, need = (size >= 24 || (size >= 18.66 && weight >= 700)) ? 3 : 4.5;
    if (ratio < need) { const k = el.className + '|' + cs.color + '|' + t.slice(0, 20); if (seen.has(k)) continue; seen.add(k);
      bad.push({ text: t.slice(0, 40), sel: el.tagName.toLowerCase() + '.' + String(el.className).trim().split(/\s+/).slice(0, 3).join('.'), fg: cs.color, bg: `rgb(${Math.round(bg.r)}, ${Math.round(bg.g)}, ${Math.round(bg.b)})`, ratio: +ratio.toFixed(2), size }); }
  }
  return { page: apex.env.APP_PAGE_ID, html: document.documentElement.className, failures: bad.length, sample: bad.slice(0, 25) };
}
```

Offline, the same maths for a palette (pick tints that pass): `.agents/knowledge/pitfalls.md` §1.7.

### Working in the user's browser (etiquette)

- Open **your own tab** (`new_page {url, background:true}`) and close it when done; the user's tabs — and other
  agents' — keep their state.
- `emulate {pageId, viewport:"1440x900x1"}` (or `375x812x2,mobile,touch`) is per tab. `resize_page` resizes the
  shared Chrome window — avoid it.
- `localStorage` is shared by every tab of the origin: never navigate to `…#theme=<name>` for a capture (it
  rewrites the user's stored theme); swap `html.app-theme-*` in the DOM instead.
- Navigating to the current URL plus a hash is a same-document navigation — nothing reloads.
- For captures: hide `#apexDevToolbar` with a temporary `<style>`, blur the focused element, open the side nav
  with `t_Button_navControl`.

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
| `element.click()` on a menu item does nothing | The APEX menu widget listens to mouse events; use `click {pageId, uid}` from a `take_snapshot`. |
| A colour has no matching rule with `style.color` | The rule sets a **custom property** (`--a-…`) or lives in an `@import`ed sheet — check `style.getPropertyValue('--…')` and walk `rule.styleSheet.cssRules`. |
| Cards render empty / hooks miss them | Cards regions load after DOM-ready; wait, or hook `tablemodelviewpagechange` on `document`. |
