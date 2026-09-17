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
