"""Install gates accept APEX 26.1.x and 26.2.x and refuse everything else."""

import unittest

from lib.theme_factory.install import PackageError, require_supported_apex_version
from lib.theme_factory.manifest import APEX_COMPATIBILITY, SUPPORTED_BASE_THEMES


class ApexVersionGateTests(unittest.TestCase):
    def test_accepts_apex_26_1_and_26_2_releases(self):
        for version in ("26.1.0", "26.1.5", "26.2.0", "26.2.1", "26.2"):
            with self.subTest(version=version):
                require_supported_apex_version(version)

    def test_refuses_other_releases(self):
        for version in ("25.2.0", "26.3.0", "26.10.0", "27.1.0", ""):
            with self.subTest(version=version):
                with self.assertRaises(PackageError) as caught:
                    require_supported_apex_version(version)
                self.assertEqual(caught.exception.exit_code, 3)
                self.assertIn("26.1.x or 26.2.x", str(caught.exception))

    def test_compatibility_range_covers_both_releases(self):
        self.assertEqual(APEX_COMPATIBILITY, ">=26.1.0 <26.3.0")

    def test_base_themes_match_the_two_releases(self):
        self.assertEqual(SUPPORTED_BASE_THEMES, ("ut-26.1", "ut-26.2"))


if __name__ == "__main__":
    unittest.main()
