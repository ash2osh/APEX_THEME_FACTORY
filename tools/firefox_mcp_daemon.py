#!/usr/bin/env python3
"""Firefox DevTools MCP daemon: the shared browser daemon bound to the Firefox backend.

Start Firefox first from its launcher (it passes --marionette and --remote-debugging-port=9333). The daemon
keeps one `@mozilla/firefox-devtools-mcp --connect-existing` child alive. Settings:
THEME_FACTORY_FIREFOX_MCP_SOCKET, _TIMEOUT, _TOKEN_DIR, _EXECUTABLE.
"""
import sys

try:
    from tools import browser_mcp_daemon as _core
except ModuleNotFoundError:  # direct execution from tools/
    import browser_mcp_daemon as _core

FIREFOX = _core.FIREFOX


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    return _core.main(["--browser", "firefox", *args])


if __name__ == "__main__":
    sys.exit(main())
