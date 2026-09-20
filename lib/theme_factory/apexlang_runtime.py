"""Byte-stable renderers for the Theme Factory APEX runtime fragments."""

import json
from typing import Optional

from lib.theme_factory.apexlang_parser import (
    BOOTSTRAP_REGION_IDS, MARKER_HTML, SWITCHER_ENTRY_PREFIX,
    SWITCHER_ITEM_CLASS, SWITCHER_PARENT_ID,
)


def build_bootstrap_html(default_theme: str, switcher_enabled: bool, themes_json_str: str) -> str:
    return f"""{MARKER_HTML}
<script>
window.APEX_THEME_FACTORY_CONFIG = {{
  appId: &APP_ID.,
  defaultTheme: "{default_theme}",
  switcherEnabled: {"true" if switcher_enabled else "false"},
  themes: {themes_json_str}
}};
(function (doc, config) {{
  "use strict";
  var root = doc.documentElement;
  var key = "apex.themeFactory." + config.appId;
  var allowed = ["iris"].concat(config.themes.map(function (theme) {{ return theme.name; }}));
  var selected = config.defaultTheme;
  if (config.switcherEnabled) {{
    try {{
      selected = window.localStorage.getItem(key) || selected;
      if (allowed.indexOf(selected) === -1) {{
        window.localStorage.removeItem(key);
        selected = config.defaultTheme;
      }}
    }} catch (e) {{
      selected = config.defaultTheme;
    }}
  }}
  Array.prototype.slice.call(root.classList).forEach(function (name) {{
    if (name.indexOf("app-theme-") === 0) {{ root.classList.remove(name); }}
  }});
  if (selected !== "iris") {{ root.classList.add("app-theme-" + selected); }}
  root.dataset.appThemeDefault = config.defaultTheme;
  root.dataset.appThemeCurrent = selected;
}}(document, window.APEX_THEME_FACTORY_CONFIG));
</script>"""


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line if line.strip() else line for line in text.splitlines())


def build_bootstrap_regions(default_theme: str, switcher_enabled: bool, themes: list) -> str:
    """Generate APEXLang for the two owned Page 0 bootstrap regions (standard + dialog slots)."""
    themes_data = [
        {
            "name": t["name"] if isinstance(t, dict) else t.name,
            "title": t["title"] if isinstance(t, dict) else t.title,
            "className": t["className"] if isinstance(t, dict) else t.class_name,
        }
        for t in themes
    ]
    bootstrap_html = _indent(
        build_bootstrap_html(default_theme, switcher_enabled, json.dumps(themes_data)), " " * 16
    )

    def region(identifier: str, name: str, sequence: int, slot: str) -> str:
        return f"""    region {identifier} (
        name: {name}
        type: staticContent
        source {{
            htmlCode:
                ```html
{bootstrap_html}
                ```
        }}
        layout {{
            sequence: {sequence}
            slot: {slot}
        }}
        appearance {{
            template: @/blank-with-attributes
            templateOptions: #DEFAULT#
        }}
        advanced {{
            htmlDomId: {identifier}
        }}
    )
"""

    return (
        "\n"
        + region(BOOTSTRAP_REGION_IDS[0], "Theme Factory Bootstrap", 10, "banner")
        + "\n"
        + region(BOOTSTRAP_REGION_IDS[1], "Theme Factory Bootstrap (Dialog)", 11, "breadcrumbBar")
    )


def build_switcher_entries(themes: list) -> str:
    """Generate static navigation-bar list entries in the grammar SQLcl 26.2 exports.

    The parent entry gets list attribute 2 (Universal Theme navigation bar: additional
    list item classes) so the runtime can find `.t-NavigationBar-item.theme-factory-managed-switcher`.
    """

    def entry(identifier: str, label: str, sequence: int, parent: Optional[str], extra: str = "") -> str:
        parent_line = f"\n            parentEntry: @{parent}" if parent else ""
        return (
            f"    entry {identifier} (\n"
            f"        label: {label}\n"
            f"        layout {{\n"
            f"            sequence: {sequence}{parent_line}\n"
            f"        }}\n"
            f"        link {{\n"
            f"            target: {{\n"
            f"                type: url\n"
            f"                url: #\n"
            f"            }}\n"
            f"        }}\n"
            f"{extra}"
            f"    )\n"
        )

    parent_extra = (
        "        icon {\n"
        "            imageIconCssClasses: fa-paint-brush\n"
        "        }\n"
        "        userDefinedAttributes {\n"
        f"            2: {SWITCHER_ITEM_CLASS}\n"
        "        }\n"
    )
    chunks = [entry(SWITCHER_PARENT_ID, "Theme", 9000, None, parent_extra)]
    sequence = 9010
    for package in themes:
        name = package["name"] if isinstance(package, dict) else package.name
        title = package["title"] if isinstance(package, dict) else package.title
        chunks.append(entry(f"{SWITCHER_ENTRY_PREFIX}choice-{name}", title, sequence, SWITCHER_PARENT_ID))
        sequence += 10
    chunks.append(entry(f"{SWITCHER_ENTRY_PREFIX}choice-iris", "Iris", sequence, SWITCHER_PARENT_ID))
    return "\n".join(chunks)



