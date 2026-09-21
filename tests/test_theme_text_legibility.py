"""Source-level guardrails for the theme text legibility review."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
THEMES = (
    "carbon-volt",
    "citrus-pop",
    "cobalt-press",
    "estate-slate",
    "estate-slate-dark",
    "linen",
    "solarized-dark",
    "velvet-signal",
)


class ThemeTextLegibilityTests(unittest.TestCase):
    def css(self, theme: str, name: str) -> str:
        return (ROOT / "sample-themes" / theme / "css" / "apex" / name).read_text(encoding="utf-8")

    def test_header_controls_do_not_use_muted_text_as_the_resting_label(self):
        """Header controls are primary navigation, not tertiary metadata."""
        for theme in THEMES:
            css = self.css(theme, "shell.css")
            match = re.search(
                r"\.t-Header \.t-Button--header\s*\{(?P<body>.*?)\}",
                css,
                re.DOTALL,
            )
            self.assertIsNotNone(match, theme)
            body = match.group("body")
            self.assertNotRegex(body, r"--a-button-text-color:\s*var\(--app-text-(?:secondary|chrome-muted)\)", theme)
            self.assertRegex(
                body,
                r"--a-button-text-color:\s*var\(--app-text-(?:emphasized|primary|chrome)\)",
                theme,
            )

    def test_calendar_demo_event_classes_define_a_theme_aware_contrast_pair(self):
        """FullCalendar's custom demo classes must not inherit white-on-vivid fills."""
        for theme in THEMES:
            css = self.css(theme, "misc.css")
            for event in ("green", "blue", "yellow"):
                self.assertIn(f".fc-event.apex-cal-{event}", css, theme)
            self.assertIn("--fc-event-text-color", css, theme)
            self.assertRegex(css, r"\.apex-cal-(?:green|blue|yellow)[\s\S]*?background-color:\s*var\(--app-color-", theme)

    def test_light_theme_code_examples_override_the_page_literal_value(self):
        """The shared p6303/p6304 inline demo color needs a stronger theme-scoped token."""
        for theme in ("citrus-pop", "cobalt-press", "estate-slate", "linen"):
            css = self.css(theme, "misc.css")
            for selector in ("class-value", "class-var"):
                self.assertRegex(
                    css,
                    rf"\.{selector}[\s\S]*?color:\s*var\(--app-text-(?:emphasized|primary)\)",
                    f"{theme}: .{selector}",
                )

    def test_popup_menu_labels_use_clear_text_roles(self):
        """Popup and menu-bar labels must not fall back to a muted Iris text tier."""
        for theme in THEMES:
            css = self.css(theme, "dialogs.css")
            match = re.search(
                r"\.apex-theme-iris\s*\{(?P<body>.*?)\}",
                css,
                re.DOTALL,
            )
            self.assertIsNotNone(match, theme)
            body = match.group("body")
            for token in (
                "--a-menu-text-color",
                "--a-menu-default-text-color",
                "--a-menu-focused-text-color",
                "--a-menu-focused-accel-text-color",
            ):
                self.assertRegex(
                    body,
                    rf"{re.escape(token)}:\s*var\(--app-text-emphasized\)",
                    f"{theme}: {token}",
                )
            for token in (
                "--a-menu-accel-text-color",
                "--a-menu-default-accel-text-color",
            ):
                self.assertRegex(
                    body,
                    rf"{re.escape(token)}:\s*var\(--app-text-primary\)",
                    f"{theme}: {token}",
                )
            self.assertRegex(
                body,
                r"--a-menu-font-weight:\s*var\(--app-font-weight-medium\)",
                theme,
            )


if __name__ == "__main__":
    unittest.main()
