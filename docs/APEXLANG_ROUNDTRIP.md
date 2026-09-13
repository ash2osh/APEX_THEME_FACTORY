# APEXLang round-trip with SQLcl (`docker-demo`)

SQLcl 26.2.1 + APEX 26.1.4. Saved connection: `docker-demo` (user `DEMO`, workspace `DEMO`).
Application **102** exports to `applications/ut/` (alias `UT`).

## Commands (verified 2026-09-13)

```bash
scripts/apex-export.sh      # apex export -applicationid 102 -exptype APEXLANG -split -dir applications -skipexportdate
scripts/apex-validate.sh    # apex validate -input applications/ut -workspace DEMO
scripts/apex-import.sh      # apex validate + apex import -input applications/ut -workspace DEMO  (same SQLcl session)
```

Raw form, inside `sql -name docker-demo`:

```sql
apex export -applicationid 102 -exptype APEXLANG -split -dir /abs/path/applications -skipexportdate
apex validate -input /abs/path/applications/ut -workspace DEMO
apex import   -input /abs/path/applications/ut -workspace DEMO
```

Notes
- `-split -dir <parent>` creates `<parent>/<alias-lowercase>/` (here `applications/ut/`), 202 files, ~6 MB.
- `-skipexportdate` keeps diffs clean. Add `-force` / `-overwrite-files` to refresh an existing export.
- Validate currently reports one warning: `pages/p00000-global-page.apx:95 PROPERTY_DEPRECATED Slot regionBody is deprecated` — pre-existing in Oracle's reference app, not ours.
- **Validate and import must run in the same SQLcl session** (apexlang skill rule). `scripts/apex-import.sh` does this.
- Import overwrites app 102 in place. Export first, diff, then import. Never import an app directory that has not just passed `apex validate`.
- `apex import` accepts `-id`, `-alias`, `-name` overrides if you ever need to install a copy instead of replacing 102.

## Export layout

```text
applications/ut/
├── application.apx                 # app UT ( ... ) — name, nav, auth, UI, theme ref
├── page-groups.apx
├── pages/pNNNNN-<alias>.apx        # one file per page (122)
├── shared-components/
│   ├── themes/universal-theme/theme.apx   # baseTheme: ut-26.1, currentThemeStyle: @/iris
│   ├── static-files.apx + static-files/  # app static files (#APP_FILES#)
│   ├── lists.apx, lovs.apx, breadcrumbs.apx, plugins/, ...
├── supporting-objects/
├── workspace-components/
├── deployments/default.json        # { app: { id: 102 } }
└── .apex/apexlang.json
```

Editing rules: spec §40 — smallest change, preserve formatting/IDs, validate, inspect runtime.
Grammar/property questions: the global `apex` skill (`~/.claude/skills/apex/apexlang`) has the
compiler-truth tools (`node tools/query-valid-props.mjs`, `apexctl.mjs apexlang format`).
