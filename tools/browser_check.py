#!/usr/bin/env python3
"""Live browser check of one installed theme, through the project Chrome MCP daemon.

Opens the consumer page in its own background tab at a given width, selects the theme through the
installed switcher runtime, reloads, and reports what a user would hit: console errors, failed
requests, fonts that did not load, AA contrast failures (the audit in docs/CHROME_DEVTOOLS_MCP.md),
a switcher that is not keyboard operable, or a selection that does not survive a reload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import zipfile
from pathlib import Path
import re
import sys
import time
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.chrome_devtools_client import ChromeDevToolsClient  # noqa: E402


@dataclass
class RowCapture:
    consumer: str
    width: int
    page: dict
    console_errors: List[str] = field(default_factory=list)
    failed_requests: List[str] = field(default_factory=list)
    fonts_verified: bool = False
    accessibility_verified: bool = False
    persistence_verified: bool = False
    notes: List[str] = field(default_factory=list)
    declared_face_count: int = 0

    def problems(self, theme: str) -> List[str]:
        """Everything a user would notice; empty means the row passed."""
        found = []
        if self.page.get("activeTheme") != theme:
            found.append(f"active theme is {self.page.get('activeTheme')!r}, not {theme!r}")
        found += [f"console error: {line}" for line in self.console_errors]
        found += [f"failed request: {line}" for line in self.failed_requests]
        if not self.fonts_verified:
            found.append("declared fonts not loaded")
        if not self.accessibility_verified:
            found.append("contrast or keyboard check failed")
        if not self.persistence_verified:
            found.append("theme selection not kept across reload")
        return found + [f"note: {note}" for note in self.notes] if found else []


PAGE_SNIPPET_TEMPLATE = r"""async () => {
  const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map(l => l.getAttribute('href') || l.href);
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.getAttribute('src') || s.src);
  const html = document.documentElement;
  const activeTheme = html.dataset.appThemeCurrent || (html.className.match(/app-theme-[a-z0-9-]+/) || ['iris'])[0].replace('app-theme-', '');
  let registry = {};
  try { const r = await fetch(apex.env.APP_FILES + 'theme-factory/runtime/registry.json'); if (r.ok) registry = await r.json(); } catch (e) {}
  const switcherItem = document.querySelector('.t-NavigationBar-item.theme-factory-managed-switcher');
  await document.fonts.ready;
  const icon = document.querySelector('.fa, .t-Icon');
  // The faces this package declares, injected from its manifest; [] for a fontless package.
  const expected = __EXPECTED_FACES__;
  // A @font-face is only downloaded once something renders text in that family, so a
  // face no captured page happens to use (solarized-dark's mono) would look broken.
  // Force each declared face, then judge that: `check` means usable, not exercised.
  const faceChecks = [];
  for (const f of expected) {
    const spec = f.weight + ' ' + f.style + ' 16px "' + f.family + '"';
    let ok = false;
    try {
      const got = await document.fonts.load(spec, 'Ag0');
      ok = got.length > 0 && got.every(x => x.status === 'loaded');
    } catch (e) { ok = false; }
    faceChecks.push({ face: f, ok: ok && document.fonts.check(spec) });
  }
  // Read resources only now, so requestUrl proves the bytes came from the package.
  const perf = performance.getEntriesByType('resource');
  const byName = {};
  for (const r of perf) { byName[r.name.split('/').pop()] = r.name; }
  const faceResults = faceChecks.map(fc => ({
    family: fc.face.family, weight: fc.face.weight, style: fc.face.style,
    check: fc.ok,
    requestUrl: byName[fc.face.file.split('/').pop()] || ''
  }));
  const fontApexLoaded = document.fonts.check('16px "Font APEX"');
  return {
    url: location.href, appId: String(apex.env.APP_ID), appAlias: String(apex.env.APP_ALIAS || ''),
    pageId: String(apex.env.APP_PAGE_ID), apexVersion: String(apex.env.APEX_VERSION),
    browserVersion: (() => {
      const match = navigator.userAgent.match(/(?:Chrome|Chromium)\/[^ ]+/);
      return match ? match[0] : navigator.userAgent;
    })(),
    bodyClasses: Array.from(document.body.classList), htmlClasses: Array.from(html.classList),
    cssUrls: links, javascriptUrls: scripts, loadedUrls: perf.map(r => r.name),
    windowApp: window.App ? { keys: Object.keys(window.App) } : null,
    windowAlpine: window.Alpine ? window.Alpine.version : null,
    activeTheme, registry, switcherAvailable: Boolean(switcherItem),
    faceResults, fontApexLoaded,
    fontApexFamilyBefore: icon ? getComputedStyle(icon, '::before').fontFamily || getComputedStyle(icon).fontFamily : '',
    fontApexFamilyAfter: icon ? getComputedStyle(icon, '::before').fontFamily || getComputedStyle(icon).fontFamily : '',
    bodyFontFamily: getComputedStyle(document.body).fontFamily,
    storedSelection: (() => { try { return localStorage.getItem('apex.themeFactory.' + apex.env.APP_ID); } catch (e) { return null; } })(),
    innerWidth: innerWidth
  };
}"""

def page_snippet(expected: List[dict]) -> str:
    """The page probe with this package's declared faces injected.

    Separate from the template so the contract - every declared face is forced to
    load before anything is measured - is testable without a browser.
    """
    return PAGE_SNIPPET_TEMPLATE.replace("__EXPECTED_FACES__", json.dumps(expected))


CONTRAST_SNIPPET = Path(__file__).resolve().parent.parent.joinpath("docs/CHROME_DEVTOOLS_MCP.md")

KEYBOARD_SNIPPET = """async () => {
  const button = document.querySelector('.t-NavigationBar-item.theme-factory-managed-switcher [data-menu]');
  if (!button) return { ok: false, reason: 'no switcher button' };
  button.focus();
  button.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
  button.click();
  await new Promise(r => setTimeout(r, 400));
  const menu = document.getElementById(button.getAttribute('data-menu'));
  const radios = menu ? Array.from(menu.querySelectorAll('[role="menuitemradio"]')) : [];
  const visible = menu && getComputedStyle(menu).display !== 'none';
  const checked = radios.filter(r => r.getAttribute('aria-checked') === 'true').map(r => r.textContent.trim());
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }));
  return { ok: Boolean(visible && radios.length >= 2 && checked.length === 1), visible, radios: radios.map(r => r.textContent.trim()), checked,
           label: button.getAttribute('aria-label') || button.textContent.trim(), hasPopup: button.getAttribute('aria-haspopup') };
}"""



def font_expectations(package: Path, theme: str) -> List[dict]:
    """Faces the package declares, as the browser should see them.

    Read from the packaged manifest rather than the repository so the evidence
    describes the artifact under test. Family names are the package-scoped ones
    the generated @font-face rules use, never the upstream (possibly reserved) name.
    """
    package = Path(package)
    if package.is_dir():
        manifest = json.loads((package / "theme.json").read_text(encoding="utf-8"))
    else:
        with zipfile.ZipFile(package) as archive:
            name = next(n for n in archive.namelist() if n.endswith("/theme.json") or n == "theme.json")
            manifest = json.loads(archive.read(name).decode("utf-8"))
    expectations: List[dict] = []
    for role in ("body", "heading", "mono"):
        role_obj = (manifest.get("fonts") or {}).get(role)
        if not role_obj:
            continue
        for face in role_obj.get("faces", []):
            expectations.append({
                "role": role,
                "family": f"ThemeFactory-{theme}-{role}",
                "weight": face["weight"],
                "style": face["style"],
                "file": face["file"],
            })
    return expectations


def evaluate_fonts(page: dict, baseline: dict, theme: str, expected: List[dict]) -> Tuple[bool, List[dict]]:
    """Decide fontsVerified, and return schema-shaped evidence for every declared face.

    A face counts only when the browser reports it usable *and* the resource was
    actually requested - `document.fonts.check` alone would pass on a fallback.
    """
    results = {(r.get("family"), r.get("weight"), r.get("style")): r for r in page.get("faceResults", [])}
    entries: List[dict] = []
    all_loaded = True
    for face in expected:
        result = results.get((face["family"], face["weight"], face["style"]), {})
        check = bool(result.get("check")) and bool(result.get("requestUrl"))
        all_loaded = all_loaded and check
        entries.append({
            "role": face["role"], "family": face["family"], "weight": face["weight"],
            "style": face["style"], "check": check,
            "requestUrl": str(result.get("requestUrl") or ""), "mimeType": "font/woff2",
        })
    body_family = page.get("bodyFontFamily") or ""
    body_ok = body_family == baseline.get("body") or f"ThemeFactory-{theme}-body" in body_family
    icon_ok = bool(page.get("fontApexLoaded")) and "Font APEX" in (page.get("fontApexFamilyAfter") or "")
    return (icon_ok and body_ok and all_loaded), entries


def _contrast_function() -> str:
    text = CONTRAST_SNIPPET.read_text(encoding="utf-8")
    match = re.search(r"```js\n(async \(\) => \{\n  await new Promise\(r => setTimeout\(r, 1500\)\);[\s\S]*?\n\}\n)```", text)
    if not match:
        raise RuntimeError("contrast audit snippet not found in docs/CHROME_DEVTOOLS_MCP.md")
    return match.group(1)


def _text(result: dict) -> str:
    return "".join(part.get("text", "") for part in result.get("content", []) if isinstance(part, dict))


def _json_result(result: dict):
    text = _text(result)
    match = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    payload = match.group(1) if match else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(payload, strict=False)


class LiveBrowserMatrix:
    def __init__(self, client: ChromeDevToolsClient, page_id: int, package: Optional[Path] = None):
        self.package = package
        self.client = client
        self.page_id = page_id

    def call(self, name: str, **arguments):
        return self.client.call_tool(name, {"pageId": self.page_id, **arguments})

    def evaluate(self, function: str):
        return _json_result(self.call("evaluate_script", function=function))

    def navigate(self, url: str) -> None:
        self.call("navigate_page", url=url)
        time.sleep(1.0)

    def console_errors(self) -> List[str]:
        text = _text(self.call("list_console_messages", types=["error"]))
        return [
            line.strip() for line in text.splitlines()
            if line.strip()
            and not line.startswith("#")
            and not line.lstrip().startswith("Emulating viewport:")
            and "no console messages" not in line.lower()
        ]

    def failed_requests(self) -> List[str]:
        text = _text(self.call("list_network_requests"))
        failed = []
        for line in text.splitlines():
            if re.search(r"\[(?:4|5)\d\d\]|\bfailed\b|net::ERR", line, re.IGNORECASE):
                failed.append(line.strip())
        return failed

    def capture_row(self, consumer: str, url: str, theme: str, width: int) -> RowCapture:
        notes: List[str] = []
        self.call("emulate", viewport=f"{width}x900x1")
        self.navigate(url)
        # baseline: bare Iris body font on this very page, for the fonts check below
        self.evaluate("() => { const api = window.ApexThemeFactory; return api ? api.use('iris') : false; }")
        time.sleep(2.0)
        baseline = self.evaluate("async () => { await document.fonts.ready; return { body: getComputedStyle(document.body).fontFamily }; }")
        # select the theme through the installed runtime, which persists and reloads
        selected = self.evaluate(
            "() => { const api = window.ApexThemeFactory; if (!api) return {api:false}; "
            f"const ok = api.use({json.dumps(theme)}); return {{api:true, ok}}; }}"
        )
        if not selected.get("api"):
            notes.append("ApexThemeFactory runtime not present (switcher disabled?)")
        time.sleep(2.0)
        expected_faces = font_expectations(self.package, theme) if self.package else []
        page = self.evaluate(page_snippet(expected_faces))
        persistence = page.get("activeTheme") == theme and page.get("storedSelection") == theme
        if not persistence:
            notes.append(f"persistence: active={page.get('activeTheme')!r} stored={page.get('storedSelection')!r}")
        # second reload must keep the selection without calling use() again
        self.navigate(url)
        after_reload = self.evaluate("() => ({ active: document.documentElement.dataset.appThemeCurrent, width: innerWidth })")
        if after_reload.get("active") != theme:
            persistence = False
            notes.append(f"selection lost on reload: {after_reload}")
        body_family = page.get("bodyFontFamily") or ""
        fonts_ok, page["fonts"] = evaluate_fonts(page, baseline, theme, expected_faces)
        page["bodyFontFamilyBareIris"] = baseline.get("body")
        if not fonts_ok:
            notes.append(f"fonts: declared={len(expected_faces)} evidence={page['fonts']} "
                         f"icon={page.get('fontApexFamilyAfter')!r} body={body_family!r} iris={baseline.get('body')!r}")
        contrast = self.evaluate(_contrast_function())
        keyboard = self.evaluate(KEYBOARD_SNIPPET)
        accessibility = contrast.get("failures") == 0 and bool(keyboard.get("ok"))
        if not accessibility:
            notes.append(f"contrast failures={contrast.get('failures')} sample={contrast.get('sample', [])[:3]} keyboard={keyboard}")
        errors = self.console_errors()
        failed = self.failed_requests()
        return RowCapture(consumer=consumer, width=width, page=page, console_errors=errors, failed_requests=failed,
                          fonts_verified=fonts_ok, accessibility_verified=accessibility, persistence_verified=persistence,
                          notes=notes, declared_face_count=len(expected_faces))
