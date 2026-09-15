#!/usr/bin/env python3
"""Persistent daemon for chrome-devtools-mcp to prevent repeated Chrome consent prompts."""

import json
import os
import socket
import subprocess
import sys
import threading

SOCKET_PATH = "/tmp/chrome_mcp.sock"


class ChromeMcpDaemon:
    def __init__(self, executable: str = "chrome-devtools-mcp"):
        self.executable = executable
        self.proc = None
        self.lock = threading.Lock()
        self.request_id = 0

    def start(self):
        print("Starting persistent chrome-devtools-mcp process...")
        self.proc = subprocess.Popen(
            [self.executable, "--auto-connect"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # 1. Initialize MCP
        self.request_id += 1
        init_payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "chrome-mcp-daemon", "version": "1.0"},
            },
        }
        self.proc.stdin.write(json.dumps(init_payload) + "\n")
        self.proc.stdin.flush()
        init_resp = self.proc.stdout.readline()
        print("MCP Initialized:", init_resp.strip())

        # 2. Initialized notification
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.proc.stdin.flush()

        # Clean up existing socket
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(SOCKET_PATH)
        server_sock.listen(10)
        print(f"Daemon listening on {SOCKET_PATH}...")

        while True:
            conn, _ = server_sock.accept()
            threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()

    def handle_client(self, conn: socket.socket):
        with conn:
            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break
            if not data:
                return

            req = json.loads(data.decode("utf-8").strip(), strict=False)
            tool_name = req.get("name")
            tool_args = req.get("arguments", {})

            with self.lock:
                self.request_id += 1
                payload = {
                    "jsonrpc": "2.0",
                    "id": self.request_id,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": tool_args,
                    },
                }
                self.proc.stdin.write(json.dumps(payload) + "\n")
                self.proc.stdin.flush()
                resp_line = self.proc.stdout.readline()

            conn.sendall(resp_line.encode("utf-8"))


if __name__ == "__main__":
    daemon = ChromeMcpDaemon()
    daemon.start()
