"""Shared adapter segments: rendering, drift detection, fence errors, and the copied-CSS measure."""

from pathlib import Path
import shutil
import tempfile
import unittest

from lib.theme_factory.adapters import (
    begin_line, copied_block_share, end_line, load_template, private_prefix, render, sync,
)
from lib.theme_factory.errors import PackageError

REPO_ROOT = Path(__file__).resolve().parent.parent

TEMPLATE = """/* header comment, ignored */

/* @segment 1 */
.app-theme-__NAME__ .t-Region {
    color: var(--__PREFIX__-cyan);
}

/* @segment 2 */
.app-theme-__NAME__ .t-Button { color: var(--app-text-primary); }
"""


class AdapterSyncTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        template = self.root / "theme-templates/adapters/demo/regions.css.tmpl"
        template.parent.mkdir(parents=True)
        template.write_text(TEMPLATE, encoding="utf-8")
        self.css = self.root / "sample-themes/alpha/css/apex/regions.css"
        self.css.parent.mkdir(parents=True)
        self.css.write_text("\n".join([
            "/* identity: alpha's own rule */",
            ".app-theme-alpha .t-Region { border: 0; }",
            begin_line("demo", "regions", 1, "al"),
            "stale text",
            end_line("demo", "regions", 1),
            "/* between segments */",
            begin_line("demo", "regions", 2, "al"),
            end_line("demo", "regions", 2),
        ]) + "\n", encoding="utf-8")

    def test_template_segments_and_rendering(self):
        segments = load_template(self.root / "theme-templates/adapters/demo/regions.css.tmpl")
        self.assertEqual(sorted(segments), [1, 2])
        self.assertEqual(render(segments[1], "alpha", "al")[1], "    color: var(--al-cyan);")

    def test_check_reports_drift_without_writing_then_sync_renders_in_place(self):
        before = self.css.read_text(encoding="utf-8")
        report = sync(self.root, check=True)
        self.assertEqual(report.drift, ("sample-themes/alpha/css/apex/regions.css",))
        self.assertEqual(self.css.read_text(encoding="utf-8"), before)

        report = sync(self.root)
        text = self.css.read_text(encoding="utf-8")
        self.assertEqual((report.files, report.segments), (1, 2))
        self.assertIn(".app-theme-alpha .t-Region {\n    color: var(--al-cyan);\n}", text)
        self.assertNotIn("stale text", text)
        self.assertTrue(text.startswith("/* identity: alpha's own rule */\n.app-theme-alpha .t-Region { border: 0; }\n"))
        self.assertIn("/* between segments */", text)
        self.assertEqual(sync(self.root, check=True).drift, ())

    def test_hand_edit_inside_a_fence_is_drift(self):
        sync(self.root)
        self.css.write_text(self.css.read_text(encoding="utf-8").replace("--al-cyan", "--al-red"), encoding="utf-8")
        self.assertEqual(len(sync(self.root, check=True).drift), 1)

    def test_malformed_fences_are_refused(self):
        cases = {
            "unclosed": begin_line("demo", "regions", 1, "al") + "\n",
            "stray end": end_line("demo", "regions", 1) + "\n",
            "nested": "\n".join([begin_line("demo", "regions", 1, "al"), begin_line("demo", "regions", 2, "al"),
                                 end_line("demo", "regions", 2), end_line("demo", "regions", 1)]) + "\n",
            "unknown segment": begin_line("demo", "regions", 9, "al") + "\n" + end_line("demo", "regions", 9) + "\n",
            "missing prefix": begin_line("demo", "regions", 1, "") + "\n" + end_line("demo", "regions", 1) + "\n",
        }
        for label, text in cases.items():
            self.css.write_text(text, encoding="utf-8")
            with self.assertRaises(PackageError, msg=label):
                sync(self.root, check=True)


class RepositoryAdapterTests(unittest.TestCase):
    def test_repository_segments_are_rendered(self):
        report = sync(REPO_ROOT, check=True)
        self.assertEqual(report.drift, ())
        self.assertGreater(report.segments, 0)

    def test_private_prefix_detection(self):
        self.assertEqual(private_prefix(REPO_ROOT / "sample-themes/solarized-dark"), "sol")
        self.assertEqual(private_prefix(REPO_ROOT / "sample-themes/carbon-volt"), "cv")


class CopiedCssTests(unittest.TestCase):
    def write_theme(self, root: Path, name: str, body: list[str]) -> Path:
        theme = root / name
        (theme / "css/apex").mkdir(parents=True)
        (theme / "css/tokens.css").write_text(f"html.app-theme-{name} {{ --{name[:2]}-cyan: #00ffff; }}\n")
        (theme / "css/apex/misc.css").write_text("\n".join(line.replace("NAME", name) for line in body) + "\n")
        return theme

    def test_copied_blocks_count_and_fenced_lines_do_not(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        block = [f".app-theme-NAME .rule-{index} {{ color: var(--app-text-primary); }}" for index in range(8)]
        original = self.write_theme(root, "original", block + [".app-theme-NAME .own { margin: 0; }"])
        copy = self.write_theme(root, "copycat", block + [".app-theme-NAME .mine { padding: 0; }"])
        share, source = copied_block_share(copy, [original])
        self.assertAlmostEqual(share, 8 / 10)  # 8 copied of 10 own lines (9 in misc.css + 1 in tokens.css)
        self.assertEqual(source, "original")

        fenced = ([begin_line("demo", "misc", 1, "co")] + block + [end_line("demo", "misc", 1)]
                  + [".app-theme-NAME .mine { padding: 0; }"])
        (copy / "css/apex/misc.css").write_text("\n".join(line.replace("NAME", "copycat") for line in fenced) + "\n")
        self.assertEqual(copied_block_share(copy, [original])[0], 0.0)


if __name__ == "__main__":
    unittest.main()
