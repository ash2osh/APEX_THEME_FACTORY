"""Git identity helpers shared by packaging and release verification.

Release evidence is captured against a commit and then committed itself. Those evidence-only
commits move HEAD without touching the source under test, so package banners and evidence
binding use the last commit that changed anything *outside* the evidence root.
"""

from pathlib import Path
import subprocess
from typing import Optional, Union

EVIDENCE_ROOT = ".agents/evaluations/runtime"


def last_source_commit(cwd: Union[str, Path, None] = None) -> Optional[str]:
    """SHA of the most recent commit touching paths outside EVIDENCE_ROOT, or None."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", ".", f":(exclude){EVIDENCE_ROOT}"],
            cwd=cwd, capture_output=True, text=True, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = result.stdout.strip()
    return commit if result.returncode == 0 and len(commit) == 40 else None


def source_equivalent(commit_a: str, commit_b: str, cwd: Union[str, Path, None] = None) -> bool:
    """True when the two commits differ only under EVIDENCE_ROOT (or are identical)."""
    if commit_a == commit_b:
        return True
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", commit_a, commit_b, "--", ".", f":(exclude){EVIDENCE_ROOT}"],
            cwd=cwd, capture_output=True, text=True, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0
