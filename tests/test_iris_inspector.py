import contextlib
import io
import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from lib.theme_factory.cli import run_cli
from lib.theme_factory.errors import PackageError
from lib.theme_factory.iris_inspector import (
    inspect_iris,
    render_drift_report,
    render_inventory_json,
)


class IrisInspectorParserTests(unittest.TestCase):
    FIXTURES = Path(__file__).resolve().parent / "fixtures/iris-inspector"

    def setUp(self):
        self.inventory = inspect_iris(self.FIXTURES)
        self.by_token = {item.token: item for item in self.inventory.declarations}

    def test_blind_spot_fixture_classifies_required_declarations(self):
        self.assertIn("--ut-palette-primary", self.by_token)
        self.assertIn("--a-palette-primary", self.by_token)
        self.assertIn("--oj-core-text-color-primary", self.by_token)
        self.assertNotIn("--comment-fake-token", self.by_token)
        self.assertNotIn("--string-fake-token", self.by_token)

        palette = self.by_token["--ut-palette-primary"]
        self.assertTrue(palette.is_literal)
        self.assertFalse(palette.is_chain)
        self.assertEqual(palette.selector, ":root")

        nested = self.by_token["--ut-body-text-color"]
        self.assertTrue(nested.is_chain)
        self.assertIn("#161513", nested.fallback_literals)
        self.assertIn("var(--ut-palette-neutral-180", nested.raw_value)

    def test_inventory_summaries_cover_html_jet_widget_fallbacks_and_pairs(self):
        self.assertIn("--oj-core-text-color-primary", self.inventory.html_only_jet_atoms)
        self.assertIn("--a-gv-cell-text-color", self.inventory.widget_fallback_tokens)
        self.assertIn("--a-datepicker-selected-background-color", self.inventory.widget_fallback_tokens)
        self.assertIn("--a-orphan", self.inventory.unpaired_color_families)
        self.assertNotIn("--a-button", self.inventory.unpaired_color_families)
        self.assertEqual(len(self.inventory.sources), 4)
        self.assertTrue(all(len(source.sha256) == 64 for source in self.inventory.sources))

    def test_inventory_json_is_deterministic_and_sorted(self):
        first = render_inventory_json(self.inventory)
        second = render_inventory_json(inspect_iris(self.FIXTURES))
        self.assertEqual(first, second)
        document = json.loads(first)
        ordering = [
            (item["token"], item["file"], item["selector"], item["offset"])
            for item in document["declarations"]
        ]
        self.assertEqual(ordering, sorted(ordering))
        self.assertEqual(document["apexVersion"], "26.1")

    def test_drift_report_names_value_changes(self):
        declarations = list(self.inventory.declarations)
        index = next(i for i, item in enumerate(declarations) if item.token == "--ut-palette-primary")
        declarations[index] = replace(declarations[index], raw_value="#123456")
        changed = replace(self.inventory, declarations=tuple(declarations))
        report = render_drift_report(changed, self.inventory)
        self.assertIn("Value changes", report)
        self.assertIn("--ut-palette-primary", report)

    def test_independent_scan_disagreement_names_dropped_token(self):
        import lib.theme_factory.iris_inspector as module
        original = module._structured_declarations

        def dropping_parser(text, logical_file):
            return tuple(
                declaration for declaration in original(text, logical_file)
                if declaration.token != "--ut-palette-primary"
            )

        with patch.object(module, "_structured_declarations", side_effect=dropping_parser):
            with self.assertRaisesRegex(PackageError, "--ut-palette-primary"):
                inspect_iris(self.FIXTURES)


class IrisInspectorCliTests(unittest.TestCase):
    FIXTURES = Path(__file__).resolve().parent / "fixtures/iris-inspector"

    @staticmethod
    def invoke(*arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = run_cli(list(arguments))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_write_then_check_and_detect_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reference = root / "reference"
            shutil.copytree(self.FIXTURES, reference)
            inventory = root / "inventory.json"
            report = root / "report.md"
            common = (
                "--reference-root", str(reference),
                "--inventory", str(inventory),
                "--report", str(report),
            )
            written = self.invoke("inspect-iris", "--write", *common)
            self.assertEqual(written[0], 0, written)
            self.assertTrue(inventory.is_file())
            self.assertTrue(report.is_file())
            checked = self.invoke("inspect-iris", "--check", *common)
            self.assertEqual(checked[0], 0, checked)

            iris = reference / "Iris.css"
            iris.write_text(iris.read_text(encoding="utf-8").replace("#ffffff", "#fefefe", 1),
                            encoding="utf-8")
            drifted = self.invoke("inspect-iris", "--check", *common)
            self.assertEqual(drifted[0], 2)
            self.assertIn("DRIFT", drifted[1])


if __name__ == "__main__":
    unittest.main()
