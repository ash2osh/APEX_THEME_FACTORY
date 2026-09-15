# Capturing Runtime Evidence via Chrome DevTools MCP

This document specifies the exact instructions for collecting runtime truth from Oracle APEX using the `chrome-devtools` MCP server attached to Chrome (`--autoConnect`).

## 1. Select the Running Tab
Call `list_pages` on `chrome-devtools` MCP to find the open Oracle APEX application tab (typically at `http://localhost:8181/ords/...`).
Select the matching target page ID.

## 2. Evaluate Runtime Evidence in the Page
Execute the following JavaScript snippet via `evaluate_expression` inside the selected tab:

```javascript
(function() {
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
    consoleErrors: [], // Populated from MCP console tools
    failedRequests: [], // Populated from MCP network tools
    fonts: [],
    fontApexFamilyBefore: window.getComputedStyle(document.body).fontFamily,
    fontApexFamilyAfter: window.getComputedStyle(document.body).fontFamily
  };
})();
```

## 3. Supplement Console and Network Information
1. Use `get_console_messages` to retrieve any errors logged in the session. Map errors to `consoleErrors`.
2. Use `get_network_activity` to retrieve failed requests (status >= 400 or failed). Map failed request URLs to `failedRequests`.

## 4. Save Evidence JSON
Validate the result against `tests/live/runtime-evidence.schema.json` and save to `.agents/evaluations/runtime/<timestamp>-evidence.json`.
