"""Classify Git path changes into the smallest safe theme-check selection."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Sequence

from lib.theme_factory.discovery import theme_names
from lib.theme_factory.errors import PackageError


SHARED_PREFIXES = (
    "lib/theme_factory/",
    "theme-templates/",
    "static-files/css/foundation/",
    "installer/",
    "scripts/",
    "tools/",
    "tests/",
    ".github/workflows/",
    "docs/generated/",
)


@dataclass(frozen=True)
class ChangedThemeSelection:
    themes: tuple[str, ...]
    repository_wide: bool
    deleted_themes: tuple[str, ...]
    changed_paths: tuple[str, ...]

    def to_matrix_dict(self) -> dict[str, object]:
        return {
            "include": [{"theme": theme} for theme in self.themes],
            "repositoryWide": self.repository_wide,
            "deletedThemes": list(self.deleted_themes),
        }

    def to_matrix_json(self) -> str:
        return json.dumps(self.to_matrix_dict(), separators=(",", ":"), sort_keys=True)


@dataclass(frozen=True)
class GitChange:
    status: str
    paths: tuple[str, ...]


def _git_changes(repo_root: Path, base: str, head: str) -> tuple[GitChange, ...]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", "-z", f"{base}...{head}"],
            cwd=repo_root, capture_output=True, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise PackageError(f"Unable to inspect Git changes: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise PackageError(f"Unable to inspect Git range {base}...{head}: {detail}")
    try:
        tokens = result.stdout.decode("utf-8").split("\0")
    except UnicodeDecodeError as exc:
        raise PackageError("Git returned a non-UTF-8 path in the changed-theme range") from exc
    if tokens and tokens[-1] == "":
        tokens.pop()
    changes: list[GitChange] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        path_count = 2 if status.startswith(("R", "C")) else 1
        if not status or index + path_count > len(tokens):
            raise PackageError("Git returned a malformed --name-status -z stream")
        paths = tuple(tokens[index:index + path_count])
        index += path_count
        changes.append(GitChange(status, paths))
    return tuple(changes)


def _theme_path(path: str) -> str | None:
    parts = PurePosixPath(path).parts
    if len(parts) >= 3 and parts[0] == "sample-themes":
        return parts[1]
    return None


def _is_shared(path: str) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in SHARED_PREFIXES)


def select_changed_themes(repo_root: Path, base: str, head: str) -> ChangedThemeSelection:
    repo_root = Path(repo_root).resolve()
    current = theme_names(repo_root)
    current_set = set(current)
    changes = _git_changes(repo_root, base, head)
    paths = tuple(path for change in changes for path in change.paths)
    repository_wide = any(_is_shared(path) for path in paths)
    selected: set[str] = set(current if repository_wide else ())
    deleted: set[str] = set()

    for change in changes:
        for position, path in enumerate(change.paths):
            theme = _theme_path(path)
            if theme is None:
                continue
            is_old_rename_path = change.status.startswith(("R", "C")) and position == 0
            is_deleted = change.status.startswith("D") or is_old_rename_path
            if is_deleted and theme not in current_set:
                deleted.add(theme)
                repository_wide = True
            if theme in current_set:
                selected.add(theme)

    if deleted:
        selected.update(current)
    return ChangedThemeSelection(
        tuple(sorted(selected)), repository_wide, tuple(sorted(deleted)), tuple(sorted(set(paths)))
    )


def changed_themes(repo_root: Path, base: str, head: str) -> tuple[str, ...]:
    return select_changed_themes(repo_root, base, head).themes


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select themes affected by a Git range")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args(argv)
    try:
        print(select_changed_themes(args.repo_root, args.base, args.head).to_matrix_json())
    except PackageError as exc:
        parser.exit(exc.exit_code, f"Error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
