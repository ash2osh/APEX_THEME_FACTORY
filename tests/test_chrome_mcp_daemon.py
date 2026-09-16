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

    def test_missing_daemon_fails_loudly_when_autostart_disabled(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(RuntimeError):
                ensure_daemon_running(Path(temp) / "missing.sock", auto_spawn=False)


if __name__ == "__main__":
    unittest.main()
