/* APEX Theme Factory — application JavaScript entry point (#APP_FILES#js/app.js).
   Alpine.js is loaded once (application-level file URL); components register on 'alpine:init'.
   Never call Alpine.start() again after region refresh (spec §33). */
window.App = window.App || {};
window.App.apex = window.App.apex || {};

/* Theme packages: all are loaded by css/app.css, scoped to html.app-theme-<name>; the page-0 "Theme"
   regions apply the class before paint and expose the app default as html[data-app-theme-default].
   The choice is per browser (localStorage 'app.theme'); 'none' = bare Iris. */
window.App.theme = {
    STORAGE_KEY: 'app.theme',
    current: function () {
        var m = /(?:^| )app-theme-([a-z0-9-]+)/.exec(document.documentElement.className);
        return m ? m[1] : null;
    },
    appDefault: function () {
        return document.documentElement.getAttribute('data-app-theme-default') || null;
    },
    /* App.theme.use('linen') — switch live. Choosing the app default (or 'default') clears the stored
       choice so the visitor follows future default changes; any #theme= hash is dropped first because
       page 0 would otherwise re-apply it on reload. */
    use: function (name) {
        if (!/^[a-z0-9-]{1,40}$/.test(name)) { throw new Error('App.theme.use: invalid theme name'); }
        var isDefault = name === 'default' || name === this.appDefault();
        try { isDefault ? localStorage.removeItem(this.STORAGE_KEY) : localStorage.setItem(this.STORAGE_KEY, name); } catch (e) {}
        if (/(?:^#|&)theme=/.test(location.hash)) { history.replaceState(null, '', location.pathname + location.search); }
        location.reload();
    }
};

/* Navigation-bar "Theme" menu (list navigation-bar, li class app-theme-switcher): the list renders one
   plain entry per theme package found in the app's static files; once Universal Theme has built the
   popup menu we rebuild it as a single radio group so the active theme is announced and checked
   (role=menuitemradio / aria-checked). Runs once per page; theme42ready fires on window after all
   .t-NavigationBar-menu widgets exist. Without this enhancement the plain entries still switch. */
apex.jQuery(window).on('theme42ready', function () {
    var $ = apex.jQuery,
        button = $('.t-NavigationBar-item.app-theme-switcher [data-menu]').first(),
        menu = button.length ? $('#' + button.attr('data-menu')) : $(),
        items, choices = [], pattern = /App\.theme\.use\('([a-z0-9-]+)'\)/;
    if (!menu.length) { return; }                                          /* no navigation bar on this page (dialogs) */
    try { items = menu.menu('option', 'items'); } catch (e) { return; }   /* menu widget not created */
    if (!Array.isArray(items)) { return; }
    items.forEach(function (item) {
        var m = item.href && pattern.exec(item.href);
        if (m) { choices.push({ label: item.label, value: m[1] }); }
    });
    if (!choices.length) { return; }
    menu.menu('option', 'items', [{
        type: 'radioGroup',
        get: function () { return App.theme.current() || 'none'; },
        set: function (value) { App.theme.use(value); },
        choices: choices
    }]);
});

/* Themes gallery (page 405, Cards region #theme_packages_cards): the cards carry app-theme-card--<name>;
   mark the active one so its "Current" badge shows (static-files/css/pages/themes.css). Cards render after
   page load and again on every data page / refresh, so hook the widget's page-change event (it bubbles). */
apex.jQuery(document).on('tablemodelviewpagechange', '#theme_packages_cards', function (event) {
    var current = App.theme.current() || 'none';
    event.currentTarget.querySelectorAll('.app-theme-card--' + current).forEach(function (card) {
        card.classList.add('is-current');
    });
});
