from pathlib import Path
import tempfile
import unittest

from lib.theme_factory.cache import CacheKey, load_cached_report, store_cached_report
from lib.theme_factory.checks import CheckIssue, CheckReport


class ThemeCacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.cache = Path(self.temporary.name)
        self.report = CheckReport(
            status="PASS",
            theme="fixture",
            cache_hit=False,
            duration_ms=12,
            input_digest="abc",
            issues=(CheckIssue("warning", "EXAMPLE", "Example warning", "theme.json", 1),),
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_round_trip_preserves_report_and_marks_cache_hit(self):
        key = CacheKey("check-v1", "abc")
        store_cached_report(self.cache, key, self.report)
        loaded = load_cached_report(self.cache, key)
        self.assertIsNotNone(loaded)
        self.assertTrue(loaded.cache_hit)
        self.assertEqual(loaded.theme, "fixture")
        self.assertEqual(loaded.issues, self.report.issues)

    def test_validator_version_change_is_a_cache_miss(self):
        store_cached_report(self.cache, CacheKey("check-v1", "abc"), self.report)
        self.assertIsNone(load_cached_report(self.cache, CacheKey("check-v2", "abc")))

    def test_corrupt_cache_entry_is_a_miss(self):
        key = CacheKey("check-v1", "abc")
        store_cached_report(self.cache, key, self.report)
        next(self.cache.glob("*.json")).write_text("not json", encoding="utf-8")
        self.assertIsNone(load_cached_report(self.cache, key))


if __name__ == "__main__":
    unittest.main()
