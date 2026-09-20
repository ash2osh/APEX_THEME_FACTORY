import tempfile
import unittest
from pathlib import Path

from PIL import Image

from lib.theme_factory.errors import PackageError
from tools.theme_visual_diff import compare_images


class ThemeVisualDiffTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.baseline = self.root / "baseline.png"
        self.candidate = self.root / "candidate.png"
        self.heatmaps = self.root / "scratch/theme-diffs"

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def _write(path: Path, size=(10, 10), pixels=None) -> None:
        image = Image.new("RGBA", size, (0, 0, 0, 255))
        for xy, color in pixels or ():
            image.putpixel(xy, color)
        image.save(path)

    def test_identical_images_report_zero_without_approval_language(self):
        self._write(self.baseline)
        self._write(self.candidate)
        report = compare_images(self.baseline, self.candidate, heatmap_root=self.heatmaps)
        self.assertEqual(report.changed_pixel_percentage, 0.0)
        self.assertEqual(report.mean_absolute_channel_delta, 0.0)
        self.assertEqual(report.status, "NO_REVIEW")
        self.assertNotIn("APPRO", report.status)
        self.assertTrue(report.heatmap_path.is_file())

    def test_more_than_two_percent_changed_is_review(self):
        white = (255, 255, 255, 255)
        self._write(self.baseline)
        self._write(self.candidate, pixels=[((0, 0), white), ((1, 0), white), ((2, 0), white)])
        report = compare_images(self.baseline, self.candidate, heatmap_root=self.heatmaps)
        self.assertAlmostEqual(report.changed_pixel_percentage, 3.0)
        self.assertAlmostEqual(report.mean_absolute_channel_delta, 5.7375)
        self.assertEqual(report.status, "REVIEW")

    def test_exactly_two_percent_does_not_trigger_review(self):
        white = (255, 255, 255, 255)
        self._write(self.baseline)
        self._write(self.candidate, pixels=[((0, 0), white), ((1, 0), white)])
        report = compare_images(self.baseline, self.candidate, heatmap_root=self.heatmaps)
        self.assertEqual(report.changed_pixel_percentage, 2.0)
        self.assertEqual(report.status, "NO_REVIEW")

    def test_dimension_mismatch_is_an_error(self):
        self._write(self.baseline, size=(10, 10))
        self._write(self.candidate, size=(11, 10))
        with self.assertRaisesRegex(PackageError, "dimensions"):
            compare_images(self.baseline, self.candidate, heatmap_root=self.heatmaps)

    def test_heatmap_name_is_deterministic(self):
        self._write(self.baseline)
        self._write(self.candidate)
        first = compare_images(self.baseline, self.candidate, heatmap_root=self.heatmaps)
        second = compare_images(self.baseline, self.candidate, heatmap_root=self.heatmaps)
        self.assertEqual(first.heatmap_path, second.heatmap_path)


if __name__ == "__main__":
    unittest.main()
