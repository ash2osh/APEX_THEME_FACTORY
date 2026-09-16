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
                "html.app-theme-css-comment-only .t-Dialog { padding: 10px !important; /* Iris: mirrors core */ }\n",
                encoding="utf-8",
            )
            violations = scan_package(theme_dir)
            important_violations = [v for v in violations if v.code == "unsupported-important"]
            self.assertEqual(len(important_violations), 0)

    def test_nearby_iris_comment_does_not_authorize_important(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                "/* Iris is discussed here but this is not an exact mirrored declaration. */\n"
                "html.app-theme-css-comment-only .t-Dialog { padding: 10px !important; }\n",
                encoding="utf-8",
            )
            violations = scan_package(theme_dir)
            self.assertTrue([v for v in violations if v.code == "unsupported-important"])

    def test_nested_media_selector_must_be_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                "@media (min-width: 40rem) { .t-Dialog { padding: 1rem; } }\n",
                encoding="utf-8",
            )
            violations = scan_package(theme_dir)
            self.assertTrue([v for v in violations if v.code == "unscoped-selector"])

    def test_scope_prefix_requires_a_selector_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                ".app-theme-css-comment-only-evil .t-Dialog { padding: 1rem; }\n",
                encoding="utf-8",
            )
            violations = scan_package(theme_dir)
            self.assertTrue([v for v in violations if v.code == "unscoped-selector"])

    def test_color_text_inside_css_string_is_not_a_literal_declaration(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                'html.app-theme-css-comment-only .t-Dialog::before { content: "#fff"; }\n',
                encoding="utf-8",
            )
            violations = scan_package(theme_dir)
            self.assertFalse([v for v in violations if v.code == "literal-color"])

    def test_literal_color_in_var_fallback_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                "html.app-theme-css-comment-only .t-Dialog { color: var(--app-test-color, #fff); }\n",
                encoding="utf-8",
            )
            self.assertTrue([v for v in scan_package(theme_dir) if v.code == "literal-color"])

    def test_modern_function_and_named_literal_colors_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                "html.app-theme-css-comment-only .a { color: oklch(60% .2 20); }\n"
                "html.app-theme-css-comment-only .b { border-color: rebeccapurple; }\n",
                encoding="utf-8",
            )
            literal_colors = [v for v in scan_package(theme_dir) if v.code == "literal-color"]
            self.assertEqual(len(literal_colors), 2)

    def test_named_color_word_in_non_color_property_is_not_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                "html.app-theme-css-comment-only .a { animation-name: red; }\n",
                encoding="utf-8",
            )
            self.assertFalse([v for v in scan_package(theme_dir) if v.code == "literal-color"])

    def test_named_colors_in_logical_border_and_filter_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                "html.app-theme-css-comment-only .a { border-block: 1px solid rebeccapurple; }\n"
                "html.app-theme-css-comment-only .b { filter: drop-shadow(0 0 1px red); }\n",
                encoding="utf-8",
            )
            literal_colors = [v for v in scan_package(theme_dir) if v.code == "literal-color"]
            self.assertEqual(len(literal_colors), 2)

    def test_named_color_in_local_url_path_is_not_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                "html.app-theme-css-comment-only .a { background-image: url(images/orange.svg); }\n",
                encoding="utf-8",
            )
            self.assertFalse([v for v in scan_package(theme_dir) if v.code == "literal-color"])

    def test_escaped_remote_url_function_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            theme_dir = Path(tmp) / "css-comment-only"
            shutil.copytree(Path("tests/fixtures/packages/css-comment-only"), theme_dir)
            (theme_dir / "css/apex/dialogs.css").write_text(
                'html.app-theme-css-comment-only .t-Dialog { background: u\\72 l("https://example.invalid/x"); }\n',
                encoding="utf-8",
            )
            self.assertTrue([v for v in scan_package(theme_dir) if v.code == "external-url"])

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
