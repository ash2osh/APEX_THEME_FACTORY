"""Responsive stylesheet generator and drift checker.

Renders sample-themes/<name>/css/apex/responsive.css from sample-themes/<name>/theme.recipe.json
and ensures it is imported last in sample-themes/<name>/css/theme.css.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lib.theme_factory.discovery import theme_names
from lib.theme_factory.recipe import load_recipe, render_responsive_css

RESPONSIVE_IMPORT = '@import "apex/responsive.css";'


def sync_responsive(repo_root: Path, check: bool = False) -> list[str]:
    repo_root = Path(repo_root).resolve()
    themes_root = repo_root / "sample-themes"
    drift: list[str] = []

    for name in theme_names(repo_root):
        theme_dir = themes_root / name
        recipe_path = theme_dir / "theme.recipe.json"
        if not recipe_path.is_file():
            continue

        recipe = load_recipe(recipe_path)
        expected_css = render_responsive_css(recipe)
        responsive_file = theme_dir / "css/apex/responsive.css"

        if not responsive_file.is_file() or responsive_file.read_text(encoding="utf-8") != expected_css:
            if check:
                drift.append(f"{name}: css/apex/responsive.css")
            else:
                responsive_file.parent.mkdir(parents=True, exist_ok=True)
                responsive_file.write_text(expected_css, encoding="utf-8")

        theme_css_path = theme_dir / "css/theme.css"
        if theme_css_path.is_file():
            content = theme_css_path.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            imports = [line for line in lines if line.startswith("@import ")]
            needs_update = not imports or imports[-1] != RESPONSIVE_IMPORT
            if needs_update:
                if check:
                    drift.append(f"{name}: css/theme.css (missing or out-of-order {RESPONSIVE_IMPORT})")
                else:
                    cleaned_lines = [line for line in content.splitlines() if RESPONSIVE_IMPORT not in line]
                    cleaned_text = "\n".join(cleaned_lines).rstrip() + f"\n{RESPONSIVE_IMPORT}\n"
                    theme_css_path.write_text(cleaned_text, encoding="utf-8")

    return drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render and check responsive CSS from theme recipes")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true", help="Report drift only; exit 1 on drift")
    args = parser.parse_args(argv)

    drift = sync_responsive(args.repo_root, check=args.check)
    if args.check:
        for item in drift:
            print(f"RESPONSIVE drift {item}")
        print(f"RESPONSIVE status={'FAIL' if drift else 'PASS'} drift={len(drift)}")
        return 1 if drift else 0

    print(f"responsive: synchronized responsive.css for themes in {args.repo_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
