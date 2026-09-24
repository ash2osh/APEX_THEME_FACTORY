# Notices

The MIT licence in [LICENSE](LICENSE) covers the original work in this repository: the theme packages in
`sample-themes/`, `static-files/`, the tooling in `lib/`, `scripts/`, `tools/`, `installer/` and `tests/`, and the
documentation. It does **not** cover the third-party material below, which keeps its own terms.

| Path | Owner | Terms |
|---|---|---|
| `applications/ut/` (except the Theme Factory pages, regions and static files listed below) | Oracle and/or its affiliates | Export of Oracle's *Universal Theme 26.1 Reference* sample application, including its demo scripts, data and images. Included only so the reference app can be re-imported for theme development; governed by your Oracle APEX licence, not by this repository's licence. |
| `applications/ut/shared-components/static-files/css/`, `…/js/` | this repository | Assembled copies of `static-files/` and `sample-themes/*/css` (MIT). |
| `sample-themes/*/fonts/`, `applications/ut/**/fonts/` | the font authors | SIL Open Font License 1.1 — see each theme's `licenses/`. |
| `static-files/js/vendor/alpine*` | Alpine.js contributors | MIT — `static-files/js/vendor/alpine.LICENSE.md`. |
| `.agents/skills/impeccable/`, `.agents/skills/web-design-guidelines/` | their upstream authors (`skills-lock.json`) | Their upstream licences. |

Oracle Universal Theme / APEX CSS and JavaScript (`Core.min.css`, `Iris.min.css`, `theme42.min.js`, …) are **not**
redistributed here. `scripts/fetch-vendor.sh --reference` copies them from your own APEX instance into the
gitignored `.agents/knowledge/reference/` for local lookup.

Oracle, APEX and Universal Theme are trademarks of Oracle and/or its affiliates. This project is not affiliated with
or endorsed by Oracle.
