import unittest

from tools.runtime_parity import compare_evidence, report_verdict


class RuntimeParityTests(unittest.TestCase):
    def test_missing_referenced_alpine_is_fail(self):
        result = compare_evidence(
            source={"javascriptUrls": ["#APP_FILES#js/vendor/alpine.min.js"], "cssUrls": []},
            database={"javascriptUrls": ["#APP_FILES#js/vendor/alpine.min.js"], "cssUrls": []},
            browser={"loadedUrls": [], "windowAlpine": None, "consoleErrors": [], "failedRequests": []},
        )
        self.assertEqual(result["alpine"]["status"], "FAIL")
        self.assertEqual(report_verdict(result), "FAIL")

    def test_omitted_browser_is_unverified(self):
        result = compare_evidence(
            source={"appId": 102, "alias": "UT", "themeNumber": 42, "baseTheme": "ut-26.1", "style": "iris", "cssUrls": [], "javascriptUrls": []},
            database={"appId": 102, "alias": "UT", "themeNumber": 42, "baseTheme": "ut-26.1", "style": "iris", "cssUrls": [], "javascriptUrls": []},
            browser=None,
        )
        self.assertEqual(result["alpine"]["status"], "UNVERIFIED")
        self.assertEqual(report_verdict(result), "UNVERIFIED")

    def test_console_errors_cause_fail(self):
        result = compare_evidence(
            source={"cssUrls": [], "javascriptUrls": []},
            database={"cssUrls": [], "javascriptUrls": []},
            browser={"consoleErrors": ["Uncaught TypeError: cannot read property"], "failedRequests": []},
        )
        self.assertEqual(result["console"]["status"], "FAIL")
        self.assertEqual(report_verdict(result), "FAIL")

    def test_all_pass(self):
        result = compare_evidence(
            source={"appId": 102, "alias": "UT", "themeNumber": 42, "baseTheme": "ut-26.1", "style": "iris", "cssUrls": ["theme.css"], "javascriptUrls": ["alpine.js"]},
            database={"appId": 102, "alias": "UT", "themeNumber": 42, "baseTheme": "ut-26.1", "style": "iris", "cssUrls": ["theme.css"], "javascriptUrls": ["alpine.js"]},
            browser={"windowAlpine": "3.17.2", "consoleErrors": [], "failedRequests": [], "cssUrls": ["theme.css"], "javascriptUrls": ["alpine.js"]},
        )
        self.assertEqual(report_verdict(result), "PASS")
