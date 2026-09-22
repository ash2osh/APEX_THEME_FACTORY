import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lib.theme_factory.uniqueness_report import (
    build_uniqueness_rows,
    render_uniqueness_report,
)


class UniquenessReportTests(unittest.TestCase):
    def test_current_repository_has_every_unordered_pair(self):
        rows = build_uniqueness_rows(Path.cwd())
        self.assertEqual(len(rows), 28)
        self.assertEqual(
            {(row.left, row.right) for row in rows},
            {(left, right) for left in (
                "carbon-volt", "citrus-pop", "cobalt-press", "estate-slate",
                "estate-slate-dark", "linen", "solarized-dark", "velvet-signal",
            ) for right in (
                "carbon-volt", "citrus-pop", "cobalt-press", "estate-slate",
                "estate-slate-dark", "linen", "solarized-dark", "velvet-signal",
            ) if left < right},
        )

    def test_rows_sort_by_css_similarity_then_theme_names(self):
        rows = build_uniqueness_rows(Path.cwd())
        keys = [(-row.report.css_similarity, row.left, row.right) for row in rows]
        self.assertEqual(keys, sorted(keys))

    def test_markdown_explains_all_similarity_dimensions(self):
        report = render_uniqueness_report(build_uniqueness_rows(Path.cwd()))
        self.assertIn("# Theme uniqueness report", report)
        self.assertIn("CSS similarity", report)
        self.assertIn("Average palette Delta E", report)
        self.assertIn("Matching profiles", report)
        self.assertIn("Font match", report)
        self.assertIn("Geometry match", report)
        self.assertIn("Severity", report)
        self.assertIn("Issue", report)
        self.assertIn("carbon-volt", report)
        self.assertIn("structural recolor CSS ≥ 0.98 with ≥ 5 matching profiles", report)
        self.assertIn("profile collision CSS ≥ 0.92 with ≥ 5 matching profiles", report)
        self.assertIn(
            "identity collision requires matching geometry, rhythm, typography treatment, "
            "interaction, and responsive strategy with palette Delta E < 20",
            report,
        )
        self.assertIn("CSS similarity ≥ 0.85", report)
        self.assertNotIn("Delta E < 12", report)
        self.assertNotIn("requires all seven profiles", report)

    def test_check_detects_drift_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.md"
            command = [
                sys.executable,
                "-m",
                "lib.theme_factory.uniqueness_report",
                "--repo-root",
                ".",
                "--output",
                str(output),
            ]
            self.assertEqual(subprocess.run(command, capture_output=True, text=True).returncode, 0)
            original = output.read_text(encoding="utf-8")
            output.write_text(original + "drift\n", encoding="utf-8")
            check = subprocess.run([*command, "--check"], capture_output=True, text=True)
            self.assertEqual(check.returncode, 1)
            self.assertIn("DRIFT", check.stdout + check.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), original + "drift\n")

    def test_check_reports_actual_pair_count(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.md"
            command = [
                sys.executable,
                "-m",
                "lib.theme_factory.uniqueness_report",
                "--repo-root",
                ".",
                "--output",
                str(output),
            ]
            generated = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(generated.returncode, 0)
            check = subprocess.run([*command, "--check"], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0)
            self.assertIn("THEME_UNIQUENESS_REPORT status=PASS rows=28", check.stdout)

    def test_common_offline_gate_checks_committed_report(self):
        script = (Path("tests/run-common-offline.sh")).read_text(encoding="utf-8")
        self.assertIn(
            "python3 -m lib.theme_factory.uniqueness_report "
            "--repo-root . --output docs/generated/theme-uniqueness-report.md --check",
            script,
        )


if __name__ == "__main__":
    unittest.main()
