#!/usr/bin/env python3
"""Fake chrome-devtools-mcp: answers initialize, then behaves per FAKE_MCP_MODE.

  hang    - never answers tools/call (Chrome consent prompt pending / connection contention)
  echo    - answers every tools/call with its arguments
"""
import json
import os
import sys

mode = os.environ.get("FAKE_MCP_MODE", "hang")
print("fake mcp: starting", file=sys.stderr, flush=True)
for line in sys.stdin:
    message = json.loads(line)
    if message.get("method") == "initialize":
        print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": {"capabilities": {}}}), flush=True)
    elif message.get("method") == "tools/call":
        if mode == "echo":
            print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": {"echo": message["params"]}}), flush=True)
        # hang: say nothing, keep reading
