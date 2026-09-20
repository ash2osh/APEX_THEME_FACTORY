import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from io import StringIO
from types import SimpleNamespace

from tools.chrome_mcp_daemon import ChromeMcpDaemon, prepare_socket_path
from tools.chrome_devtools_client import ensure_daemon_running


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


if __name__ == "__main__":
    unittest.main()
