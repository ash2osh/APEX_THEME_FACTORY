# APEX Theme Factory: Full Implementation & Chrome DevTools MCP Daemon Report

**Date:** 2026-09-15  
**Target Environment:** Oracle APEX 26.1.4 | Universal Theme 42 | Theme Style: Iris (Light)  
**Workspace:** `DEMO` | **Primary Application:** `102` (`UT`)  
**Repository Branch:** `main` (Clean at commit `7c2d4a9`)

---

## Executive Summary

All three design and engineering specifications in `docs/superpowers/specs/` have been implemented, tested offline and live against the running Oracle APEX database, verified in Chrome via the persistent DevTools MCP daemon, and committed to git:

1. **Portable Single-Theme Distribution (`2026-09-15-portable-single-theme-distribution.md`)**
   - Implemented deterministic packaging (`theme_factory.archive`), comment-preserving CSS bundling (`theme_factory.css_bundle`), and strict manifest validation (`theme_factory.manifest`).
   - Implemented self-contained CLI and install engine (`theme_factory.install` / `installer/install.sh`) supporting staged APEXLang declarative patching, immutable backups, drift detection, and reversible uninstallation (`theme_factory.uninstall`).
   - Implemented multi-theme coexistence with namespaced `localStorage` persistence and client-side switcher.

2. **Agent Runtime Compatibility (`2026-09-15-agent-runtime-compatibility.md`)**
   - Reorganized repository skills to the canonical 20-skill layout with frontmatter, router links, and layout verification via `scripts/check-agent-layout.sh`.
   - Updated ambiguous evaluation scenarios (01–05) and 7 pending findings with explicit live evidence criteria.

3. **Theme Factory Verification & Release (`2026-09-15-theme-factory-verification-release.md`)**
   - Created credential-free offline gate (`tests/run-offline.sh` executing 178 unit tests).
   - Created Page 409 Alpine lifecycle fixture (`p00409-theme-factory-lifecycle.apx`), deployed to live App 102, and verified dynamic refresh, item synchronization (`P409_DISCLOSURE_OPEN`), and zero console errors.
   - Built disposable consumer fixtures (Minimal `9010` and Business `9011`), verified single-theme install, multi-theme coexistence, switcher switching, state persistence, and clean uninstallation, followed by clean removal.
   - Built release report engine (`theme_factory.release` / `scripts/release-check.sh`) and generated `VERIFIED` release reports for both `linen` and `solarized-dark` across Layers A through E.

4. **Chrome DevTools MCP Daemon**:
   - Engineered a background daemon architecture (`tools/chrome_mcp_daemon.py` and `tools/chrome_devtools_client.py`) that eliminated repeated Chrome remote debugging consent popups by holding a single persistent session over a Unix domain socket (`/tmp/chrome_mcp.sock`).

---

## Chrome DevTools MCP Daemon Architecture & Usage

### 1. Problem Analysis: Why Chrome Repeatedly Prompted for Consent

When Chrome runs with remote debugging enabled (`--remote-debugging-port=9222`), Chrome's internal security model displays a user consent dialog:
> *"An application wants to start debugging Chrome. Do you want to allow it?"*

Whenever a client process runs `npx -y chrome-devtools-mcp@latest --auto-connect`, it opens a new connection to port 9222. When that command finishes, the process exits, tearing down the session. Every subsequent tool call spawns a *new* process, prompting the user again every few seconds.

### 2. Daemon Solution Architecture

To solve this permanently without compromising security or restarting Chrome:

```
┌────────────────────────────────────────────────────────┐
│ User's Running Google Chrome (Remote Debugging :9222)   │
└───────────────────────────▲────────────────────────────┘
                            │ Single Persistent CDP Connection
┌───────────────────────────┴────────────────────────────┐
│ Background Daemon: tools/chrome_mcp_daemon.py          │
│ - Launches chrome-devtools-mcp subprocess once         │
│ - Keeps stdin/stdout open indefinitely                 │
│ - Listens on Unix domain socket: /tmp/chrome_mcp.sock │
└───────────────────────────▲────────────────────────────┘
                            │ UNIX Socket JSON Requests
┌───────────────────────────┴────────────────────────────┐
│ Client Helper: tools/chrome_devtools_client.py         │
│ - Connects to socket /tmp/chrome_mcp.sock              │
│ - Sends tool calls (navigate, eval, screenshot, etc.)  │
│ - Receives sub-second JSON response with 0 prompts     │
└────────────────────────────────────────────────────────┘
```

- **Persistence**: `tools/chrome_mcp_daemon.py` runs once in the background. It connects to Chrome, prompts for approval **once**, and keeps that connection alive.
- **Fast Execution**: Any client script connects to `/tmp/chrome_mcp.sock`, sends a JSON payload specifying the MCP tool name and arguments, and receives the response in milliseconds without process spawn overhead.

---

### 3. Usage Guide: Client Helper & CLI

#### CLI Usage (`tools/chrome_devtools_client.py`)

You can execute any Chrome DevTools MCP tool directly from the terminal:

```bash
# List all open pages/tabs and their IDs
python3 tools/chrome_devtools_client.py list_pages

# Navigate page 1 to a specific URL
python3 tools/chrome_devtools_client.py navigate_page '{"pageId": 1, "url": "http://localhost:8181/ords/r/demo/ut/theme-factory-lifecycle"}'

# List console messages on page 1 (checks for JavaScript errors)
python3 tools/chrome_devtools_client.py list_console_messages '{"pageId": 1}'

# Evaluate JavaScript inside page 1
python3 tools/chrome_devtools_client.py evaluate_script '{"pageId": 1, "function": "() => document.title"}'

# Take a screenshot of page 1
python3 tools/chrome_devtools_client.py take_screenshot '{"pageId": 1, "filePath": "screenshot.png"}'
```

#### Python Programmatic Usage

You can import `ChromeDevToolsClient` in any script:

```python
from tools.chrome_devtools_client import ChromeDevToolsClient

client = ChromeDevToolsClient()

# 1. Inspect open pages
pages = client.call_tool("list_pages")
print("Open pages:", pages)

# 2. Navigate to an APEX page
client.navigate_page(page_id=1, url="http://localhost:8181/ords/r/demo/ut/home")

# 3. Evaluate DOM or APEX JavaScript state
result = client.evaluate_script(page_id=1, function_code="""() => {
    return {
        appId: window.apex?.env?.APP_ID,
        themeClass: document.documentElement.className,
        activeTheme: document.documentElement.dataset.appThemeCurrent,
        bodyBg: window.getComputedStyle(document.body).backgroundColor
    };
}""")
print("Runtime state:", result)

# 4. Check for console errors
console_msgs = client.call_tool("list_console_messages", {"pageId": 1})
print("Console logs:", console_msgs)
```

#### Daemon Lifecycle Management

- **Status Check**: Check if socket exists and daemon process is running:
  ```bash
  python3 -c "import socket; s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect('/tmp/chrome_mcp.sock'); print('Daemon alive!'); s.close()"
  ```
- **Auto-Spawn**: `ChromeDevToolsClient()` automatically checks for `/tmp/chrome_mcp.sock`. If not running, it starts `tools/chrome_mcp_daemon.py` automatically.
- **Stop Daemon**:
  ```bash
  pkill -f "python3 tools/chrome_mcp_daemon.py" && rm -f /tmp/chrome_mcp.sock
  ```

---

## Detailed Implementation Breakdown

### 1. Plan 1: Portable Single-Theme Distribution

#### Packaging Engine (`lib/theme_factory/`)
- `archive.py`: Deterministic packaging (`build_theme_package`, `verify_package`). Generates byte-identical ZIPs with normalized POSIX permissions (`0o644` files, `0o755` dirs), sorted zip entries, and SHA-256 verification against internal `checksums.sha256`.
- `css_bundle.py`: Local `@import` flattening, import cycle detection, rejection of protocol-relative or remote URL imports, and isolated `@font-face` generation.
- `manifest.py`: Validates `theme.json` schemas, semver compliance, licensed WOFF2 font declarations (with mandatory `OFL.txt` / license file check), and compatibility constraints (Universal Theme 42 / Iris only).

#### Installer & APEXLang Patch Engine (`lib/theme_factory/apexlang.py`, `install.py`)
- **Non-Mutating Staging**: Inspects APEXLang export trees in a read-only manner (`inspect_export`), preventing unintended directory modification prior to computing baseline digests.
- **Declarative Patching (`plan_install` / `apply_patch`)**:
  - `application.apx`: Ensures `globalPage: 0` in `userInterface {}` and adds package CSS URLs to `css { fileUrls: [...] }` preserving existing URLs.
  - `pages/p00000-global-page.apx`: Generates banner and dialog bootstrap regions with early-execution JavaScript preventing white flashes before paint.
  - `shared-components/navigation/lists/navigation-bar.apx`: Injects managed theme switcher list entries when `--with-switcher` is selected.
  - `shared-components/static-files.apx`: Registers theme static assets (`theme.css`, `theme.json`, `cover.jpg`, runtime JS, and `registry.json`).
- **Drift Protection**: Validates staged changes using `apex validate -workspace DEMO`. Re-exports the application from the live database to confirm no external modifications occurred during staging.
- **Immutable Backups**: Creates timestamped backups in `theme-factory-backups/<workspace>-<app_id>/<timestamp>-before-<theme>/` with `target.json` containing export SHA-256 digests.
- **Reversible Uninstaller (`uninstall.py`)**:
  - Automatically cleans up static files and CSS references.
  - When multiple themes are installed, uninstallation of one theme automatically falls back to the remaining theme, updating Page 0 bootstrap regions and switcher entries without duplicate components.

---

### 2. Plan 2: Agent Runtime Compatibility

- **20-Skill Canonical Hierarchy**: Organized under `.agents/skills/` and mirrored in `.agent/skills/`.
  - Skill router: `design-to-apex`.
  - Focused skills: `apex-ut-dom-knowledge`, `apex-alpine-lifecycle`, `apex-alpine-components`, `apex-alpine-server-integration`, `apex-css-design-system`, `apex-css-selector-strategy`, `apex-template-options`, `apex-component-selection`, `apex-layout-design`, `apex-responsive-design`, `apex-visual-comparison`, `apex-design-system`, `apex-accessibility`, `apexlang-design-editor`, `apexlang-roundtrip`, `chrome-devtools-mcp`, `impeccable`, `web-design-guidelines`, `a11y-debugging`.
- **Validation Suite**:
  - `tests/test_agent_layout.py`: Enforces skill structure, descriptions, and Claude desktop link format.
  - `scripts/check-agent-layout.sh`: Validates layout integrity, link integrity, and router linkage.
  - `tests/test_agent_smoke.py`: Ensures router resolves design goals to the correct subset of skills.
- **Evaluations & Findings**:
  - Resolved ambiguous evaluation suites (01–05) by requiring explicit runtime evidence.
  - Updated pending findings in `.agents/findings/pending/` with exact criteria for validation.

---

### 3. Plan 3: Verification & Release Gate

#### Unified Offline Gate (`tests/run-offline.sh`)
- Enforces bash syntax checking (`bash -n`).
- Runs 117 unit tests across manifests, CSS bundling, archive determinism, runtime contracts, APEXLang patching, SQLcl execution, and agent layout.
- Runs 61 package and uninstaller tests.
- Validates repository cleanliness (no uncommitted dirty files).
- Executes in under 4 seconds without database or browser dependencies.

#### Live APEX & Alpine Lifecycle Verification (Page 409)
- Provisioned Page 409 (`p00409-theme-factory-lifecycle.apx`) to live application 102.
- Verified dynamic region refresh via `apex.region('theme_factory_disclosure_region').refresh()`.
- Verified item sync: Alpine disclosure state binds bidirectionally to `P409_DISCLOSURE_OPEN` (`"N"` -> `"Y"` -> `"N"`).
- Verified runtime parity report: 12 out of 12 checks passed (App ID, alias, theme number, base theme, theme style, CSS URLs, JavaScript URLs, Alpine object, console, network, body classes, HTML classes).

#### Multi-Consumer Topology Verification (Apps 9010 & 9011)
- **App 9010 (Minimal Consumer)**:
  - Installed `linen` 1.0.0.
  - Verified `html` class `app-theme-linen`, background `#fbf9f8`, clean console.
- **App 9011 (Business Consumer)**:
  - Installed `solarized-dark` 1.0.0 with `--with-switcher`.
  - Installed second theme `linen` 1.0.0.
  - Verified registry contains both themes.
  - Tested theme switcher in browser: switching to `solarized-dark` applied `#002b36`, switching to `iris` restored base Iris light styles.
  - Tested persistence: `localStorage["apex.themeFactory.9011"]` retained choice across page reloads.
  - Tested uninstallation: cleanly removed `linen`, updated Page 0 bootstrap to `solarized-dark` as sole default, with zero duplicate components.
  - Cleaned up fixtures using `scripts/cleanup-consumer-fixtures.sh`.

#### Release Reports & Final Gate
- Created `lib/theme_factory/release.py` and `scripts/release-check.sh`.
- Enforces five-layer verification requirement (Layers A, B, C, D, E must all be `PASS` to earn `VERIFIED`).
- Generated release reports:
  - `dist/linen/RELEASE-REPORT.md`: **`VERIFIED`**
  - `dist/solarized-dark/RELEASE-REPORT.md`: **`VERIFIED`**

---

## Verification Evidence Matrix

| Layer | Verification Gate | Evidence Artifact | Verdict |
|---|---|---|:---:|
| **Layer A** | Offline source, packaging & CSS policy gate | `tests/run-offline.sh` (178 unit tests pass) | **PASS** |
| **Layer B** | Source to database export parity | `.agents/evaluations/runtime/20260915T163631Z-parity.json` (12/12 match) | **PASS** |
| **Layer C** | Browser runtime truth (Chrome DevTools) | `.agents/evaluations/runtime/2026-09-15-p409-evidence.json` (Page 409 verified) | **PASS** |
| **Layer D** | Multi-consumer fixture topologies & persistence | Apps 9010 & 9011 tested live, switcher verified, clean uninstalled | **PASS** |
| **Layer E** | Agent layout & evaluation scenarios | `scripts/check-agent-layout.sh` & `.agents/evaluations/` | **PASS** |

---

## Current Repository & Database State

- **Git Commit**: `7c2d4a9` (`feat: complete verification and release matrix for single-theme packages`)
- **Working Tree**: Clean (`git status` shows nothing to commit).
- **Primary Database App (102)**: Running with Page 409 lifecycle fixture intact.
- **Consumer Fixtures (9010, 9011)**: Completely cleaned up and removed from workspace `DEMO`.
- **Persistent Chrome DevTools Daemon**: Active and listening on `/tmp/chrome_mcp.sock`.
