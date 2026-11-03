#!/usr/bin/env python3
"""Page-by-page audit of an APEX app in the browser, through the browser daemon (Firefox by default).

For every page of the app, in each of the given themes, it records the page status, error alerts, console
errors and failed requests of this app, the contrast failures per theme, and horizontal overflow at a phone
width. Results are written one JSON object per page (JSON Lines).

--inject-css loads the current theme stylesheets from this repository into each page. Use it on an app whose
own copy of the theme CSS is older than this checkout (the 26.2 copy of app 102 is one).

    python3 tools/page_audit.py --label 26.2 --base http://localhost:8181/ords/r/demo/ut --inject-css \\
        --themes velvet-signal,solarized-dark,linen --out scratch/audit-262.jsonl
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.browser_check import _contrast_function, _json_result, _text  # noqa: E402
from tools.browser_client import BrowserClient  # noqa: E402
from tools.phone_frame import DESKTOP_MIN_WIDTH, PHONE_CLOSE_JS, phone_open_js  # noqa: E402

PAGE_FILE_RE = re.compile(r"^p(\d+)-.*\.apx$")
THEME_CSS_DIR = ROOT / "applications/ut/shared-components/static-files/css/themes"
CSS_SERVER_PORT = 8765
ERROR_LINE_RE = re.compile(r"\bERROR\b")
FAILED_LINE_RE = re.compile(r"\[(?:4|5)\d\d\b|\bfailed\b|net::ERR", re.IGNORECASE)

PAGE_INFO_JS = """() => ({
  title: document.title,
  apexPage: (typeof apex !== 'undefined' && apex.env) ? apex.env.APP_PAGE_ID : null,
  notFound: /Page not found|Application not found/i.test(document.body ? document.body.innerText.slice(0, 4000) : ''),
  alerts: Array.from(document.querySelectorAll('.t-Alert--danger, .t-Alert--error, .a-Alert--error, .apex-error'))
    .map(e => e.innerText.trim().replace(/\\s+/g, ' ').slice(0, 200)).slice(0, 5),
  themeClasses: document.documentElement.className.split(' ').filter(c => c.startsWith('app-theme-')),
  svgText: document.querySelectorAll('svg text').length
})"""

OVERFLOW_JS = """() => {
  const right = innerWidth + 1;
  const wide = Array.from(document.querySelectorAll('body *'))
    .filter(e => e.getBoundingClientRect().right > right && e.getBoundingClientRect().width > 0)
    .slice(0, 3).map(e => e.tagName.toLowerCase() + '.' + String(e.className).trim().split(/\\s+/).slice(0, 2).join('.'));
  return { width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
           overflow: document.documentElement.scrollWidth > right, wide: wide };
}"""


def page_ids(pages_dir: Path) -> List[int]:
    found = {int(m.group(1)) for path in pages_dir.iterdir() if (m := PAGE_FILE_RE.match(path.name))}
    return sorted(page for page in found if page != 0)


def inject_css_js(urls: List[str]) -> str:
    return ("async () => { const urls = " + json.dumps(urls) + "; for (const u of urls) { await new Promise(res => {"
            " const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = u; l.dataset.tfAudit = '1';"
            " l.onload = res; l.onerror = res; document.head.appendChild(l); }); } return document.querySelectorAll('link[data-tf-audit]').length; }")


BARE = "bare"   # the control: stock Iris with no theme package class


def theme_swap_js(theme: str, settle_ms: int = 2000) -> str:
    """Show one theme by swapping the html class (the same way the runtime does), then let the CSS settle.

    `bare` removes the package class entirely: the stock Universal Theme look, used as the control for findings.
    """
    suffix = "" if theme == BARE else f" + ' app-theme-{theme}'"
    return ("async () => { const orig = document.documentElement.dataset.tfOrig || document.documentElement.className;"
            " document.documentElement.dataset.tfOrig = orig;"
            " document.documentElement.className = orig.split(/\\s+/).filter(c => !c.startsWith('app-theme-')).join(' ')"
            + suffix + ";"
            f" await new Promise(r => setTimeout(r, {settle_ms})); return document.documentElement.className; }}")


def theme_restore_js() -> str:
    return ("() => { const orig = document.documentElement.dataset.tfOrig; if (orig) { document.documentElement.className = orig;"
            " delete document.documentElement.dataset.tfOrig; } return true; }")


def _lines(result) -> List[str]:
    return [line.strip() for line in _text(result).splitlines() if line.strip()]


def chart_theme_js(theme: str) -> str:
    """Choose a theme the way the runtime does (it stores the choice and reloads, so JET draws the charts in it)."""
    choice = "iris" if theme == BARE else theme   # the runtime's own name for stock Iris
    return f"() => {{ window.ApexThemeFactory.use({json.dumps(choice)}); return true; }}"


def stored_choice_js() -> str:
    return ("() => { try { return localStorage.getItem('apex.themeFactory.' + apex.env.APP_ID); } catch (e) { return null; } }")


def restore_choice_js(stored) -> str:
    key = "'apex.themeFactory.' + apex.env.APP_ID"
    if stored is None:
        return f"() => {{ try {{ localStorage.removeItem({key}); }} catch (e) {{}} return true; }}"
    return f"() => {{ try {{ localStorage.setItem({key}, {json.dumps(stored)}); }} catch (e) {{}} return true; }}"


def chart_contrast(client: BrowserClient, page_id: int, url: str, themes: List[str]) -> Dict:
    """Per theme: the runtime reloads the page in that theme, then the contrast audit runs on the drawn charts."""
    stored = _json_result(client.call_tool("evaluate_script", {"pageId": page_id, "function": stored_choice_js()}))
    result: Dict = {}
    try:
        for theme in themes:
            client.call_tool("evaluate_script", {"pageId": page_id, "function": chart_theme_js(theme)})
            time.sleep(4.0)
            info = _json_result(client.call_tool("evaluate_script", {"pageId": page_id, "function": PAGE_INFO_JS}))
            audit = _json_result(client.call_tool("evaluate_script", {
                "pageId": page_id, "function": _contrast_function(), "timeout": 30000}))
            result[theme] = {"failures": audit.get("failures"), "text": audit.get("textNodesScanned"),
                             "svg": audit.get("svgTextScanned"), "sample": audit.get("sample", [])[:4],
                             "themeAfterReload": info.get("themeClasses")}
    finally:
        client.call_tool("evaluate_script", {"pageId": page_id, "function": restore_choice_js(stored)})
        client.call_tool("navigate_page", {"pageId": page_id, "url": url})
        time.sleep(2.5)
    return result


def audit_page(client: BrowserClient, page_id: int, url: str, host: str, themes: List[str],
               css_urls: List[str], widths: List[int], shots: Optional[Path] = None, label: str = "",
               chart_reload_themes: Optional[List[str]] = None) -> Dict:
    started_ms = time.time() * 1000
    client.call_tool("navigate_page", {"pageId": page_id, "url": url})
    time.sleep(2.5)
    record: Dict = {"page": int(url.rsplit("/", 1)[-1]), "url": url}
    if css_urls:
        client.call_tool("evaluate_script", {"pageId": page_id, "function": inject_css_js(css_urls)})
        time.sleep(0.5)
    record.update(_json_result(client.call_tool("evaluate_script", {"pageId": page_id, "function": PAGE_INFO_JS})))
    record["contrast"] = {}
    for theme in themes:
        client.call_tool("evaluate_script", {"pageId": page_id, "function": theme_swap_js(theme)})
        record["contrast"][theme] = _json_result(client.call_tool("evaluate_script", {
            "pageId": page_id, "function": _contrast_function(), "timeout": 30000}))
    client.call_tool("evaluate_script", {"pageId": page_id, "function": theme_restore_js()})
    since = max(0, int(time.time() * 1000 - started_ms))
    record["console"] = [line for line in _lines(client.call_tool("list_console_messages", {
        "pageId": page_id, "types": ["error"], "sinceMs": since})) if ERROR_LINE_RE.search(line)]
    record["failed"] = [line for line in _lines(client.call_tool("list_network_requests", {
        "pageId": page_id, "urlContains": host, "sinceMs": since})) if FAILED_LINE_RE.search(line)]
    number = int(url.rsplit("/", 1)[-1])
    for width in widths:
        if width >= DESKTOP_MIN_WIDTH:
            record[f"overflow_{width}"] = _json_result(client.call_tool("evaluate_script", {
                "pageId": page_id, "function": OVERFLOW_JS}))
            if shots is not None:
                record[f"screenshot_{width}"] = save_screenshot(
                    client, page_id, shots / f"{label}-p{number}-{width}.png")
            continue
        # Firefox cannot shrink the window below about 500 px, so a phone width is measured inside a same-origin frame
        frame_started_ms = time.time() * 1000
        record[f"overflow_{width}"] = _json_result(client.call_tool("evaluate_script", {
            "pageId": page_id, "function": phone_open_js(width), "timeout": 30000}))
        if shots is not None:
            record[f"screenshot_{width}"] = save_screenshot(
                client, page_id, shots / f"{label}-p{number}-{width}.png")
        client.call_tool("evaluate_script", {"pageId": page_id, "function": PHONE_CLOSE_JS})
        since = max(0, int(time.time() * 1000 - frame_started_ms))
        frame_errors = [line for line in _lines(client.call_tool("list_console_messages", {
            "pageId": page_id, "types": ["error"], "sinceMs": since})) if ERROR_LINE_RE.search(line)]
        frame_failed = [line for line in _lines(client.call_tool("list_network_requests", {
            "pageId": page_id, "urlContains": host, "sinceMs": since})) if FAILED_LINE_RE.search(line)]
        record["console"] += [f"phone {width}px: {line}" for line in frame_errors]
        record["failed"] += [f"phone {width}px: {line}" for line in frame_failed]
    if record.get("svgText") and chart_reload_themes:
        record["chartContrast"] = chart_contrast(client, page_id, url, chart_reload_themes)
    return record


def save_screenshot(client: BrowserClient, page_id: int, path: Path, full_page: bool = True) -> str:
    """Write the page's screenshot (PNG, from the browser) to `path`; returns the path or a note on failure."""
    result = client.call_tool("take_screenshot", {"pageId": page_id, "fullPage": full_page})
    for block in result.get("content", []):
        if isinstance(block, dict) and block.get("type") == "image" and block.get("data"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(block["data"]))
            return str(path)
    return "no image in the browser reply"


CSS_SERVER_CODE = """
import functools, http.server, sys
class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Fonts referenced by an injected stylesheet are cross-origin: Firefox refuses them without CORS.
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()
    def log_message(self, *args):
        pass
port, directory = int(sys.argv[1]), sys.argv[2]
http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=directory)).serve_forever()
"""


def start_css_server() -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-c", CSS_SERVER_CODE, str(CSS_SERVER_PORT), str(THEME_CSS_DIR)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", required=True, help="APEX version label written into each record, e.g. 26.2")
    parser.add_argument("--base", required=True, help="app base URL, e.g. http://localhost:8181/ords/r/demo/ut")
    parser.add_argument("--themes", default="velvet-signal,solarized-dark,linen")
    parser.add_argument("--pages", default="", help="comma list of page numbers; default every page of the app")
    parser.add_argument("--widths", default="375", help="phone widths for the overflow check")
    parser.add_argument("--inject-css", action="store_true", help="load this checkout's theme CSS into each page")
    parser.add_argument("--app-dir", default=str(ROOT / "applications/ut"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--resume", action="store_true", help="skip pages already recorded in --out and append")
    parser.add_argument("--screenshots", default="", help="directory for a full-page PNG per page and width")
    parser.add_argument("--chart-reload", action="store_true",
                        help="on pages that draw SVG charts, also check each theme after a reload (JET paints once)")
    args = parser.parse_args(argv)

    themes = [t for t in args.themes.split(",") if t]
    pages = [int(p) for p in args.pages.split(",") if p] or page_ids(Path(args.app_dir) / "pages")
    widths = [int(w) for w in args.widths.split(",") if w]
    host = urlsplit(args.base).netloc
    css_urls = [f"http://127.0.0.1:{CSS_SERVER_PORT}/{t}/theme.css" for t in themes] if args.inject_css else []
    server = start_css_server() if args.inject_css else None
    client = BrowserClient()
    page_id = None
    try:
        time.sleep(1.0 if server else 0)
        opened = client.call_tool("new_page", {"url": f"{args.base}/{pages[0]}", "background": True})
        page_id = int(re.match(r"(\d+):", _text(opened)).group(1))
        done = set()
        if args.resume and Path(args.out).exists():
            with open(args.out, encoding="utf-8") as recorded:
                done = {json.loads(line)["url"] for line in recorded if line.strip()}
        with open(args.out, "a" if args.resume else "w", encoding="utf-8") as out:
            for number in pages:
                url = f"{args.base}/{number}"
                if url in done:
                    continue
                record = None
                for attempt in (1, 2):
                    try:
                        record = audit_page(client, page_id, url, host, themes, css_urls, widths,
                                            Path(args.screenshots) if args.screenshots else None, args.label,
                                            themes if args.chart_reload else None)
                        break
                    except Exception as exc:  # one broken page must not stop the audit; record it and go on
                        record = {"page": number, "url": url, "error": f"attempt {attempt}: {str(exc)[:300]}"}
                        time.sleep(3)
                record["version"] = args.label
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                out.flush()
                if "error" in record:
                    print(f"{args.label} page {number}: ERROR {record['error'][:120]}", flush=True)
                    continue
                print(f"{args.label} page {number}: contrast={ {t: v.get('failures') for t, v in record['contrast'].items()} } "
                      f"console={len(record['console'])} failed={len(record['failed'])} "
                      f"overflow={[record.get(f'overflow_{w}', {}).get('overflow') for w in widths]}", flush=True)
    finally:
        if page_id is not None:
            try:
                client.call_tool("close_page", {"pageId": page_id})
            except Exception:
                pass
        if server is not None:
            server.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
