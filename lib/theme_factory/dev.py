"""Explicit, failure-oriented orchestration for the Theme Workshop candidate lane."""

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import time
from typing import Callable, Sequence

from lib.theme_factory.checks import CheckReport, run_theme_checks
from lib.theme_factory.errors import PackageError


MAX_FAILURE_OUTPUT = 2000
THEME_LAB_URL = "http://localhost:8181/ords/r/demo/ut/theme-lab"


@dataclass(frozen=True)
class DevOptions:
    repo_root: Path
    theme_name: str
    sync: bool = False
    validate: bool = False
    import_app: bool = False
    apply: bool = False
    open_browser: bool = False


@dataclass(frozen=True)
class DevStep:
    name: str
    command: tuple[str, ...]
    exit_code: int
    duration_ms: int
    output: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "command": list(self.command), "exitCode": self.exit_code,
                "durationMs": self.duration_ms, "output": self.output}


@dataclass(frozen=True)
class DevReport:
    status: str
    theme: str
    steps: tuple[DevStep, ...]

    def to_dict(self) -> dict[str, object]:
        return {"status": self.status, "theme": self.theme,
                "steps": [step.to_dict() for step in self.steps]}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    def to_human(self) -> str:
        lines = [f"THEME_DEV status={self.status} theme={self.theme} steps={len(self.steps)}"]
        for step in self.steps:
            lines.append(f"{step.name}: {'PASS' if step.exit_code == 0 else 'ERROR'} ({step.duration_ms} ms)")
            if step.output:
                lines.append(step.output)
        return "\n".join(lines)


def _default_command_runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(command), cwd=cwd, text=True, capture_output=True, check=False)


def _default_browser_opener(url: str) -> object:
    from tools.chrome_devtools_client import ChromeDevToolsClient
    return ChromeDevToolsClient().call_tool("new_page", {"url": url, "background": True})


def _failure_output(result: subprocess.CompletedProcess[str]) -> str:
    if result.returncode == 0:
        return ""
    combined = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part and part.strip())
    return combined if len(combined) <= MAX_FAILURE_OUTPUT else combined[: MAX_FAILURE_OUTPUT - 16] + "\n… [truncated]"


def _run_command(name: str, command: Sequence[str], repo_root: Path,
                 runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]) -> DevStep:
    started = time.perf_counter()
    result = runner(command, repo_root)
    return DevStep(name, tuple(str(part) for part in command), result.returncode,
                   round((time.perf_counter() - started) * 1000), _failure_output(result))


def run_dev(
    options: DevOptions,
    *,
    check_runner: Callable[[Path, str], CheckReport] = run_theme_checks,
    command_runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] = _default_command_runner,
    browser_opener: Callable[[str], object] = _default_browser_opener,
) -> DevReport:
    """Run requested candidate gates in order, stopping before downstream mutation on failure."""

    if options.import_app and not options.apply:
        raise PackageError("dev --import requires --apply")
    if options.apply and not options.import_app:
        raise PackageError("dev --apply requires --import")

    repo_root = Path(options.repo_root).resolve()
    steps: list[DevStep] = []
    started = time.perf_counter()
    check = check_runner(repo_root, options.theme_name)
    steps.append(DevStep("check", ("theme", "check", options.theme_name),
                         0 if check.status == "PASS" else 2,
                         round((time.perf_counter() - started) * 1000),
                         "" if check.status == "PASS" else check.to_human()))
    if check.status != "PASS":
        return DevReport("ERROR", options.theme_name, tuple(steps))

    commands: list[tuple[str, tuple[str, ...]]] = []
    if options.sync:
        commands.append(("sync", (str(repo_root / "scripts/sync-static.sh"),)))
    if options.validate:
        commands.append(("validate", (str(repo_root / "scripts/apex-validate.sh"),)))
    if options.import_app:
        commands.append(("import", (str(repo_root / "scripts/apex-import.sh"), "--yes")))

    for name, command in commands:
        step = _run_command(name, command, repo_root, command_runner)
        steps.append(step)
        if step.exit_code != 0:
            return DevReport("ERROR", options.theme_name, tuple(steps))

    if options.open_browser:
        started = time.perf_counter()
        command = ("chrome-devtools", "new_page", THEME_LAB_URL)
        try:
            browser_opener(THEME_LAB_URL)
        except Exception as exc:
            steps.append(DevStep("open", command, 1, round((time.perf_counter() - started) * 1000),
                                 str(exc)[:MAX_FAILURE_OUTPUT]))
            return DevReport("ERROR", options.theme_name, tuple(steps))
        steps.append(DevStep("open", command, 0, round((time.perf_counter() - started) * 1000)))

    return DevReport("PASS", options.theme_name, tuple(steps))
