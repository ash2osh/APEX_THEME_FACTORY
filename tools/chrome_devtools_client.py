#!/usr/bin/env python3
"""Client helper for interacting with persistent chrome-devtools-mcp daemon."""

import json
import os
import socket
import subprocess
import sys
import time
from typing import Any, Dict, Optional

SOCKET_PATH = "/tmp/chrome_mcp.sock"


def ensure_daemon_running():
    if os.path.exists(SOCKET_PATH):
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(SOCKET_PATH)
            s.close()
            return
        except Exception:
            if os.path.exists(SOCKET_PATH):
                os.remove(SOCKET_PATH)

    # Spawn daemon in background
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "chrome_mcp_daemon.py")]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    # Wait for socket to become ready
    for _ in range(50):
        if os.path.exists(SOCKET_PATH):
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(SOCKET_PATH)
                s.close()
                return
            except Exception:
                pass
        time.sleep(0.1)


class ChromeDevToolsClient:
    def __init__(self):
        ensure_daemon_running()

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        ensure_daemon_running()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)
        with sock:
            req = {"name": name, "arguments": arguments or {}}
            sock.sendall((json.dumps(req) + "\n").encode("utf-8"))
            data = b""
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break
        if not data:
            return None
        res = json.loads(data.decode("utf-8").strip(), strict=False)
        if "error" in res:
            raise RuntimeError(f"MCP error: {res['error']}")
        return res.get("result", {})

    def list_pages(self) -> Any:
        return self.call_tool("list_pages")

    def navigate_page(self, page_id: int, url: str) -> Any:
        return self.call_tool("navigate_page", {"pageId": page_id, "url": url})

    def evaluate_script(self, page_id: int, function_code: str) -> Any:
        return self.call_tool("evaluate_script", {"pageId": page_id, "function": function_code})

    def close(self) -> None:
        pass


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 tools/chrome_devtools_client.py <tool_name> [json_args]")
        sys.exit(1)

    tool_name = sys.argv[1]
    args = json.loads(sys.argv[2], strict=False) if len(sys.argv) > 2 else {}

    client = ChromeDevToolsClient()
    res = client.call_tool(tool_name, args)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
