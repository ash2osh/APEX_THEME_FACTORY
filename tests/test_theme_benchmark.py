import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from lib.theme_factory.errors import PackageError
from tools.theme_benchmark import (
    BenchmarkRun, load_run, main, render_report, summarize_runs,
)


class ThemeBenchmarkTests(unittest.TestCase):
    def run_record(self, *, theme="trial", tokens=45_000, scaffold=4.0,
                   check=8.0, preview=60.0, result="PASS"):
        input_tokens = None if tokens is None else tokens - 5_000
        output_tokens = None if tokens is None else 5_000
        return BenchmarkRun(
            schema_version=1,
            theme=theme,
            source_commit="a" * 40,
            recipe_sha256="b" * 64,
            started_at="2026-09-20T10:00:00Z",
            finished_at="2026-09-20T10:02:00Z",
            scaffold_seconds=scaffold,
            check_seconds=check,
            dev_seconds=preview,
            first_preview_seconds=preview,
            commands=("scripts/theme.sh new trial --recipe recipe.json",),
            files_read=("recipe.json",),
            files_written=("sample-themes/trial/theme.json",),
            validation_reruns=0,
            browser_rows=4,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            result=result,
        )

    def baseline(self, tokens=100_000):
        return self.run_record(theme="four-theme-2026-09-19", tokens=tokens,
                               scaffold=30.0, check=60.0, preview=240.0)

    def test_token_reduction_is_calculated_from_total_input_and_output(self):
        summary = summarize_runs(self.baseline(tokens=100_000), [self.run_record(tokens=45_000)])
        self.assertEqual(summary.token_reduction_percent, 55.0)
        self.assertEqual(summary.token_status, "UNVERIFIED")

    def test_success_target_requires_three_candidate_runs_with_token_usage(self):
        with self.assertRaisesRegex(PackageError, "three.*token"):
            summarize_runs(self.baseline(tokens=100_000), [self.run_record(tokens=None)])

    def test_three_runs_report_each_threshold_independently(self):
        runs = [self.run_record(theme=name, tokens=value)
                for name, value in (("light", 40_000), ("dark", 50_000), ("bilingual", 45_000))]
        summary = summarize_runs(self.baseline(), runs)
        self.assertEqual(summary.scaffold_status, "PASS")
        self.assertEqual(summary.check_status, "PASS")
        self.assertEqual(summary.preview_status, "PASS")
        self.assertEqual(summary.token_status, "PASS")
        self.assertEqual(summary.overall_status, "PASS")

    def test_invalid_identity_and_negative_measurements_fail(self):
        with self.assertRaisesRegex(PackageError, "source commit"):
            self.run_record().__class__(**{**self.run_record().__dict__, "source_commit": "HEAD"})
        with self.assertRaisesRegex(PackageError, "nonnegative"):
            self.run_record().__class__(**{**self.run_record().__dict__, "check_seconds": -1})

    def test_incomplete_report_never_claims_pass(self):
        report = render_report(self.baseline(tokens=None), [], allow_incomplete=True)
        self.assertIn("UNVERIFIED", report)
        self.assertNotIn("| Overall | PASS |", report)

    def test_record_cli_round_trips_explicit_token_totals(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "run.json"
            arguments = [
                "record", "--output", str(output), "--theme", "trial",
                "--source-commit", "a" * 40, "--recipe-sha256", "b" * 64,
                "--started-at", "2026-09-20T10:00:00Z",
                "--finished-at", "2026-09-20T10:02:00Z",
                "--scaffold-seconds", "4", "--check-seconds", "8",
                "--dev-seconds", "55", "--first-preview-seconds", "60",
                "--command", "scripts/theme.sh check trial",
                "--file-read", "recipe.json", "--file-written", "theme.json",
                "--validation-reruns", "1", "--browser-rows", "4",
                "--input-tokens", "40000", "--output-tokens", "5000",
                "--result", "PASS",
            ]
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(arguments), 0)
            loaded = load_run(output)
            self.assertEqual(loaded.total_tokens, 45_000)
            document = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(document["inputTokens"], 40_000)
            self.assertEqual(document["outputTokens"], 5_000)


if __name__ == "__main__":
    unittest.main()
