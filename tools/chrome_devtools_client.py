#!/usr/bin/env python3
"""Client for the explicitly started, persistent Chrome DevTools MCP daemon (the Chrome backend of browser_client)."""
import sys
from typing import Any, Dict, Optional, Union
from pathlib import Path

try:
    from tools import browser_client as _client
    from tools.browser_mcp_daemon import CHROME, DEFAULT_REQUEST_TIMEOUT, ALLOWED_TOOLS  # noqa: F401
except ModuleNotFoundError:  # direct execution from tools/
    import browser_client as _client
    from browser_mcp_daemon import CHROME, DEFAULT_REQUEST_TIMEOUT, ALLOWED_TOOLS  # noqa: F401

_can_connect = _client._can_connect


def ensure_daemon_running(socket_path: Optional[Union[str, Path]] = None, auto_spawn: bool = False):
    return _client.ensure_daemon_running(socket_path, auto_spawn=auto_spawn, backend=CHROME)


class ChromeDevToolsClient(_client.BrowserClient):
    def __init__(self, socket_path: Optional[Union[str, Path]] = None, auto_spawn: bool = False,
                 response_timeout: Optional[float] = None):
        super().__init__(browser="chrome", socket_path=socket_path, auto_spawn=auto_spawn,
                         response_timeout=response_timeout)


def main() -> None:
    _client.main(["--browser", "chrome", *sys.argv[1:]])


if __name__ == "__main__":
    main()
