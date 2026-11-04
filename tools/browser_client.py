#!/usr/bin/env python3
"""Client for the persistent browser DevTools MCP daemons: Firefox by default, Chrome on request.

Call sites use the Chrome-style tool names and page ids that the browser checks were written with, for
example `call_tool("evaluate_script", {"pageId": 3, "function": "..."})`. The Firefox backend translates
each call onto the Firefox DevTools MCP tools (pages are addressed by index and selected first) and reshapes
the reply, so the checks read the same text for either browser. The Chrome backend passes calls through.

Select the browser with THEME_FACTORY_BROWSER=firefox|chrome or the `browser=` argument (default: firefox).
"""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from typing import Any, Dict, Optional, Union

try:
    from tools.browser_mcp_daemon import (
        BACKENDS, Backend, default_socket_path, is_tcp_address, parse_tcp_address,
        read_token, request_timeout_for, token_path,
    )
except ModuleNotFoundError:  # direct execution from tools/
    from browser_mcp_daemon import (
        BACKENDS, Backend, default_socket_path, is_tcp_address, parse_tcp_address,
        read_token, request_timeout_for, token_path,
    )

DEFAULT_BROWSER = "firefox"


def selected_browser(browser: Optional[str] = None) -> Backend:
    name = (browser or os.environ.get("THEME_FACTORY_BROWSER") or DEFAULT_BROWSER).strip().lower()
    if name not in BACKENDS:
        raise ValueError(f"Unknown browser {name!r}; use 'firefox' or 'chrome'")
    return BACKENDS[name]


def _can_connect(socket_path: Union[str, Path]) -> bool:
    try:
        if is_tcp_address(socket_path):
            host, port = parse_tcp_address(socket_path)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
                connection.settimeout(0.5)
                connection.connect((host, port))
            return True
        if not hasattr(socket, "AF_UNIX"):
            return False
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(0.5)
            connection.connect(str(socket_path))
        return True
    except OSError:
        return False


def ensure_daemon_running(
    socket_path: Optional[Union[str, Path]] = None,
    auto_spawn: bool = False,
    backend: Optional[Backend] = None,
) -> Union[str, Path]:
    backend = backend or selected_browser()
    path = socket_path or default_socket_path(backend)
    if _can_connect(path):
        return path
    if not auto_spawn:
        raise RuntimeError(
            f"{backend.daemon_label} daemon is not running at {path}; start tools/{backend.key}_mcp_daemon.py explicitly"
        )
    command = [sys.executable, str(Path(__file__).with_name(f"{backend.key}_mcp_daemon.py"))]
    # The daemon reads its address from the environment: spawn it on the one we will poll.
    env = {**os.environ, f"{backend.env_prefix}_SOCKET": str(path)}
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        process = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=creationflags)
    else:
        process = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
    for _ in range(50):
        if process.poll() is not None:
            raise RuntimeError(f"{backend.daemon_label} daemon failed to start (exit {process.returncode})")
        if _can_connect(path):
            return path
        time.sleep(0.1)
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
        except Exception:
            pass
    process.terminate()
    raise RuntimeError(f"{backend.daemon_label} daemon did not become ready at {path}")


def _text(result: Any) -> str:
    if not isinstance(result, dict):
        return str(result)
    return "".join(part.get("text", "") for part in result.get("content", []) if isinstance(part, dict))


def _reply(text: str) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


class FirefoxTranslator:
    """Chrome-style calls -> Firefox DevTools MCP calls, with replies shaped the way the checks read them."""

    PAGES_RE = re.compile(r"^(>?)\s*\[(\d+)\] (.*) \((.*)\)$")

    def __init__(self, client: "BrowserClient"):
        self.client = client
        self.restore_index: Optional[int] = None   # tab that was selected before a background page opened

    def _raw(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        result = self.client.send(name, arguments or {})
        if isinstance(result, dict) and result.get("isError"):
            # An error is never an empty answer: the checks must see why the browser did not respond.
            raise RuntimeError(f"{self.client.backend.label} error in '{name}': {_text(result)}")
        return result

    def _pages(self):
        pages = []
        for line in _text(self._raw("list_pages")).splitlines():
            match = self.PAGES_RE.match(line.strip())
            if match:
                pages.append({"index": int(match.group(2)), "title": match.group(3),
                              "url": match.group(4), "selected": match.group(1) == ">"})
        return pages

    def _select(self, page_id: Any) -> None:
        self._raw("select_page", {"pageIdx": int(page_id)})

    def call(self, name: str, arguments: Dict[str, Any]) -> Any:
        handler = getattr(self, f"_{name}", None)
        if handler is not None:
            return handler(dict(arguments))
        if name in self.client.backend.allowed_tools:
            return self._raw(name, arguments)
        raise ValueError(f"Tool is not supported by the Firefox backend: {name!r}")

    def _list_pages(self, args):
        lines = []
        for page in self._pages():
            marker = " [selected]" if page["selected"] else ""
            lines.append(f"{page['index']}: {page['title']} ({page['url']}){marker}")
        return _reply("\n".join(lines))

    def _new_page(self, args):
        previous = next((page["index"] for page in self._pages() if page["selected"]), None)
        opened = _text(self._raw("new_page", {"url": args["url"]}))
        match = re.search(r"new page \[(\d+)\]", opened)
        if match is None:
            raise RuntimeError(f"Firefox did not report the new tab index: {opened[:160]!r}")
        index = int(match.group(1))
        if args.get("background"):
            self.restore_index = previous
        return _reply(f"{index}: {args['url']} [selected]")

    def _close_page(self, args):
        closed = self._raw("close_page", {"pageIdx": int(args["pageId"])})
        if self.restore_index is not None:
            try:
                self._select(self.restore_index)
            except RuntimeError:
                pass
            self.restore_index = None
        return closed

    def _navigate_page(self, args):
        self._select(args.pop("pageId"))
        return self._raw("navigate_page", {"url": args["url"]})

    def _evaluate_script(self, args):
        self._select(args.pop("pageId"))
        query = {"function": args["function"]}
        if args.get("timeout") is not None:
            query["timeout"] = int(args["timeout"])   # Firefox's default is 5000 ms; long audits ask for more
        return self._raw("evaluate_script", query)

    LEVEL_LINE_RE = re.compile(r"\b(ERROR|WARN|INFO|LOG|DEBUG)\b")

    def _list_console_messages(self, args):
        self._select(args.pop("pageId"))
        types = args.get("types") or []
        level = types[0] if len(types) == 1 else None
        query = {"level": level} if level else {}
        if args.get("sinceMs") is not None:
            query["sinceMs"] = int(args["sinceMs"])
        raw = self._raw("list_console_messages", query)
        text = _text(raw)
        if "No console messages found" in text:
            return _reply("")
        # Message lines look like "[time] ERROR [source]: text"; footers such as "Total messages" are not messages.
        return _reply("\n".join(line for line in text.splitlines() if self.LEVEL_LINE_RE.search(line)))

    def _list_network_requests(self, args):
        self._select(args.pop("pageId"))
        query = {"statusMin": 400, "limit": 200}
        if args.get("urlContains"):
            query["urlContains"] = args["urlContains"]
        if args.get("sinceMs") is not None:
            query["sinceMs"] = int(args["sinceMs"])
        return self._raw("list_network_requests", query)

    def _emulate(self, args):
        self._select(args.pop("pageId"))
        match = re.match(r"^\s*(\d+)x(\d+)", str(args.get("viewport", "")))
        if match is None:
            raise ValueError(f"viewport must look like 1440x900x1, got {args.get('viewport')!r}")
        return self._raw("set_viewport_size", {"width": int(match.group(1)), "height": int(match.group(2))})

    def _take_screenshot(self, args):
        self._select(args.pop("pageId"))
        query = {"fullPage": True} if args.get("fullPage") else {}
        return self._raw("screenshot_page", query)


class BrowserClient:
    def __init__(
        self,
        browser: Optional[str] = None,
        socket_path: Optional[Union[str, Path]] = None,
        auto_spawn: bool = False,
        response_timeout: Optional[float] = None,
    ):
        self.backend = selected_browser(browser)
        self.socket_path = ensure_daemon_running(socket_path, auto_spawn=auto_spawn, backend=self.backend)
        # slightly longer than the daemon's own request timeout so its error reaches us first
        self.response_timeout = response_timeout if response_timeout is not None else request_timeout_for(self.backend) + 10.0
        self._translator = FirefoxTranslator(self) if self.backend.key == "firefox" else None

    def _create_connection(self) -> socket.socket:
        if is_tcp_address(self.socket_path):
            host, port = parse_tcp_address(self.socket_path)
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(self.response_timeout)
            conn.connect((host, port))
            return conn
        if not hasattr(socket, "AF_UNIX"):
            raise RuntimeError(
                f"Cannot connect to UNIX socket '{self.socket_path}': AF_UNIX is not supported on this platform. "
                f"Use a TCP address (e.g. {self.backend.default_tcp}) instead."
            )
        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.settimeout(self.response_timeout)
        conn.connect(str(self.socket_path))
        return conn

    def send(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """One raw request to the daemon, using the browser's own tool names."""
        if name not in self.backend.allowed_tools:
            raise ValueError(f"{self.backend.daemon_label} tool is not allowed: {name!r}")
        ensure_daemon_running(self.socket_path, backend=self.backend)
        request: Dict[str, Any] = {"name": name, "arguments": arguments or {}}
        if is_tcp_address(self.socket_path):
            # Read per call: a restarted daemon writes a new token.
            _host, port = parse_tcp_address(self.socket_path)
            token = read_token(token_path(port, self.backend))
            if token is None:
                raise RuntimeError(
                    f"No {self.backend.daemon_label} daemon token at {token_path(port, self.backend)}; the daemon on "
                    f"{self.socket_path} was not started by this account"
                )
            request["token"] = token
        with self._create_connection() as connection:
            connection.sendall((json.dumps(request) + "\n").encode("utf-8"))
            data = b""
            try:
                while b"\n" not in data:
                    chunk = connection.recv(65536)
                    if not chunk:
                        break
                    data += chunk
            except socket.timeout as exc:
                raise RuntimeError(
                    f"{self.backend.daemon_label} daemon did not answer '{name}' within {self.response_timeout:g}s; "
                    "request timed out"
                ) from exc
        if not data:
            raise RuntimeError(f"{self.backend.daemon_label} daemon returned no response")
        response = json.loads(data.split(b"\n", 1)[0])
        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")
        return response.get("result", {})

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        if self._translator is not None:
            return self._translator.call(name, dict(arguments or {}))
        return self.send(name, arguments)

    def list_pages(self) -> Any:
        return self.call_tool("list_pages")

    def close(self) -> None:
        pass


def main(argv: Optional[list] = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    browser = None
    if argv[:1] == ["--browser"] and len(argv) >= 2:
        browser, argv = argv[1], argv[2:]
    if not argv:
        print("Usage: python3 tools/browser_client.py [--browser firefox|chrome] <tool_name> [json_args]", file=sys.stderr)
        raise SystemExit(1)
    tool_name = argv[0]
    arguments = json.loads(argv[1]) if len(argv) > 1 else {}
    print(json.dumps(BrowserClient(browser=browser).call_tool(tool_name, arguments), indent=2))


if __name__ == "__main__":
    main()
