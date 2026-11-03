#!/usr/bin/env python3
"""One-user browser DevTools MCP daemon with a persistent consent session (Firefox by default, or Chrome).

One MCP child is kept alive (`chrome-devtools-mcp --autoConnect` for Chrome, or the Firefox DevTools MCP
attached to a running Firefox) so the browser asks for remote-debugging consent once; local clients (same uid, private UNIX socket) send `{"name","arguments"}` lines
and receive the JSON-RPC response. Over TCP loopback (the default on Windows, or an explicit
`host:port`) any local account can connect, so the daemon writes a random token to a per-user
file and refuses every request that does not carry it. Requests are correlated by id through a
reader thread, so a call the MCP never answers (consent prompt pending, another instance holding
the connection) times out and reports an error instead of wedging every later client.
"""

import argparse
from dataclasses import dataclass
import hmac
import ipaddress
import json
import os
from pathlib import Path
import queue
import secrets
import select
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any

try:
    import fcntl
except ModuleNotFoundError:  # Windows: the Unix-socket mode and its flock are unavailable
    fcntl = None  # type: ignore[assignment]

CHROME_TOOLS = frozenset({
    "click", "close_page", "drag", "emulate", "evaluate_script", "fill", "fill_form",
    "get_console_message", "get_network_request", "handle_dialog", "hover",
    "list_console_messages", "list_network_requests", "list_pages", "navigate_page",
    "new_page", "performance_analyze_insight", "performance_start_trace",
    "performance_stop_trace", "press_key", "resize_page", "select_page",
    "take_screenshot", "take_snapshot", "type_text", "upload_file", "wait_for",
})
# Firefox DevTools MCP (@mozilla/firefox-devtools-mcp) tool names the daemon may forward. Pages are
# addressed by index (select_page/pageIdx); install/uninstall, profiler, logpoint and PDF tools are not allowed.
FIREFOX_TOOLS = frozenset({
    "list_pages", "new_page", "navigate_page", "select_page", "close_page", "get_page_text",
    "take_snapshot", "click_by_uid", "hover_by_uid", "fill_by_uid", "press_key", "type_text",
    "list_network_requests", "get_network_request", "list_console_messages", "clear_console_messages",
    "screenshot_page", "screenshot_by_uid", "set_viewport_size", "evaluate_script", "navigate_history",
    "accept_dialog", "dismiss_dialog", "list_downloads", "set_download_behavior",
})
MAX_REQUEST_BYTES = 1024 * 1024
ACCEPT_POLL_SECONDS = 0.5
CLIENT_IO_TIMEOUT = 10.0


@dataclass(frozen=True)
class Backend:
    """What differs between the browsers: the MCP command, its tools, and the names used for paths and messages."""
    key: str                  # "chrome" or "firefox"; also the client-facing name
    label: str                # "Chrome DevTools MCP" / "Firefox DevTools MCP"
    daemon_label: str         # "Chrome MCP" / "Firefox MCP", as used in messages
    process_name: str         # the MCP process as it appears in logs
    command: tuple            # full MCP command; command[0] is replaced by <ENV_PREFIX>_EXECUTABLE
    env_prefix: str           # THEME_FACTORY_<BROWSER>_MCP: _SOCKET, _TIMEOUT, _TOKEN_DIR, _EXECUTABLE
    state_dirname: str        # per-user folder for sockets and TCP tokens
    default_tcp: str          # TCP endpoint on native Windows
    allowed_tools: frozenset  # tools a client may forward
    consent_hint: str         # shown when the MCP does not answer


CHROME = Backend(
    key="chrome",
    label="Chrome DevTools MCP",
    daemon_label="Chrome MCP",
    process_name="chrome-devtools-mcp",
    command=("chrome-devtools-mcp", "--autoConnect"),
    env_prefix="THEME_FACTORY_CHROME_MCP",
    state_dirname="chrome-mcp",
    default_tcp="127.0.0.1:9223",
    allowed_tools=CHROME_TOOLS,
    consent_hint="Chrome's remote-debugging consent prompt",
)
FIREFOX = Backend(
    key="firefox",
    label="Firefox DevTools MCP",
    daemon_label="Firefox MCP",
    process_name="firefox-devtools-mcp",
    # --connect-existing attaches to a Firefox started with --marionette and --remote-debugging-port
    # (the Start-menu launcher passes both; the debugging port is 9333). Marionette is on 2828 by default.
    command=("npx", "-y", "@mozilla/firefox-devtools-mcp@0.10.6", "--connect-existing",
             "--marionette-port", "2828", "--tool-preset", "developer"),
    env_prefix="THEME_FACTORY_FIREFOX_MCP",
    state_dirname="firefox-mcp",
    default_tcp="127.0.0.1:9224",
    allowed_tools=FIREFOX_TOOLS,
    consent_hint="that Firefox was started with --marionette and --remote-debugging-port, and that Marionette is reachable",
)
BACKENDS = {CHROME.key: CHROME, FIREFOX.key: FIREFOX}
# Chrome names kept for the modules and tests that predate the backend table.
ALLOWED_TOOLS = CHROME_TOOLS
DEFAULT_TCP_ENDPOINT = CHROME.default_tcp
DEFAULT_REQUEST_TIMEOUT = float(os.environ.get("THEME_FACTORY_CHROME_MCP_TIMEOUT", "60"))


def request_timeout_for(backend: Backend = CHROME) -> float:
    return float(os.environ.get(f"{backend.env_prefix}_TIMEOUT", "60"))

ACCEPT_POLL_SECONDS = 0.5


def unix_socket_mode_supported() -> bool:
    """The private Unix socket needs AF_UNIX, flock and POSIX file modes: not native Windows."""
    return sys.platform != "win32" and os.name != "nt" and hasattr(socket, "AF_UNIX") and fcntl is not None


def _foreign_owner(info: os.stat_result) -> bool:
    """True when a path is owned by another user. Platforms without uids (native Windows) cannot tell."""
    return hasattr(os, "getuid") and info.st_uid != os.getuid()


def _owned_by_us(info: os.stat_result) -> bool:
    return not hasattr(os, "getuid") or info.st_uid == os.getuid()


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def is_tcp_address(address: str | Path) -> bool:
    addr_str = str(address)
    if addr_str.startswith("tcp://"):
        return True
    if addr_str.isdigit():
        return True
    if ":" in addr_str:
        # Windows drive letter like C:\ or D:/ is a path, not a host:port
        if len(addr_str) >= 2 and addr_str[1] == ":" and addr_str[0].isalpha():
            rest = addr_str[2:]
            if ":" in rest:
                return rest.rsplit(":", 1)[1].isdigit()
            return False
        parts = addr_str.rsplit(":", 1)
        return len(parts) == 2 and parts[1].isdigit()
    return False


def parse_tcp_address(address: str | Path) -> tuple[str, int]:
    addr_str = str(address)
    if addr_str.startswith("tcp://"):
        addr_str = addr_str[6:]
    if addr_str.isdigit():
        return ("127.0.0.1", int(addr_str))
    parts = addr_str.rsplit(":", 1)
    return (parts[0] or "127.0.0.1", int(parts[1]))


def user_state_dir(backend: Backend = CHROME) -> Path:
    """Per-user directory for the socket and the TCP token: other local accounts cannot read it."""
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        base = (Path(local) if local else Path.home() / "AppData" / "Local") / "apex-theme-factory"
    else:
        runtime = os.environ.get("XDG_RUNTIME_DIR")
        if runtime:
            base = Path(runtime)
        elif hasattr(os, "getuid"):
            base = Path(f"/tmp/apex-theme-factory-{os.getuid()}")
        else:
            user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
            base = Path(tempfile.gettempdir()) / f"apex-theme-factory-{user}"
    return base / backend.state_dirname


def token_path(port: int, backend: Backend = CHROME) -> Path:
    """Where the daemon listening on TCP `port` keeps the token its clients must send."""
    override = os.environ.get(f"{backend.env_prefix}_TOKEN_DIR")
    return (Path(override) if override else user_state_dir(backend)) / f"tcp-{port}.token"


def write_token(path: Path, token: str) -> None:
    if os.name == "nt":
        # %LOCALAPPDATA% is readable by its owner (and administrators) only.
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        _ensure_private_socket_directory(path.parent)
    staged = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as handle:
        handle.write(token)
    os.replace(staged, path)


def read_token(path: Path) -> str | None:
    try:
        return path.read_text(encoding="ascii").strip() or None
    except (OSError, UnicodeDecodeError):
        return None


def default_socket_path(backend: Backend = CHROME) -> str | Path:
    override = os.environ.get(f"{backend.env_prefix}_SOCKET")
    if override:
        return override if is_tcp_address(override) else Path(override)
    if not unix_socket_mode_supported():
        return backend.default_tcp
    return user_state_dir(backend) / f"{backend.state_dirname}.sock"


def _resolve_command(executable: str) -> list[str]:
    """The command line for the MCP executable: npm's Windows wrappers run through cmd.exe."""
    if executable.endswith(".py"):
        return [sys.executable, shutil.which(executable) or executable]
    target = shutil.which(executable) or executable
    if sys.platform == "win32" and target.lower().endswith((".cmd", ".bat")):
        return ["cmd.exe", "/c", target]
    return [target]


def _create_kill_on_close_job(process: subprocess.Popen) -> Any:
    """Windows: put the MCP child in a job that ends it and everything it started (node.exe
    under npm's cmd.exe wrapper) when terminated or when this daemon's handle closes."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION), ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryLimit", ctypes.c_size_t), ("PeakJobMemoryLimit", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
        kernel32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD)
        kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not (kernel32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
                and kernel32.AssignProcessToJobObject(job, int(process._handle))):
            kernel32.CloseHandle(job)
            return None
        return job
    except (OSError, AttributeError, ValueError):
        return None


def _terminate_job(job: Any) -> None:
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel32.TerminateJobObject(job, 1)


def _close_job(job: Any) -> None:
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle(job)


def prepare_socket_path(path: Path) -> Path:
    path = path.expanduser().absolute()
    _ensure_private_socket_directory(path.parent)
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if _foreign_owner(info) or not stat.S_ISSOCK(info.st_mode):
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
            raise RuntimeError(f"A browser MCP daemon is already listening on {path}")
        finally:
            probe.close()
        path.unlink()
    return path


def _ensure_private_socket_directory(parent: Path) -> None:
    """Create only the dedicated socket directory; never chmod an existing path."""
    parent = parent.absolute()
    for ancestor in reversed(parent.parents):
        try:
            info = ancestor.lstat()
        except FileNotFoundError as exc:
            raise RuntimeError(f"Socket directory ancestor does not exist: {ancestor}") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise RuntimeError(f"Socket path has an unsafe directory ancestor: {ancestor}")

    created = False
    try:
        parent.mkdir(mode=0o700)
        created = True
    except FileExistsError:
        pass
    except FileNotFoundError as exc:
        raise RuntimeError(f"Socket parent must have an existing parent directory: {parent}") from exc

    if created:
        os.chmod(parent, 0o700)
    try:
        info = parent.lstat()
    except OSError as exc:
        raise RuntimeError(f"Cannot inspect socket directory {parent}: {exc}") from exc
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISDIR(info.st_mode)
        or _foreign_owner(info)
        or (info.st_mode & 0o777) != 0o700
    ):
        raise RuntimeError(
            f"Socket parent must be an owned, non-symlink directory with mode 0700: {parent}"
        )


class BrowserMcpDaemon:
    def __init__(
        self,
        backend: Backend = CHROME,
        executable: str | None = None,
        socket_path: str | Path | None = None,
        request_timeout: float | None = None,
        initialize_timeout: float | None = None,
    ):
        self.backend = backend
        command = list(backend.command)
        override = executable or os.environ.get(f"{backend.env_prefix}_EXECUTABLE")
        if override:
            command[0] = override
        self.command = tuple(command)
        self.socket_path = socket_path or default_socket_path(backend)
        self.request_timeout = request_timeout if request_timeout is not None else request_timeout_for(backend)
        self.initialize_timeout = self.request_timeout if initialize_timeout is None else initialize_timeout
        self.proc: subprocess.Popen | None = None
        self.lock = threading.Lock()            # serialises writes to the MCP stdin and id allocation
        self.request_id = 0
        self.pending: dict[int, queue.Queue[dict]] = {}
        self.pending_lock = threading.Lock()
        self.server_sock: socket.socket | None = None
        self.socket_identity: tuple[int, int] | None = None
        self.lock_fd: int | None = None
        self.lock_path: Path | None = None
        self.job: Any = None                    # Windows job object holding the MCP child's tree
        self.auth_token: str | None = None      # TCP only: loopback is reachable by every local account
        self.token_file: Path | None = None
        self.stopping = threading.Event()
        self.initialize_timed_out = threading.Event()
        self.initialize_complete = threading.Event()
        self.reader_thread: threading.Thread | None = None
        self.stderr_thread: threading.Thread | None = None

    def _acquire_startup_lock(self) -> None:
        _ensure_private_socket_directory(self.socket_path.expanduser().absolute().parent)
        self.socket_path = self.socket_path.expanduser().absolute()
        lock_path = self.socket_path.with_name(self.socket_path.name + ".lock")
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        created = False
        try:
            fd = os.open(lock_path, flags | os.O_EXCL, 0o600)
            created = True
        except FileExistsError:
            try:
                fd = os.open(lock_path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
            except OSError as exc:
                raise RuntimeError(f"Cannot safely open daemon lock {lock_path}: {exc}") from exc
        except OSError as exc:
            raise RuntimeError(f"Cannot create daemon lock {lock_path}: {exc}") from exc

        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or _foreign_owner(info)
                or (info.st_mode & 0o777) != 0o600
            ):
                raise RuntimeError(f"Refusing unsafe daemon lock file: {lock_path}")
            if created:
                os.fchmod(fd, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError(f"A {self.backend.daemon_label} daemon is already starting or running for {self.socket_path}") from exc
        except Exception:
            os.close(fd)
            raise
        self.lock_fd = fd
        self.lock_path = lock_path

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
            self._log(f"{self.backend.process_name}: {line.rstrip()}")

    def _write(self, payload: dict, deadline: float | None = None) -> None:
        assert self.proc and self.proc.stdin
        fd = self.proc.stdin.fileno()
        encoded = (json.dumps(payload) + "\n").encode("utf-8")
        write_deadline = deadline if deadline is not None else time.monotonic() + self.request_timeout
        if os.name == "nt":
            self._write_with_thread(fd, encoded, write_deadline)
            return
        if os.get_blocking(fd):
            os.set_blocking(fd, False)
        offset = 0
        while offset < len(encoded):
            remaining = write_deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Timed out writing a request to {self.backend.process_name}")
            try:
                _readable, writable, _exceptional = select.select([], [fd], [], remaining)
            except OSError as exc:
                raise RuntimeError(f"Failed to wait for {self.backend.process_name} stdin: {exc}") from exc
            if not writable:
                raise TimeoutError(f"Timed out writing a request to {self.backend.process_name}")
            try:
                written = os.write(fd, encoded[offset:])
            except BlockingIOError:
                continue
            if written <= 0:
                raise RuntimeError(f"{self.backend.process_name} stdin closed while writing")
            offset += written

    def _write_with_thread(self, fd: int, encoded: bytes, deadline: float) -> None:
        """Windows has no select() for pipes: write in a helper thread and stop waiting at the
        deadline. A write still blocked then ends when the caller stops the MCP child."""
        outcome: list[BaseException | None] = []

        def write_all() -> None:
            try:
                offset = 0
                while offset < len(encoded):
                    written = os.write(fd, encoded[offset:])
                    if written <= 0:
                        raise RuntimeError(f"{self.backend.process_name} stdin closed while writing")
                    offset += written
                outcome.append(None)
            except BaseException as exc:  # handed to the waiting caller
                outcome.append(exc)

        writer = threading.Thread(target=write_all, name="mcp-stdin", daemon=True)
        writer.start()
        writer.join(max(0.0, deadline - time.monotonic()))
        if writer.is_alive():
            raise TimeoutError(f"Timed out writing a request to {self.backend.process_name}")
        if outcome and outcome[0] is not None:
            raise outcome[0]

    def _read_response(self, request_id: int) -> dict:
        """Synchronous reader used only for the initialize handshake (before the reader thread)."""
        assert self.proc and self.proc.stdout
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"{self.backend.process_name} closed its response stream")
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSON-RPC response from {self.backend.process_name}: {exc}") from exc
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
                self._log(f"{self.backend.process_name}: non-JSON output ignored: {line.rstrip()[:200]}")
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
                self._log(f"{self.backend.process_name}: late or unknown response id {message.get('id')!r} dropped")
                continue
            waiter.put(message)
        # stdout closed: fail every pending request
        with self.pending_lock:
            waiters = list(self.pending.values())
            self.pending.clear()
        for waiter in waiters:
            waiter.put({"jsonrpc": "2.0", "error": {"code": -32000, "message": f"{self.backend.process_name} closed its response stream"}})
        if not self.stopping.is_set():
            # The MCP child is gone: a daemon without it would only fail every later call.
            self._log(f"{self.backend.process_name} exited; shutting down daemon")
            self.shutdown()

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        if tool_name not in self.backend.allowed_tools:
            raise ValueError(f"Tool is not allowed: {tool_name!r}")
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be an object")
        deadline = time.monotonic() + self.request_timeout
        waiter: queue.Queue[dict] = queue.Queue(maxsize=1)
        remaining = max(0.0, deadline - time.monotonic())
        if not self.lock.acquire(timeout=remaining):
            self.shutdown()
            raise RuntimeError(
                f"{self.backend.process_name} did not accept '{tool_name}' within {self.request_timeout:g}s; request timed out."
            )
        request_id: int | None = None
        try:
            if not self.proc or self.proc.poll() is not None:
                raise RuntimeError(f"{self.backend.process_name} process is not running")
            self.request_id += 1
            request_id = self.request_id
            with self.pending_lock:
                self.pending[request_id] = waiter
            try:
                self._write({"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
                             "params": {"name": tool_name, "arguments": arguments}}, deadline=deadline)
            except TimeoutError as exc:
                with self.pending_lock:
                    self.pending.pop(request_id, None)
                self.shutdown()
                raise RuntimeError(
                    f"{self.backend.process_name} timed out writing '{tool_name}' within {self.request_timeout:g}s; daemon stopped."
                ) from exc
            except (OSError, ValueError, RuntimeError) as exc:
                with self.pending_lock:
                    self.pending.pop(request_id, None)
                raise RuntimeError(f"Failed to send request to {self.backend.process_name}: {exc}") from exc
        finally:
            self.lock.release()

        try:
            return waiter.get(timeout=max(0.0, deadline - time.monotonic()))
        except queue.Empty:
            with self.pending_lock:
                if request_id is not None:
                    self.pending.pop(request_id, None)
            raise RuntimeError(
                f"{self.backend.process_name} did not answer '{tool_name}' within {self.request_timeout:g}s total; request timed out. "
                f"Check {self.backend.consent_hint} and that no other MCP instance holds the connection."
            ) from None

    # ------------------------------------------------------------------ lifecycle
    def _bind_unix_socket(self) -> str:
        if not unix_socket_mode_supported():
            raise RuntimeError(
                f"Cannot serve the Unix socket {self.socket_path} on this platform; "
                f"set {self.backend.env_prefix}_SOCKET to a TCP loopback address such as {self.backend.default_tcp}"
            )
        self.socket_path = Path(self.socket_path)
        # The sidecar flock serializes socket replacement and child startup.
        self._acquire_startup_lock()
        socket_path = prepare_socket_path(Path(self.socket_path))
        self.socket_path = socket_path
        self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_sock.bind(str(socket_path))
        os.chmod(socket_path, 0o600)
        bound = socket_path.lstat()
        self.socket_identity = (bound.st_dev, bound.st_ino)
        self.server_sock.listen(10)
        return str(socket_path)

    def _bind_tcp_socket(self) -> str:
        host, port = parse_tcp_address(self.socket_path)
        if not _is_loopback(host):
            raise RuntimeError(f"Refusing TCP endpoint {host}:{port}: the daemon listens on a loopback address only")
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                # Windows: no other socket may share the port, SO_REUSEADDR or not.
                server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((host, port))
        except OSError as exc:
            server.close()
            raise RuntimeError(f"{self.backend.daemon_label} daemon is already listening on {host}:{port}, or the port is taken: {exc}") from exc
        self.server_sock = server
        # Written before listen(), so a client that can connect can also read the token.
        self.auth_token = secrets.token_urlsafe(32)
        self.token_file = token_path(port)
        write_token(self.token_file, self.auth_token)
        server.listen(10)
        return f"tcp://{host}:{port}"

    def start(self) -> None:
        self._install_signal_handlers()
        try:
            # Bind (the exclusive port, or the flock and socket) before spawning MCP so a
            # competing daemon cannot create a second browser connection.
            if is_tcp_address(self.socket_path):
                endpoint = self._bind_tcp_socket()
            else:
                endpoint = self._bind_unix_socket()

            self._log(f"Starting persistent {self.backend.process_name} process...")
            self.proc = subprocess.Popen(
                _resolve_command(self.command[0]) + list(self.command[1:]), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1, encoding="utf-8", errors="replace",
            )
            self.job = _create_kill_on_close_job(self.proc)
            self.stderr_thread = threading.Thread(target=self._drain_stderr, name="mcp-stderr")
            self.stderr_thread.start()

            initialize_deadline = time.monotonic() + self.initialize_timeout
            init_timer = threading.Timer(self.initialize_timeout, self._expire_initialize)
            init_timer.daemon = True
            init_timer.start()
            try:
                self.request_id += 1
                self._write({
                    "jsonrpc": "2.0", "id": self.request_id, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": f"{self.backend.key}-mcp-daemon", "version": "1.0"}},
                }, deadline=initialize_deadline)
                response = self._read_response(self.request_id)
                if self.initialize_timed_out.is_set():
                    raise TimeoutError(f"Timed out waiting for {self.backend.process_name} initialization")
                if response.get("error") or response.get("id") != self.request_id:
                    raise RuntimeError(f"{self.backend.process_name} initialization failed: {response}")
                self._write({"jsonrpc": "2.0", "method": "notifications/initialized"},
                            deadline=initialize_deadline)
                self.initialize_complete.set()
            except TimeoutError as exc:
                self.initialize_timed_out.set()
                self.shutdown()
                raise RuntimeError(
                    f"{self.backend.process_name} initialization timed out after {self.initialize_timeout:g}s"
                ) from exc
            except RuntimeError as exc:
                if self.initialize_timed_out.is_set():
                    raise RuntimeError(
                        f"{self.backend.process_name} initialization timed out after {self.initialize_timeout:g}s"
                    ) from exc
                if self.stopping.is_set():
                    return
                raise
            except OSError as exc:
                if self.initialize_timed_out.is_set():
                    raise RuntimeError(
                        f"{self.backend.process_name} initialization timed out after {self.initialize_timeout:g}s"
                    ) from exc
                if self.stopping.is_set():
                    return
                raise RuntimeError(f"{self.backend.process_name} initialization failed: {exc}") from exc
            finally:
                init_timer.cancel()

            self.reader_thread = threading.Thread(target=self._dispatch_responses, name="mcp-stdout")
            self.reader_thread.start()
            self._log(f"Daemon listening on {endpoint}")
            # A short accept timeout lets the main thread run signal handlers: on Windows a
            # blocking accept() is not interrupted by Ctrl-C or Ctrl-Break.
            try:
                self.server_sock.settimeout(ACCEPT_POLL_SECONDS)
            except OSError:
                pass  # closed by shutdown() (a signal) just now: accept() below fails and ends the loop
            while not self.stopping.is_set():
                try:
                    connection, _ = self.server_sock.accept()
                except TimeoutError:
                    continue
                except OSError:
                    break  # socket closed by shutdown()
                connection.settimeout(None)
                threading.Thread(target=self.handle_client, args=(connection,), daemon=True).start()
        finally:
            self.close()

    def _expire_initialize(self) -> None:
        if not self.initialize_complete.is_set():
            self.initialize_timed_out.set()
            self._log(f"{self.backend.process_name} initialization timed out after {self.initialize_timeout:g}s")
            self.shutdown()

    def _install_signal_handlers(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            return

        def _stop(signum, _frame):
            self._log(f"Received signal {signum}; shutting down")
            self.shutdown()

        # SIGBREAK is Ctrl-Break, the console event a Windows supervisor can send a process group.
        for name in ("SIGTERM", "SIGINT", "SIGHUP", "SIGBREAK"):
            signum = getattr(signal, name, None)
            if signum is not None:
                signal.signal(signum, _stop)

    def _stop_child(self, process: subprocess.Popen) -> None:
        """Ask the MCP child to end; on Windows end its whole tree (npm's cmd.exe wrapper
        would otherwise leave node.exe running and holding the pipes open)."""
        if os.name == "nt":
            if self.job is not None:
                _terminate_job(self.job)
            else:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
        try:
            process.terminate()
        except OSError:
            pass

    def shutdown(self) -> None:
        """Stop accepting requests and terminate MCP to unblock startup or pipe I/O."""
        self.stopping.set()
        server = self.server_sock
        if server is not None:
            # shutdown() wakes a thread blocked in accept(); close() alone does not on Linux
            for action in (lambda: server.shutdown(socket.SHUT_RDWR), server.close):
                try:
                    action()
                except OSError:
                    pass
        process = self.proc
        if process is not None and process.poll() is None:
            self._stop_child(process)

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
                if not isinstance(request, dict):
                    raise ValueError("request must be a JSON object")
                if self.auth_token is not None and not hmac.compare_digest(
                    str(request.get("token", "")).encode("utf-8"), self.auth_token.encode("utf-8")
                ):
                    raise PermissionError("missing or invalid daemon token")
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
        if process:
            if process.poll() is None:
                self._stop_child(process)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for thread in (self.reader_thread, self.stderr_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=2)
        if process:
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream:
                    stream.close()
        self.proc = None
        if self.job is not None:
            _close_job(self.job)
            self.job = None
        if self.token_file is not None:
            # Remove the token only while it is still ours (a later daemon may own the port by now).
            if read_token(self.token_file) == self.auth_token:
                try:
                    self.token_file.unlink()
                except OSError:
                    pass
            self.token_file = None
        if self.socket_identity is not None:
            socket_path = Path(self.socket_path)
            try:
                info = socket_path.lstat()
                identity = (info.st_dev, info.st_ino)
                if (
                    identity == self.socket_identity
                    and _owned_by_us(info)
                    and stat.S_ISSOCK(info.st_mode)
                ):
                    socket_path.unlink()
            except FileNotFoundError:
                pass
        self.socket_identity = None
        if self.lock_fd is not None:
            try:
                os.close(self.lock_fd)
            except OSError:
                pass
            self.lock_fd = None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Persistent DevTools MCP daemon for one browser.")
    parser.add_argument("--browser", choices=sorted(BACKENDS), default=FIREFOX.key,
                        help="browser backend (default: firefox)")
    args = parser.parse_args(argv)
    backend = BACKENDS[args.browser]
    try:
        BrowserMcpDaemon(backend).start()
    except RuntimeError as exc:
        print(f"{backend.key}-mcp-daemon: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
