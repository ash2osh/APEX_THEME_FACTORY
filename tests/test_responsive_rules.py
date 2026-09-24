"""Generated responsive.css must aim at markup Universal Theme 26.1 renders (checked against its
Core.min.css: .t-Cards--Ncols and .a-CardView-items--gridNcol are grids, .t-Region-header is a non-wrapping
flex row, .t-ButtonRegion-wrap is a one-row grid, controls size from --a-button/field-input-padding-y)."""

from dataclasses import replace
from pathlib import Path
import unittest

from lib.theme_factory.recipe import Responsive, load_recipe, render_responsive_css

REPO_ROOT = Path(__file__).resolve().parent.parent


class ResponsiveRuleTests(unittest.TestCase):
    def render(self, strategy: str, compact_at: int = 768) -> str:
        recipe = load_recipe(REPO_ROOT / "sample-themes/linen/theme.recipe.json")
        return render_responsive_css(replace(recipe, responsive=Responsive(strategy, compact_at)))

    def test_stack_targets_the_column_grids(self):
        css = self.render("stack")
        for selector in (".t-Cards--3cols", ".t-Cards--cols", ".a-CardView-items--grid3col"):
            self.assertIn(f"html.app-theme-linen {selector}", css)
        self.assertIn("grid-template-columns: 1fr;", css)
        self.assertNotIn(".t-Region--cards", css)       # no such class in UT 26.1
        self.assertNotRegex(css, r"\.t-Cards[ ,{]")      # .t-Cards alone is a flex row: grid columns do nothing

    def test_reflow_targets_containers_that_do_not_wrap(self):
        css = self.render("reflow")
        self.assertIn("html.app-theme-linen .t-Region-header { flex-wrap: wrap; }", css)
        self.assertIn('grid-template-areas: "button-left button-right" "button-content button-content";', css)
        self.assertNotIn(".t-Header-controls", css)       # a grid item, not a flex container
        self.assertNotIn(".t-Body-actions", css)

    def test_compress_shrinks_the_padding_atoms_controls_are_sized_from(self):
        css = self.render("compress")
        self.assertIn("html.app-theme-linen .apex-theme-iris {", css)
        self.assertIn("--a-button-padding-y: .375rem;", css)
        self.assertNotIn("--a-field-input-padding-y", css)
        self.assertIn("--app-control-h: calc(2.25rem * 0.875);", css)
        self.assertNotIn("calc(var(", css)                 # no self-referencing custom property

    def test_breakpoint_follows_the_recipe_and_zero_disables(self):
        self.assertIn("@media (max-width: 1024px)", self.render("stack", 1024))
        self.assertNotIn("@media", self.render("stack", 0))


if __name__ == "__main__":
    unittest.main()
