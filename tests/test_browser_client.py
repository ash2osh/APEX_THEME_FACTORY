"""Firefox translation and backend settings, tested against a recording fake daemon (no browser needed)."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.browser_client import FirefoxTranslator, selected_browser
from tools.browser_mcp_daemon import CHROME, FIREFOX, BACKENDS, default_socket_path, FIREFOX_TOOLS


def _text(result):
    return "".join(part.get("text", "") for part in result.get("content", []))


class FakeClient:
    """Records every raw daemon call and answers with canned Firefox DevTools MCP text."""

    backend = FIREFOX

    def __init__(self, replies=None):
        self.calls = []
        self.replies = replies or {}

    def send(self, name, arguments=None):
        self.calls.append((name, dict(arguments or {})))
        reply = self.replies.get(name, "")
        if callable(reply):
            reply = reply(arguments or {})
        return {"content": [{"type": "text", "text": reply}]}


PAGES = "2 pages (selected: 0)\n> [0] Estate Slate (https://ords/app/102)\n  [1] Theme Lab (http://localhost:8181/406)"


class FirefoxTranslationTests(unittest.TestCase):
    def test_list_pages_is_reshaped_like_the_chrome_listing(self):
        client = FakeClient({"list_pages": PAGES})
        text = _text(FirefoxTranslator(client).call("list_pages", {}))
        self.assertEqual(text.splitlines(), [
            "0: Estate Slate (https://ords/app/102) [selected]",
            "1: Theme Lab (http://localhost:8181/406)",
        ])

    def test_new_page_in_background_keeps_the_previous_tab_selected_afterwards(self):
        client = FakeClient({
            "list_pages": PAGES,
            "new_page": "new page [2] → http://localhost:8181/ords/x",
            "close_page": "closed [2]",
            "select_page": "selected",
        })
        translator = FirefoxTranslator(client)
        opened = _text(translator.call("new_page", {"url": "http://localhost:8181/ords/x", "background": True}))
        self.assertEqual(opened, "2: http://localhost:8181/ords/x [selected]")
        translator.call("close_page", {"pageId": 2})
        self.assertIn(("select_page", {"pageIdx": 0}), client.calls)
        self.assertEqual(client.calls[-2][0], "close_page")

    def test_page_scoped_calls_select_their_page_first(self):
        client = FakeClient({"navigate_page": "→ url", "select_page": "ok"})
        FirefoxTranslator(client).call("navigate_page", {"pageId": 1, "url": "http://x/home"})
        self.assertEqual(client.calls, [("select_page", {"pageIdx": 1}), ("navigate_page", {"url": "http://x/home"})])

    def test_console_types_become_a_level_filter(self):
        client = FakeClient({"select_page": "ok", "list_console_messages": ""})
        FirefoxTranslator(client).call("list_console_messages", {"pageId": 1, "types": ["error"]})
        self.assertEqual(client.calls[-1], ("list_console_messages", {"level": "error"}))

    def test_network_check_asks_only_for_failed_responses(self):
        client = FakeClient({"select_page": "ok", "list_network_requests": ""})
        FirefoxTranslator(client).call("list_network_requests", {"pageId": 2})
        self.assertEqual(client.calls[-1], ("list_network_requests", {"statusMin": 400, "limit": 200}))

    def test_network_check_can_be_scoped_to_the_tested_app(self):
        client = FakeClient({"select_page": "ok", "list_network_requests": ""})
        FirefoxTranslator(client).call("list_network_requests", {"pageId": 2, "urlContains": "localhost:8182"})
        self.assertEqual(client.calls[-1], ("list_network_requests", {"statusMin": 400, "limit": 200, "urlContains": "localhost:8182"}))

    def test_viewport_string_becomes_a_viewport_size(self):
        client = FakeClient({"select_page": "ok", "set_viewport_size": "1440x900"})
        FirefoxTranslator(client).call("emulate", {"pageId": 1, "viewport": "1440x900x1"})
        self.assertEqual(client.calls[-1], ("set_viewport_size", {"width": 1440, "height": 900}))

    def test_script_results_pass_through_unchanged(self):
        reply = 'Script ran on page and returned:\n```json\n{"ok": true}\n```'
        client = FakeClient({"select_page": "ok", "evaluate_script": reply})
        result = FirefoxTranslator(client).call("evaluate_script", {"pageId": 1, "function": "() => 1"})
        self.assertEqual(_text(result), reply)
        self.assertEqual(client.calls[-1], ("evaluate_script", {"function": "() => 1"}))

    def test_native_firefox_names_pass_through_when_allowed(self):
        client = FakeClient({"get_page_text": "text"})
        FirefoxTranslator(client).call("get_page_text", {})
        self.assertEqual(client.calls, [("get_page_text", {})])

    def test_mcp_errors_are_raised_not_read_as_empty_answers(self):
        client = FakeClient({"list_pages": lambda args: ""})
        client.send = lambda name, arguments=None: {"content": [{"type": "text", "text": "Error: No Marionette listener"}], "isError": True}
        with self.assertRaises(RuntimeError) as caught:
            FirefoxTranslator(client).call("list_pages", {})
        self.assertIn("No Marionette listener", str(caught.exception))

    def test_tools_outside_the_allowlist_are_refused(self):
        with self.assertRaises(ValueError):
            FirefoxTranslator(FakeClient()).call("install_extension", {})


class BackendSettingsTests(unittest.TestCase):
    def test_firefox_attaches_to_an_existing_browser_with_the_pinned_package(self):
        self.assertIn("@mozilla/firefox-devtools-mcp@0.10.6", FIREFOX.command)
        self.assertIn("--connect-existing", FIREFOX.command)
        self.assertEqual(FIREFOX.command[FIREFOX.command.index("--marionette-port") + 1], "2828")

    def test_firefox_tools_exclude_installation_and_profiler_tools(self):
        for name in ("install_extension", "uninstall_extension", "profiler_start", "print_page", "close_firefox_session"):
            self.assertNotIn(name, FIREFOX_TOOLS)
        for name in ("evaluate_script", "list_console_messages", "list_network_requests", "set_viewport_size"):
            self.assertIn(name, FIREFOX_TOOLS)

    def test_firefox_socket_lives_in_its_own_state_folder(self):
        with patch.dict(os.environ, {"XDG_RUNTIME_DIR": "/tmp/xdg-test"}, clear=False):
            os.environ.pop("THEME_FACTORY_FIREFOX_MCP_SOCKET", None)
            self.assertEqual(default_socket_path(FIREFOX), Path("/tmp/xdg-test/firefox-mcp/firefox-mcp.sock"))
            self.assertEqual(default_socket_path(CHROME), Path("/tmp/xdg-test/chrome-mcp/chrome-mcp.sock"))

    def test_socket_override_is_per_browser(self):
        with patch.dict(os.environ, {"THEME_FACTORY_FIREFOX_MCP_SOCKET": "127.0.0.1:9999"}):
            self.assertEqual(default_socket_path(FIREFOX), "127.0.0.1:9999")
            self.assertNotEqual(default_socket_path(CHROME), "127.0.0.1:9999")

    def test_firefox_is_the_default_browser(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIs(selected_browser(), FIREFOX)
        with patch.dict(os.environ, {"THEME_FACTORY_BROWSER": "chrome"}):
            self.assertIs(selected_browser(), CHROME)
        with self.assertRaises(ValueError):
            selected_browser("safari")
        self.assertEqual(set(BACKENDS), {"chrome", "firefox"})


if __name__ == "__main__":
    unittest.main()
