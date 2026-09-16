#!/usr/bin/env python3
"""Simulate what SQLcl `apex export` does to an APEXLang tree that was just imported.

Observed against APEX 26.1.4 / SQLcl 26.2.1 (theme-factory-backups DEMO-9011, 2026-09-15):

* APEXLang comment lines (`//`, `--`) are not stored in APEX and never come back.
* Fenced code (``` blocks) is re-emitted with every content line prefixed by the fence
  column, so staged content that was not indented ends up shifted right.
* `file "..." ( ... )` blocks in static-files.apx are sorted by path.
* Page files are named `pNNNNN-<slug of page name>.apx`.

The fake `sql` fixture runs this on the directory it "exports" after an import so that
offline tests see the same shapes a real target produces.
"""

from pathlib import Path
import re
import sys

FENCE_RE = re.compile(r"^(\s*)```")
COMMENT_RE = re.compile(r"^\s*(?://|--)(?:\s|$)")
FILE_BLOCK_RE = re.compile(r'^file\s+("?)([^"\n]+?)\1\s*\(\n(?:.*\n)*?\)\n?', re.MULTILINE)
PAGE_HEADER_RE = re.compile(r"^page\s+([0-9]+)\s*\(", re.MULTILINE)
NAME_RE = re.compile(r"^\s*name:\s*(.+?)\s*$", re.MULTILINE)


def normalize_apx_text(text: str) -> str:
    out = []
    fence_indent = None
    for line in text.splitlines():
        fence = FENCE_RE.match(line)
        if fence_indent is None:
            if fence:
                fence_indent = fence.group(1)
                out.append(line)
                continue
            if COMMENT_RE.match(line):
                continue
            out.append(line)
        else:
            if fence and fence.group(1) == fence_indent and line.strip() == "```":
                fence_indent = None
                out.append(line)
                continue
            out.append(fence_indent + line if line.strip() else line)
    return "\n".join(out) + "\n"


def sort_static_files(text: str) -> str:
    blocks = list(FILE_BLOCK_RE.finditer(text))
    if not blocks:
        return text
    remainder = FILE_BLOCK_RE.sub("", text).strip()
    ordered = sorted(blocks, key=lambda m: m.group(2))
    body = "\n".join(m.group(0).strip() + "\n" for m in ordered)
    return (remainder + "\n\n" if remainder else "") + body


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "page"


def rename_pages(pages_dir: Path) -> None:
    if not pages_dir.is_dir():
        return
    for path in sorted(pages_dir.glob("*.apx")):
        text = path.read_text(encoding="utf-8")
        header = PAGE_HEADER_RE.search(text)
        name = NAME_RE.search(text)
        if not header or not name:
            continue
        target = pages_dir / f"p{int(header.group(1)):05d}-{slugify(name.group(1))}.apx"
        if target != path:
            path.rename(target)


def simulate_export(export_dir: Path) -> None:
    export_dir = Path(export_dir)
    for path in export_dir.rglob("*.apx"):
        text = normalize_apx_text(path.read_text(encoding="utf-8"))
        if path.name == "static-files.apx":
            text = sort_static_files(text)
        path.write_text(text, encoding="utf-8")
    rename_pages(export_dir / "pages")


if __name__ == "__main__":
    simulate_export(Path(sys.argv[1]))
