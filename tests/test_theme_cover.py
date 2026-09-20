import base64
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from lib.theme_factory.checks import CheckIssue, CheckReport
from lib.theme_factory.cli import run_cli
from lib.theme_factory.errors import PackageError
from tools.theme_cover import PAGE_500, capture_cover


def _text_result(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


def _jpeg(width: int = 960, height: int = 525) -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (width, height), "#2457ff").save(stream, format="JPEG", quality=90)
    return stream.getvalue()


class FakeClient:
    def __init__(self, *, screenshot: bytes | None = None, fail_screenshot: bool = False,
                 console: str = "No console messages found.", network: str = "No network requests found."):
        self.calls: list[tuple[str, dict]] = []
        self.screenshot = screenshot or _jpeg()
        self.fail_screenshot = fail_screenshot
        self.console = console
        self.network = network

    def call_tool(self, name: str, arguments: dict | None = None):
        arguments = arguments or {}
        self.calls.append((name, arguments))
        if name == "new_page":
            return _text_result("## Pages\n41: Theme cover (http://localhost/) [selected]")
        if name == "evaluate_script":
            return _text_result(json.dumps({
                "appId": "102", "pageId": "500", "theme": "carbon-volt",
                "fontsStatus": "loaded",
            }))
        if name == "list_console_messages":
            return _text_result(self.console)
        if name == "list_network_requests":
            return _text_result(self.network)
        if name == "take_screenshot":
            if self.fail_screenshot:
                raise RuntimeError("simulated screenshot failure")
            return {"content": [{
                "type": "image", "mimeType": "image/jpeg",
                "data": base64.b64encode(self.screenshot).decode("ascii"),
            }]}
        return _text_result("ok")


class ThemeCoverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.output = Path(self.temporary.name) / "preview/cover.jpg"
        self.client = FakeClient()

    def tearDown(self):
        self.temporary.cleanup()

    def test_capture_uses_background_tab_and_per_tab_emulation(self):
        capture_cover(self.client, "carbon-volt", self.output, apply=True, overwrite=False)
        self.assertIn(("new_page", {"url": PAGE_500, "background": True}), self.client.calls)
        self.assertTrue(any(
            name == "emulate" and args["viewport"] == "1280x700x0.75"
            for name, args in self.client.calls
        ))
        self.assertFalse(any(name == "resize_page" for name, _ in self.client.calls))
        self.assertTrue(any(name == "close_page" for name, _ in self.client.calls))

    def test_capture_never_writes_local_storage(self):
        capture_cover(self.client, "carbon-volt", self.output, apply=True, overwrite=False)
        scripts = "\n".join(
            args.get("function", "") for name, args in self.client.calls
            if name == "evaluate_script"
        )
        self.assertNotIn("localStorage", scripts)
        self.assertIn("app-theme-", scripts)
        self.assertIn("appThemeCurrent", scripts)

    def test_capture_writes_a_valid_960_pixel_jpeg(self):
        report = capture_cover(
            self.client, "carbon-volt", self.output, apply=True, overwrite=False
        )
        self.assertEqual(report.status, "CAPTURED")
        self.assertTrue(report.written)
        self.assertEqual(report.width, 960)
        self.assertEqual(self.output.read_bytes()[:2], b"\xff\xd8")
        screenshot = next(args for name, args in self.client.calls if name == "take_screenshot")
        self.assertEqual(screenshot["format"], "jpeg")
        self.assertEqual(screenshot["quality"], 90)

    def test_dry_run_never_opens_chrome_or_replaces_an_existing_file(self):
        self.output.parent.mkdir(parents=True)
        self.output.write_bytes(b"keep")
        report = capture_cover(None, "carbon-volt", self.output, apply=False, overwrite=False)
        self.assertEqual(report.status, "DRY_RUN")
        self.assertFalse(report.written)
        self.assertEqual(self.output.read_bytes(), b"keep")

    def test_existing_output_requires_overwrite_before_chrome_opens(self):
        self.output.parent.mkdir(parents=True)
        self.output.write_bytes(b"keep")
        with self.assertRaisesRegex(PackageError, "--overwrite"):
            capture_cover(self.client, "carbon-volt", self.output, apply=True, overwrite=False)
        self.assertEqual(self.client.calls, [])

        report = capture_cover(self.client, "carbon-volt", self.output, apply=True, overwrite=True)
        self.assertTrue(report.written)
        self.assertNotEqual(self.output.read_bytes(), b"keep")

    def test_screenshot_failure_closes_tab_and_leaves_no_partial_output(self):
        client = FakeClient(fail_screenshot=True)
        with self.assertRaisesRegex(RuntimeError, "simulated screenshot failure"):
            capture_cover(client, "carbon-volt", self.output, apply=True, overwrite=False)
        self.assertFalse(self.output.exists())
        self.assertTrue(any(name == "close_page" for name, _ in client.calls))

    def test_console_or_network_errors_prevent_capture(self):
        cases = (
            FakeClient(console="1: Uncaught TypeError: broken [error]"),
            FakeClient(network="12: GET /missing.css [failed] net::ERR_FAILED"),
            FakeClient(network="12: GET /missing.css [status 404]"),
        )
        for client in cases:
            with self.subTest(calls=len(client.calls)):
                with self.assertRaises(PackageError):
                    capture_cover(client, "carbon-volt", self.output, apply=True, overwrite=False)
                self.assertFalse(any(name == "take_screenshot" for name, _ in client.calls))
                self.assertTrue(any(name == "close_page" for name, _ in client.calls))

    def test_daemon_viewport_annotation_is_not_a_console_error(self):
        client = FakeClient(
            console='Emulating viewport: {"width":1280,"height":700}\n'
                    "## Console messages\n<no console messages found>"
        )
        report = capture_cover(client, "carbon-volt", self.output, apply=True, overwrite=False)
        self.assertEqual(report.status, "CAPTURED")

    def test_wrong_width_is_rejected_without_output(self):
        client = FakeClient(screenshot=_jpeg(width=959))
        with self.assertRaisesRegex(PackageError, "960"):
            capture_cover(client, "carbon-volt", self.output, apply=True, overwrite=False)
        self.assertFalse(self.output.exists())

    def test_wrong_runtime_page_is_rejected(self):
        client = FakeClient()
        original = client.call_tool

        def wrong_page(name, arguments=None):
            if name == "evaluate_script":
                client.calls.append((name, arguments or {}))
                return _text_result(json.dumps({
                    "appId": "102", "pageId": "405", "theme": "carbon-volt",
                    "fontsStatus": "loaded",
                }))
            return original(name, arguments)

        client.call_tool = wrong_page
        with self.assertRaisesRegex(PackageError, "page 500"):
            capture_cover(client, "carbon-volt", self.output, apply=True, overwrite=False)
        self.assertTrue(any(name == "close_page" for name, _ in client.calls))


class ThemeCoverCliTests(unittest.TestCase):
    @staticmethod
    def _report(status: str) -> CheckReport:
        issues = () if status == "PASS" else (
            CheckIssue("error", "BROKEN", "broken package", "theme.json", 1),
        )
        return CheckReport(status, "carbon-volt", False, 4, "a" * 64, issues)

    @staticmethod
    def _invoke(*arguments: str):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = run_cli(list(arguments))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cover_is_dry_run_by_default_and_does_not_construct_client(self):
        with tempfile.TemporaryDirectory() as temp, \
                patch("lib.theme_factory.cli.run_theme_checks", return_value=self._report("PASS")), \
                patch("tools.chrome_devtools_client.ChromeDevToolsClient",
                      side_effect=AssertionError("client must not be constructed")):
            output = Path(temp) / "cover.jpg"
            code, stdout, stderr = self._invoke(
                "cover", "carbon-volt", "--repo-root", temp, "--output", str(output)
            )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("DRY_RUN", stdout)
        self.assertIn(PAGE_500, stdout)

    def test_failed_theme_check_is_rejected_before_chrome(self):
        with tempfile.TemporaryDirectory() as temp, \
                patch("lib.theme_factory.cli.run_theme_checks", return_value=self._report("ERROR")), \
                patch("tools.chrome_devtools_client.ChromeDevToolsClient") as client:
            code, _, stderr = self._invoke(
                "cover", "carbon-volt", "--repo-root", temp,
                "--output", str(Path(temp) / "cover.jpg"), "--apply",
            )
        self.assertEqual(code, 2)
        self.assertIn("theme check", stderr)
        client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
