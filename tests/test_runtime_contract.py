from pathlib import Path
import unittest


class RuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("installer/theme-factory-runtime.js").read_text(encoding="utf-8")
        cls.bootstrap_tmpl = Path("installer/templates/bootstrap.html.tmpl").read_text(encoding="utf-8")

    def test_storage_is_application_namespaced(self):
        self.assertIn("apex.themeFactory.", self.source)
        self.assertNotIn("localStorage['app.theme']", self.source)
        self.assertIn("apex.themeFactory.", self.bootstrap_tmpl)

    def test_uses_native_radio_group(self):
        self.assertIn('type: "radioGroup"', self.source)

    def test_allowlist_validation_and_iris_handling(self):
        self.assertIn('"iris"', self.source)
        self.assertIn("allowed.indexOf", self.source)

    def test_no_alpine_start(self):
        self.assertNotIn("Alpine.start", self.source)

    def test_bound_to_window_theme42ready(self):
        self.assertIn('(window)', self.source)
        self.assertIn('theme42ready.apexThemeFactory', self.source)

    def test_no_dynamic_stylesheet_insertion(self):
        self.assertNotIn("createElement('link')", self.source)
        self.assertNotIn('createElement("link")', self.source)

    def test_supports_app_theme_switcher_selector(self):
        self.assertIn(".app-theme-switcher [data-menu]", self.source)

    def test_bootstrap_byte_identical_when_features_off(self):
        from lib.theme_factory.apexlang_runtime import build_bootstrap_html
        baseline = """<!-- APEX_THEME_FACTORY_MANAGED:BOOTSTRAP -->
<script>
window.APEX_THEME_FACTORY_CONFIG = {
  appId: &APP_ID.,
  defaultTheme: "linen",
  switcherEnabled: true,
  themes: []
};
(function (doc, config) {
  "use strict";
  var root = doc.documentElement;
  var key = "apex.themeFactory." + config.appId;
  var allowed = ["iris"].concat(config.themes.map(function (theme) { return theme.name; }));
  var selected = config.defaultTheme;
  if (config.switcherEnabled) {
    try {
      selected = window.localStorage.getItem(key) || selected;
      if (allowed.indexOf(selected) === -1) {
        window.localStorage.removeItem(key);
        selected = config.defaultTheme;
      }
    } catch (e) {
      selected = config.defaultTheme;
    }
  }
  Array.prototype.slice.call(root.classList).forEach(function (name) {
    if (name.indexOf("app-theme-") === 0) { root.classList.remove(name); }
  });
  if (selected !== "iris") { root.classList.add("app-theme-" + selected); }
  root.dataset.appThemeDefault = config.defaultTheme;
  root.dataset.appThemeCurrent = selected;
}(document, window.APEX_THEME_FACTORY_CONFIG));
</script>"""
        self.assertEqual(build_bootstrap_html("linen", True, "[]"), baseline)

    def _run_bootstrap_in_node(self, html: str, storage: dict, hash_str: str = "", app_id: int = 102) -> dict:
        import json, subprocess
        start = html.find("<script>") + len("<script>")
        end = html.rfind("</script>")
        js = html[start:end].replace("&APP_ID.", str(app_id))
        runner = f"""
const storage = {json.dumps(storage)};
const classList = new Set();
const dataset = {{}};
const doc = {{
  documentElement: {{
    classList: {{
      add: (c) => classList.add(c),
      remove: (c) => classList.delete(c),
      [Symbol.iterator]: () => classList.values()
    }},
    dataset: dataset
  }}
}};
const win = {{
  location: {{ hash: {json.dumps(hash_str)} }},
  localStorage: {{
    getItem: (k) => Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : null,
    setItem: (k, v) => {{ storage[k] = String(v); }},
    removeItem: (k) => {{ delete storage[k]; }}
  }}
}};
globalThis.window = win;
globalThis.document = doc;
globalThis.localStorage = win.localStorage;
globalThis.location = win.location;
{js}
console.log(JSON.stringify({{ storage, classes: Array.from(classList), dataset }}));
"""
        res = subprocess.run(["node", "-e", runner], capture_output=True, text=True, check=True)
        return json.loads(res.stdout)

    def _use_in_node(self, name: str, storage: dict, hash_str: str = "") -> dict:
        """Load the runtime with a config (default linen), call ApexThemeFactory.use(name)."""
        import json, subprocess
        runtime = (Path(__file__).resolve().parent.parent / "installer/theme-factory-runtime.js").read_text(encoding="utf-8")
        runner = f"""
const storage = {json.dumps(storage)};
let reloaded = false, replaced = null;
globalThis.window = {{
  APEX_THEME_FACTORY_CONFIG: {{ appId: 102, defaultTheme: "linen", switcherEnabled: true,
    themes: [{{ name: "linen", title: "Linen" }}, {{ name: "cobalt-press", title: "Cobalt Press" }}] }},
  location: {{ hash: {json.dumps(hash_str)}, pathname: "/p", search: "", reload: () => {{ reloaded = true; }} }},
  history: {{ replaceState: (a, b, url) => {{ replaced = url; }} }},
  localStorage: {{
    getItem: (k) => Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : null,
    setItem: (k, v) => {{ storage[k] = String(v); }},
    removeItem: (k) => {{ delete storage[k]; }}
  }}
}};
globalThis.document = {{ documentElement: {{ dataset: {{}} }} }};
{runtime}
const result = window.ApexThemeFactory.use({json.dumps(name)});
console.log(JSON.stringify({{ result, storage, reloaded, replaced }}));
"""
        res = subprocess.run(["node", "-e", runner], capture_output=True, text=True, check=True)
        return json.loads(res.stdout)

    def test_runtime_use_stores_choices_and_forgets_the_app_default(self):
        key = "apex.themeFactory.102"
        picked = self._use_in_node("cobalt-press", {}, "#theme=linen")
        self.assertEqual((picked["result"], picked["storage"].get(key), picked["reloaded"]), (True, "cobalt-press", True))
        self.assertEqual(picked["replaced"], "/p")  # a #theme= hash would re-apply itself on reload
        # choosing the app default forgets the stored choice, so later default changes still reach the visitor
        for name in ("linen", "default"):
            chosen = self._use_in_node(name, {key: "cobalt-press"})
            self.assertTrue(chosen["result"])
            self.assertNotIn(key, chosen["storage"], name)
        refused = self._use_in_node("typo", {key: "cobalt-press"})
        self.assertEqual((refused["result"], refused["storage"][key], refused["reloaded"]), (False, "cobalt-press", False))

    def test_bootstrap_node_execution_cases(self):
        from lib.theme_factory.apexlang_runtime import build_bootstrap_html, script_json
        themes = [
            {"name": "linen", "title": "Linen", "className": "app-theme-linen"},
            {"name": "cobalt-press", "title": "Cobalt Press", "className": "app-theme-cobalt-press"},
            {"name": "solarized-dark", "title": "Solarized Dark", "className": "app-theme-solarized-dark"},
        ]
        themes_json = script_json(themes)
        html_app = build_bootstrap_html("linen", True, themes_json, hash_links=True, legacy_key="app.theme")
        html_inst = build_bootstrap_html("linen", True, themes_json, hash_links=False)

        # 1. Typo in storage
        r = self._run_bootstrap_in_node(html_app, {"apex.themeFactory.102": "typo"})
        self.assertEqual(r["dataset"]["appThemeCurrent"], "linen")
        self.assertNotIn("apex.themeFactory.102", r["storage"])

        # 2. Removed theme
        r = self._run_bootstrap_in_node(html_app, {"apex.themeFactory.102": "gone"})
        self.assertEqual(r["dataset"]["appThemeCurrent"], "linen")
        self.assertNotIn("apex.themeFactory.102", r["storage"])

        # 3. Legacy migration none -> iris
        r = self._run_bootstrap_in_node(html_app, {"app.theme": "none"})
        self.assertEqual(r["dataset"]["appThemeCurrent"], "iris")
        self.assertEqual(r["storage"].get("apex.themeFactory.102"), "iris")
        self.assertNotIn("app.theme", r["storage"])
        self.assertFalse(any(c.startswith("app-theme-") for c in r["classes"]))

        # 4. Legacy migration solarized-dark
        r = self._run_bootstrap_in_node(html_app, {"app.theme": "solarized-dark"})
        self.assertEqual(r["dataset"]["appThemeCurrent"], "solarized-dark")
        self.assertEqual(r["storage"].get("apex.themeFactory.102"), "solarized-dark")
        self.assertNotIn("app.theme", r["storage"])
        self.assertIn("app-theme-solarized-dark", r["classes"])

        # 5. Legacy migration invalid theme
        r = self._run_bootstrap_in_node(html_app, {"app.theme": "typo"})
        self.assertEqual(r["dataset"]["appThemeCurrent"], "linen")
        self.assertNotIn("app.theme", r["storage"])
        self.assertNotIn("apex.themeFactory.102", r["storage"])

        # 6. Hash link #theme=cobalt-press
        r = self._run_bootstrap_in_node(html_app, {}, "#theme=cobalt-press")
        self.assertEqual(r["dataset"]["appThemeCurrent"], "cobalt-press")
        self.assertEqual(r["storage"].get("apex.themeFactory.102"), "cobalt-press")

        # 7. Hash link #theme=none
        r = self._run_bootstrap_in_node(html_app, {}, "#theme=none")
        self.assertEqual(r["dataset"]["appThemeCurrent"], "iris")
        self.assertEqual(r["storage"].get("apex.themeFactory.102"), "iris")

        # 8. Hash link #theme=default clears choice
        r = self._run_bootstrap_in_node(html_app, {"apex.themeFactory.102": "cobalt-press"}, "#theme=default")
        self.assertEqual(r["dataset"]["appThemeCurrent"], "linen")
        self.assertNotIn("apex.themeFactory.102", r["storage"])

        # 9. Hash disabled in installer
        r = self._run_bootstrap_in_node(html_inst, {}, "#theme=cobalt-press")
        self.assertEqual(r["dataset"]["appThemeCurrent"], "linen")
        self.assertNotIn("apex.themeFactory.102", r["storage"])


if __name__ == "__main__":
    unittest.main()
