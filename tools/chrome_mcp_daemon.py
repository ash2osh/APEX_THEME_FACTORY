#!/usr/bin/env python3
"""One-user Chrome DevTools MCP daemon with a persistent consent session.

One `chrome-devtools-mcp --autoConnect` child is kept alive so Chrome asks for remote-debugging
consent once; local clients (same uid, private UNIX socket) send `{"name","arguments"}` lines
and receive the JSON-RPC response. Requests are correlated by id through a reader thread, so a
call the MCP never answers (consent prompt pending, another instance holding the connection)
times out and reports an error instead of wedging every later client.
"""

import json
import os
from pathlib import Path
import queue
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
from typing import Dict, Optional, Tuple, Union

ALLOWED_TOOLS = frozenset({
    "click", "close_page", "drag", "emulate", "evaluate_script", "fill", "fill_form",
    "get_console_message", "get_network_request", "handle_dialog", "hover",
    "list_console_messages", "list_network_requests", "list_pages", "navigate_page",
    "new_page", "performance_analyze_insight", "performance_start_trace",
    "performance_stop_trace", "press_key", "resize_page", "select_page",
    "take_screenshot", "take_snapshot", "type_text", "upload_file", "wait_for",
})
DEFAULT_REQUEST_TIMEOUT = float(os.environ.get("THEME_FACTORY_CHROME_MCP_TIMEOUT", "60"))
CLIENT_IO_TIMEOUT = 10.0
MAX_REQUEST_BYTES = 1024 * 1024


def is_tcp_address(addr: Union[str, Path]) -> bool:
    addr_str = str(addr)
    if addr_str.startswith("tcp://"):
        return True
    if addr_str.isdigit():
        return True
    if ":" in addr_str:
        # Check for Windows drive letter like C:\ or D:\
        if len(addr_str) >= 2 and addr_str[1] == ":" and addr_str[0].isalpha():
            rest = addr_str[2:]
            if ":" in rest:
                parts = rest.rsplit(":", 1)
                return parts[1].isdigit()
            return False
        parts = addr_str.rsplit(":", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return True
    return False


def parse_tcp_address(addr: Union[str, Path]) -> Tuple[str, int]:
    addr_str = str(addr)
    if addr_str.startswith("tcp://"):
        addr_str = addr_str[6:]
    if addr_str.isdigit():
        return ("127.0.0.1", int(addr_str))
    parts = addr_str.rsplit(":", 1)
    host = parts[0] or "127.0.0.1"
    port = int(parts[1])
    return (host, port)


DEFAULT_TCP_ENDPOINT = "127.0.0.1:9223"


def default_socket_path() -> Union[str, Path]:
    override = os.environ.get("THEME_FACTORY_CHROME_MCP_SOCKET")
    if override:
        if is_tcp_address(override):
            return override
        return Path(override)
    if not hasattr(socket, "AF_UNIX") or sys.platform == "win32":
        return DEFAULT_TCP_ENDPOINT
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        base = Path(runtime)
    elif hasattr(os, "getuid"):
        base = Path(f"/tmp/apex-theme-factory-{os.getuid()}")
    else:
        user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
        base = Path(tempfile.gettempdir()) / f"apex-theme-factory-{user}"
    return base / "chrome-mcp/chrome-mcp.sock"


def prepare_socket_path(path: Union[str, Path]) -> Path:
    path = Path(path).expanduser().absolute()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if hasattr(os, "getuid") and hasattr(info, "st_uid"):
            if info.st_uid != os.getuid():
                raise RuntimeError(f"Refusing to replace unsafe socket path: {path}")
        if hasattr(stat, "S_ISSOCK") and not stat.S_ISSOCK(info.st_mode):
            raise RuntimeError(f"Refusing to replace unsafe socket path: {path}")
        if hasattr(socket, "AF_UNIX"):
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            probe.settimeout(0.25)
            try:
                probe.connect(str(path))
            except ConnectionRefusedError:
                pass
            except OSError as exc:
                if getattr(exc, "winerror", None) == 10061 or "refused" in str(exc).lower():
                    pass
                else:
                    raise RuntimeError(f"Refusing to replace ambiguous socket path {path}: {exc}") from exc
            else:
                raise RuntimeError(f"Chrome MCP daemon is already listening on {path}")
            finally:
                probe.close()
        try:
            path.unlink()
        except OSError as exc:
            raise RuntimeError(f"Failed to unlink stale socket path {path}: {exc}") from exc
    return path


def _resolve_command(executable: str) -> list[str]:
    """Resolve executable path and wrapper commands across Linux, macOS, and Windows."""
    if executable.endswith(".py"):
        which = shutil.which(executable) or executable
        return [sys.executable, str(which)]

    which = shutil.which(executable)
    target = which or executable
    if sys.platform == "win32":
        target_str = str(target)
        if target_str.lower().endswith((".cmd", ".bat")):
            return ["cmd.exe", "/c", target_str]
    return [str(target)]


class ChromeMcpDaemon:
    def __init__(
        self,
        executable: Optional[str] = None,
        socket_path: Optional[Union[str, Path]] = None,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
    ):
        self.executable = executable or os.environ.get("THEME_FACTORY_CHROME_MCP_EXECUTABLE", "chrome-devtools-mcp")
        self.socket_path = socket_path or default_socket_path()
        self.request_timeout = request_timeout
        self.proc: Optional[subprocess.Popen] = None
        self.lock = threading.Lock()            # serialises writes to the MCP stdin and id allocation
        self.request_id = 0
        self.pending: Dict[int, "queue.Queue[dict]"] = {}
        self.pending_lock = threading.Lock()
        self.server_sock: Optional[socket.socket] = None
        self.socket_identity: Optional[tuple[int, int]] = None
        self.stopping = threading.Event()
        self.reader_thread: Optional[threading.Thread] = None
        self.stderr_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ MCP child I/O
    def _log(self, message: str) -> None:
        if not self.stopping.is_set():
            try:
                print(message, flush=True)
            except (ValueError, OSError):
                pass

    def _drain_stderr(self) -> None:
        assert self.proc and self.proc.stderr
        for line in self.proc.stderr:
            self._log(f"chrome-devtools-mcp: {line.rstrip()}")

    def _write(self, payload: dict) -> None:
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def _read_response(self, request_id: int) -> dict:
        """Synchronous reader used only for the initialize handshake (before the reader thread)."""
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

    def _dispatch_responses(self) -> None:
        """Route every MCP stdout line to the waiting request; answer server->client requests."""
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                self._log(f"chrome-devtools-mcp: non-JSON output ignored: {line.rstrip()[:200]}")
                continue
            if "id" in message and "method" in message:
                # A request from the server (roots/list, sampling, ...): decline politely.
                with self.lock:
                    try:
                        self._write({"jsonrpc": "2.0", "id": message["id"],
                                     "error": {"code": -32601, "message": "Method not supported by daemon"}})
                    except (OSError, ValueError):
                        pass
                continue
            if "id" not in message:
                continue  # notification
            with self.pending_lock:
                waiter = self.pending.pop(message["id"], None)
            if waiter is None:
                self._log(f"chrome-devtools-mcp: late or unknown response id {message.get('id')!r} dropped")
                continue
            waiter.put(message)
        # stdout closed: fail every pending request
        with self.pending_lock:
            waiters = list(self.pending.values())
            self.pending.clear()
        for waiter in waiters:
            waiter.put({"jsonrpc": "2.0", "error": {"code": -32000, "message": "chrome-devtools-mcp closed its response stream"}})

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        if tool_name not in ALLOWED_TOOLS:
            raise ValueError(f"Tool is not allowed: {tool_name!r}")
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be an object")
        waiter: "queue.Queue[dict]" = queue.Queue(maxsize=1)
        with self.lock:
            if not self.proc or self.proc.poll() is not None:
                raise RuntimeError("chrome-devtools-mcp process is not running")
            self.request_id += 1
            request_id = self.request_id
            with self.pending_lock:
                self.pending[request_id] = waiter
            try:
                self._write({"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
                             "params": {"name": tool_name, "arguments": arguments}})
            except (OSError, ValueError) as exc:
                with self.pending_lock:
                    self.pending.pop(request_id, None)
                raise RuntimeError(f"Failed to send request to chrome-devtools-mcp: {exc}") from exc
        try:
            return waiter.get(timeout=self.request_timeout)
        except queue.Empty:
            with self.pending_lock:
                self.pending.pop(request_id, None)
            raise RuntimeError(
                f"chrome-devtools-mcp did not answer '{tool_name}' within {self.request_timeout:g}s; request timed out. "
                "Check Chrome's remote-debugging consent prompt and that no other MCP instance holds the connection."
            )

    # ------------------------------------------------------------------ lifecycle
    def _start_mcp_child(self) -> None:
        self._log("Starting persistent chrome-devtools-mcp process...")
        cmd = _resolve_command(self.executable) + ["--autoConnect"]
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        self.stderr_thread = threading.Thread(target=self._drain_stderr, name="mcp-stderr")
        self.stderr_thread.start()
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
        self.reader_thread = threading.Thread(target=self._dispatch_responses, name="mcp-stdout")
        self.reader_thread.start()

    def start(self) -> None:
        self._install_signal_handlers()
        if is_tcp_address(self.socket_path):
            host, port = parse_tcp_address(self.socket_path)
            self._start_mcp_child()
            try:
                self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_sock.bind((host, port))
                self.server_sock.listen(10)
                self._log(f"Daemon listening on tcp://{host}:{port}")
                while not self.stopping.is_set():
                    try:
                        connection, _ = self.server_sock.accept()
                    except OSError:
                        break  # socket closed by shutdown()
                    threading.Thread(target=self.handle_client, args=(connection,), daemon=True).start()
            finally:
                self.close()
        else:
            if not hasattr(socket, "AF_UNIX"):
                raise RuntimeError(
                    f"Cannot use UNIX socket '{self.socket_path}': AF_UNIX is not supported on this platform. "
                    "Use a TCP address (e.g. 127.0.0.1:9223) instead."
                )
            socket_path = prepare_socket_path(self.socket_path)
            self.socket_path = socket_path
            self._start_mcp_child()
            try:
                self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.server_sock.bind(str(socket_path))
                try:
                    os.chmod(socket_path, 0o600)
                except OSError:
                    pass
                bound = socket_path.lstat()
                self.socket_identity = (bound.st_dev, bound.st_ino)
                self.server_sock.listen(10)
                self._log(f"Daemon listening on {socket_path}")
                while not self.stopping.is_set():
                    try:
                        connection, _ = self.server_sock.accept()
                    except OSError:
                        break  # socket closed by shutdown()
                    threading.Thread(target=self.handle_client, args=(connection,), daemon=True).start()
            finally:
                self.close()

    def _install_signal_handlers(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            return

        def _stop(signum, _frame):
            self._log(f"Received signal {signum}; shutting down")
            self.shutdown()

        signals_to_catch = [signal.SIGTERM, signal.SIGINT]
        for sig_name in ("SIGHUP", "SIGBREAK"):
            sig = getattr(signal, sig_name, None)
            if sig is not None:
                signals_to_catch.append(sig)

        for signum in signals_to_catch:
            try:
                signal.signal(signum, _stop)
            except (ValueError, OSError):
                pass

    def shutdown(self) -> None:
        """Ask the accept loop to stop; safe to call from a signal handler or another thread."""
        self.stopping.set()
        server = self.server_sock
        if server is not None:
            # shutdown() wakes a thread blocked in accept(); close() alone does not on Linux
            for action in (lambda: server.shutdown(socket.SHUT_RDWR), server.close):
                try:
                    action()
                except OSError:
                    pass

    def handle_client(self, connection: socket.socket) -> None:
        with connection:
            try:
                connection.settimeout(CLIENT_IO_TIMEOUT)
                data = b""
                while b"\n" not in data:
                    chunk = connection.recv(4096)
                    if not chunk:
                        return
                    data += chunk
                    if len(data) > MAX_REQUEST_BYTES:
                        raise ValueError("request exceeds 1 MiB")
                request = json.loads(data.split(b"\n", 1)[0])
                response = self.call_tool(request.get("name"), request.get("arguments", {}))
                connection.settimeout(CLIENT_IO_TIMEOUT)
                connection.sendall((json.dumps(response) + "\n").encode("utf-8"))
            except Exception as exc:
                response = {"jsonrpc": "2.0", "error": {"code": -32600, "message": str(exc)}}
                try:
                    connection.sendall((json.dumps(response) + "\n").encode("utf-8"))
                except OSError:
                    pass

    def close(self) -> None:
        self.stopping.set()
        process = self.proc
        if self.server_sock:
            try:
                self.server_sock.close()
            except OSError:
                pass
            self.server_sock = None
        if process and process.poll() is None:
            try:
                if process.stdin:
                    process.stdin.close()
            except OSError:
                pass
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for thread in (self.reader_thread, self.stderr_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=2)
        if process:
            for stream in (process.stdout, process.stderr):
                if stream:
                    stream.close()
        self.proc = None
        if self.socket_identity is not None and not is_tcp_address(self.socket_path):
            try:
                sock_p = Path(self.socket_path)
                info = sock_p.lstat()
                identity = (info.st_dev, info.st_ino)
                is_owner = (
                    not hasattr(os, "getuid")
                    or not hasattr(info, "st_uid")
                    or info.st_uid == os.getuid()
                )
                is_socket = (
                    not hasattr(stat, "S_ISSOCK")
                    or stat.S_ISSOCK(info.st_mode)
                )
                if identity == self.socket_identity and is_owner and is_socket:
                    sock_p.unlink()
            except (FileNotFoundError, OSError):
                pass
            self.socket_identity = None


if __name__ == "__main__":
    try:
        ChromeMcpDaemon().start()
    except RuntimeError as exc:
        print(f"chrome-mcp-daemon: {exc}", file=sys.stderr)
        sys.exit(1)
