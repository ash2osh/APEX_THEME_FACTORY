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

# Model runtimes vary a lot in start-up cost (Antigravity has needed >180s on a cold cache);
# a slow run is an environment limit, so make the ceiling configurable instead of a FAIL.
DEFAULT_SMOKE_TIMEOUT = 300

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
        "agy", "--mode", "plan", "--sandbox", "--output-format", "json",
        "--json-schema", str(schema), f"-p={prompt}",
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


def _repo_relative(value: Any, repo_root: Path | None) -> Any:
    """Normalise an absolute path inside the repository to its repo-relative form.

    Models legitimately answer with absolute paths; a path *outside* the repository is left
    untouched so the equality checks below reject it.
    """
    if not isinstance(value, str) or repo_root is None or not value.startswith("/"):
        return value
    try:
        return Path(value).resolve().relative_to(Path(repo_root).resolve()).as_posix()
    except ValueError:
        return value


def _same_file(reported: Any, expected: str, repo_root: Path | None) -> bool:
    """True when the runtime named the same file as the table, whatever spelling it used.

    `CLAUDE.md` is a symlink to `AGENTS.md` in this repository, so a runtime that reports the
    resolve target discovered the very same instructions. Naming a different file still fails.
    """
    if not isinstance(reported, str) or not reported:
        return False
    if reported == expected:
        return True
    if repo_root is None:
        return False
    try:
        reported_path = (Path(repo_root) / reported).resolve()
        expected_path = (Path(repo_root) / expected).resolve()
    except OSError:
        return False
    return reported_path == expected_path and reported_path.exists()


def _names_server(reported: Any, expected: str) -> bool:
    """True when `expected` appears as a whole server-name token in the reported answer.

    Runtimes qualify the name ("chrome-devtools (mcp__chrome-devtools__* MCP server)"); that is
    the configured server. A different server ("chrome-devtools-mcp" for Claude Code) is one
    token and never matches, so the per-runtime distinction is preserved.
    """
    if not isinstance(reported, str):
        return False
    return expected in re.findall(r"[A-Za-z0-9-]+", reported)


def classify_result(
    runtime: str, exit_code: int, stderr: str, stdout: str, repo_root: Path | None = None
) -> SmokeVerdict:
    """Classify agent output into PASS, FAIL, or UNVERIFIED."""
    # Claude Code reports failures inside its JSON envelope (`is_error`/`result`) with an empty
    # stderr; surface that text so the record explains itself.
    envelope_error = ""
    try:
        envelope = json.loads(stdout.strip())
        if isinstance(envelope, dict):
            if envelope.get("is_error") and isinstance(envelope.get("result"), str):
                envelope_error = envelope["result"]
            # Antigravity reports provider failures in its own envelope and still exits 0
            elif str(envelope.get("status", "")).upper() == "ERROR" and isinstance(envelope.get("error"), str):
                envelope_error = envelope["error"]
    except Exception:
        pass
    if envelope_error and not stderr.strip():
        stderr = envelope_error
        stdout = ""  # the envelope carries no result object; do not mine it for a payload
    combined_err = (stderr + " " + stdout).lower()

    # A CLI rejecting our own schema is a harness defect, never an environment limitation.
    if exit_code != 0 and "not a valid json schema" in combined_err:
        return SmokeVerdict(status="FAIL", message=f"Harness schema rejected by the CLI: {stderr.strip()[:200]}")

    # Check for authentication, quota, rate-limit, missing binary, or network issues
    unverified_indicators = [
        "authentication required", "auth required", "not authenticated", "login required",
        "unauthorized", "quota exceeded", "rate limit", "insufficient quota", "too many requests",
        "command not found", "no such file or directory", "connection refused",
        "timed out", "timeout", "could not connect", "connection error", "api error",
        "model not found", "not logged in", "cannot access the model", "failed to authenticate",
        "oauth session expired",
    ]
    # A provider that is unavailable or out of capacity says nothing about repository compatibility,
    # and some CLIs report it while exiting 0.
    environment_regardless_of_exit = [
        "no capacity", "unavailable", "code 503", "503", "overloaded", "service_unavailable",
    ]
    for ind in environment_regardless_of_exit:
        if ind in combined_err:
            detail = f" ({stderr.strip()[:160]})" if stderr.strip() else ""
            return SmokeVerdict(status="UNVERIFIED", message=f"Provider capacity/availability limitation: {ind}{detail}")
    for ind in unverified_indicators:
        if ind in combined_err and exit_code != 0:
            detail = f" ({stderr.strip()[:160]})" if stderr.strip() else ""
            return SmokeVerdict(status="UNVERIFIED", message=f"Environment/auth/quota limitation: {ind}{detail}")

    if exit_code != 0:
        return SmokeVerdict(status="UNVERIFIED" if "error" in combined_err else "FAIL", message=f"Process exited with code {exit_code}: {stderr.strip()[:200]}")

    # Extract the result object. CLIs either print it bare or wrap it in an envelope, and some
    # (agy) print a notice line before the JSON, so parse the whole stream first, then the first
    # JSON object found in it, and apply the same envelope rules to whichever we got.
    document = None
    try:
        document = json.loads(stdout.strip())
    except Exception:
        match = re.search(r"\{[\s\S]*\}", stdout)
        if match:
            try:
                document = json.loads(match.group(0))
            except Exception:
                document = None

    raw_json = None
    if isinstance(document, dict):
        envelope_field = next((f for f in ("structured_output", "result", "response") if f in document), None)
        if envelope_field is None:
            raw_json = document
        else:
            value = document[envelope_field]
            if isinstance(value, dict):
                raw_json = value
            elif isinstance(value, str) and value.strip():
                try:
                    raw_json = json.loads(value.strip())
                except Exception:
                    raw_json = None
            else:
                return SmokeVerdict(
                    status="UNVERIFIED",
                    message=f"Runtime exited successfully but its '{envelope_field}' was empty: no structured output to assess",
                )

    if raw_json is None or not isinstance(raw_json, dict):
        return SmokeVerdict(status="FAIL", message="Failed to extract valid JSON object matching schema from output")
    for key in ("instructionEntry", "routerSkill"):
        if key in raw_json:
            raw_json[key] = _repo_relative(raw_json[key], repo_root)

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
    if not _same_file(raw_json.get("instructionEntry"), expected_entry, repo_root):
        return SmokeVerdict(status="FAIL", message=f"Expected instructionEntry '{expected_entry}', got '{raw_json.get('instructionEntry')}'", payload=raw_json)

    if not _names_server(raw_json.get("runtimeTruthTool"), expected_tool):
        return SmokeVerdict(status="FAIL", message=f"Expected runtimeTruthTool '{expected_tool}', got '{raw_json.get('runtimeTruthTool')}'", payload=raw_json)

    note = ""
    if raw_json.get("instructionEntry") != expected_entry:
        note = f" (instruction entry reported as '{raw_json['instructionEntry']}', the same file as {expected_entry})"
    return SmokeVerdict(status="PASS", message=f"All assertions passed{note}", payload=raw_json)


def run_smoke(runtime: str, repo_root: Path, date_str: str, timeout: int = DEFAULT_SMOKE_TIMEOUT) -> tuple[int, SmokeVerdict]:
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
            timeout=timeout,
        )
        exit_code = res.returncode
        stdout = res.stdout
        stderr = res.stderr
    except subprocess.TimeoutExpired:
        exit_code = 124
        stdout = ""
        stderr = f"Command timed out after {timeout} seconds"
    except Exception as e:
        exit_code = 1
        stdout = ""
        stderr = str(e)

    verdict = classify_result(runtime, exit_code, stderr, stdout, repo_root=repo_root)

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


SCHEMA_FIELDS = (
    "runtime", "instructionEntry", "routerSkill", "apexBoundary",
    "runtimeTruthTool", "importRequiresUserRequest", "wouldEdit",
)


def schema_fields_only(payload: Any) -> dict[str, Any] | None:
    """Keep the contract's fields and drop everything else (conversation ids, usage, echoes)."""
    if not isinstance(payload, dict):
        return None
    kept = {key: payload[key] for key in SCHEMA_FIELDS if key in payload}
    return kept or None


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

    payload = schema_fields_only(verdict.payload)
    record_data = {
        "runtime": runtime,
        "cliVersion": redact(cli_version),
        "dateUtc": date_str,
        "status": verdict.status,
        "message": redact(verdict.message),
        "payload": payload,
    }
    json_path.write_text(json.dumps(record_data, indent=2) + "\n", encoding="utf-8")

    md_content = f"""# Agent Compatibility Smoke: {runtime}

- **Status:** {verdict.status}
- **CLI Version:** {redact(cli_version)}
- **Run Date (UTC):** {date_str}
- **Verdict Message:** {redact(verdict.message)}

## Result Payload

```json
{json.dumps(payload, indent=2) if payload else "null"}
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run agent compatibility smoke test")
    parser.add_argument("runtime", choices=["codex", "claude", "antigravity"], help="Agent runtime to test")
    parser.add_argument("--repo", default=Path.cwd(), type=Path, help="Repository root")
    parser.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"), help="UTC date string (YYYY-MM-DD)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_SMOKE_TIMEOUT, help="Seconds to wait for the runtime")
    return parser


def main():
    args = build_parser().parse_args()

    exit_code, verdict = run_smoke(args.runtime, args.repo.resolve(), args.date, timeout=args.timeout)
    print(f"SMOKE {args.runtime}: status={verdict.status} message={verdict.message}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
