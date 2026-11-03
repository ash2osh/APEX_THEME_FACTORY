#!/usr/bin/env python3
"""Chrome DevTools MCP daemon: the shared browser daemon bound to the Chrome backend.

Start it explicitly; it keeps one `chrome-devtools-mcp --autoConnect` child alive so Chrome asks for
consent once. Settings: THEME_FACTORY_CHROME_MCP_SOCKET, _TIMEOUT, _TOKEN_DIR, _EXECUTABLE.
"""
import sys

try:
    from tools import browser_mcp_daemon as _core
    from tools.browser_mcp_daemon import is_tcp_address, parse_tcp_address, prepare_socket_path, read_token  # noqa: F401
    from tools.browser_mcp_daemon import _resolve_command  # noqa: F401
except ModuleNotFoundError:  # direct execution from tools/
    import browser_mcp_daemon as _core
    from browser_mcp_daemon import is_tcp_address, parse_tcp_address, prepare_socket_path, read_token  # noqa: F401
    from browser_mcp_daemon import _resolve_command  # noqa: F401

CHROME = _core.CHROME
ALLOWED_TOOLS = _core.CHROME_TOOLS
DEFAULT_REQUEST_TIMEOUT = _core.DEFAULT_REQUEST_TIMEOUT
DEFAULT_TCP_ENDPOINT = CHROME.default_tcp


def default_socket_path():
    return _core.default_socket_path(CHROME)


def token_path(port: int):
    return _core.token_path(port, CHROME)


def user_state_dir():
    return _core.user_state_dir(CHROME)


class ChromeMcpDaemon(_core.BrowserMcpDaemon):
    def __init__(self, executable=None, socket_path=None, request_timeout=None, initialize_timeout=None):
        super().__init__(CHROME, executable=executable, socket_path=socket_path,
                         request_timeout=request_timeout, initialize_timeout=initialize_timeout)


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    return _core.main(["--browser", "chrome", *args])


if __name__ == "__main__":
    sys.exit(main())
