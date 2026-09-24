"""Shared adapter segments: CSS that several theme packages carry verbatim.

Themes of one family (for example the dark themes) restate the same Universal Theme / Iris adapter
rules. Those rules live once, as numbered segments, in
``theme-templates/adapters/<family>/<file>.css.tmpl``; each member theme carries the rendered text
between fences in its own ``css/apex/<file>.css``::

    /* @adapter dark/shell#1 prefix=sol - generated from theme-templates/adapters/dark/shell.css.tmpl;
       edit there, then run scripts/theme.sh adapters */      (one line in the file)
    ...rendered segment...
    /* @adapter-end dark/shell#1 */

Everything outside the fences is the theme's own CSS, in its original order, so the cascade is exactly
what a hand-written file would give. The rendered text is committed in every theme, so packages stay
self-contained and packaging, ``sync-static`` and the browser see ordinary CSS.

Placeholders: ``__NAME__`` (theme name) and ``__PREFIX__`` (the theme's private palette prefix, as in
``--__PREFIX__-cyan``).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import difflib
from pathlib import Path
import re
import sys

from lib.theme_factory.errors import PackageError

TEMPLATE_ROOT = Path("theme-templates/adapters")
BEGIN_RE = re.compile(
    r"^/\* @adapter (?P<family>[a-z0-9-]+)/(?P<file>[a-z0-9-]+)#(?P<segment>[0-9]+) "
    r"prefix=(?P<prefix>[a-z0-9]*)(?: .*)? \*/$"
)
END_RE = re.compile(r"^/\* @adapter-end (?P<family>[a-z0-9-]+)/(?P<file>[a-z0-9-]+)#(?P<segment>[0-9]+) \*/$")
SEGMENT_RE = re.compile(r"^/\* @segment (?P<segment>[0-9]+) \*/$")


def begin_line(family: str, file: str, segment: int, prefix: str) -> str:
    return (f"/* @adapter {family}/{file}#{segment} prefix={prefix} - generated from "
            f"{TEMPLATE_ROOT.as_posix()}/{family}/{file}.css.tmpl; edit there, then run scripts/theme.sh adapters */")


def end_line(family: str, file: str, segment: int) -> str:
    return f"/* @adapter-end {family}/{file}#{segment} */"


def template_path(repo_root: Path, family: str, file: str) -> Path:
    return repo_root / TEMPLATE_ROOT / family / f"{file}.css.tmpl"


def load_template(path: Path) -> dict[int, list[str]]:
    """Segments of one template, keyed by number; text before the first marker is a header comment."""
    if not path.is_file():
        raise PackageError(f"Adapter template not found: {path}")
    segments: dict[int, list[str]] = {}
    current: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        marker = SEGMENT_RE.match(line)
        if marker:
            number = int(marker["segment"])
            if number in segments:
                raise PackageError(f"{path}: segment {number} is defined twice")
            current = segments[number] = []
        elif current is not None:
            current.append(line)
    for lines in segments.values():
        while lines and not lines[-1].strip():
            lines.pop()  # the blank line that separates segments in the template file
    return segments


def render(lines: list[str], name: str, prefix: str) -> list[str]:
    if "__PREFIX__" in "\n".join(lines) and not prefix:
        raise PackageError(f"Adapter segment for '{name}' uses __PREFIX__ but the fence declares no prefix")
    return [line.replace("__NAME__", name).replace("__PREFIX__", prefix) for line in lines]


@dataclass(frozen=True)
class AdapterReport:
    files: int
    segments: int
    drift: tuple[str, ...]


def sync_file(repo_root: Path, css_path: Path, theme: str,
              cache: dict[Path, dict[int, list[str]]]) -> tuple[str, int]:
    """Return the file text with every fenced segment re-rendered, and the number of segments."""
    lines = css_path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    count = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        begin = BEGIN_RE.match(line)
        if END_RE.match(line):
            raise PackageError(f"{css_path}:{index + 1}: @adapter-end without a matching @adapter")
        if not begin:
            out.append(line)
            index += 1
            continue
        family, file, number, prefix = begin["family"], begin["file"], int(begin["segment"]), begin["prefix"]
        close = end_line(family, file, number)
        try:
            stop = lines.index(close, index + 1)
        except ValueError:
            raise PackageError(f"{css_path}:{index + 1}: @adapter {family}/{file}#{number} is never closed") from None
        inner = lines[index + 1:stop]
        if any(BEGIN_RE.match(item) or END_RE.match(item) for item in inner):
            raise PackageError(f"{css_path}:{index + 1}: adapter fences must not nest")
        path = template_path(repo_root, family, file)
        if path not in cache:
            cache[path] = load_template(path)
        if number not in cache[path]:
            raise PackageError(f"{css_path}:{index + 1}: {path} has no segment {number}")
        out.append(begin_line(family, file, number, prefix))
        out.extend(render(cache[path][number], theme, prefix))
        out.append(close)
        count += 1
        index = stop + 1
    return "\n".join(out) + "\n", count


def sync(repo_root: Path, check: bool = False) -> AdapterReport:
    """Re-render every fenced segment in sample-themes/*/css; with check, only report drift."""
    repo_root = Path(repo_root).resolve()
    cache: dict[Path, dict[int, list[str]]] = {}
    drift: list[str] = []
    files = segments = 0
    for css_path in sorted((repo_root / "sample-themes").glob("*/css/**/*.css")):
        text = css_path.read_text(encoding="utf-8")
        if "/* @adapter " not in text and "/* @adapter-end " not in text:
            continue
        theme = css_path.relative_to(repo_root / "sample-themes").parts[0]
        rendered, count = sync_file(repo_root, css_path, theme, cache)
        files += 1
        segments += count
        if rendered != text:
            drift.append(css_path.relative_to(repo_root).as_posix())
            if not check:
                css_path.write_text(rendered, encoding="utf-8")
    return AdapterReport(files, segments, tuple(drift))


# A theme whose own (unfenced) CSS is mostly copied, in blocks, from another theme should share it
# through an adapter family instead: every fix would otherwise have to be repeated by hand.
COPY_BLOCK_MIN_LINES = 6
COPY_SHARE_WARNING = 0.65
_BUILTIN_PREFIXES = frozenset({"app", "ut", "a", "oj", "ojet", "jui", "fc"})
_THEME_MODULES = ("tokens.css", "apex/shell.css", "apex/regions.css", "apex/buttons.css", "apex/forms.css",
                  "apex/reports.css", "apex/dialogs.css", "apex/misc.css")


def private_prefix(theme_root: Path) -> str | None:
    """The theme's own palette prefix (``--sol-*`` -> ``sol``): its most declared non-UT prefix."""
    tokens = theme_root / "css/tokens.css"
    if not tokens.is_file():
        return None
    found = [name for name in re.findall(r"--([a-z]{2,4})-[a-z0-9-]+\s*:", tokens.read_text(encoding="utf-8"))
             if name not in _BUILTIN_PREFIXES]
    return max(sorted(set(found)), key=found.count) if found else None


def _comparable_lines(theme_root: Path, relative: str, own_only: bool) -> list[str | None]:
    path = theme_root / "css" / relative
    if not path.is_file():
        return []
    name, prefix = theme_root.name, private_prefix(theme_root)
    lines: list[str | None] = []
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if BEGIN_RE.match(line):
            inside = True
        elif END_RE.match(line):
            inside = False
        elif inside and own_only:
            lines.append(None)  # shared on purpose: never counted, never matched
        else:
            line = line.strip().replace(name, "__NAME__")
            lines.append(line.replace(f"--{prefix}-", "--__PREFIX__-") if prefix else line)
    return lines


def copied_block_share(theme_root: Path, others: list[Path]) -> tuple[float, str | None]:
    """Share of the theme's own non-blank CSS lines that sit in blocks of COPY_BLOCK_MIN_LINES or more
    identical to another theme's same file, and the theme most copied from."""
    total = 0
    copied: set[tuple[str, int]] = set()
    per_theme: dict[str, int] = {}
    for relative in _THEME_MODULES:
        mine = _comparable_lines(theme_root, relative, own_only=True)
        total += sum(1 for line in mine if line)
        probe = [line if line is not None else "\0" for line in mine]
        for other in others:
            theirs = _comparable_lines(other, relative, own_only=False)
            matcher = difflib.SequenceMatcher(None, probe, theirs, autojunk=False)
            for block in matcher.get_matching_blocks():
                hits = [index for index in range(block.a, block.a + block.size) if mine[index]]
                if len(hits) >= COPY_BLOCK_MIN_LINES:
                    copied.update((relative, index) for index in hits)
                    per_theme[other.name] = per_theme.get(other.name, 0) + len(hits)
    if not total:
        return 0.0, None
    source = max(sorted(per_theme), key=per_theme.get) if per_theme else None
    return len(copied) / total, source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render shared adapter segments into theme CSS")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true", help="Report drift only; exit 1 on drift")
    args = parser.parse_args(argv)
    try:
        report = sync(args.repo_root, check=args.check)
    except PackageError as exc:
        print(f"ADAPTERS status=ERROR {exc}", file=sys.stderr)
        return 2
    for path in report.drift:
        print(f"{'drift' if args.check else 'rendered'}: {path}")
    failed = args.check and bool(report.drift)
    print(f"ADAPTERS status={'FAIL' if failed else 'PASS'} files={report.files} "
          f"segments={report.segments} drift={len(report.drift)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
