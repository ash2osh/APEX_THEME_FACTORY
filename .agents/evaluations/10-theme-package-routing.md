# Evaluation: Theme Package Routing
Given: "make the side navigation white and the buttons flat, app-wide, as a new look called <name>".
Expected: a package `sample-themes/<name>/{theme.json, css/tokens.css, css/apex/*.css}` with every rule
scoped to `html.app-theme-<name>`, `--app-*` roles (defaults added to `foundation/tokens.css` first), then
`scripts/sync-static.sh` — and, if it is a dark look, Iris' literal `:root` tokens remapped.
Failure: rules in `static-files/css/apex/…` or `static-files/css/app.css`, unscoped `.t-*` overrides, a hand-edited
`@themes` block, or literal colours in `css/apex/*.css`.
Skills under test: apex-css-design-system, design-to-apex, apex-design-system.
