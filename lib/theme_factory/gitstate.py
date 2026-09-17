"""Git identity helpers shared by packaging and release verification.

Release evidence is captured against a commit and then committed itself. Those evidence-only
commits move HEAD without touching the source under test, so package banners and evidence
binding use the last commit that changed anything *outside* the evidence root.
"""

from pathlib import Path
import re
import subprocess
import zipfile
from typing import Optional, Union

EVIDENCE_ROOT = ".agents/evaluations/runtime"
# Paths that never influence a package or the installer: evidence artifacts and Markdown docs.
NON_SOURCE_PATHSPECS = (".", f":(exclude){EVIDENCE_ROOT}", ":(exclude,glob)**/*.md")

# Markdown that IS source for Layer E: the agent-readiness smokes measure what a runtime does
# after reading these files, so an edit here invalidates Layer E's binding even though it is
# Markdown. Deliberately separate from NON_SOURCE_PATHSPECS rather than folded into it (plan
# Task 3) - Layers C and D depend on code and package bytes, not on what an agent reads, so
# coupling them to instruction edits would force a live re-capture for a skill wording change.
# CLAUDE.md is a symlink to AGENTS.md (`git diff` follows symlink content, not just the link
# target), so watching AGENTS.md alone would already catch a content edit; it is listed anyway
# in case the symlink itself is ever repointed or replaced with a real file.
INSTRUCTION_PATHSPECS = ("AGENTS.md", "CLAUDE.md", ".agents/rules", ".agents/skills")


def last_source_commit(cwd: Union[str, Path, None] = None) -> Optional[str]:
    """SHA of the most recent commit touching source (not evidence, not Markdown), or None."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", *NON_SOURCE_PATHSPECS],
            cwd=cwd, capture_output=True, text=True, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = result.stdout.strip()
    return commit if result.returncode == 0 and len(commit) == 40 else None


def source_equivalent(commit_a: str, commit_b: str, cwd: Union[str, Path, None] = None) -> bool:
    """True when the two commits differ only in evidence or Markdown (or are identical)."""
    if commit_a == commit_b:
        return True
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", commit_a, commit_b, "--", *NON_SOURCE_PATHSPECS],
            cwd=cwd, capture_output=True, text=True, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def last_instruction_commit(cwd: Union[str, Path, None] = None) -> Optional[str]:
    """SHA of the most recent commit touching instruction Markdown Layer E depends on, or None."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", *INSTRUCTION_PATHSPECS],
            cwd=cwd, capture_output=True, text=True, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = result.stdout.strip()
    return commit if result.returncode == 0 and len(commit) == 40 else None


def instruction_equivalent(commit_a: str, commit_b: str, cwd: Union[str, Path, None] = None) -> bool:
    """True when the two commits agree on every instruction file Layer E's smokes read."""
    if commit_a == commit_b:
        return True
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", commit_a, commit_b, "--", *INSTRUCTION_PATHSPECS],
            cwd=cwd, capture_output=True, text=True, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


BANNER_RE = re.compile(r"^\s*\*\s*Source commit:\s*(\S+)\s*$", re.MULTILINE)


def package_source_commit(package: Union[str, Path]) -> Optional[str]:
    """The `Source commit:` stamp inside a built package's theme.css, verbatim.

    Returned as written, `-dirty` suffix included, so a caller can refuse it rather
    than silently normalising a package that was built from an uncommitted tree.
    """
    package = Path(package)
    try:
        if package.is_dir():
            css = (package / "theme.css").read_text(encoding="utf-8")
        else:
            with zipfile.ZipFile(package) as archive:
                name = next((n for n in archive.namelist() if n.endswith("theme.css")), None)
                if name is None:
                    return None
                css = archive.read(name).decode("utf-8")
    except (OSError, KeyError, StopIteration, zipfile.BadZipFile, UnicodeDecodeError):
        return None
    match = BANNER_RE.search(css)
    return match.group(1) if match else None


def package_matches_source(package: Union[str, Path], source_commit: Optional[str]) -> bool:
    """True when the package was built from exactly this source commit, cleanly.

    Evidence captured against a package that does not satisfy this is bound to bytes the
    current source does not produce, and `release-check.sh` rejects it *after* the whole
    matrix has run. Check it before capturing, not after.
    """
    stamped = package_source_commit(package)
    return bool(stamped) and bool(source_commit) and stamped == source_commit
