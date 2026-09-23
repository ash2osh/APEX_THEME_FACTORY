"""Assemble app 102's static files into its APEXLang export (scripts/sync-static.sh).

  static-files/css/**, static-files/js/**   -> applications/ut/shared-components/static-files/css|js/**
  sample-themes/<name>/css/**               -> …/css/themes/<name>/**  (theme.css gains the generated @font-face)
  sample-themes/<name>/fonts/**/*.woff2     -> …/css/themes/<name>/fonts/  (only when the theme declares fonts)
  sample-themes/<name>/theme.json           -> …/css/themes/<name>/theme.json  (read by the switcher and page 405)
  sample-themes/<name>/preview/cover.jpg    -> …/css/themes/<name>/cover.jpg

Also regenerates the @themes block in static-files/css/app.css, registers every synced file in
static-files.apx, and prunes export files under css/ and js/ that no longer have a source.
Sources are the only editable copies. check=True reports drift and writes nothing.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import re

from lib.theme_factory.css_bundle import render_font_css
from lib.theme_factory.manifest import load_manifest
from lib.theme_factory.static_files import file_block

THEMES_BLOCK_RE = re.compile(r"/\* @themes:start \*/.*?/\* @themes:end \*/", re.S)


@dataclass
class SyncReport:
    themes: list[str]
    copied: int = 0
    registered: int = 0
    pruned: int = 0
    drift: list[str] = field(default_factory=list)


def _byte_order(path: Path) -> bytes:
    return path.as_posix().encode("utf-8")


def _theme_names(themes_root: Path) -> list[str]:
    # Sorting "<name>/" as bytes keeps the historical order (estate-slate-dark before estate-slate).
    names = [path.parent.name for path in themes_root.glob("*/theme.json") if path.is_file()]
    return sorted(names, key=lambda name: (name + "/").encode("utf-8"))


def _skipped(rel: str) -> bool:
    return (
        rel.endswith("README.md")
        or "/.about" in "/" + rel
        or "LICENSE" in rel
        or rel == "js/vendor/alpine.js"
    )


def _files(root: Path) -> list[Path]:
    return sorted((path for path in root.rglob("*") if path.is_file()), key=_byte_order) if root.is_dir() else []


def _theme_files(theme_root: Path, name: str) -> dict[str, bytes]:
    font_css = render_font_css(load_manifest(theme_root / "theme.json", theme_root)).rstrip("\n")
    wanted: dict[str, bytes] = {}
    css_root = theme_root / "css"
    for path in _files(css_root):
        data = path.read_bytes()
        if font_css and path == css_root / "theme.css":
            data = data + b"\n" + font_css.encode("utf-8") + b"\n"
        wanted[f"css/themes/{name}/{path.relative_to(css_root).as_posix()}"] = data
    if font_css:
        for font in (path for path in _files(theme_root / "fonts") if path.suffix == ".woff2"):
            wanted[f"css/themes/{name}/fonts/{font.name}"] = font.read_bytes()
    wanted[f"css/themes/{name}/theme.json"] = (theme_root / "theme.json").read_bytes()
    cover = theme_root / "preview/cover.jpg"
    if cover.is_file():
        wanted[f"css/themes/{name}/cover.jpg"] = cover.read_bytes()
    return wanted


def _reconcile_block(text: str, rel: str) -> tuple[str, str]:
    want = file_block(rel)
    pattern = re.compile(r'file "' + re.escape(rel) + r'" \(\n(?:    [^\n]*\n)*\)')
    match = pattern.search(text)
    if match and match.group(0) == want:
        return text, "same"
    if match:
        text = pattern.sub("", text, count=1)
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text.rstrip("\n") + "\n\n" + want + "\n", "changed" if match else "new"


def _remove_block(text: str, rel: str) -> str:
    return re.sub(r'\n*file "' + re.escape(rel) + r'" \(\n(?:    .*\n)*\)\n', "\n", text)


def _remove_empty_dirs(base: Path) -> None:
    if not base.is_dir():
        return
    for directory in sorted((p for p in base.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    if not any(base.iterdir()):
        base.rmdir()


def sync(root: Path, *, check: bool = False) -> SyncReport:
    root = Path(root).resolve()
    source = root / "static-files"
    dst = root / "applications/ut/shared-components/static-files"
    apx = root / "applications/ut/shared-components/static-files.apx"
    app_css = source / "css/app.css"
    themes = _theme_names(root / "sample-themes")
    report = SyncReport(themes)

    # (1) themes block in app.css
    block = "\n".join(["/* @themes:start */", *(f'@import "themes/{name}/theme.css";' for name in themes),
                       "/* @themes:end */"])
    current_css = app_css.read_text(encoding="utf-8")
    new_css = THEMES_BLOCK_RE.sub(lambda _match: block, current_css)
    if new_css != current_css:
        if check:
            report.drift.append("static-files/css/app.css: @themes block")
        else:
            app_css.write_text(new_css, encoding="utf-8")

    # (2) desired export content
    wanted: dict[str, bytes] = {}
    for path in _files(source / "css") + _files(source / "js"):
        rel = path.relative_to(source).as_posix()
        if not _skipped(rel):
            wanted[rel] = new_css.encode("utf-8") if path == app_css else path.read_bytes()
    for name in themes:
        wanted.update(_theme_files(root / "sample-themes" / name, name))

    # (3) copy + register
    original_apx = apx.read_text(encoding="utf-8")
    apx_text = original_apx
    for rel, data in wanted.items():
        target = dst / rel
        if not target.is_file() or target.read_bytes() != data:
            report.copied += 1
            if check:
                report.drift.append(f"{rel}: content")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        apx_text, status = _reconcile_block(apx_text, rel)
        if status == "new":
            report.registered += 1
        if status != "same" and check:
            report.drift.append(f"{rel}: registration {status}")

    # (4) prune
    for path in _files(dst / "css") + _files(dst / "js"):
        rel = path.relative_to(dst).as_posix()
        if rel not in wanted:
            report.pruned += 1
            if check:
                report.drift.append(f"{rel}: stale")
            else:
                path.unlink()
                apx_text = _remove_block(apx_text, rel)

    if not check:
        if apx_text != original_apx:
            apx.write_text(apx_text, encoding="utf-8")
        _remove_empty_dirs(dst / "css")
        _remove_empty_dirs(dst / "js")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble app 102 static files into the APEXLang export")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--check", action="store_true", help="Report drift between sources and export; write nothing")
    args = parser.parse_args(argv)
    report = sync(args.repo_root, check=args.check)
    if args.check:
        for item in report.drift:
            print(f"SYNC_STATIC drift {item}")
        print(f"SYNC_STATIC status={'FAIL' if report.drift else 'PASS'} drift={len(report.drift)}")
        return 1 if report.drift else 0
    print(f"sync-static: themes=[{' '.join(report.themes)}] copied={report.copied} "
          f"registered={report.registered} pruned={report.pruned}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
