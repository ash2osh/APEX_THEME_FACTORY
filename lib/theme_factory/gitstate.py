"""Git identity helpers shared by packaging and release verification.

Release evidence is captured against a commit and then committed itself. Those evidence-only
commits move HEAD without touching the source under test, so package banners and evidence
binding use the last commit that changed anything *outside* the evidence root.
"""

from pathlib import Path
import subprocess
from typing import Optional, Union

EVIDENCE_ROOT = ".agents/evaluations/runtime"
# Paths that never influence a package or the installer: evidence artifacts and Markdown docs.
NON_SOURCE_PATHSPECS = (".", f":(exclude){EVIDENCE_ROOT}", ":(exclude,glob)**/*.md")


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
