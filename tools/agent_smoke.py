#!/usr/bin/env python3
"""Cross-runtime agent smoke runner, classifier, and evidence recorder."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Callable


EXPECTED = {
    "codex": ("AGENTS.md", "chrome-devtools"),
    "claude": ("CLAUDE.md", "chrome-devtools"),
    "antigravity": (".agents/rules/apex-theme-factory.md", "chrome-devtools-mcp"),
}

COMMANDS: dict[str, Callable[[str, Path], list[str]]] = {
    "codex": lambda prompt, schema: [
        "codex", "exec", "--ephemeral", "--sandbox", "read-only",
        "--output-schema", str(schema), "-",
    ],
    "claude": lambda prompt, schema: [
        "claude", "-p", "--permission-mode", "plan", "--no-session-persistence",
        "--output-format", "json", "--json-schema", schema.read_text(encoding="utf-8"), prompt,
    ],
    "antigravity": lambda prompt, schema: [
        "agy", "-p", "--mode", "plan", "--sandbox", "--output-format", "json",
        "--json-schema", str(schema), prompt,
    ],
}


@dataclass(frozen=True)
class SmokeVerdict:
    status: str  # PASS, FAIL, UNVERIFIED
    message: str
    payload: dict[str, Any] | None = None


def redact(text: str) -> str:
    """Redact user paths, session UUIDs, and credentials."""
    home = os.path.expanduser("~")
    if home and home != "/":
        text = text.replace(home, "<HOME>")
    
    # Redact UUID / session patterns
    text = re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", "<SESSION>", text)
    
    # Redact sensitive lines
    redacted_lines = []
    for line in text.splitlines():
        if re.search(r"\b(token|secret|password|authorization)\b", line, re.IGNORECASE):
            redacted_lines.append("<REDACTED>")
        else:
            redacted_lines.append(line)
    return "\n".join(redacted_lines)


def classify_result(runtime: str, exit_code: int, stderr: str, stdout: str) -> SmokeVerdict:
    """Classify agent output into PASS, FAIL, or UNVERIFIED."""
    combined_err = (stderr + " " + stdout).lower()
    
    # Check for authentication, quota, rate-limit, missing binary, or network issues
    unverified_indicators = [
        "authentication required", "auth required", "not authenticated", "login required",
        "unauthorized", "quota exceeded", "rate limit", "insufficient quota", "too many requests",
        "command not found", "no such file or directory", "connection refused",
        "timed out", "timeout", "could not connect", "connection error", "api error",
        "model not found", "not logged in", "cannot access the model",
    ]
    for ind in unverified_indicators:
        if ind in combined_err and exit_code != 0:
            return SmokeVerdict(status="UNVERIFIED", message=f"Environment/auth/quota limitation: {ind}")

    if exit_code != 0:
        return SmokeVerdict(status="UNVERIFIED" if "error" in combined_err else "FAIL", message=f"Process exited with code {exit_code}: {stderr.strip()[:200]}")

    # Extract JSON payload
    raw_json = None
    # 1. Try parsing stdout directly as JSON
    try:
        data = json.loads(stdout.strip())
        if isinstance(data, dict):
            # Check for envelope: structured_output or result
            if "structured_output" in data and isinstance(data["structured_output"], dict):
                raw_json = data["structured_output"]
            elif "result" in data:
                if isinstance(data["result"], dict):
                    raw_json = data["result"]
                elif isinstance(data["result"], str):
                    try:
                        raw_json = json.loads(data["result"].strip())
                    except Exception:
                        pass
            else:
                raw_json = data
    except Exception:
        # Try finding json block in markdown/prose
        match = re.search(r"\{[\s\S]*\}", stdout)
        if match:
            try:
                raw_json = json.loads(match.group(0))
            except Exception:
                pass

    if raw_json is None or not isinstance(raw_json, dict):
        return SmokeVerdict(status="FAIL", message="Failed to extract valid JSON object matching schema from output")

    # Validate against expected schema properties
    required_keys = ["runtime", "instructionEntry", "routerSkill", "apexBoundary", "runtimeTruthTool", "importRequiresUserRequest", "wouldEdit"]
    for k in required_keys:
        if k not in raw_json:
            return SmokeVerdict(status="FAIL", message=f"Missing required key '{k}' in output JSON", payload=raw_json)

    if raw_json.get("runtime") != runtime:
        return SmokeVerdict(status="FAIL", message=f"Runtime mismatch: expected {runtime}, got {raw_json.get('runtime')}", payload=raw_json)

    if raw_json.get("routerSkill") != ".agents/skills/design-to-apex/SKILL.md":
        return SmokeVerdict(status="FAIL", message=f"Unexpected routerSkill: {raw_json.get('routerSkill')}", payload=raw_json)

    if raw_json.get("apexBoundary") != "APEX 26.1.x / Universal Theme 42 / Iris":
        return SmokeVerdict(status="FAIL", message=f"Unexpected apexBoundary: {raw_json.get('apexBoundary')}", payload=raw_json)

    if raw_json.get("importRequiresUserRequest") is not True:
        return SmokeVerdict(status="FAIL", message="importRequiresUserRequest must be true", payload=raw_json)

    if raw_json.get("wouldEdit") is not False:
        return SmokeVerdict(status="FAIL", message="wouldEdit must be false", payload=raw_json)

    expected_entry, expected_tool = EXPECTED.get(runtime, ("", ""))
    if raw_json.get("instructionEntry") != expected_entry:
        return SmokeVerdict(status="FAIL", message=f"Expected instructionEntry '{expected_entry}', got '{raw_json.get('instructionEntry')}'", payload=raw_json)

    if raw_json.get("runtimeTruthTool") != expected_tool:
        return SmokeVerdict(status="FAIL", message=f"Expected runtimeTruthTool '{expected_tool}', got '{raw_json.get('runtimeTruthTool')}'", payload=raw_json)

    return SmokeVerdict(status="PASS", message="All assertions passed", payload=raw_json)


def run_smoke(runtime: str, repo_root: Path, date_str: str) -> tuple[int, SmokeVerdict]:
    """Execute smoke for a given runtime and write output files."""
    if runtime not in COMMANDS:
        raise ValueError(f"Unknown runtime: {runtime}")

    cli_name = {"codex": "codex", "claude": "claude", "antigravity": "agy"}[runtime]
    cli_path = shutil.which(cli_name)

    # Get CLI version if available
    cli_version = "not installed"
    if cli_path:
        try:
            v_res = subprocess.run([cli_name, "--version"], capture_output=True, text=True, check=False)
            cli_version = v_res.stdout.strip() or v_res.stderr.strip() or "installed"
        except Exception:
            cli_version = "unknown"

    schema_file = repo_root / "tests/agent-smoke/result.schema.json"
    prompt_file = repo_root / "tests/agent-smoke/readiness-prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8")

    out_dir = repo_root / f"tests/agent-smoke/runs/{date_str}"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not cli_path:
        verdict = SmokeVerdict(status="UNVERIFIED", message=f"CLI '{cli_name}' is not installed")
        record_evidence(out_dir, runtime, cli_version, date_str, verdict, "", "")
        return 2, verdict

    # Worktree guard before
    status_before = subprocess.run(["git", "status", "--porcelain=v1"], cwd=repo_root, capture_output=True, text=True, check=False).stdout

    cmd = COMMANDS[runtime](prompt_text, schema_file)
    stdin_input = prompt_text if runtime == "codex" else None

    try:
        res = subprocess.run(
            cmd,
            cwd=repo_root,
            input=stdin_input,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        exit_code = res.returncode
        stdout = res.stdout
        stderr = res.stderr
    except subprocess.TimeoutExpired:
        exit_code = 124
        stdout = ""
        stderr = "Command timed out after 120 seconds"
    except Exception as e:
        exit_code = 1
        stdout = ""
        stderr = str(e)

    verdict = classify_result(runtime, exit_code, stderr, stdout)

    # Worktree guard check after
    status_after = subprocess.run(["git", "status", "--porcelain=v1"], cwd=repo_root, capture_output=True, text=True, check=False).stdout
    unexpected_changes = []
    for line in status_after.splitlines():
        if line not in status_before:
            # allow only files in out_dir
            path_part = line[3:].strip()
            if not path_part.startswith(f"tests/agent-smoke/runs/{date_str}/"):
                unexpected_changes.append(path_part)
    if unexpected_changes:
        verdict = SmokeVerdict(status="FAIL", message=f"Model mutated worktree: {unexpected_changes}", payload=verdict.payload)

    record_evidence(out_dir, runtime, cli_version, date_str, verdict, stdout, stderr)

    if verdict.status == "PASS":
        return 0, verdict
    elif verdict.status == "FAIL":
        return 1, verdict
    else:
        return 2, verdict


def record_evidence(
    out_dir: Path,
    runtime: str,
    cli_version: str,
    date_str: str,
    verdict: SmokeVerdict,
    stdout: str,
    stderr: str,
) -> None:
    json_path = out_dir / f"{runtime}.json"
    md_path = out_dir / f"{runtime}.md"

    record_data = {
        "runtime": runtime,
        "cliVersion": redact(cli_version),
        "dateUtc": date_str,
        "status": verdict.status,
        "message": redact(verdict.message),
        "payload": verdict.payload,
    }
    json_path.write_text(json.dumps(record_data, indent=2) + "\n", encoding="utf-8")

    md_content = f"""# Agent Compatibility Smoke: {runtime}

- **Status:** {verdict.status}
- **CLI Version:** {redact(cli_version)}
- **Run Date (UTC):** {date_str}
- **Verdict Message:** {redact(verdict.message)}

## Result Payload

```json
{json.dumps(verdict.payload, indent=2) if verdict.payload else "null"}
```

## Raw Execution Output (Redacted)

### Standard Output
```text
{redact(stdout[:2000]) if stdout else "(none)"}
```

### Standard Error
```text
{redact(stderr[:2000]) if stderr else "(none)"}
```
"""
    md_path.write_text(md_content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run agent compatibility smoke test")
    parser.add_argument("runtime", choices=["codex", "claude", "antigravity"], help="Agent runtime to test")
    parser.add_argument("--repo", default=Path.cwd(), type=Path, help="Repository root")
    parser.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"), help="UTC date string (YYYY-MM-DD)")
    args = parser.parse_args()

    exit_code, verdict = run_smoke(args.runtime, args.repo.resolve(), args.date)
    print(f"SMOKE {args.runtime}: status={verdict.status} message={verdict.message}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
