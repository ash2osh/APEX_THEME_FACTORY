# Cross-Platform Chrome MCP Daemon (Linux, macOS, Windows) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable `tools/chrome_mcp_daemon.py` and `tools/chrome_devtools_client.py` to run seamlessly across Linux, macOS, and Windows while preserving existing UNIX domain socket security and guarantees on POSIX.

**Architecture:** Abstract socket/endpoint addressing to support both UNIX domain sockets (`AF_UNIX`) and TCP loopback (`127.0.0.1:<port>`), guard POSIX-only APIs (`os.getuid()`, `stat.S_ISSOCK`, `chmod 0o700`, `start_new_session`) with cross-platform fallbacks, and resolve executable invocations properly on Windows (including `.cmd`/`.bat` and Python scripts).

**Tech Stack:** Python 3 (standard library: `socket`, `subprocess`, `shutil`, `signal`, `stat`, `tempfile`, `pathlib`), Chrome DevTools MCP.

**Spec:** `docs/CHROME_DEVTOOLS_MCP.md`, `AGENTS.md`.

## Global Constraints

- Target APEX 26.1.x, Universal Theme 42, theme style Iris light.
- Offline tests (`tests/run-offline.sh`) must pass with `OFFLINE status=PASS`.
- Never break existing Unix socket paths, permissions, or security guarantees on Linux and macOS.
- No third-party dependencies; use Python standard library only.

## Review Focus

1. **Windows missing `os.getuid()`**: Invoking `default_socket_path()`, `prepare_socket_path()`, or `close()` on Windows must not raise `AttributeError`.
2. **Windows subprocess execution**: Global npm binaries on Windows are `.cmd` files (`chrome-devtools-mcp.cmd`); spawning must not raise `FileNotFoundError` or `WinError 193`.
3. **Windows background process creation**: `start_new_session=True` in `ensure_daemon_running` raises `ValueError` on Windows; must use `creationflags` on Windows.
4. **macOS path compatibility**: macOS `/tmp` symlink and missing `XDG_RUNTIME_DIR` must resolve safely without triggering false symlink-rejection errors.
5. **TCP address support**: Support `THEME_FACTORY_CHROME_MCP_SOCKET` as `host:port` or `tcp://host:port` across all platforms for environments where UNIX domain sockets are unavailable or inconvenient.

---

### Task 1: Cross-Platform Addressing and Platform Helpers

**Files:**
- Modify: `tools/chrome_mcp_daemon.py`
- Modify: `tests/test_chrome_mcp_daemon.py`

- [ ] Add platform helpers for address parsing (`is_tcp_address`, `parse_tcp_address`) and safe file ownership checks (`_is_safe_file_owner`).
- [ ] Update `default_socket_path()` to provide a safe fallback for Windows (`%TEMP%/apex-theme-factory-<user>/chrome-mcp/chrome-mcp.sock`) when `XDG_RUNTIME_DIR` and `os.getuid` are absent.
- [ ] Add unit tests in `tests/test_chrome_mcp_daemon.py` verifying TCP address detection, Windows default socket path fallback, and ownership checking without `os.getuid`.
- [ ] Run `python3 -m unittest tests/test_chrome_mcp_daemon.py` and verify all tests pass.

---

### Task 2: Executable Resolution and Process Spawning for Windows, macOS, and Linux

**Files:**
- Modify: `tools/chrome_mcp_daemon.py`
- Modify: `tools/chrome_devtools_client.py`
- Modify: `tests/test_chrome_mcp_daemon.py`

- [ ] Implement `_resolve_command(executable)` in `tools/chrome_mcp_daemon.py` using `shutil.which` to resolve `.cmd`/`.bat` wrappers on Windows and `.py` scripts via `sys.executable`.
- [ ] Update `ensure_daemon_running` in `tools/chrome_devtools_client.py` to use `creationflags` (`CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`) on Windows instead of `start_new_session=True`.
- [ ] Add unit tests in `tests/test_chrome_mcp_daemon.py` for command resolution across `.cmd`, `.py`, and standard binary paths.
- [ ] Run `python3 -m unittest tests/test_chrome_mcp_daemon.py` and verify all tests pass.

---

### Task 3: Dual AF_UNIX and TCP Socket IPC Handling

**Files:**
- Modify: `tools/chrome_mcp_daemon.py`
- Modify: `tools/chrome_devtools_client.py`
- Modify: `tests/test_chrome_mcp_daemon.py`

- [ ] Update `prepare_socket_path` to handle Windows error codes (WinError 10061 connection refused) and safe `chmod`/permissions.
- [ ] Update `ChromeMcpDaemon` and `ChromeDevToolsClient` to connect and communicate over either `AF_UNIX` or `AF_INET` (TCP) depending on the address format.
- [ ] Update signal handler installation in `ChromeMcpDaemon` to handle Windows-supported signals (`SIGBREAK`, `SIGTERM`, `SIGINT`).
- [ ] Add unit tests verifying TCP loopback daemon communication alongside AF_UNIX.
- [ ] Run `python3 -m unittest tests/test_chrome_mcp_daemon.py` and verify all tests pass.

---

### Task 4: Documentation and Offline Suite Verification

**Files:**
- Modify: `docs/CHROME_DEVTOOLS_MCP.md`
- Test: `tests/run-offline.sh`

- [ ] Update `docs/CHROME_DEVTOOLS_MCP.md` with instructions and notes for Windows, macOS, and Linux (including `THEME_FACTORY_CHROME_MCP_SOCKET` TCP syntax and Windows npm execution notes).
- [ ] Run full test suite `./tests/run-offline.sh` to ensure `OFFLINE status=PASS`.
