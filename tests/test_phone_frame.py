"""Tests for the phone-width frame used by the page audit and the release check (tools/phone_frame.py)."""

import unittest

from tools import phone_frame


class PhoneFrameTests(unittest.TestCase):
    """Phone widths are measured in a same-origin iframe; resizing the Firefox window cannot reach 375 px."""

    def test_open_script_sizes_the_frame_to_the_requested_width(self):
        script = phone_frame.phone_open_js(375)
        self.assertIn("width:375px", script)
        self.assertIn(f"frame.id = '{phone_frame.PHONE_FRAME_ID}'", script)

    def test_open_script_measures_the_frame_not_the_window(self):
        script = phone_frame.phone_open_js(375)
        self.assertIn("frame.contentDocument", script)
        self.assertIn("frame.contentWindow", script)

    def test_open_script_reports_the_theme_the_frame_loaded_with(self):
        self.assertIn("app-theme-", phone_frame.phone_open_js(375))

    def test_close_script_removes_the_frame_and_restores_the_page(self):
        self.assertIn(phone_frame.PHONE_FRAME_ID, phone_frame.PHONE_CLOSE_JS)
        self.assertIn("visibility = ''", phone_frame.PHONE_CLOSE_JS)

    def test_checks_run_inside_the_frame_realm(self):
        script = phone_frame.phone_run_js("async () => 1")
        self.assertIn("frame.contentWindow.eval", script)
        self.assertIn(phone_frame.PHONE_FRAME_ID, script)

    def test_desktop_threshold_separates_window_widths_from_phone_widths(self):
        self.assertLess(375, phone_frame.DESKTOP_MIN_WIDTH)
        self.assertGreaterEqual(1440, phone_frame.DESKTOP_MIN_WIDTH)


if __name__ == "__main__":
    unittest.main()
