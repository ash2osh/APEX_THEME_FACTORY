# Firefox DevTools daemon

Firefox is the default browser for live checks: the release smoke, the browser check and the
runtime checks of this project. The daemon keeps one Firefox DevTools MCP connection open, so the
browser asks for permission once instead of on every call.

## Start Firefox first

Start Firefox from its launcher (on this PC: the Firefox entry in the application menu). The launcher
passes both flags the MCP needs:

    /snap/bin/firefox --remote-debugging-port=9333 --marionette

- `--remote-debugging-port=9333` opens the WebDriver BiDi endpoint on port 9333.
- `--marionette` opens Marionette, which the MCP attaches to on port 2828 (its default).

If Firefox was started with only one of the flags, the MCP answers with `No Marionette listener` or asks
for both flags. Start Firefox again from the launcher.

> Marionette sets `navigator.webdriver` and other fingerprint signals. Restart Firefox normally after the
> checks. The MCP can reach every tab, cookie and login in the profile it attaches to, so use a dedicated
> profile for automation when you can.

## Run the daemon

    python3 tools/firefox_mcp_daemon.py          # keep this running; Ctrl+C or kill to stop

The daemon starts one `@mozilla/firefox-devtools-mcp@0.10.6 --connect-existing --marionette-port 2828`
child. It listens on `$XDG_RUNTIME_DIR/firefox-mcp/firefox-mcp.sock` (Linux and macOS) or on
`127.0.0.1:9224` with a per-user token (native Windows). Its settings are environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `THEME_FACTORY_FIREFOX_MCP_SOCKET` | the socket above | address to listen on |
| `THEME_FACTORY_FIREFOX_MCP_TIMEOUT` | 60 s | how long a call may wait for Firefox |
| `THEME_FACTORY_FIREFOX_MCP_TOKEN_DIR` | per-user state folder | where the TCP token is written |
| `THEME_FACTORY_FIREFOX_MCP_EXECUTABLE` | `npx` | replaces the first word of the MCP command |

Only one Firefox daemon may run per user. A second one refuses to start.

## Call it

    python3 tools/browser_client.py list_pages
    python3 tools/browser_client.py navigate_page '{"pageId": 1, "url": "http://localhost:8181/ords/r/demo/ut/406"}'

The checks use the same client from Python (`tools.browser_client.BrowserClient`). Set
`THEME_FACTORY_BROWSER=chrome` to use the Chrome daemon instead.

## How the Chrome-style calls map

The checks were written for Chrome's tools. The Firefox backend translates them and reshapes the answers:

| Call used by the checks | What the Firefox backend does |
|---|---|
| `list_pages` | lists tabs as `index: title (url)`, with `[selected]` on the current tab |
| `new_page {url, background}` | opens a tab and reports its index; with `background`, the previous tab is selected again after `close_page` |
| `navigate_page {pageId, url}` | selects the tab, then navigates it |
| `evaluate_script {pageId, function}` | selects the tab, then runs the script; the reply format is unchanged |
| `list_console_messages {pageId, types}` | selects the tab, then filters by level (`types: ["error"]` becomes `level: "error"`) |
| `list_network_requests {pageId}` | selects the tab, then lists responses with status 400 or more |
| `emulate {pageId, viewport}` | selects the tab, then sets the viewport size |
| `take_screenshot {pageId}` | selects the tab, then takes a PNG screenshot |
| `close_page {pageId}` | closes the tab |

An error from Firefox is raised, never turned into an empty answer. A call the Firefox backend does not
know is refused.

## Limits to know

- New tabs open in the front of the Firefox window. The checks select their own tab for each call and
  select the previous tab again when they close it.
- `emulate` resizes the Firefox window, because Firefox sets the viewport through the window size.
- Screenshots are PNG. Theme cover images are JPEG, so `tools/theme_cover.py` and `lib/theme_factory/cli.py cover`
  keep using the Chrome daemon.
- Page indexes can shift when a tab in front of yours closes. The checks read the index again on each run.

## Troubleshooting

| Message | Cause and fix |
|---|---|
| `No Marionette listener on 127.0.0.1:2828` | Firefox is not running with `--marionette`. Start it from its launcher. |
| `Firefox DevTools daemon is not running` | Start `python3 tools/firefox_mcp_daemon.py` in its own terminal. |
| `did not answer ... within 60s` | The MCP is waiting for Firefox or another client holds the connection. Close other Firefox MCP instances. |
