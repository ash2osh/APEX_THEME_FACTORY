#!/usr/bin/env python3
"""Build the public demo: the reference app with all themes, as one APEXLang ZIP for App Builder's import page.

Every change is made to a copy, so applications/ut/ stays the source. The demo differs from it in that it:
  - has its own name, alias and logo, so nobody takes it for an Oracle application
  - opens on the theme gallery, with a notice on the gallery and Getting Started pages
  - gets a new session-state protection salt, because the one in the source is public
  - allows no runtime API changes to the application, and carries no fixed application ID
  - loads all the map sample data whatever the database's date format
  - drops the Theme Version menu and the installer's test page, which only make sense on a development machine

    scripts/build-demo.sh                 # writes dist/demo/theme-factory-demo.zip and its .sha256
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.theme_factory.errors import PackageError  # noqa: E402
from lib.theme_factory.sync_static import sync  # noqa: E402

DEMO_ALIAS = "THEME-FACTORY-DEMO"
DEMO_NAME = "APEX Theme Factory Demo"
REPOSITORY_URL = "https://github.com/ash2osh/APEX_THEME_FACTORY"
FIXED_DATETIME = (1980, 1, 1, 0, 0, 0)

NOTICE_REGION = f"""
    region theme-factory-demo-notice (
        name: Theme Factory Demo Notice
        type: staticContent
        source {{
            htmlCode:
                ```html
                <p><small>Community demo of <a href="{REPOSITORY_URL}">APEX Theme Factory</a>. It is not affiliated
                with or endorsed by Oracle. Based on Oracle's Universal Theme Reference sample application, used
                under the Universal Permissive License 1.0. Oracle, APEX and Universal Theme are trademarks of
                Oracle and/or its affiliates.</small></p>
                ```
        }}
        layout {{
            sequence: 9000
            slot: body
        }}
        appearance {{
            template: @/content-block
            templateOptions: #DEFAULT#
        }}
        serverSideCondition {{
            type: currentPageInList
            pages: [
                405
                500
            ]
        }}
    )
"""


def _replace_once(text: str, pattern: str, replacement: str, what: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise PackageError(f"Demo build: could not find {what}")
    return updated


def demo_application(text: str, salt: str) -> str:
    text = _replace_once(text, r"^app [A-Za-z0-9_$-]+ \(", f"app {DEMO_ALIAS} (", "the application alias")
    text = _replace_once(text, r"^(    name: ).+$", rf"\g<1>{DEMO_NAME}", "the application name")
    text = _replace_once(text, r"^(\s+text: )Universal Theme$", r"\g<1>Theme Factory Demo", "the logo text")
    text = _replace_once(text, r"(homeUrl: \{\s+page: )500\b", r"\g<1>405", "the home page")
    text = _replace_once(text, r"^(\s+checksumSalt: )\w+$", rf"\g<1>{salt}", "the checksum salt")
    text = _replace_once(text, r"^\s+runtimeApiUsage: \w+\n", "", "the runtime API usage")
    text = _replace_once(text, r"^(\s+appDescription: ).+$",
                         r"\g<1>Community demo of APEX Theme Factory themes for Oracle APEX.", "the description")
    return text


def demo_lists(text: str) -> str:
    """Drop the Theme Version menu and the entry for the installer's test page."""
    text, menu = re.subn(
        r"[ \t]*select 1 node_id,(?:(?!union all).)*?'Theme Version' label,(?:(?!union all).)*?union all[ \t]*\n\s*\n",
        "", text, count=1, flags=re.DOTALL)
    text, versions = re.subn(
        r"[ \t]*select null node_id,\s+1 parent_node_id,(?:(?!union all).)*?union all[ \t]*\n\s*\n",
        "", text, count=1, flags=re.DOTALL)
    text, entry = re.subn(r"[ \t]*entry theme-factory-lifecycle \(.*?\n[ \t]*\)[ \t]*\n\s*\n", "", text, count=1,
                          flags=re.DOTALL)
    if (menu, versions, entry) != (1, 1, 1):
        raise PackageError("Demo build: could not remove the development-only navigation entries")
    return text


def demo_gallery(text: str) -> str:
    """Tell visitors where to get the themes, at the top of the gallery."""
    return _replace_once(
        text, r"^([ \t]*)<p>Pick a package below",
        rf'\g<1><p>To use these themes in your own app, get them from <a href="{REPOSITORY_URL}">APEX Theme Factory on '
        r"GitHub</a>.</p>\n\g<1><p>Pick a package below",
        "the gallery text")


def demo_deployment(text: str) -> str:
    """Without a fixed ID, an import can't replace whatever app already uses it (102 is the source's own ID)."""
    settings = json.loads(text)
    settings["app"].pop("id", None)
    return json.dumps(settings, indent=2) + "\n"


def demo_airports(text: str) -> str:
    """Oracle's script writes to_date('04/01/1940') and relies on the session's date format, so on most databases
    only the rows without a date load and the map page shows one airport."""
    first = "alter session set nls_numeric_characters='.,';\n"
    if first not in text:
        raise PackageError("Demo build: could not find the start of the airports script")
    return text.replace(first, first + "alter session set nls_date_format='MM/DD/YYYY';\n", 1)


def demo_global_page(text: str) -> str:
    close = text.rstrip().rfind(")")
    if close == -1:
        raise PackageError("Demo build: global page has no closing parenthesis")
    return text[:close].rstrip() + "\n" + NOTICE_REGION + ")\n"


def prepare(source: Path, destination: Path, salt: str) -> None:
    shutil.copytree(source, destination)
    application = destination / "application.apx"
    application.write_text(demo_application(application.read_text(encoding="utf-8"), salt),
                           encoding="utf-8", newline="\n")
    lists = destination / "shared-components/lists.apx"
    lists.write_text(demo_lists(lists.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    global_page = destination / "pages/p00000-global-page.apx"
    global_page.write_text(demo_global_page(global_page.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    gallery = destination / "pages/p00405-themes.apx"
    gallery.write_text(demo_gallery(gallery.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    airports = destination / "supporting-objects/install-scripts/create-airports-table.sql"
    airports.write_text(demo_airports(airports.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    deployment = destination / "deployments/default.json"
    deployment.write_text(demo_deployment(deployment.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    # Not an application file: the Theme Factory build reads it, and no import needs it.
    (destination / "theme-factory.json").unlink()


def write_zip(root: Path, zip_path: Path) -> None:
    """Application files at the ZIP's top level, the layout of Oracle's own sample-app ZIPs."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=FIXED_DATETIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o644 & 0xFFFF) << 16
                archive.writestr(info, path.read_bytes())


def build(output_dir: Path, repo_root: Path = ROOT, salt: str | None = None) -> Path:
    if sync(repo_root, check=True).drift:
        raise PackageError("applications/ut is out of date: run scripts/sync-static.sh first")
    zip_path = output_dir / "theme-factory-demo.zip"
    with tempfile.TemporaryDirectory(prefix="theme-factory-demo-") as temporary:
        staged = Path(temporary) / "app"
        prepare(repo_root / "applications/ut", staged, salt or secrets.token_hex(32).upper())
        write_zip(staged, zip_path)
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    zip_path.with_name(zip_path.name + ".sha256").write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8",
                                                             newline="\n")
    return zip_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist/demo")
    args = parser.parse_args(argv)
    try:
        path = build(args.output_dir)
    except PackageError as exc:
        print(f"DEMO status=FAIL {exc}", file=sys.stderr)
        return 2
    print(f"DEMO status=PASS package={path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
