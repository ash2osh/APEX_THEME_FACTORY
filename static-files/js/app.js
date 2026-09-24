/* APEX Theme Factory — application JavaScript entry point (#APP_FILES#js/app.js).
   Alpine.js is loaded once (application-level file URL); components register on 'alpine:init'.
   Never call Alpine.start() again after region refresh (spec §33). */
window.App = window.App || {};
window.App.apex = window.App.apex || {};

/* Theme packages: delegate to ApexThemeFactory (theme-factory-runtime.js).
   App.theme is retained for compatibility with navigation list entries (lists.apx) and page 405. */
window.App.theme = {
    current: function () {
        if (window.ApexThemeFactory) {
            var cur = window.ApexThemeFactory.current();
            return cur === "iris" ? null : cur;
        }
        var m = /(?:^| )app-theme-([a-z0-9-]+)/.exec(document.documentElement.className);
        return m ? m[1] : null;
    },
    appDefault: function () {
        return document.documentElement.dataset.appThemeDefault || null;
    },
    use: function (name) {
        var target = name === "none" ? "iris" : name;
        if (window.ApexThemeFactory) {
            return window.ApexThemeFactory.use(target);
        }
        return false;
    }
};

/* Themes gallery (page 405, Cards region #theme_packages_cards): the cards carry app-theme-card--<name>;
   mark the active one so its "Current" badge shows (static-files/css/pages/themes.css). Cards render after
   page load and again on every data page / refresh, so hook the widget's page-change event (it bubbles). */
apex.jQuery(document).on('tablemodelviewpagechange', '#theme_packages_cards', function (event) {
    var current = App.theme.current() || 'none';
    event.currentTarget.querySelectorAll('.app-theme-card--' + current).forEach(function (card) {
        card.classList.add('is-current');
    });
});
