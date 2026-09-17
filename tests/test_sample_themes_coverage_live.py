"""Separated from tests/test_sample_themes_coverage.py because this one test runs against the
real, evolving repo rather than a fixture - the property Task 6 exists to guarantee, not a check
of the checker.

Expected RED at the point Task 6's code lands (estate-slate/estate-slate-dark have no row yet in
sample-themes/README.md); expected GREEN once their evidence and README rows are added as part of
the same session's Task 7 work. Not part of tests/run-offline.sh until it is green - a test tied to
real content that is *known* to be incomplete mid-task would otherwise gate every commit in
between, for a gap this very task is in the middle of closing (same reasoning as
tests/test_evidence_schema.py's property test during Tasks 2-6).
"""

import subprocess
import unittest


class RealRepositoryCoverageTests(unittest.TestCase):
    def test_every_sample_theme_is_verified_or_explicitly_marked_unverified(self):
        result = subprocess.run(
            ["bash", "scripts/check-sample-themes-coverage.sh"], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
