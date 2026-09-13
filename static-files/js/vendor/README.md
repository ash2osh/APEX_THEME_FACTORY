# Vendor libraries (shipped to app 102 as `#APP_FILES#js/vendor/…`)

| Library | Version | File | License |
|---|---|---|---|
| Alpine.js (core, CDN build — auto-starts on `DOMContentLoaded`) | 3.17.2 | `alpine.min.js` (`alpine.js` = readable build for debugging only) | MIT, `alpine.LICENSE.md` |

Managed by `scripts/fetch-vendor.sh` (pin `ALPINE_VERSION` there). No Alpine plugins are installed —
spec §68: add one only for a documented, real requirement.

Load order (User Interface → JavaScript → File URLs): verified on page 500 that APEX emits file URLs
as plain `<script>` tags at the end of `<body>`, after `desktop_all.min.js` and `theme42.min.js`,
in list order. Because the CDN build auto-starts via `queueMicrotask(() => Alpine.start())` — i.e. right after its own
`<script>` finishes, before the next one runs — register components
**before** it starts: list `js/components/*.js` (which hook `alpine:init`) *before* `alpine.min.js`,
or list `alpine.min.js` last. Never call `Alpine.start()` yourself (spec §33).
