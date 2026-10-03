import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from io import StringIO
from types import SimpleNamespace

from unittest.mock import patch

from tools.chrome_mcp_daemon import (
    ChromeMcpDaemon, prepare_socket_path, is_tcp_address, parse_tcp_address,
    default_socket_path, _resolve_command,
)
from tools.chrome_devtools_client import ChromeDevToolsClient, ensure_daemon_running


class ChromeMcpDaemonTests(unittest.TestCase):
    def test_socket_directory_is_private(self):
        with tempfile.TemporaryDirectory() as temp:
            path = prepare_socket_path(Path(temp) / "service/chrome.sock")
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

    def test_existing_regular_file_is_never_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "service/chrome.sock"
            target.parent.mkdir()
            target.write_text("keep", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                prepare_socket_path(target)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep")

    def test_existing_symlink_is_never_followed_or_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            protected = root / "protected"
            protected.write_text("keep", encoding="utf-8")
            target = root / "service/chrome.sock"
            target.parent.mkdir()
            target.symlink_to(protected)
            with self.assertRaises(RuntimeError):
                prepare_socket_path(target)
            self.assertTrue(target.is_symlink())
            self.assertEqual(protected.read_text(encoding="utf-8"), "keep")

    def test_unknown_tool_is_rejected_without_forwarding(self):
        daemon = ChromeMcpDaemon(socket_path=Path("/tmp/unused-test.sock"))
        server, client = socket.socketpair()
        self.addCleanup(server.close)
        self.addCleanup(client.close)
        client.sendall(b'{"name":"arbitrary_tool","arguments":{}}\n')
        client.shutdown(socket.SHUT_WR)
        daemon.handle_client(server)
        response = json.loads(client.recv(4096).decode("utf-8"))
        self.assertIn("not allowed", response["error"]["message"])

    def test_response_reader_skips_notifications_and_matches_id(self):
        daemon = ChromeMcpDaemon(socket_path=Path("/tmp/unused-test.sock"))
        daemon.proc = SimpleNamespace(stdout=StringIO(
            '{"jsonrpc":"2.0","method":"notifications/message","params":{}}\n'
            '{"jsonrpc":"2.0","id":7,"result":{"ok":true}}\n'
        ))
        response = daemon._read_response(7)
        self.assertEqual(response["result"], {"ok": True})

    def test_live_socket_is_not_unlinked_by_second_daemon(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "service/chrome.sock"
            target.parent.mkdir()
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.addCleanup(listener.close)
            listener.bind(str(target))
            listener.listen(1)
            with self.assertRaises(RuntimeError):
                prepare_socket_path(target)
            self.assertTrue(target.exists())

    def test_client_gives_up_on_a_silent_daemon(self):
        import threading
        from tools.chrome_devtools_client import ChromeDevToolsClient
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "silent.sock"
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.addCleanup(listener.close)
            listener.bind(str(target))
            listener.listen(2)
            accepted = []
            def accept_connections():
                for _ in range(2):
                    connection, _address = listener.accept()
                    accepted.append(connection)

            thread = threading.Thread(target=accept_connections, daemon=True)
            thread.start()
            try:
                client = ChromeDevToolsClient(socket_path=target, response_timeout=0.3)
                with self.assertRaises(RuntimeError) as context:
                    client.call_tool("list_pages")
                self.assertIn("timed out", str(context.exception))
            finally:
                for connection in accepted:
                    connection.close()
                thread.join(timeout=1)

    def test_missing_daemon_fails_loudly_when_autostart_disabled(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(RuntimeError):
                ensure_daemon_running(Path(temp) / "missing.sock", auto_spawn=False)


class ChromeMcpDaemonLifecycleTests(unittest.TestCase):
    FAKE = str(Path(__file__).resolve().parent / "fixtures/mcp/fake_mcp_server.py")

    def call(self, socket_path: Path, name: str, timeout: float = 5.0) -> dict:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(timeout)
            connection.connect(str(socket_path))
            connection.sendall((json.dumps({"name": name, "arguments": {}}) + "\n").encode("utf-8"))
            data = b""
            while b"\n" not in data:
                chunk = connection.recv(65536)
                if not chunk:
                    break
                data += chunk
        return json.loads(data.split(b"\n", 1)[0])

    def wait_for_socket(self, socket_path: Path, seconds: float = 5.0) -> None:
        import time
        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                    probe.settimeout(0.2)
                    probe.connect(str(socket_path))
                return
            except OSError:
                time.sleep(0.05)
        self.fail(f"daemon socket {socket_path} never became ready")

    def test_unanswered_tool_call_times_out_and_releases_the_lock(self):
        import threading
        import time
        with tempfile.TemporaryDirectory() as temp:
            socket_path = Path(temp) / "service/chrome.sock"
            os.environ["FAKE_MCP_MODE"] = "hang"
            daemon = ChromeMcpDaemon(executable=self.FAKE, socket_path=socket_path, request_timeout=0.3)
            thread = threading.Thread(target=daemon.start, daemon=True)
            thread.start()
            try:
                self.wait_for_socket(socket_path)
                started = time.time()
                first = self.call(socket_path, "list_pages")
                second = self.call(socket_path, "list_pages")
                self.assertLess(time.time() - started, 3.0)
                self.assertIn("timed out", first["error"]["message"])
                self.assertIn("timed out", second["error"]["message"])
                self.assertTrue(daemon.proc and daemon.proc.poll() is None, "MCP child must survive a timeout")
            finally:
                daemon.shutdown()
                thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertFalse(socket_path.exists())

    def test_answered_tool_call_is_correlated_by_id(self):
        import threading
        with tempfile.TemporaryDirectory() as temp:
            socket_path = Path(temp) / "service/chrome.sock"
            os.environ["FAKE_MCP_MODE"] = "echo"
            daemon = ChromeMcpDaemon(executable=self.FAKE, socket_path=socket_path, request_timeout=2.0)
            thread = threading.Thread(target=daemon.start, daemon=True)
            thread.start()
            try:
                self.wait_for_socket(socket_path)
                response = self.call(socket_path, "list_pages")
                self.assertEqual(response["result"]["echo"]["name"], "list_pages")
            finally:
                daemon.shutdown()
                thread.join(timeout=5)

    def test_sigterm_exits_cleanly_and_removes_the_socket(self):
        import signal
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as temp:
            socket_path = Path(temp) / "service/chrome.sock"
            env = os.environ.copy()
            env["THEME_FACTORY_CHROME_MCP_SOCKET"] = str(socket_path)
            env["THEME_FACTORY_CHROME_MCP_EXECUTABLE"] = self.FAKE
            env["FAKE_MCP_MODE"] = "hang"
            process = subprocess.Popen(
                [sys.executable, "tools/chrome_mcp_daemon.py"], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            try:
                self.wait_for_socket(socket_path)
                process.send_signal(signal.SIGTERM)
                output, _ = process.communicate(timeout=10)
            finally:
                if process.poll() is None:
                    process.kill()
            self.assertEqual(process.returncode, 0, output)
            self.assertNotIn("Fatal Python error", output)
            self.assertNotIn("Traceback", output)
            self.assertFalse(socket_path.exists())


class ChromeMcpDaemonCrossPlatformTests(unittest.TestCase):
    FAKE = str(Path(__file__).resolve().parent / "fixtures/mcp/fake_mcp_server.py")

    def test_tcp_address_detection_and_parsing(self):
        self.assertTrue(is_tcp_address("127.0.0.1:9223"))
        self.assertEqual(parse_tcp_address("127.0.0.1:9223"), ("127.0.0.1", 9223))

        self.assertTrue(is_tcp_address("tcp://127.0.0.1:9223"))
        self.assertEqual(parse_tcp_address("tcp://127.0.0.1:9223"), ("127.0.0.1", 9223))

        self.assertTrue(is_tcp_address("9223"))
        self.assertEqual(parse_tcp_address("9223"), ("127.0.0.1", 9223))

        self.assertTrue(is_tcp_address("localhost:9000"))
        self.assertEqual(parse_tcp_address("localhost:9000"), ("localhost", 9000))

        # File paths should not be detected as TCP addresses
        self.assertFalse(is_tcp_address(Path("/tmp/chrome.sock")))
        self.assertFalse(is_tcp_address("/tmp/chrome.sock"))
        self.assertFalse(is_tcp_address(r"C:\Users\User\AppData\Local\Temp\chrome.sock"))
        self.assertFalse(is_tcp_address("C:/Users/User/AppData/Local/Temp/chrome.sock"))

    def test_default_socket_path_override(self):
        with patch.dict(os.environ, {"THEME_FACTORY_CHROME_MCP_SOCKET": "127.0.0.1:9223"}):
            self.assertEqual(default_socket_path(), "127.0.0.1:9223")

        with patch.dict(os.environ, {"THEME_FACTORY_CHROME_MCP_SOCKET": "/custom/path.sock"}):
            self.assertEqual(default_socket_path(), Path("/custom/path.sock"))

    def test_default_socket_path_windows_fallback(self):
        env = os.environ.copy()
        env.pop("THEME_FACTORY_CHROME_MCP_SOCKET", None)
        env.pop("XDG_RUNTIME_DIR", None)
        env["USERNAME"] = "testuser"
        with patch.dict(os.environ, env, clear=True):
            with patch("os.getuid", create=True) as mock_getuid:
                del mock_getuid  # ensure hasattr(os, "getuid") is False
                with patch("os.path.exists", return_value=True):
                    # temporarily remove getuid attribute from os module
                    orig_getuid = getattr(os, "getuid", None)
                    try:
                        if hasattr(os, "getuid"):
                            delattr(os, "getuid")
                        path = default_socket_path()
                        self.assertIn("apex-theme-factory-testuser", str(path))
                    finally:
                        if orig_getuid is not None:
                            os.getuid = orig_getuid

    def test_resolve_command(self):
        # Python script
        resolved_py = _resolve_command(self.FAKE)
        self.assertEqual(resolved_py[0], sys.executable)
        self.assertEqual(resolved_py[1], self.FAKE)

        # Windows .cmd script simulation
        with patch("sys.platform", "win32"):
            with patch("shutil.which", return_value=r"C:\Users\test\npm\chrome-devtools-mcp.cmd"):
                resolved_cmd = _resolve_command("chrome-devtools-mcp")
                self.assertEqual(resolved_cmd, ["cmd.exe", "/c", r"C:\Users\test\npm\chrome-devtools-mcp.cmd"])

        # POSIX binary
        with patch("sys.platform", "linux"):
            with patch("shutil.which", return_value="/usr/bin/chrome-devtools-mcp"):
                resolved_bin = _resolve_command("chrome-devtools-mcp")
                self.assertEqual(resolved_bin, ["/usr/bin/chrome-devtools-mcp"])

    def test_prepare_socket_path_without_getuid(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "service/chrome.sock"
            orig_getuid = getattr(os, "getuid", None)
            try:
                if hasattr(os, "getuid"):
                    delattr(os, "getuid")
                path = prepare_socket_path(target)
                self.assertEqual(path, target)
            finally:
                if orig_getuid is not None:
                    os.getuid = orig_getuid

    def test_tcp_loopback_client_daemon_communication(self):
        import threading
        import time

        # Find a free ephemeral port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            free_port = probe.getsockname()[1]

        tcp_addr = f"127.0.0.1:{free_port}"
        os.environ["FAKE_MCP_MODE"] = "echo"
        daemon = ChromeMcpDaemon(executable=self.FAKE, socket_path=tcp_addr, request_timeout=2.0)
        thread = threading.Thread(target=daemon.start, daemon=True)
        thread.start()
        try:
            # Wait for TCP server to listen
            deadline = time.time() + 5.0
            ready = False
            while time.time() < deadline:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
                        conn.settimeout(0.2)
                        conn.connect(("127.0.0.1", free_port))
                        ready = True
                        break
                except OSError:
                    time.sleep(0.05)
            self.assertTrue(ready, "TCP daemon never became ready")

            client = ChromeDevToolsClient(socket_path=tcp_addr, response_timeout=2.0)
            res = client.call_tool("list_pages")
            self.assertEqual(res["echo"]["name"], "list_pages")
        finally:
            daemon.shutdown()
            thread.join(timeout=5)

    def test_ensure_daemon_running_spawns_process_with_windows_flags(self):
        mock_proc = SimpleNamespace(poll=lambda: None)
        with patch("sys.platform", "win32"):
            with patch("tools.chrome_devtools_client._can_connect", side_effect=[False, True]):
                with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
                    path = ensure_daemon_running(Path("/tmp/test.sock"), auto_spawn=True)
                    self.assertEqual(path, Path("/tmp/test.sock"))
                    mock_popen.assert_called_once()
                    _, kwargs = mock_popen.call_args
                    self.assertIn("creationflags", kwargs)
                    self.assertNotIn("start_new_session", kwargs)


if __name__ == "__main__":
    unittest.main()

