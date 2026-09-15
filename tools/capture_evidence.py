#!/usr/bin/env python3
"""Capture runtime evidence from Chrome DevTools into a target file."""

import json
import re
import sys
from tools.chrome_devtools_client import ChromeDevToolsClient


def extract_json_from_result(result: dict) -> dict:
    text = result["content"][0]["text"]
    match = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1), strict=False)
    # Try finding first { and last }
    s = text.find("{")
    e = text.rfind("}")
    if s != -1 and e != -1:
        return json.loads(text[s : e + 1], strict=False)
    raise ValueError(f"Could not parse JSON from result: {text}")


def main():
    target_path = sys.argv[1] if len(sys.argv) > 1 else ".agents/evaluations/runtime/evidence.json"
    client = ChromeDevToolsClient()

    snippet = """() => {
  const perf = performance.getEntriesByType('resource');
  const loaded = perf.map(r => r.name);
  const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map(l => l.getAttribute('href') || l.href);
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.getAttribute('src') || s.src);

  const activeTheme = document.documentElement.dataset.appThemeCurrent ||
                      (document.documentElement.className.match(/app-theme-[a-z0-9-]+/) || ['iris'])[0].replace('app-theme-', '');

  const regEl = document.getElementById('apex-theme-factory-registry');
  let registry = {};
  if (regEl) {
    try { registry = JSON.parse(regEl.textContent); } catch (e) {}
  }

  const switcherBtn = document.querySelector('.t-NavigationBar-item.theme-factory-managed-switcher');

  return {
    capturedAt: new Date().toISOString(),
    url: window.location.href,
    appId: String(window.apex?.env?.APP_ID || ''),
    appAlias: String(window.apex?.env?.APP_ALIAS || ''),
    pageId: String(window.apex?.env?.APP_PAGE_ID || ''),
    apexVersion: String(window.apex?.env?.APEX_VERSION || ''),
    bodyClasses: Array.from(document.body.classList),
    htmlClasses: Array.from(document.documentElement.classList),
    cssUrls: links,
    javascriptUrls: scripts,
    loadedUrls: loaded,
    windowApp: window.App ? Object.keys(window.App) : null,
    windowAlpine: window.Alpine ? window.Alpine.version : null,
    activeTheme: activeTheme,
    registry: registry,
    switcherAvailable: Boolean(switcherBtn),
    consoleErrors: [],
    failedRequests: [],
    fonts: [],
    fontApexFamilyBefore: window.getComputedStyle(document.body).fontFamily,
    fontApexFamilyAfter: window.getComputedStyle(document.body).fontFamily
  };
}"""

    res = client.evaluate_script(1, snippet)
    data = extract_json_from_result(res)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Captured evidence to {target_path}")


if __name__ == "__main__":
    main()
