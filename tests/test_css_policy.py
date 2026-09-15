from pathlib import Path
import shutil
import tempfile
import unittest

from lib.theme_factory.css_policy import scan_package, PolicyViolation


class CssPolicyTests(unittest.TestCase):
    def test_comments_do_not_count_as_literal_declarations(self):
        violations = scan_package(Path("tests/fixtures/packages/css-comment-only"))
        self.assertFalse([v for v in violations if v.code == "literal-color"])

    def test_unscoped_selector_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                ".t-Dialog { color: var(--app-test-color); }\n",
                encoding="utf-8",
            )
            violations = scan_package(theme_dir)
            codes = [v.code for v in violations]
            self.assertIn("unscoped-selector", codes)

    def test_literal_color_in_component_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                "html.app-theme-css-comment-only .t-Dialog { background-color: #ff0000; }\n",
                encoding="utf-8",
            )
            violations = scan_package(theme_dir)
            codes = [v.code for v in violations]
            self.assertIn("literal-color", codes)

    def test_unsupported_important_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                "html.app-theme-css-comment-only .t-Dialog { padding: 10px !important; }\n",
                encoding="utf-8",
            )
            violations = scan_package(theme_dir)
            codes = [v.code for v in violations]
            self.assertIn("unsupported-important", codes)

    def test_supported_important_with_iris_comment_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                "/* Iris: mirrors core */\nhtml.app-theme-css-comment-only .t-Dialog { padding: 10px !important; }\n",
                encoding="utf-8",
            )
            violations = scan_package(theme_dir)
            important_violations = [v for v in violations if v.code == "unsupported-important"]
            self.assertEqual(len(important_violations), 0)

    def test_undeclared_app_token_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                "html.app-theme-css-comment-only .t-Dialog { color: var(--app-non-existent-token); }\n",
                encoding="utf-8",
            )
            violations = scan_package(theme_dir)
            codes = [v.code for v in violations]
            self.assertIn("undeclared-app-token", codes)

    def test_existing_themes_have_no_policy_violations(self):
        for name in ("linen", "solarized-dark"):
            with self.subTest(name=name):
                violations = scan_package(Path("sample-themes") / name)
                self.assertEqual(violations, (), f"Violations in {name}: {violations}")
