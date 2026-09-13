/* APEX Theme Factory — application JavaScript entry point (#APP_FILES#js/app.js).
   Alpine.js is loaded once (application-level file URL); components register on 'alpine:init'.
   Never call Alpine.start() again after region refresh (spec §33). */
window.App = window.App || {};
window.App.apex = window.App.apex || {};

/* Theme packages: all are loaded by css/app.css, scoped to html.app-theme-<name>; the page-0 "Theme"
   region applies the class before paint. This helper switches at runtime (persisted in localStorage). */
window.App.theme = {
    current: function () {
        var m = /(?:^| )app-theme-([a-z0-9-]+)/.exec(document.documentElement.className);
        return m ? m[1] : null;
    },
    /* App.theme.use('linen') — switch live; App.theme.use('default') — back to the app default */
    use: function (name) {
        if (!/^[a-z0-9-]{1,40}$/.test(name)) { throw new Error('App.theme.use: invalid theme name'); }
        try { name === 'default' ? localStorage.removeItem('app.theme') : localStorage.setItem('app.theme', name); } catch (e) {}
        location.hash = 'theme=' + name;
        location.reload();
    }
};
