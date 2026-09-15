# Portable Single-Theme Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic, self-contained, single-theme ZIPs with optional licensed custom fonts, a safe SQLcl installer/uninstaller, an optional native APEX switcher, per-browser persistence, and complete manual installation instructions.

**Architecture:** A Python 3.10 standard-library package owns manifest validation, CSS/font assembly, deterministic archives, APEXLang transforms, SQLcl orchestration, and install/uninstall transactions. Thin Bash entry points call that package from the repository and from an extracted ZIP. All live changes use a fresh APEXLang export, exact-target checks, validation, a drift guard, and explicit application-ID confirmation; no internal APEX repository API is used.

**Tech Stack:** Python 3.10+ standard library (`argparse`, `dataclasses`, `hashlib`, `json`, `pathlib`, `re`, `subprocess`, `tempfile`, `zipfile`), Bash, Oracle SQLcl 26.1+ APEXLang commands, JavaScript ES5-compatible runtime, Oracle APEX 26.1.x Universal Theme 42/Iris.

**Spec:** `docs/superpowers/specs/2026-09-15-portable-single-theme-distribution-design.md`

## Global Constraints

- Support only Oracle APEX `26.1.x`, Universal Theme `42`, subscribed base theme `ut-26.1`, and current style `Iris`.
- Each ZIP contains exactly one theme manifest and one theme stylesheet.
- Custom fonts are optional, self-hosted WOFF2 files with bundled licenses; external font URLs and data URLs are forbidden.
- Font roles are `body`, optional `heading`, and optional `mono`; missing roles fall back to Oracle Sans or Iris' monospace stack.
- Keep Font APEX icons untouched.
- Use only Python's standard library; do not introduce a package-manager dependency.
- Dry-run is the default for install and uninstall; `--apply` still requires typing the exact numeric application ID.
- `--with-switcher` enables, `--without-switcher` disables, and no switcher flag preserves existing state; a clean target defaults to fixed-theme mode.
- Persist switcher choice only in `localStorage["apex.themeFactory.<APP_ID>"]`.
- Never call undocumented `wwv_flow_*` APIs or write directly to APEX repository tables.
- Never import `applications/ut/` into a consumer application.
- Preserve unrelated target files, application properties, Global Page content, and navigation entries.
- An executor must read `AGENTS.md`, `docs/PROJECT.md`, `.agents/knowledge/pitfalls.md`, and this plan's spec before Task 1.

## File Map

| Path | Responsibility |
|---|---|
| `schemas/theme-package.schema.json` | Human/tool-readable strict version-one manifest schema. |
| `lib/theme_factory/errors.py` | Typed user-facing failures and exit codes. |
| `lib/theme_factory/manifest.py` | Strict manifest, font, license, and source-path validation. |
| `lib/theme_factory/css_bundle.py` | Safe recursive CSS import flattening and generated font CSS. |
| `lib/theme_factory/archive.py` | Deterministic package directory and ZIP creation/checksum verification. |
| `lib/theme_factory/apexlang.py` | Narrow, marker-aware APEXLang parsing, patching, diffing, and canonical digests. |
| `lib/theme_factory/sqlcl.py` | Safe SQLcl subprocess boundary, preflight/export/validate/import calls. |
| `lib/theme_factory/install.py` | Install dry-run/apply transaction and post-install verification. |
| `lib/theme_factory/uninstall.py` | Owned-content removal, fallback selection, and recovery transaction. |
| `lib/theme_factory/cli.py` | `package`, `install`, `uninstall`, and `verify-package` argument contracts. |
| `installer/install.sh`, `installer/uninstall.sh` | Portable Bash launchers copied into each ZIP. |
| `installer/theme-factory-runtime.js` | Optional native-menu radio enhancement and browser persistence. |
| `installer/templates/*.tmpl` | Generated README, manual guide, bootstrap, and managed APEXLang snippets. |
| `scripts/package-theme.sh` | Repository-facing single-theme build command. |
| `tests/test_*.py` and `tests/fixtures/` | Offline TDD coverage and fake SQLcl behavior. |

---

### Task 1: Strict Manifest Model and Schema

**Files:**
- Create: `schemas/theme-package.schema.json`
- Create: `lib/theme_factory/__init__.py`
- Create: `lib/theme_factory/errors.py`
- Create: `lib/theme_factory/manifest.py`
- Create: `tests/__init__.py`
- Create: `tests/test_manifest.py`
- Create: `tests/fixtures/packages/valid-basic/theme.json`
- Create: `tests/fixtures/packages/invalid/external-font/theme.json`

**Interfaces:**
- Consumes: theme directories under `sample-themes/<name>/` or `tests/fixtures/packages/<case>/`.
- Produces: `load_manifest(path: Path, package_root: Path) -> ThemeManifest`, `ThemeManifest.font_asset_files() -> tuple[Path, ...]`, and `PackageError(message: str, exit_code: int)`.

- [ ] **Step 1: Write failing manifest tests**

```python
# tests/test_manifest.py
import json
import tempfile
import unittest
from pathlib import Path

from lib.theme_factory.manifest import load_manifest


class ManifestTests(unittest.TestCase):
    def write_package(self, payload: dict, files: dict[str, bytes] | None = None) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "theme.json").write_text(json.dumps(payload), encoding="utf-8")
        for relative, content in (files or {}).items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return root

    def test_accepts_no_font_manifest(self):
        manifest = load_manifest(
            Path("tests/fixtures/packages/valid-basic/theme.json"),
            Path("tests/fixtures/packages/valid-basic"),
        )
        self.assertEqual(manifest.name, "fixture-basic")
        self.assertEqual(manifest.fonts, {})

    def test_rejects_external_font_path(self):
        with self.assertRaisesRegex(ValueError, "fonts/body/faces/0/file must stay under fonts/"):
            load_manifest(
                Path("tests/fixtures/packages/invalid/external-font/theme.json"),
                Path("tests/fixtures/packages/invalid/external-font"),
            )
```

Add focused cases for unknown keys, directory/name mismatch, invalid semantic version, wrong compatibility boundary, missing body role, invalid weight/style, missing fallback, unsafe family/fallback strings, non-WOFF2 extension/signature, missing/empty license, duplicate face tuple, unreferenced file, traversal, absolute path, external URL, and a valid body/heading/mono package. Generate test WOFF2 bytes as `b"wOF2" + b"fixture"`; binary font parsing beyond the required signature belongs to browser release verification.

- [ ] **Step 2: Run the tests and verify the red state**

Run: `python3 -m unittest tests.test_manifest -v`

Expected: `ImportError` or `ModuleNotFoundError` for `lib.theme_factory.manifest`.

- [ ] **Step 3: Implement the error types and immutable manifest dataclasses**

```python
# lib/theme_factory/errors.py
class PackageError(ValueError):
    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code
```

```python
# lib/theme_factory/manifest.py
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FontFace:
    file: Path
    weight: int
    style: str


@dataclass(frozen=True)
class FontRole:
    family: str
    fallback: tuple[str, ...]
    license: Path
    faces: tuple[FontFace, ...]


@dataclass(frozen=True)
class ThemeManifest:
    schema_version: int
    name: str
    title: str
    version: str
    tagline: str
    class_name: str
    navigation_menu_style: str | None
    fonts: dict[str, FontRole]
    stylesheet: Path
    runtime: Path
    cover: Path

    def font_asset_files(self) -> tuple[Path, ...]:
        font_files = {face.file for role in self.fonts.values() for face in role.faces}
        licenses = {role.license for role in self.fonts.values()}
        return tuple(sorted({*font_files, *licenses}))
```

Implement `load_manifest()` with explicit allowed-key sets at every object level. Treat `assets.stylesheet`, `assets.runtime`, and `assets.cover` as logical distribution paths and require the exact values `theme.css`, `theme-factory-runtime.js`, and `preview/cover.jpg`; their authoring sources are fixed at `css/theme.css`, `installer/theme-factory-runtime.js`, and `preview/cover.jpg`. Resolve font/license assets with `candidate.resolve().is_relative_to(package_root.resolve())`, require lowercase kebab-case paths for font files, check the first four bytes are `b"wOF2"`, and raise `PackageError` with the JSON property path in every message. Parse semantic versions with `r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$"`. Accept family and named-fallback values only when they match `^[A-Za-z][A-Za-z0-9 _-]{0,63}$`; separately allow the CSS generic/system families `serif`, `sans-serif`, `monospace`, `system-ui`, `ui-serif`, `ui-sans-serif`, and `ui-monospace`. Reject quotes, semicolons, backslashes, control characters, and empty/duplicate fallback entries so manifest text cannot escape a generated CSS declaration.

- [ ] **Step 4: Add the strict JSON schema matching the Python validator**

Set `$schema` to draft 2020-12, `additionalProperties: false` at each object level, `schemaVersion.const: 1`, `name.pattern: ^[a-z0-9]+(?:-[a-z0-9]+)*$`, `class.pattern: ^app-theme-[a-z0-9]+(?:-[a-z0-9]+)*$`, `version.pattern` to the semantic-version regex above, and `fonts.propertyNames.enum` to `body`, `heading`, `mono`. Require `body` whenever `fonts` exists; constrain family and fallback strings to the validator's safe-name contract, set `uniqueItems: true` on fallback arrays, use face-weight enum `[100,200,300,400,500,600,700,800,900]`, and style enum `["normal","italic"]`.

Define the reusable safe-name and font-role fragments explicitly:

```json
{
  "$defs": {
    "fontName": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9 _-]{0,63}$"},
    "fontFace": {
      "type": "object",
      "additionalProperties": false,
      "required": ["file", "weight", "style"],
      "properties": {
        "file": {"type": "string", "pattern": "^fonts/[a-z0-9]+(?:-[a-z0-9]+)*\\.woff2$"},
        "weight": {"enum": [100, 200, 300, 400, 500, 600, 700, 800, 900]},
        "style": {"enum": ["normal", "italic"]}
      }
    },
    "fontRole": {
      "type": "object",
      "additionalProperties": false,
      "required": ["family", "fallback", "license", "faces"],
      "properties": {
        "family": {"$ref": "#/$defs/fontName"},
        "fallback": {"type": "array", "minItems": 1, "uniqueItems": true, "items": {"$ref": "#/$defs/fontName"}},
        "license": {"type": "string", "pattern": "^licenses/[A-Za-z0-9][A-Za-z0-9._-]*$"},
        "faces": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/fontFace"}}
      }
    }
  }
}
```

Because JSON Schema cannot express the separate generic-family allowlist or duplicate `(weight, style)` tuple rule cleanly, keep those two checks in `load_manifest()` and cover them with parity tests.

- [ ] **Step 5: Run the manifest suite**

Run: `python3 -m unittest tests.test_manifest -v`

Expected: all manifest cases pass, including the no-font backward-compatible case.

- [ ] **Step 6: Commit the manifest contract**

```bash
git add schemas/theme-package.schema.json lib/theme_factory/__init__.py lib/theme_factory/errors.py lib/theme_factory/manifest.py tests/__init__.py tests/test_manifest.py tests/fixtures/packages
git commit -m "feat: define strict theme package manifest"
```

---

### Task 2: Safe CSS and Custom-Font Assembly

**Files:**
- Create: `lib/theme_factory/css_bundle.py`
- Create: `tests/test_css_bundle.py`
- Modify: `static-files/css/foundation/tokens.css`
- Modify: `docs/DESIGN_SYSTEM.md`
- Modify: `sample-themes/README.md`
- Modify: `.agents/skills/apex-design-system/SKILL.md`
- Modify: `.agents/skills/apex-css-design-system/SKILL.md`

**Interfaces:**
- Consumes: `ThemeManifest` from Task 1 and CSS roots `static-files/css/foundation/` plus `sample-themes/<name>/css/`.
- Produces: `flatten_css(entry: Path, allowed_roots: tuple[Path, ...]) -> str`, `render_font_css(manifest: ThemeManifest) -> str`, and `build_theme_css(repo_root: Path, theme_root: Path, manifest: ThemeManifest, source_commit: str) -> str`.

- [ ] **Step 1: Write failing CSS graph tests**

```python
# tests/test_css_bundle.py
import tempfile
import unittest
from pathlib import Path

from lib.theme_factory.css_bundle import flatten_css, render_font_css


class CssBundleTests(unittest.TestCase):
    def test_flattens_each_local_import_once_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.css").write_text('@import "b.css";\n.a { color: red; }\n', encoding="utf-8")
            (root / "b.css").write_text('.b { color: blue; }\n', encoding="utf-8")
            self.assertEqual(
                flatten_css(root / "a.css", (root,)),
                '.b { color: blue; }\n.a { color: red; }\n',
            )

    def test_rejects_remote_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.css").write_text('@import url("https://fonts.example/x.css");\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "remote CSS imports are forbidden"):
                flatten_css(root / "a.css", (root,))
```

Add cases for cycles, missing files, root escape, duplicate imports, `url(data:)`, `url(http:)`, `url(//...)`, no-font output, all three roles, reused source file across roles, package-prefixed family aliases, `font-display: swap`, relative `./fonts/` URLs, and icon-safe scoped token output.

- [ ] **Step 2: Verify the tests fail before implementation**

Run: `python3 -m unittest tests.test_css_bundle -v`

Expected: import failure for `lib.theme_factory.css_bundle`.

- [ ] **Step 3: Implement import parsing and recursion**

Use one anchored import pattern and reject every import not consumed at the start of a logical CSS line:

```python
IMPORT_RE = re.compile(
    r'^\s*@import\s+(?:url\()?\s*["\']([^"\']+)["\']\s*\)?\s*;\s*$',
    re.MULTILINE,
)
```

`flatten_css()` must track an ordered `visited` set plus an active recursion stack. Resolve a relative import against the importing file, require it to be under an allowed root, reject a second visit as a duplicate rather than silently dropping it, and concatenate normalized UTF-8 text with exactly one trailing newline per source file.

`build_theme_css()` must assemble in this exact order: deterministic source/version banner; generated `@font-face` blocks and scoped font-token overrides; flattened foundation files in `tokens`, `reset`, `typography`, `utilities` order; then the recursively flattened theme entrypoint. Assert that order in a golden-output test so future refactors cannot move font declarations behind their consumers or reorder the shared foundation.

- [ ] **Step 4: Implement generated font CSS and scoped typography tokens**

```python
def internal_family(theme_name: str, role: str) -> str:
    return f"ThemeFactory-{theme_name}-{role}"


def render_face(theme_name: str, role: str, face: FontFace) -> str:
    return (
        "@font-face {\n"
        f'  font-family: "{internal_family(theme_name, role)}";\n'
        f'  src: url("./{face.file.as_posix()}") format("woff2");\n'
        f"  font-weight: {face.weight};\n"
        f"  font-style: {face.style};\n"
        "  font-display: swap;\n"
        "}\n"
    )
```

Generate `--app-font-family-body`, `--app-font-family-heading`, and `--app-font-family-mono` under `html.app-theme-<name>`. Map body to scoped `--a-base-font-family`; apply heading only to verified Universal Theme heading/title selectors listed in `docs/DESIGN_SYSTEM.md`; map mono to scoped `--a-base-font-family-mono`. Do not emit a universal `* { font-family: ... }` rule and do not match `.fa`, `.fa-*`, `.t-Icon`, or `[class*=icon]`.

- [ ] **Step 5: Add Iris-default font tokens and authoring documentation**

Add these foundation declarations:

```css
--app-font-family-body: var(--a-base-font-family);
--app-font-family-heading: var(--a-base-font-family);
--app-font-family-mono: var(--a-base-font-family-mono);
```

Document the three roles, package directory layout, WOFF2/license rule, no-external-font rule, generated family aliases, and Font APEX isolation in `docs/DESIGN_SYSTEM.md` and `sample-themes/README.md`. Add the same concise rule to both font-related project skills so a theme-generating agent cannot propose Google Fonts or an unlicensed binary.

- [ ] **Step 6: Run CSS and manifest tests**

Run: `python3 -m unittest tests.test_manifest tests.test_css_bundle -v`

Expected: all tests pass and the no-font fixture emits no `@font-face`.

- [ ] **Step 7: Commit CSS/font assembly**

```bash
git add lib/theme_factory/css_bundle.py tests/test_css_bundle.py static-files/css/foundation/tokens.css docs/DESIGN_SYSTEM.md sample-themes/README.md .agents/skills/apex-design-system/SKILL.md .agents/skills/apex-css-design-system/SKILL.md
git commit -m "feat: bundle licensed theme fonts"
```

---

### Task 3: Deterministic Single-Theme ZIP Builder

**Files:**
- Create: `lib/theme_factory/archive.py`
- Create: `installer/install.sh`
- Create: `installer/uninstall.sh`
- Create: `installer/theme-factory-runtime.js`
- Create: `installer/templates/README.md.tmpl`
- Create: `installer/templates/MANUAL-INSTALL.md.tmpl`
- Create: `installer/templates/bootstrap.html.tmpl`
- Create: `installer/templates/switcher-entry.apx.tmpl`
- Create: `scripts/package-theme.sh`
- Create: `tests/test_package_archive.py`

**Interfaces:**
- Consumes: Task 1 manifest objects and Task 2 `build_theme_css()` output.
- Produces: `build_package(repo_root: Path, theme_name: str, output_dir: Path) -> Path`, `build_package_from_root(repo_root: Path, theme_root: Path, output_dir: Path) -> Path`, and `verify_package(package_root: Path) -> ThemeManifest`.

- [ ] **Step 1: Write failing archive-contract tests**

```python
# tests/test_package_archive.py
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

from lib.theme_factory.archive import build_package


class ArchiveTests(unittest.TestCase):
    def test_two_builds_are_byte_identical_and_single_theme(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            zip_a = build_package(Path.cwd(), "linen", Path(first))
            zip_b = build_package(Path.cwd(), "linen", Path(second))
            self.assertEqual(hashlib.sha256(zip_a.read_bytes()).digest(), hashlib.sha256(zip_b.read_bytes()).digest())
            with zipfile.ZipFile(zip_a) as archive:
                names = archive.namelist()
                self.assertEqual(sum(name.endswith("/theme.json") for name in names), 1)
                self.assertNotIn("sample-themes/solarized-dark/theme.json", names)
```

Add tests for sorted members, fixed ZIP timestamps `(1980, 1, 1, 0, 0, 0)`, executable mode on two shell files, no symlinks, no absolute/traversal/duplicate names, checksum coverage, extracted verification, no repository dependency after extraction, optional font/license inclusion, and rejection of unreferenced font files.

- [ ] **Step 2: Run the archive suite and verify failure**

Run: `python3 -m unittest tests.test_package_archive -v`

Expected: import failure for `lib.theme_factory.archive`.

- [ ] **Step 3: Implement deterministic staging and checksums**

Create a temporary staging root named `<name>-<version>`. Copy only the manifest, generated `theme.css`, runtime, launchers, local `lib/theme_factory/*.py`, cover, manifest-referenced fonts/licenses, and rendered documents. Generate `licenses/THIRD_PARTY.md` from declared families and license paths. Write `checksums.sha256` last with sorted lines in the format `<hex><two spaces><relative-path>` and exclude itself.

When writing ZIP entries, construct `ZipInfo` explicitly:

```python
info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
info.compress_type = zipfile.ZIP_DEFLATED
info.external_attr = ((0o755 if archive_name.endswith(("/install.sh", "/uninstall.sh")) else 0o644) & 0xFFFF) << 16
archive.writestr(info, source_bytes)
```

The build banner contains only theme name, version, compatibility, and `git rev-parse HEAD`; refuse packaging a dirty tree unless `THEME_FACTORY_ALLOW_DIRTY=1` is set, and put `source=dirty` in the banner when that explicit development override is used.

- [ ] **Step 4: Implement portable launchers**

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null || { echo "Python 3.10+ is required" >&2; exit 2; }
PYTHONPATH="$SCRIPT_DIR/lib" exec python3 -m theme_factory.cli install --package-root "$SCRIPT_DIR" "$@"
```

Use the same launcher for uninstall with the `uninstall` subcommand. Do not use `$HOME`, `~`, or a package-external module path.

- [ ] **Step 5: Add the repository build wrapper**

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
name="${1:?usage: scripts/package-theme.sh <theme-name> [output-dir]}"
output="${2:-$ROOT/dist/$name}"
PYTHONPATH="$ROOT/lib" exec python3 -m theme_factory.cli package --repo-root "$ROOT" --theme "$name" --output-dir "$output"
```

- [ ] **Step 6: Run archive tests and inspect both real package listings**

Run: `python3 -m unittest tests.test_manifest tests.test_css_bundle tests.test_package_archive -v`

Expected: all tests pass.

Run: `scripts/package-theme.sh linen /tmp/theme-factory-linen && unzip -l /tmp/theme-factory-linen/linen-1.0.0.zip`

Expected: one `theme.json`, one `theme.css`, no Solarized files, and no font directory because Linen declares no custom font.

Run: `scripts/package-theme.sh solarized-dark /tmp/theme-factory-solarized && unzip -l /tmp/theme-factory-solarized/solarized-dark-1.0.0.zip`

Expected: one Solarized manifest/stylesheet and no Linen files.

- [ ] **Step 7: Commit deterministic packaging**

```bash
git add lib/theme_factory/archive.py installer scripts/package-theme.sh tests/test_package_archive.py
git commit -m "feat: build deterministic single-theme zips"
```

---

### Task 4: Theme Runtime and Namespaced Browser Persistence

**Files:**
- Modify: `installer/theme-factory-runtime.js`
- Create: `tests/test_runtime_contract.py`
- Modify: `installer/templates/bootstrap.html.tmpl`

**Interfaces:**
- Consumes: bootstrap global `window.APEX_THEME_FACTORY_CONFIG = {appId: number, defaultTheme: string, switcherEnabled: boolean, themes: Array<{name: string, title: string, className: string}>}`.
- Produces: `window.ApexThemeFactory.current()`, `.use(name)`, `.choices()`, and storage key `apex.themeFactory.<APP_ID>`.

- [ ] **Step 1: Write failing runtime source-contract tests**

```python
# tests/test_runtime_contract.py
import unittest
from pathlib import Path


class RuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("installer/theme-factory-runtime.js").read_text(encoding="utf-8")

    def test_storage_is_application_namespaced(self):
        self.assertIn("apex.themeFactory.", self.source)
        self.assertNotIn("localStorage['app.theme']", self.source)

    def test_uses_native_radio_group(self):
        self.assertIn("type: 'radioGroup'", self.source)
        self.assertIn("menuitemradio", Path("docs/superpowers/specs/2026-09-15-portable-single-theme-distribution-design.md").read_text())
```

Also assert allowlist validation, `iris` handling, invalid-value removal, fixed-mode localStorage bypass, no dynamic stylesheet insertion, one `theme42ready` handler namespace, and no `Alpine.start()`.

- [ ] **Step 2: Run the runtime contract test**

Run: `python3 -m unittest tests.test_runtime_contract -v`

Expected: failures for namespaced storage and the new API.

- [ ] **Step 3: Implement the pre-paint bootstrap**

Render an inline IIFE that reads only the embedded config, computes `key = "apex.themeFactory." + appId`, accepts an installed name or `iris`, removes stale values, removes every `app-theme-*` class, applies exactly one allowed class or bare Iris, and writes `data-app-theme-default` plus `data-app-theme-current`. When `switcherEnabled` is false, it never reads localStorage.

```javascript
(function (doc, config) {
  "use strict";
  var root = doc.documentElement;
  var key = "apex.themeFactory." + config.appId;
  var allowed = ["iris"].concat(config.themes.map(function (theme) { return theme.name; }));
  var selected = config.defaultTheme;
  if (config.switcherEnabled) {
    selected = window.localStorage.getItem(key) || selected;
    if (allowed.indexOf(selected) === -1) {
      window.localStorage.removeItem(key);
      selected = config.defaultTheme;
    }
  }
  Array.prototype.slice.call(root.classList).forEach(function (name) {
    if (name.indexOf("app-theme-") === 0) { root.classList.remove(name); }
  });
  if (selected !== "iris") { root.classList.add("app-theme-" + selected); }
  root.dataset.appThemeDefault = config.defaultTheme;
  root.dataset.appThemeCurrent = selected;
}(document, window.APEX_THEME_FACTORY_CONFIG));
```

- [ ] **Step 4: Implement the shared runtime API and native menu adapter**

`use(name)` must reject names outside the embedded allowlist plus `iris`, store only in switcher mode, remove every prior package class, and reload. On `theme42ready.apexThemeFactory` bound to `window` (not `document`), locate only the marked navigation entry and replace its children with one Universal Theme menu `radioGroup`; do not create a floating control or custom ARIA menu.

```javascript
window.ApexThemeFactory = Object.freeze({
  current: function () { return document.documentElement.dataset.appThemeCurrent; },
  choices: function () {
    return config.themes.map(function (theme) { return {label: theme.title, value: theme.name}; })
      .concat([{label: "Iris", value: "iris"}]);
  },
  use: function (name) {
    if (!config.switcherEnabled || allowed.indexOf(name) === -1) { return false; }
    window.localStorage.setItem(key, name);
    window.location.reload();
    return true;
  }
});

apex.jQuery(window)
  .off("theme42ready.apexThemeFactory")
  .on("theme42ready.apexThemeFactory", function () {
    var $ = apex.jQuery;
    var button = $(".t-NavigationBar-item.theme-factory-managed-switcher [data-menu]").first();
    var menu = button.length ? $("#" + button.attr("data-menu")) : $();
    if (!menu.length) { return; }
    menu.menu("option", "items", [{
      type: "radioGroup",
      get: window.ApexThemeFactory.current,
      set: window.ApexThemeFactory.use,
      choices: window.ApexThemeFactory.choices()
    }]);
  });
```

- [ ] **Step 5: Run runtime and package tests**

Run: `python3 -m unittest tests.test_runtime_contract tests.test_package_archive -v`

Expected: all tests pass and packaging includes the updated runtime.

- [ ] **Step 6: Commit the runtime**

```bash
git add installer/theme-factory-runtime.js installer/templates/bootstrap.html.tmpl tests/test_runtime_contract.py
git commit -m "feat: add optional namespaced theme switcher"
```

---

### Task 5: APEXLang Install Patcher

**Files:**
- Create: `lib/theme_factory/apexlang.py`
- Create: `tests/test_apexlang_patch.py`
- Create: `tests/fixtures/apexlang/minimal/application.apx`
- Create: `tests/fixtures/apexlang/minimal/shared-components/themes/universal-theme/theme.apx`
- Create: `tests/fixtures/apexlang/minimal/shared-components/static-files.apx`
- Create: `tests/fixtures/apexlang/with-existing-assets/`
- Create: `tests/fixtures/apexlang/no-global-page/`
- Create: `tests/fixtures/apexlang/ambiguous-css-block/`

**Interfaces:**
- Consumes: fresh split APEXLang directory, extracted package root, and switcher mode `Literal["preserve", "enable", "disable"]`.
- Produces: `TargetExport`, `InstallState`, `InstallPatch`, `inspect_export(export_dir: Path) -> TargetExport`, `plan_install(export_dir: Path, package_root: Path, mode: str) -> InstallPatch`, `apply_patch(patch: InstallPatch) -> None`, and `canonical_digest(export_dir: Path) -> str`.

- [ ] **Step 1: Copy minimal exact APEXLang shapes into fixtures and write failing tests**

Use the repository's current `application.apx`, `shared-components/themes/universal-theme/theme.apx`, `shared-components/static-files.apx`, Page 0, and list syntax as the source for reduced fixtures. Preserve the exact braces, list syntax, and named references emitted by APEX 26.1.

```python
# tests/test_apexlang_patch.py
import shutil
import tempfile
import unittest
from pathlib import Path

from lib.theme_factory.apexlang import inspect_export, plan_install


class ApexLangPatchTests(unittest.TestCase):
    def fixture_copy(self, name: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        shutil.copytree(Path("tests/fixtures/apexlang") / name, tmp / "app")
        return tmp / "app"

    def test_reads_supported_theme_boundary(self):
        target = inspect_export(self.fixture_copy("minimal"))
        self.assertEqual((target.theme_number, target.base_theme, target.style), (42, "ut-26.1", "iris"))

    def test_install_preserves_existing_urls(self):
        root = self.fixture_copy("with-existing-assets")
        patch = plan_install(root, Path("tests/fixtures/packages/valid-basic"), "preserve")
        self.assertIn("#APP_FILES#existing.css", patch.after_files[Path("application.apx")])
```

Add tests for exact single insertion, reinstall idempotence, old-version URL replacement with removal of every owned prior-version static file, multiple package coexistence, no-Page-0 creation, standard/dialog bootstrap regions, enable/disable/preserve transitions, static navigation-list insertion, SQL-query navigation-list refusal, marker collision refusal, ambiguous CSS/JS blocks, unsupported theme/style, registry ordering, font/license copying, and canonical digest stability across export dates or irrelevant line endings.

- [ ] **Step 2: Run the patcher suite and confirm failure**

Run: `python3 -m unittest tests.test_apexlang_patch -v`

Expected: import failure for `lib.theme_factory.apexlang`.

- [ ] **Step 3: Implement structural readers and boundary checks**

Parse only these exact structures:

```text
app <alias> (... javaScript { fileUrls: ... } ... css { fileUrls: ... } ... userInterface { globalPage: ... })
theme <name> (... themeNumber: 42 ... baseTheme: ut-26.1 ... style { currentThemeStyle: @/iris })
file "<path>" (...)
page 0 (...)
list <name> (... entry <name> (...))
```

Write balanced-brace and balanced-bracket scanners that ignore fenced blocks rather than using one whole-file regex. Require exactly one application block and one current theme block. Return line-aware `PackageError` messages when a supported shape is missing or duplicated.

- [ ] **Step 4: Implement package static-file and application URL changes**

Copy package assets under `shared-components/static-files/theme-factory/packages/<name>/<version>/`; add sorted `file` declarations using `font/woff2` for fonts, `text/css`, `application/json`, `application/javascript`, `image/jpeg`, and `text/plain` for licenses. On same-theme upgrade, first verify the existing registry/checksums prove ownership, then remove the entire prior-version namespace before inserting the new one. Insert the package CSS URL once, replace a prior version of the same theme, reject an unowned or modified prior namespace, and preserve every unrelated URL and its order.

```python
MIME_BY_SUFFIX = {
    ".css": "text/css", ".js": "application/javascript", ".json": "application/json",
    ".jpg": "image/jpeg", ".woff2": "font/woff2", ".txt": "text/plain",
}

old = state.package_for(manifest.name)
if old is not None:
    verify_owned_namespace(export_dir, old, state.registry)
    remove_static_prefix(export_dir, f"theme-factory/packages/{old.name}/{old.version}/")
copy_package_files(package_root, export_dir, manifest, MIME_BY_SUFFIX)
replace_theme_url(target.css_urls, old, manifest)
```

- [ ] **Step 5: Implement marked bootstrap and switcher transforms**

Use names beginning `theme-factory-managed-` and include `APEX_THEME_FACTORY_MANAGED` inside each generated HTML/comment body. For switcher enablement, support only a statically declared navigation-bar list; add one parent entry and package/Iris child entries with deterministic sequences. Refuse query-backed or structurally ambiguous lists and direct the user to `MANUAL-INSTALL.md`. For disablement remove only exact marked entries and the runtime URL. For preserve mode retain the prior switcher state while regenerating installed choices.

```python
MARKER = "APEX_THEME_FACTORY_MANAGED"

def desired_switcher(mode: str, prior: bool) -> bool:
    return prior if mode == "preserve" else mode == "enable"

enabled = desired_switcher(mode, state.switcher_enabled)
replace_marked_page_zero_regions(export_dir, render_bootstrap_regions(registry, enabled, MARKER))
if enabled:
    nav = require_static_navigation_bar_list(export_dir)
    replace_marked_list_entries(nav, render_switcher_entries(registry, start_sequence=9000))
else:
    remove_marked_list_entries(export_dir, MARKER)
    remove_exact_url(target.javascript_urls, "#APP_FILES#theme-factory/theme-factory-runtime.js")
```

- [ ] **Step 6: Implement canonical diff and digest**

Hash sorted relative paths and normalized file bytes while excluding export-date lines and the default deployment file's known exporter-only metadata. `InstallPatch.diff` must be a unified diff containing only files present in `before_files`/`after_files`; reject any changed path outside application properties, Page 0, navigation list, static registry, or owned static files.

```python
def canonical_digest(export_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in export_dir.rglob("*") if p.is_file()):
        relative = path.relative_to(export_dir).as_posix()
        normalized = normalize_apexlang(relative, path.read_bytes())
        digest.update(relative.encode("utf-8") + b"\0" + normalized + b"\0")
    return digest.hexdigest()

allowed = {target.application_file, target.page_zero_file, target.navigation_file,
           target.static_registry_file, *owned_static_paths}
unexpected = set(after_files) ^ set(before_files) | {
    path for path in before_files.keys() & after_files.keys()
    if before_files[path] != after_files[path]
}
require_paths_within(unexpected, allowed)
```

- [ ] **Step 7: Run all patcher tests**

Run: `python3 -m unittest tests.test_apexlang_patch -v`

Expected: all transitions, refusals, and preservation assertions pass.

- [ ] **Step 8: Commit the APEXLang patcher**

```bash
git add lib/theme_factory/apexlang.py tests/test_apexlang_patch.py tests/fixtures/apexlang
git commit -m "feat: stage narrow apexlang theme installs"
```

---

### Task 6: SQLcl Boundary, Preflight, Export, Validation, and Drift Guard

**Files:**
- Create: `lib/theme_factory/sqlcl.py`
- Create: `installer/sql/preflight.sql`
- Create: `tests/test_sqlcl.py`
- Create: `tests/fixtures/bin/sql`

**Interfaces:**
- Consumes: saved connection name, uppercase workspace, numeric application ID, and staged export path.
- Produces: `SqlclClient`, `TargetMetadata`, `SqlclResult`; methods `preflight()`, `export_apexlang()`, `validate()`, `import_apexlang()`, and `post_export()`.

- [ ] **Step 1: Write failing fake-SQLcl tests**

```python
# tests/test_sqlcl.py
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib.theme_factory.sqlcl import SqlclClient


class SqlclTests(unittest.TestCase):
    def test_export_uses_exact_application_id_and_skip_export_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls.log"
            with patch.dict(os.environ, {"FAKE_SQL_LOG": str(log)}):
                SqlclClient("demo-connection").export_apexlang(314, Path(tmp) / "export")
            call = log.read_text(encoding="utf-8")
            self.assertIn("apex export -applicationid 314", call)
            self.assertIn("-exptype APEXLANG", call)
            self.assertIn("-skipexportdate", call.lower())
```

Add tests for safe connection-name characters, uppercase workspace validation, nonnumeric app rejection, masked logs, nonzero exits, timeout, missing `Validation successful.`, warnings, alias-directory discovery, duplicate export directory refusal, and validation/import in one SQLcl process.

- [ ] **Step 2: Run the SQLcl suite and confirm failure**

Run: `PATH="$PWD/tests/fixtures/bin:$PATH" python3 -m unittest tests.test_sqlcl -v`

Expected: import failure for `lib.theme_factory.sqlcl`.

- [ ] **Step 3: Implement the fake `sql` executable**

The executable reads stdin, appends arguments plus stdin to `$FAKE_SQL_LOG`, uses `$FAKE_SQL_MODE` to choose `success`, `validation-warning`, `export-two-aliases`, `connection-failure`, or `import-failure`, and creates the requested reduced APEXLang fixture under the `-dir` path for export mode. It must never call a real database.

```bash
#!/usr/bin/env bash
set -euo pipefail
input="$(</dev/stdin)"
printf 'argv=%q\nstdin=%s\n' "$*" "$input" >>"${FAKE_SQL_LOG:?}"
if [[ "$input" =~ -dir[[:space:]]+\"([^\"]+)\" ]]; then
  export_dir="${BASH_REMATCH[1]}"
else
  export_dir=""
fi
case "${FAKE_SQL_MODE:-success}" in
  success)
    if [[ "$input" == *"apex export"* ]]; then
      mkdir -p "$export_dir"
      cp -R tests/fixtures/apexlang/minimal "$export_dir/fixture-app"
    fi
    printf '%s\n' 'Validation completed successfully.'
    ;;
  validation-warning) printf '%s\n' 'WARNING fixture validation warning' ;;
  export-two-aliases)
    mkdir -p "$export_dir"
    cp -R tests/fixtures/apexlang/minimal "$export_dir/one"
    cp -R tests/fixtures/apexlang/minimal "$export_dir/two"
    ;;
  connection-failure) printf '%s\n' 'ORA-17820: network adapter error' >&2; exit 1 ;;
  import-failure) printf '%s\n' 'ERROR import failed' >&2; exit 1 ;;
  *) printf 'unknown FAKE_SQL_MODE=%s\n' "$FAKE_SQL_MODE" >&2; exit 2 ;;
esac
```

- [ ] **Step 4: Implement safe subprocess execution and preflight SQL**

Use `subprocess.run(["sql", "-S", "-name", connection], input=script, text=True, capture_output=True, timeout=120, check=False)` with no shell. Accept connection names matching `^[A-Za-z0-9_.-]{1,128}$`, workspaces matching `^[A-Z][A-Z0-9_$#]{0,127}$`, and positive application IDs.

`preflight.sql` emits exactly one prefixed JSON line from public views:

```sql
set heading off feedback off pagesize 0 verify off echo off
whenever sqlerror exit failure
select 'THEME_FACTORY_TARGET=' || json_object(
           'appId' value a.application_id,
           'alias' value a.alias,
           'name' value a.application_name,
           'workspace' value a.workspace,
           'apexVersion' value r.version_no
         returning varchar2)
  from apex_applications a
 cross join apex_release r
 where a.application_id = to_number('&1')
   and upper(a.workspace) = upper('&2');
exit
```

Require exactly one prefixed JSON object; zero or multiple records refuse. Confirm theme number/base/style by parsing the resulting fresh APEXLang theme file, avoiding unstable or undocumented repository columns.

- [ ] **Step 5: Implement export, validate, and same-session import**

Export with `apex export -applicationid <id> -exptype APEXLANG -split -dir <temp-parent> -skipexportdate -overwrite-files`. Discover exactly one child directory containing `application.apx`; do not assume its alias. Validation requires the exact success phrase and no line beginning `WARNING` or `ERROR`. `import_apexlang()` sends `apex validate -input <path> -workspace <workspace>` followed by `apex import -input <path> -workspace <workspace> -id <confirmed-app-id>` in the same stdin script with `whenever sqlerror exit failure`; passing `-id` is mandatory even when the deployment file already contains an ID.

```python
script = "\n".join((
    "whenever sqlerror exit failure",
    f'apex validate -input "{apexlang_dir}" -workspace "{workspace}"',
    f'apex import -input "{apexlang_dir}" -workspace "{workspace}" -id {confirmed_app_id}',
    "exit",
))
result = subprocess.run(
    ["sql", "-S", "-name", connection], input=script, text=True,
    capture_output=True, check=False, timeout=timeout_seconds,
)
require_clean_sqlcl_result(result)
```

- [ ] **Step 6: Run the fake-SQLcl suite**

Run: `PATH="$PWD/tests/fixtures/bin:$PATH" python3 -m unittest tests.test_sqlcl -v`

Expected: every success/refusal branch passes without a real connection.

- [ ] **Step 7: Commit the SQLcl boundary**

```bash
git add lib/theme_factory/sqlcl.py installer/sql/preflight.sql tests/test_sqlcl.py tests/fixtures/bin/sql
git commit -m "feat: add safe sqlcl installer boundary"
```

---

### Task 7: Install Transaction and Portable CLI

**Files:**
- Create: `lib/theme_factory/install.py`
- Create: `lib/theme_factory/cli.py`
- Create: `tests/test_installer_cli.py`
- Modify: `installer/templates/README.md.tmpl`
- Modify: `installer/templates/MANUAL-INSTALL.md.tmpl`

**Interfaces:**
- Consumes: `SqlclClient`, `plan_install()`, verified package root, `InstallOptions`.
- Produces: `run_install(options: InstallOptions) -> OperationReport` and CLI exit codes `0` success/dry-run, `2` package/argument error, `3` unsupported target, `4` drift, `5` validation/import failure, `6` post-check failure.

- [ ] **Step 1: Write failing dry-run and confirmation tests**

```python
# tests/test_installer_cli.py
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class InstallerCliTests(unittest.TestCase):
    def run_cli(self, package: Path, *args: str, stdin: str = ""):
        env = os.environ | {"PATH": f"{Path.cwd() / 'tests/fixtures/bin'}:{os.environ['PATH']}"}
        return subprocess.run(
            ["python3", "-m", "lib.theme_factory.cli", "install", "--package-root", str(package), *args],
            input=stdin,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_dry_run_never_imports(self):
        result = self.run_cli(Path("tests/fixtures/packages/valid-basic"), "--connection", "demo", "--workspace", "DEMO", "--app-id", "314")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("apex import", result.stdout + result.stderr)
```

Add cases for checksum failure before SQLcl, unsupported APEX/theme/style, exact target summary, backup contents and `target.json`, switcher flag exclusivity, default preserve behavior, second-export drift, wrong typed ID, cancellation, same-session validate/import, post-export verification, status labels `TARGET_UNTOUCHED`, `STAGED_ONLY`, `IMPORTED_POSTCHECK_FAILED`, and no secrets in output.

- [ ] **Step 2: Run installer tests and confirm failure**

Run: `PATH="$PWD/tests/fixtures/bin:$PATH" python3 -m unittest tests.test_installer_cli -v`

Expected: import failure for `lib.theme_factory.install` or missing CLI subcommand.

- [ ] **Step 3: Implement the dry-run transaction**

Use this order without shortcuts:

```text
verify ZIP checksums -> load manifest -> validate arguments -> SQLcl preflight
-> fresh export -> inspect theme boundary -> copy immutable backup + target.json
-> plan/apply staged files -> apex validate -> print owned diff
-> second fresh export -> compare canonical digest -> report STAGED_ONLY
```

Create staging with `TemporaryDirectory(prefix="apex-theme-factory-")`; create backups only under the explicit/default `./theme-factory-backups/<workspace>-<app-id>/<UTC>-before-<theme>/`. Use `Path.resolve()` and `is_relative_to()` before cleanup. `target.json` stores metadata and digests, never environment variables or connection contents.

- [ ] **Step 4: Implement apply confirmation and post-check**

After a clean drift comparison, print target metadata again, prompt `Type application ID <id> to import: `, and compare the complete stripped input to `str(app_id)`. On match, call same-session validate/import; reconnect by exporting again and inspect exact static paths, URLs, theme 42/base/style, switcher state, and target alias. Report imported-but-postcheck-failed distinctly and preserve both backup and staged export path.

```python
print(render_target_summary(target, manifest, staged_digest))
typed = input(f"Type application ID {options.app_id} to import: ").strip()
if typed != str(options.app_id):
    return OperationReport("TARGET_UNTOUCHED", 0, backup_dir, staged_dir)
sqlcl.import_apexlang(staged_dir, options.workspace, options.app_id)
post = inspect_export(sqlcl.export_apexlang(options.app_id))
if not post.matches_install(target.alias, manifest, options.switcher_mode):
    return OperationReport("IMPORTED_POSTCHECK_FAILED", 6, backup_dir, staged_dir)
return OperationReport("IMPORTED", 0, backup_dir, None)
```

- [ ] **Step 5: Implement `argparse` subcommands**

Define package/install/uninstall/verify-package parsers. Package accepts exactly one of `--theme <name>` (resolved under `<repo-root>/sample-themes`) or `--theme-root <path>` (used for committed test/release fixtures) plus `--output-dir`. Install requires `--package-root`, `--connection`, `--workspace`, and `--app-id`; accepts mutually exclusive `--with-switcher`/`--without-switcher`, optional `--backup-dir`, and `--apply`. Do not add `--yes`, password, connect-string, or skip-validation flags.

```python
package = subparsers.add_parser("package")
source = package.add_mutually_exclusive_group(required=True)
source.add_argument("--theme")
source.add_argument("--theme-root", type=Path)
package.add_argument("--output-dir", type=Path, required=True)

install = subparsers.add_parser("install")
for flag in ("package-root", "connection", "workspace", "app-id"):
    install.add_argument(f"--{flag}", required=True, type=int if flag == "app-id" else str)
switcher = install.add_mutually_exclusive_group()
switcher.add_argument("--with-switcher", action="store_true")
switcher.add_argument("--without-switcher", action="store_true")
install.add_argument("--backup-dir", type=Path)
install.add_argument("--apply", action="store_true")
```

- [ ] **Step 6: Render complete package documentation**

The README includes compatibility, prerequisites, checksum verification, dry-run/apply examples, switcher flag semantics, persistence key, status/exit codes, and backup location. The manual guide includes fixed and switcher paths, exact APEX Builder navigation, static filenames/MIME types, generated CSS/JS URLs, both Global Page snippets, native list entries, custom-font upload order, font checks, uninstall, and recovery. Assert in tests that neither template contains “repeat the automated process” or an unresolved `{{...}}` marker.

Use this fixed heading contract so rendered documentation is independently actionable:

```markdown
# Install THEME_TITLE
## Compatibility
## Package contents and checksums
## Automated SQLcl dry-run
## Automated SQLcl apply
## Optional switcher
## Per-browser persistence
## Uninstall and restore
## Exit codes and recovery artifacts

# Manual APEX Builder installation
## Verify the ZIP
## Upload application static files
## Add the stylesheet URL
## Add the Global Page pre-paint bootstrap
## Optional native navigation switcher
## Verify fonts, Font APEX, dialogs, and refreshes
## Manual uninstall and recovery
```

- [ ] **Step 7: Run the installer and archive suites**

Run: `PATH="$PWD/tests/fixtures/bin:$PATH" python3 -m unittest tests.test_installer_cli tests.test_package_archive -v`

Expected: all tests pass and dry-run logs contain no import call.

- [ ] **Step 8: Commit the installer**

```bash
git add lib/theme_factory/install.py lib/theme_factory/cli.py installer/templates tests/test_installer_cli.py
git commit -m "feat: install theme zips through fresh apexlang exports"
```

---

### Task 8: Uninstall, Fallback, and Backup Recovery

**Files:**
- Create: `lib/theme_factory/uninstall.py`
- Create: `tests/test_uninstaller_cli.py`
- Modify: `lib/theme_factory/cli.py`
- Modify: `installer/templates/README.md.tmpl`
- Modify: `installer/templates/MANUAL-INSTALL.md.tmpl`

**Interfaces:**
- Consumes: target export inspection, selected package manifest, current registry, and common SQLcl transaction.
- Produces: `run_uninstall(options: UninstallOptions) -> OperationReport` and `choose_fallback(current_default: str | None, remaining: tuple[str, ...]) -> str`.

- [ ] **Step 1: Write failing uninstall ownership tests**

```python
# tests/test_uninstaller_cli.py
import unittest

from lib.theme_factory.uninstall import choose_fallback


class UninstallTests(unittest.TestCase):
    def test_keeps_valid_default_then_uses_lexicographic_fallback(self):
        self.assertEqual(choose_fallback("linen", ("linen", "solarized-dark")), "linen")
        self.assertEqual(choose_fallback("removed", ("solarized-dark", "linen")), "linen")
        self.assertEqual(choose_fallback("removed", ()), "iris")
```

Add tests for dry-run no import, selected-package files only, font/license removal, other-package preservation, active-package fallback, final-package cleanup, modified-marker refusal, modified-owned-checksum refusal, drift refusal, typed confirmation, backup preservation, and idempotent already-absent status.

- [ ] **Step 2: Run uninstaller tests and verify failure**

Run: `PATH="$PWD/tests/fixtures/bin:$PATH" python3 -m unittest tests.test_uninstaller_cli -v`

Expected: import failure for `lib.theme_factory.uninstall`.

- [ ] **Step 3: Implement an ownership-first uninstall plan**

Fresh-export and back up before calculating changes. Remove only `theme-factory/packages/<selected-name>/<selected-version>/`, its exact CSS URL, and its registry record. Verify generated content against stored checksums/markers before removal. Rebuild the bootstrap/switcher from remaining manifests; when none remain, remove exact managed Page 0 regions, navigation entries, runtime/registry, and leave bare Iris.

```python
installed = inspect_install_state(fresh_export)
selected = installed.require_theme(options.theme_name)
verify_owned_namespace(fresh_export, selected, installed.registry)
remove_static_prefix(fresh_export, selected.static_prefix)
remove_exact_url(installed.target.css_urls, selected.css_url)
remaining = installed.without(selected.name)
replace_registry(fresh_export, remaining)
replace_marked_page_zero_regions(fresh_export, render_bootstrap_regions(remaining, installed.switcher_enabled))
if not remaining.themes:
    remove_exact_managed_runtime(fresh_export)
    remove_marked_list_entries(fresh_export, "APEX_THEME_FACTORY_MANAGED")
```

- [ ] **Step 4: Implement recovery instructions and command**

Add CLI `restore --connection <name> --workspace <workspace> --app-id <id> --backup <path> --apply`. Validate `target.json`, fresh-export the live target, print both digests, require typing the app ID, and validate/import the backup in one SQLcl session using both `apex validate` and `apex import -id <confirmed-app-id>`. Do not auto-restore after an import failure because the database outcome may be uncertain.

```python
metadata = json.loads((backup / "target.json").read_text(encoding="utf-8"))
require_exact_target(metadata, workspace=options.workspace, app_id=options.app_id)
live = sqlcl.export_apexlang(options.app_id)
print(render_restore_summary(canonical_digest(live), canonical_digest(backup / "apexlang")))
typed = input(f"Type application ID {options.app_id} to restore: ").strip()
if typed != str(options.app_id):
    return OperationReport("TARGET_UNTOUCHED", 0, backup, None)
sqlcl.import_apexlang(backup / "apexlang", options.workspace, options.app_id)
return verify_restored_target(sqlcl, metadata)
```

- [ ] **Step 5: Run install/uninstall transaction suites**

Run: `PATH="$PWD/tests/fixtures/bin:$PATH" python3 -m unittest tests.test_installer_cli tests.test_uninstaller_cli -v`

Expected: all ownership, fallback, refusal, and recovery cases pass.

- [ ] **Step 6: Commit uninstall and recovery**

```bash
git add lib/theme_factory/uninstall.py lib/theme_factory/cli.py installer/templates tests/test_uninstaller_cli.py
git commit -m "feat: uninstall themes with deterministic fallback"
```

---

### Task 9: Migrate Real Theme Manifests and Complete Offline Acceptance

**Files:**
- Modify: `sample-themes/linen/theme.json`
- Modify: `sample-themes/solarized-dark/theme.json`
- Modify: `sample-themes/linen/README.md`
- Modify: `sample-themes/solarized-dark/README.md`
- Modify: `.gitignore`
- Create: `tests/run-package-offline.sh`
- Modify: `README.md`

**Interfaces:**
- Consumes: all package library and test interfaces from Tasks 1-8.
- Produces: versioned Linen and Solarized Dark package inputs plus one command that proves Layer A/B package readiness.

- [ ] **Step 1: Write the failing package acceptance script**

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 -m unittest \
  tests.test_manifest tests.test_css_bundle tests.test_package_archive \
  tests.test_runtime_contract tests.test_apexlang_patch tests.test_sqlcl \
  tests.test_installer_cli tests.test_uninstaller_cli -v
bash -n scripts/package-theme.sh installer/install.sh installer/uninstall.sh
tmp="$(mktemp -d)"
trap 'test -n "$tmp" && test "$tmp" != / && rm -rf -- "$tmp"' EXIT
scripts/package-theme.sh linen "$tmp/linen"
scripts/package-theme.sh solarized-dark "$tmp/solarized-dark"
```

- [ ] **Step 2: Run it and confirm manifest migration is required**

Run: `bash tests/run-package-offline.sh`

Expected: fail because current manifests do not yet satisfy schema version, version, compatibility, template option, and assets fields.

- [ ] **Step 3: Migrate Linen and Solarized Dark manifests without adding fonts**

Set `schemaVersion` to `1`, `version` to `1.0.0`, compatibility to `>=26.1.0 <26.2.0`/42/`ut-26.1`/Iris, rename `templateOptions.navigationMenu.style` to `templateOptions.navigationMenuStyle`, and add `assets.stylesheet`, `runtime`, and `cover`. Omit `fonts` so both existing themes retain Oracle Sans.

Each manifest must contain this exact contract with its existing name/title/tagline/class values substituted literally during the edit:

```json
{
  "schemaVersion": 1,
  "version": "1.0.0",
  "compatibility": {"apex": ">=26.1.0 <26.2.0", "themeNumber": 42, "baseTheme": "ut-26.1", "style": "iris"},
  "assets": {"stylesheet": "theme.css", "runtime": "theme-factory-runtime.js", "cover": "preview/cover.jpg"},
  "templateOptions": {"navigationMenuStyle": "side"}
}
```

Do not add a `fonts` property to either existing theme.

- [ ] **Step 4: Update user documentation and ignored build outputs**

Document package/build/install commands, single-theme guarantee, custom-font source layout, optional switcher transitions, browser/device persistence, backups, manual guide location, and the separate live-verification requirement. Ignore `/dist/` and `/theme-factory-backups/` while preserving checked-in fixtures.

Append only these root-relative ignore rules:

```gitignore
/dist/
/theme-factory-backups/
```

Add README examples for `scripts/package-theme.sh linen`, extracted `./install.sh` dry-run/apply, `--with-switcher`, `--without-switcher`, and `./uninstall.sh`; every example uses symbolic app/workspace values and explicitly tells the operator to replace them before execution.

- [ ] **Step 5: Run the complete package offline gate twice**

Run: `bash tests/run-package-offline.sh && bash tests/run-package-offline.sh`

Expected: both runs pass; generated ZIP hashes within each run match their second-build comparison and `git status --short` shows no generated source drift.

- [ ] **Step 6: Verify extracted portability explicitly**

Run: `tmp="$(mktemp -d)" && scripts/package-theme.sh linen "$tmp/out" && mkdir "$tmp/extracted" && unzip -q "$tmp/out/linen-1.0.0.zip" -d "$tmp/extracted" && cd "$tmp/extracted/linen-1.0.0" && ./install.sh --help && ./uninstall.sh --help`

Expected: both help commands exit 0 from outside the repository and mention dry-run default, `--apply`, switcher flags, and required SQLcl connection/workspace/app ID.

- [ ] **Step 7: Commit package acceptance**

```bash
git add sample-themes/linen/theme.json sample-themes/solarized-dark/theme.json sample-themes/linen/README.md sample-themes/solarized-dark/README.md README.md .gitignore tests/run-package-offline.sh
git commit -m "docs: publish portable theme package workflow"
```

## Plan Acceptance

- `bash tests/run-package-offline.sh` passes without Oracle, Chrome, or model credentials.
- Linen and Solarized Dark each produce a byte-reproducible ZIP containing only that theme.
- An extracted ZIP runs its own help, checksum verification, dry-run, and fake-SQLcl tests without repository files.
- Font-bearing fixtures accept only declared WOFF2 faces with non-empty licenses and generated package-prefixed families.
- No-font packages retain Iris/Oracle Sans typography and emit no font assets.
- Every refusal path proves that no import was issued.
- Live Oracle/APEX and browser proof is deliberately deferred to `2026-09-15-theme-factory-verification-release.md` and must remain `UNVERIFIED` until executed.
