#!/usr/bin/env python3
"""Browser runtime matrix (Layer D) through the project Chrome MCP daemon.

For each consumer application and required width (1440, 1024, 768, 375) the tool opens the
consumer's home page in its own tab, activates the theme under test through the installed
switcher API, reloads, and records:

* identity: app, alias, page, APEX version, html/body classes, CSS/JS URLs, loaded resources
* console errors and failed network requests since the navigation
* fonts: Font APEX stays loaded and is the icon family; the body family equals bare Iris on the
  same page (a package without custom fonts must not change it — Iris 26.1.4 resolves to the
  system stack, `oraclesans-apex.min.css` is linked but unused) or names the package family
* persistence: the selection survives a reload under `apex.themeFactory.<APP_ID>`
* accessibility: the documented AA contrast audit (docs/CHROME_DEVTOOLS_MCP.md) reports zero
  failures and the switcher menu is keyboard operable (Enter opens a `menuitemradio` group)

Every verification boolean is `true` only when its check passed; a row with errors or an
unverified flag makes the Layer D summary `FAIL`, never `PASS`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import zipfile
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.chrome_devtools_client import ChromeDevToolsClient  # noqa: E402

REQUIRED_WIDTHS = (1440, 1024, 768, 375)
CONSUMERS = ("minimal", "business")


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


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_runtime_artifact(theme: str, git_commit: str, package_sha256: str, row: RowCapture,
                           captured_at: Optional[str] = None) -> dict:
    page = row.page
    window_app = page.get("windowApp")
    if isinstance(window_app, list):
        window_app = {"keys": window_app}
    return {
        "schemaVersion": 1,
        "evidenceType": "browser-runtime",
        "theme": theme,
        "gitCommit": git_commit,
        "packageSha256": package_sha256,
        "capturedAt": captured_at or _now(),
        "consumer": row.consumer,
        "viewportWidth": row.width,
        "url": page.get("url", ""),
        "appId": str(page.get("appId", "")),
        "appAlias": str(page.get("appAlias", "")),
        "pageId": str(page.get("pageId", "")),
        "apexVersion": str(page.get("apexVersion", "")),
        "bodyClasses": list(page.get("bodyClasses", [])),
        "htmlClasses": list(page.get("htmlClasses", [])),
        "cssUrls": list(page.get("cssUrls", [])),
        "javascriptUrls": list(page.get("javascriptUrls", [])),
        "loadedUrls": list(page.get("loadedUrls", [])),
        "windowApp": window_app if isinstance(window_app, dict) or window_app is None else {"value": window_app},
        "windowAlpine": page.get("windowAlpine"),
        "activeTheme": str(page.get("activeTheme", "")),
        "registry": page.get("registry") if isinstance(page.get("registry"), dict) else {},
        "switcherAvailable": bool(page.get("switcherAvailable")),
        "consoleErrors": list(row.console_errors),
        "failedRequests": list(row.failed_requests),
        "fonts": list(page.get("fonts", [])),
        "fontApexFamilyBefore": str(page.get("fontApexFamilyBefore", "")),
        "fontApexFamilyAfter": str(page.get("fontApexFamilyAfter", "")),
        "fontsVerified": bool(row.fonts_verified),
        "accessibilityVerified": bool(row.accessibility_verified),
        "persistenceVerified": bool(row.persistence_verified),
        "notes": list(row.notes),
    }


def write_layer_d_evidence(evidence_dir: Path, theme: str, git_commit: str, package_sha256: str,
                           rows: List[RowCapture], captured_at: Optional[str] = None) -> Path:
    from lib.theme_factory.release import _valid_browser_runtime_artifact  # local import keeps tools importable alone

    captured_at = captured_at or _now()
    evidence_dir = Path(evidence_dir)
    raw_dir = evidence_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    row_refs = []
    failures = []
    covered = set()
    for row in rows:
        artifact = build_runtime_artifact(theme, git_commit, package_sha256, row, captured_at)
        page_label = re.sub(r"[^a-z0-9]+", "-", (row.page.get("pageId") or "p").lower()) or "p"
        path = raw_dir / f"browser-{row.consumer}-page{page_label}-{row.width}.json"
        path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        row_refs.append({"consumer": row.consumer, "width": row.width,
                         "evidence": {"path": f"raw/{path.name}", "sha256": _sha256(path)}})
        if _valid_browser_runtime_artifact(artifact, theme, row.consumer, row.width):
            covered.add((row.consumer, row.width))
        else:
            reasons = []
            if artifact["consoleErrors"]:
                reasons.append(f"console errors: {artifact['consoleErrors'][:3]}")
            if artifact["failedRequests"]:
                reasons.append(f"failed requests: {artifact['failedRequests'][:3]}")
            for flag in ("fontsVerified", "accessibilityVerified", "persistenceVerified"):
                if not artifact[flag]:
                    reasons.append(f"{flag} false")
            if artifact["activeTheme"] != theme:
                reasons.append(f"active theme {artifact['activeTheme']!r}")
            failures.append(f"{row.consumer}@{row.width}: {'; '.join(reasons) or 'contract violation'}" + (f" ({' | '.join(row.notes)})" if row.notes else ""))
    missing = sorted({(c, w) for c in CONSUMERS for w in REQUIRED_WIDTHS} - covered)
    for consumer, width in missing:
        if not any(f.startswith(f"{consumer}@{width}:") for f in failures):
            failures.append(f"{consumer}@{width}: no passing capture")
    status = "PASS" if not failures else "FAIL"
    summary = {
        "schemaVersion": 1, "theme": theme, "gitCommit": git_commit, "packageSha256": package_sha256,
        "capturedAt": captured_at, "layer": "D", "check": "browser_runtime_matrix", "status": status,
        "results": {"rows": row_refs, "failures": failures},
    }
    summary_path = evidence_dir / "browser_runtime_matrix.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest_path = evidence_dir / "evidence.json"
    manifest = {"schemaVersion": 1, "theme": theme, "checks": []}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["checks"] = [c for c in manifest.get("checks", []) if not (c.get("layer") == "D" and c.get("check") == "browser_runtime_matrix")]
    manifest["checks"].append({
        "layer": "D", "check": "browser_runtime_matrix", "status": status,
        "artifact": summary_path.name, "artifactSha256": _sha256(summary_path),
        "details": f"{len(covered)}/{len(CONSUMERS) * len(REQUIRED_WIDTHS)} consumer/width rows verified live at commit {git_commit[:12]}"
                   + ("" if status == "PASS" else f"; failures: {'; '.join(failures)}"),
    })
    manifest["checks"].sort(key=lambda c: (c["layer"], c["check"]))
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return summary_path


# ---------------------------------------------------------------- live capture

PAGE_SNIPPET_TEMPLATE = """async () => {
  const perf = performance.getEntriesByType('resource');
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
  const byName = {};
  for (const r of perf) { byName[r.name.split('/').pop()] = r.name; }
  const faceResults = expected.map(f => ({
    family: f.family, weight: f.weight, style: f.style,
    check: document.fonts.check(f.weight + ' ' + f.style + ' 16px "' + f.family + '"'),
    requestUrl: byName[f.file.split('/').pop()] || ''
  }));
  const fontApexLoaded = document.fonts.check('16px "Font APEX"');
  return {
    url: location.href, appId: String(apex.env.APP_ID), appAlias: String(apex.env.APP_ALIAS || ''),
    pageId: String(apex.env.APP_PAGE_ID), apexVersion: String(apex.env.APEX_VERSION),
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
        return [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#") and "no console messages" not in line.lower()]

    def failed_requests(self) -> List[str]:
        text = _text(self.call("list_network_requests"))
        failed = []
        for line in text.splitlines():
            if re.search(r"\[(?:4|5)\d\d\]|\bfailed\b|net::ERR", line, re.IGNORECASE):
                failed.append(line.strip())
        return failed

    def capture_row(self, consumer: str, url: str, theme: str, width: int) -> RowCapture:
        notes: List[str] = []
        self.call("resize_page", width=width, height=900)
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
        page = self.evaluate(PAGE_SNIPPET_TEMPLATE.replace("__EXPECTED_FACES__", json.dumps(expected_faces)))
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
                          fonts_verified=fonts_ok, accessibility_verified=accessibility, persistence_verified=persistence, notes=notes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture the Layer D browser matrix through the Chrome MCP daemon")
    parser.add_argument("--theme", required=True)
    parser.add_argument("--package", type=Path, required=True, help="the theme's ZIP (for its SHA-256)")
    parser.add_argument("--minimal-url", required=True)
    parser.add_argument("--business-url", required=True)
    parser.add_argument("--business-extra-urls", default="", help="comma-separated extra business pages (reports, widgets, ...) captured at the outer widths")
    parser.add_argument("--evidence-root", type=Path, default=Path(".agents/evaluations/runtime"))
    parser.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    parser.add_argument("--widths", default=",".join(map(str, REQUIRED_WIDTHS)))
    args = parser.parse_args()

    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    from lib.theme_factory.gitstate import last_source_commit, package_source_commit, package_matches_source
    _source_commit = last_source_commit()
    if not package_matches_source(args.package, _source_commit):
        print(f"Refusing: package {args.package} was built at {package_source_commit(args.package)!r}, "
              f"but the current source is {_source_commit!r}; rebuild it before capturing evidence",
              file=sys.stderr)
        raise SystemExit(2)
    package_sha = _sha256(args.package)
    client = ChromeDevToolsClient()
    opened = client.call_tool("new_page", {"url": args.minimal_url, "background": True})
    page_id = int(re.findall(r"^(\d+): .*\[selected\]", _text(opened), re.MULTILINE)[0])
    matrix = LiveBrowserMatrix(client, page_id, package=args.package)
    rows: List[RowCapture] = []
    try:
        widths = [int(w) for w in args.widths.split(",")]
        plan = [("minimal", args.minimal_url, widths), ("business", args.business_url, widths)]
        outer = [w for w in widths if w in (max(widths), min(widths))]
        plan += [("business", url.strip(), outer) for url in args.business_extra_urls.split(",") if url.strip()]
        for consumer, url, plan_widths in plan:
            for width in plan_widths:
                row = matrix.capture_row(consumer, url, args.theme, width)
                status = "ok" if (row.fonts_verified and row.accessibility_verified and row.persistence_verified and not row.console_errors and not row.failed_requests) else "issues"
                print(f"{consumer} page {row.page.get('pageId')}@{width}: {status} {'; '.join(row.notes)}")
                rows.append(row)
    finally:
        try:
            client.call_tool("close_page", {"pageId": page_id})
        except Exception:
            pass
    summary = write_layer_d_evidence(args.evidence_root / f"{args.date}-release-{args.theme}", args.theme, commit, package_sha, rows)
    print(f"Layer D evidence written: {summary}")


if __name__ == "__main__":
    main()
