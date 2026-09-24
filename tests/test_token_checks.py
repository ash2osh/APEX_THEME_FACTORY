"""theme.sh check reads the colours a theme ships (css/tokens.css), not only its recipe."""

from pathlib import Path
import shutil
import tempfile
import unittest

from lib.theme_factory.archive import build_package_from_root
from lib.theme_factory.checks import _token_issues
from lib.theme_factory.recipe import load_recipe

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKENS = """html.app-theme-demo {
    --demo-ink: #111111;
    --app-surface-page: #ffffff;
    --app-surface-card: #fff;
    --app-surface-chrome: #ffffff;
    --app-text-primary: var(--demo-ink);
    --app-text-secondary: rgb(85, 85, 85);
    --app-text-on-accent: #ffffff;
    --app-color-primary: #0B5CAD;
    --app-color-danger: #B42318;
}
"""


class TokenCheckTests(unittest.TestCase):
    def theme(self, tokens: str) -> Path:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        (root / "css").mkdir()
        (root / "css/tokens.css").write_text(tokens, encoding="utf-8")
        return root

    def codes(self, tokens: str, recipe=None) -> list[str]:
        root = self.theme(tokens)
        return [issue.code for issue in _token_issues(root, root, recipe)]

    def test_passing_tokens_in_any_colour_notation(self):
        self.assertEqual(self.codes(TOKENS), [])

    def test_low_contrast_text_is_an_error(self):
        issues = self.codes(TOKENS.replace("rgb(85, 85, 85)", "#bbbbbb"))
        self.assertEqual(issues.count("TOKEN_CONTRAST"), 2)  # secondary on page and on card

    def test_aliases_of_iris_are_reported_not_failed(self):
        self.assertEqual(self.codes(TOKENS.replace("#0B5CAD", "var(--ut-palette-primary)")), ["TOKENS_UNRESOLVED"])

    def test_a_theme_that_aliases_iris_throughout_stays_quiet(self):
        aliased = "\n".join(line if ":" not in line or line.strip().startswith("--demo") else
                             line.split(":")[0] + ": var(--ut-component-text-default-color);"
                             for line in TOKENS.splitlines())
        self.assertEqual(self.codes(aliased), [])

    def test_recipe_that_disagrees_with_the_shipped_tokens_is_drift(self):
        recipe = load_recipe(REPO_ROOT / "sample-themes/carbon-volt/theme.recipe.json")
        tokens = (REPO_ROOT / "sample-themes/carbon-volt/css/tokens.css").read_text(encoding="utf-8")
        self.assertNotIn("RECIPE_DRIFT", self.codes(tokens, recipe))
        self.assertIn("RECIPE_DRIFT", self.codes(tokens.replace("--app-text-primary:     var(--cv-base2)",
                                                                "--app-text-primary:     var(--cv-base3)"), recipe))


class ReducedMotionTests(unittest.TestCase):
    def test_every_package_carries_the_reduced_motion_guard(self):
        foundation = (REPO_ROOT / "static-files/css/foundation/tokens.css").read_text(encoding="utf-8")
        self.assertIn("@media (prefers-reduced-motion: reduce)", foundation)
        self.assertIn(':root:root[class*="app-theme-"]', foundation)
        with tempfile.TemporaryDirectory() as out:
            package = build_package_from_root(REPO_ROOT, REPO_ROOT / "sample-themes/citrus-pop", Path(out), "test")
            import zipfile
            with zipfile.ZipFile(package) as archive:
                css = archive.read(next(n for n in archive.namelist() if n.endswith("/theme.css"))).decode("utf-8")
        self.assertIn("prefers-reduced-motion: reduce", css)

    def test_theme_motion_goes_through_the_tokens(self):
        for css in (REPO_ROOT / "sample-themes").glob("*/css/**/*.css"):
            text = css.read_text(encoding="utf-8")
            with self.subTest(file=css.relative_to(REPO_ROOT).as_posix()):
                # property declarations only (not the --app-hover-transform token itself)
                self.assertNotRegex(text, r"(?<![-\w])transition:[^;]*\b\d*\.?\d+m?s\b")  # literal durations
                self.assertNotRegex(text, r"(?<![-\w])transform:\s*translate")                # literal hover moves


if __name__ == "__main__":
    unittest.main()
