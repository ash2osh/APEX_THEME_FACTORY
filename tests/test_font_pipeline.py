import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import subprocess

from lib.theme_factory.cli import main
from lib.theme_factory.errors import PackageError
from lib.theme_factory.font_pipeline import (
    FontInstallResult,
    FontRequest,
    InstalledFace,
    _create_isolated_venv,
    inspect_metadata,
    install_font,
)
from lib.theme_factory.manifest import load_manifest
from lib.theme_factory.recipe import load_recipe
from lib.theme_factory.scaffold import create_theme


class FakeFontRunner:
    def __init__(self, metadata: bytes, license_text: bytes):
        self.metadata = metadata
        self.license_text = license_text
        self.output_cmap = set(range(0x20, 0x7F)) | {0x0627}
        self.fetches = []
        self.conversions = []

    def fetch(self, url: str) -> bytes:
        self.fetches.append(url)
        if url.endswith("METADATA.pb"):
            return self.metadata
        if url.endswith("OFL.txt"):
            return self.license_text
        return b"fixture variable font"

    def convert(self, source_fonts, outputs, requirements):
        self.conversions.append((dict(source_fonts), dict(outputs), requirements))
        coverage = {}
        for weight, output in outputs.items():
            output.write_bytes(b"wOF2" + str(weight).encode("ascii"))
            coverage[weight] = set(self.output_cmap)
        return coverage


class FontPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_repo = Path(__file__).resolve().parent.parent
        fixtures = cls.real_repo / "tests/fixtures/fonts"
        cls.metadata_text = (fixtures / "metadata.pb").read_text(encoding="utf-8")
        cls.metadata_bytes = cls.metadata_text.encode("utf-8")
        cls.license_bytes = (fixtures / "OFL.txt").read_bytes()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name) / "repo"
        shutil.copytree(self.real_repo / "theme-templates", self.repo / "theme-templates")
        shutil.copytree(self.real_repo / "tools", self.repo / "tools")
        (self.repo / "sample-themes").mkdir()
        raw = json.loads(
            (self.real_repo / "tests/fixtures/recipes/valid-dark.json").read_text(encoding="utf-8")
        )
        raw["identity"]["name"] = "fixture-theme"
        raw["typography"]["bodyFamily"] = "Fixture Arabic"
        recipe_root = self.repo / "recipes/fixture-theme"
        recipe_root.mkdir(parents=True)
        recipe_path = recipe_root / "theme.recipe.json"
        recipe_path.write_text(json.dumps(raw), encoding="utf-8")
        self.theme = create_theme(self.repo, load_recipe(recipe_path)).created
        self.runner = FakeFontRunner(self.metadata_bytes, self.license_bytes)

    def tearDown(self):
        self.temporary.cleanup()

    def request(self, **overrides):
        values = {
            "family": "Fixture Arabic",
            "metadata_url": "https://github.com/example/fonts/blob/main/ofl/fixturearabic/METADATA.pb",
            "source_revision": "0123456789abcdef0123456789abcdef01234567",
            "weights": (400, 500, 600, 700),
        }
        values.update(overrides)
        return FontRequest(**values)

    def test_inspect_metadata_extracts_required_official_fields(self):
        metadata = inspect_metadata(self.metadata_text)
        self.assertEqual(metadata.family, "Fixture Arabic")
        self.assertEqual(metadata.license, "OFL")
        self.assertEqual(metadata.repository_url, "https://github.com/upstream/fixture-arabic")
        self.assertEqual(metadata.source_commit, "fedcba9876543210fedcba9876543210fedcba98")
        self.assertEqual(metadata.filenames, ("FixtureArabic[wght].ttf",))
        self.assertEqual((metadata.weight_min, metadata.weight_max), (300, 800))
        self.assertEqual(metadata.subsets, ("arabic", "latin"))

    def test_static_family_metadata_is_supported_without_a_wght_axis(self):
        static_metadata = self.metadata_text.replace(
            'fonts {\n  name: "Fixture Arabic"\n  style: "normal"\n  weight: 400\n  filename: "FixtureArabic[wght].ttf"\n}',
            'fonts {\n  name: "Fixture Arabic"\n  style: "normal"\n  weight: 400\n  filename: "FixtureArabic-Regular.ttf"\n}\n'
            'fonts {\n  name: "Fixture Arabic"\n  style: "normal"\n  weight: 700\n  filename: "FixtureArabic-Bold.ttf"\n}',
        )
        static_metadata = static_metadata.replace(
            'axes {\n  tag: "wght"\n  min_value: 300.0\n  max_value: 800.0\n}\n',
            "",
        )
        runner = FakeFontRunner(static_metadata.encode("utf-8"), self.license_bytes)

        result = install_font(
            self.repo,
            self.theme,
            self.request(weights=(400, 700)),
            runner=runner,
        )

        self.assertEqual([face.weight for face in result.faces], [400, 700])
        self.assertIn("FixtureArabic-Regular.ttf", result.source_filename)
        self.assertIn("FixtureArabic-Bold.ttf", result.source_filename)

    def test_source_revision_is_required(self):
        with self.assertRaisesRegex(PackageError, "source revision"):
            self.request(source_revision="")

    def test_uv_seeded_venv_is_the_fallback_when_ensurepip_is_missing(self):
        failed = subprocess.CompletedProcess(["python", "-m", "venv"], 1, b"", b"ensurepip unavailable")
        passed = subprocess.CompletedProcess(["uv", "venv"], 0, b"", b"")
        environment = self.repo / "isolated-venv"
        calls = []

        def fake_run(arguments, **kwargs):
            calls.append(arguments)
            if len(calls) == 1:
                environment.mkdir(parents=True)
                (environment / "partial").write_text("failed", encoding="utf-8")
                return failed
            self.assertFalse(environment.exists())
            return passed

        with patch("lib.theme_factory.font_pipeline.USE_MANAGED_TOOL_PYTHON", False), patch(
            "lib.theme_factory.font_pipeline.subprocess.run", side_effect=fake_run
        ) as run, patch(
            "lib.theme_factory.font_pipeline.shutil.which", return_value="/usr/bin/uv"
        ):
            _create_isolated_venv(environment)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[1].args[0][:3], ["/usr/bin/uv", "venv", "--seed"])

    def test_python_314_uses_a_managed_wheel_compatible_runtime(self):
        environment = self.repo / "isolated-venv"
        passed = subprocess.CompletedProcess(["uv", "venv"], 0, b"", b"")
        with patch("lib.theme_factory.font_pipeline.USE_MANAGED_TOOL_PYTHON", True), patch(
            "lib.theme_factory.font_pipeline.subprocess.run", return_value=passed
        ) as run, patch("lib.theme_factory.font_pipeline.shutil.which", return_value="/usr/bin/uv"):
            _create_isolated_venv(environment)
        arguments = run.call_args.args[0]
        self.assertIn("3.12", arguments)
        self.assertNotIn("/usr/bin/python3", arguments)

    def test_unsupported_weight_fails_before_writing_assets(self):
        request = self.request(weights=(400, 450, 700))
        with self.assertRaisesRegex(PackageError, "450.*not supported"):
            install_font(self.repo, self.theme, request, runner=self.runner)
        self.assertFalse((self.theme / "fonts").exists())
        self.assertFalse((self.theme / ".font-staging").exists())

    def test_missing_arabic_coverage_removes_staging_directory(self):
        self.runner.output_cmap = set(range(0x20, 0x7F))
        with self.assertRaisesRegex(PackageError, "Arabic"):
            install_font(self.repo, self.theme, self.request(), runner=self.runner)
        self.assertFalse((self.theme / ".font-staging").exists())
        self.assertFalse((self.theme / "fonts").exists())

    def test_missing_basic_latin_coverage_is_rejected(self):
        self.runner.output_cmap = {ord("A"), 0x0627}
        with self.assertRaisesRegex(PackageError, "Basic Latin"):
            install_font(self.repo, self.theme, self.request(), runner=self.runner)
        self.assertFalse((self.theme / "fonts").exists())

    def test_dry_run_resolves_source_without_writing_theme(self):
        before = {path.relative_to(self.theme): path.read_bytes() for path in self.theme.rglob("*") if path.is_file()}
        result = install_font(self.repo, self.theme, self.request(), runner=self.runner, dry_run=True)
        after = {path.relative_to(self.theme): path.read_bytes() for path in self.theme.rglob("*") if path.is_file()}
        self.assertTrue(result.dry_run)
        self.assertEqual(before, after)
        self.assertEqual(self.runner.conversions, [])
        self.assertFalse((self.repo / ".theme-factory").exists())

    def test_installs_four_faces_manifest_recipe_license_and_provenance(self):
        result = install_font(self.repo, self.theme, self.request(), runner=self.runner)

        self.assertFalse(result.dry_run)
        self.assertEqual([face.weight for face in result.faces], [400, 500, 600, 700])
        self.assertFalse((self.theme / ".font-staging").exists())
        self.assertEqual(len(list((self.theme / "fonts").glob("*.woff2"))), 4)
        self.assertEqual(list((self.theme / "fonts").glob("*.ttf")), [])
        manifest = load_manifest(self.theme / "theme.json", self.theme)
        self.assertEqual(manifest.fonts["body"].family, "Fixture Arabic")
        self.assertEqual([face.weight for face in manifest.fonts["body"].faces], [400, 500, 600, 700])
        recipe = load_recipe(self.theme / "theme.recipe.json")
        self.assertIsNotNone(recipe.font_provenance)
        self.assertEqual(recipe.font_provenance.source_revision, self.request().source_revision)
        readme = (self.theme / "README.md").read_text(encoding="utf-8")
        self.assertIn("fonttools 4.60.1", readme)
        self.assertIn("brotli 1.1.0", readme)
        self.assertIn(self.request().source_revision, readme)
        self.assertEqual((self.theme / "licenses/OFL.txt").read_bytes(), self.license_bytes)

    def test_family_mismatch_fails_closed(self):
        with self.assertRaisesRegex(PackageError, "family.*does not match"):
            install_font(
                self.repo,
                self.theme,
                self.request(family="Another Family"),
                runner=self.runner,
            )

    def test_cli_machine_mode_returns_faces(self):
        result = FontInstallResult(
            family="Fixture Arabic",
            source_filename="FixtureArabic[wght].ttf",
            faces=(InstalledFace("fonts/fixture-arabic-400.woff2", 400, "a" * 64),),
            dry_run=False,
        )
        args = [
            "font", "add", "fixture-theme", "--repo-root", str(self.repo),
            "--family", "Fixture Arabic", "--metadata-url", self.request().metadata_url,
            "--source-revision", self.request().source_revision, "--weights", "400", "--json",
        ]
        output = io.StringIO()
        with patch("lib.theme_factory.font_pipeline.install_font", return_value=result), contextlib.redirect_stdout(output):
            main(args)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["faces"][0]["weight"], 400)


if __name__ == "__main__":
    unittest.main()
