#!/usr/bin/env python3
"""One-user Chrome DevTools MCP daemon with a persistent consent session."""

import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import threading
from typing import Optional

ALLOWED_TOOLS = frozenset({
    "click", "close_page", "drag", "emulate", "evaluate_script", "fill", "fill_form",
    "get_console_message", "get_network_request", "handle_dialog", "hover",
    "list_console_messages", "list_network_requests", "list_pages", "navigate_page",
    "new_page", "performance_analyze_insight", "performance_start_trace",
    "performance_stop_trace", "press_key", "resize_page", "select_page",
    "take_screenshot", "take_snapshot", "upload_file", "wait_for",
})


def default_socket_path() -> Path:
    override = os.environ.get("THEME_FACTORY_CHROME_MCP_SOCKET")
    if override:
        return Path(override)
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    base = Path(runtime) if runtime else Path(f"/tmp/apex-theme-factory-{os.getuid()}")
    return base / "chrome-mcp/chrome-mcp.sock"


def prepare_socket_path(path: Path) -> Path:
    path = path.expanduser().absolute()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if info.st_uid != os.getuid() or not stat.S_ISSOCK(info.st_mode):
            raise RuntimeError(f"Refusing to replace unsafe socket path: {path}")
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        probe.settimeout(0.25)
        try:
            probe.connect(str(path))
        except ConnectionRefusedError:
            pass
        except OSError as exc:
            raise RuntimeError(f"Refusing to replace ambiguous socket path {path}: {exc}") from exc
        else:
            raise RuntimeError(f"Chrome MCP daemon is already listening on {path}")
        finally:
            probe.close()
        path.unlink()
    return path


class ChromeMcpDaemon:
    def __init__(self, executable: str = "chrome-devtools-mcp", socket_path: Optional[Path] = None):
        self.executable = executable
        self.socket_path = socket_path or default_socket_path()
        self.proc: Optional[subprocess.Popen] = None
        self.lock = threading.Lock()
        self.request_id = 0
        self.server_sock: Optional[socket.socket] = None
        self.socket_identity: Optional[tuple[int, int]] = None

    def _drain_stderr(self) -> None:
        assert self.proc and self.proc.stderr
        for line in self.proc.stderr:
            print(f"chrome-devtools-mcp: {line.rstrip()}", flush=True)

    def _write(self, payload: dict) -> None:
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def _read_response(self, request_id: int) -> dict:
        assert self.proc and self.proc.stdout
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("chrome-devtools-mcp closed its response stream")
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSON-RPC response from chrome-devtools-mcp: {exc}") from exc
            if message.get("id") == request_id:
                return message
            if "id" in message:
                raise RuntimeError(
                    f"Unexpected JSON-RPC response id {message.get('id')!r}; expected {request_id!r}"
                )
            # Legal notification/log message; keep reading for this request's response.

    def start(self) -> None:
        socket_path = prepare_socket_path(self.socket_path)
        self.socket_path = socket_path
        print("Starting persistent chrome-devtools-mcp process...", flush=True)
        self.proc = subprocess.Popen(
            [self.executable, "--auto-connect"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        try:
            self.request_id += 1
            self._write({
                "jsonrpc": "2.0", "id": self.request_id, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "apex-theme-factory", "version": "1.0"}},
            })
            response = self._read_response(self.request_id)
            if response.get("error") or response.get("id") != self.request_id:
                raise RuntimeError(f"chrome-devtools-mcp initialization failed: {response}")
            self._write({"jsonrpc": "2.0", "method": "notifications/initialized"})

            self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_sock.bind(str(socket_path))
            os.chmod(socket_path, 0o600)
            bound = socket_path.lstat()
            self.socket_identity = (bound.st_dev, bound.st_ino)
            self.server_sock.listen(10)
            print(f"Daemon listening on {socket_path}", flush=True)
            while True:
                connection, _ = self.server_sock.accept()
                threading.Thread(target=self.handle_client, args=(connection,), daemon=True).start()
        finally:
            self.close()

    def handle_client(self, connection: socket.socket) -> None:
        with connection:
            try:
                data = b""
                while b"\n" not in data:
                    chunk = connection.recv(4096)
                    if not chunk:
                        return
                    data += chunk
                    if len(data) > 1024 * 1024:
                        raise ValueError("request exceeds 1 MiB")
                request = json.loads(data.split(b"\n", 1)[0])
                tool_name = request.get("name")
                arguments = request.get("arguments", {})
                if tool_name not in ALLOWED_TOOLS:
                    raise ValueError(f"Tool is not allowed: {tool_name!r}")
                if not isinstance(arguments, dict):
                    raise ValueError("arguments must be an object")
                with self.lock:
                    if not self.proc or self.proc.poll() is not None:
                        raise RuntimeError("chrome-devtools-mcp process is not running")
                    self.request_id += 1
                    request_id = self.request_id
                    self._write({"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
                                 "params": {"name": tool_name, "arguments": arguments}})
                    response = self._read_response(request_id)
                connection.sendall((json.dumps(response) + "\n").encode("utf-8"))
            except Exception as exc:
                response = {"jsonrpc": "2.0", "error": {"code": -32600, "message": str(exc)}}
                connection.sendall((json.dumps(response) + "\n").encode("utf-8"))

    def close(self) -> None:
        if self.server_sock:
            self.server_sock.close()
            self.server_sock = None
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
        try:
            info = self.socket_path.lstat()
            identity = (info.st_dev, info.st_ino)
            if (
                self.socket_identity is not None
                and identity == self.socket_identity
                and info.st_uid == os.getuid()
                and stat.S_ISSOCK(info.st_mode)
            ):
                self.socket_path.unlink()
        except FileNotFoundError:
            pass
        self.socket_identity = None


if __name__ == "__main__":
    ChromeMcpDaemon().start()
