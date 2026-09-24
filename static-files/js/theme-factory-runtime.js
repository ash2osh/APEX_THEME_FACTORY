/* Oracle APEX Theme Factory - Runtime Switcher and Persistence
   Bound to Universal Theme 42 (Iris). Namespaced per application. */
(function (window, document, apex) {
  "use strict";

  var config = window.APEX_THEME_FACTORY_CONFIG || {
    appId: 0,
    defaultTheme: "iris",
    switcherEnabled: false,
    themes: []
  };

  var key = "apex.themeFactory." + config.appId;
  var allowed = ["iris"].concat(config.themes.map(function (t) { return t.name; }));

  window.ApexThemeFactory = Object.freeze({
    current: function () {
      return document.documentElement.dataset.appThemeCurrent || config.defaultTheme;
    },
    choices: function () {
      var list = config.themes.map(function (theme) {
        return { label: theme.title, value: theme.name };
      });
      return list.concat([{ label: "Iris", value: "iris" }]);
    },
    use: function (name) {
      if (!config.switcherEnabled) {
        return false;
      }
      /* Choosing the app default forgets the stored choice, so the visitor follows later default changes. */
      if (name === "default" || name === config.defaultTheme) {
        try {
          window.localStorage.removeItem(key);
        } catch (e) {}
        if (/(?:^#|&)theme=/.test(window.location.hash)) {
          try {
            window.history.replaceState(null, "", window.location.pathname + window.location.search);
          } catch (e) {}
        }
        window.location.reload();
        return true;
      }
      if (allowed.indexOf(name) === -1) {
        return false;
      }
      try {
        window.localStorage.setItem(key, name);
      } catch (e) {
        /* storage may be disabled in private browsing */
      }
      if (/(?:^#|&)theme=/.test(window.location.hash)) {
        try {
          window.history.replaceState(null, "", window.location.pathname + window.location.search);
        } catch (e) {}
      }
      window.location.reload();
      return true;
    }
  });

  if (apex && apex.jQuery) {
    apex.jQuery(window)
      .off("theme42ready.apexThemeFactory")
      .on("theme42ready.apexThemeFactory", function () {
        var $ = apex.jQuery;
        var button = $(".t-NavigationBar-item.theme-factory-managed-switcher [data-menu], .t-NavigationBar-item.app-theme-switcher [data-menu]").first();
        var menu = button.length ? $("#" + button.attr("data-menu")) : $();
        if (!menu.length) {
          return;
        }
        try {
          menu.menu("option", "items", [{
            type: "radioGroup",
            get: window.ApexThemeFactory.current,
            set: window.ApexThemeFactory.use,
            choices: window.ApexThemeFactory.choices()
          }]);
        } catch (e) {
          /* menu widget not created on this page (e.g. a dialog); the plain list entries still work */
        }
      });
  }
}(window, document, window.apex));
