# Notices

The MIT licence in [LICENSE](LICENSE) covers the original work in this repository: the theme packages in
`sample-themes/`, `static-files/`, the tooling in `lib/`, `scripts/`, `tools/`, `installer/` and `tests/`, and the
documentation. It does **not** cover the third-party material below, which keeps its own terms.

| Path | Owner | Terms |
|---|---|---|
| `applications/ut/` (except the Theme Factory pages, regions and static files listed below) | Oracle and/or its affiliates | Derived from Oracle's *Universal Theme Reference* sample application, which Oracle publishes under the Universal Permissive License 1.0 at [oracle/apex](https://github.com/oracle/apex/tree/26.1/sample-apps/universal-theme-reference). See [licenses/UPL-1.0-oracle-apex.txt](licenses/UPL-1.0-oracle-apex.txt). |
| `applications/ut/shared-components/static-files/css/`, `…/js/`, pages 405, 406 and 409 | this repository | Theme Factory additions and assembled copies of `static-files/` and `sample-themes/*/css` (MIT). |
| `sample-themes/*/fonts/`, `applications/ut/**/fonts/` | the font authors | SIL Open Font License 1.1: see each theme's `licenses/`. The IBM Plex files are Modified Versions, renamed as the licence requires. |
| `static-files/js/vendor/alpine*` | Alpine.js contributors | MIT: `static-files/js/vendor/alpine.LICENSE.md`. |

Oracle's Universal Theme and APEX runtime files (`Core.min.css`, `Iris.min.css`, `theme42.min.js`, …) are **not**
redistributed here. `scripts/fetch-vendor.sh --reference` copies them from your own APEX instance into the
gitignored `.agents/knowledge/reference/` for local lookup.

The agent skills `impeccable` and `web-design-guidelines` are not part of this repository. `skills-lock.json`
records where they come from if you want to install them yourself.

Oracle, APEX and Universal Theme are trademarks of Oracle and/or its affiliates. This project is not affiliated with
or endorsed by Oracle.
