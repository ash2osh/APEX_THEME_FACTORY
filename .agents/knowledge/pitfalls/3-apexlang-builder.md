# Pitfalls §3 — APEXLang / Builder

Part of the [pitfalls index](../pitfalls.md); entry numbers are stable and cited as `pitfalls §3.N`.

## 3. APEXLang / Builder

### 3.1 Static ID is `advanced { htmlDomId: … }`
- `staticId` in the same group is the compiler's internal component identifier; it validates and does
  nothing at runtime. Export examples: `p00300-grid-layout.apx:911`.

### 3.2 App-level CSS/JS are top-level blocks
- `application.apx` → `css { fileUrls }`, `javaScript { fileUrls }` (not `userInterface { }`).

### 3.3 Theme styles of a subscribed theme are read-only and not in APEXLang
- With `baseTheme: ut-26.1` the grammar has no style children (only `style { currentThemeStyle }`); the
  Builder shows every theme-style field read-only with no Delete because the theme is subscribed to the
  standard Universal Theme. Deleting Vita/Redwood rows means **unsubscribing** (lose Refresh Theme, export
  balloons). Decision 2026-09-14: leave the rows inert; remove every *reference* instead (nav-bar list,
  page 405, app process, P0 item, preview PNGs, dead `.apex-theme-vita-dark` CSS).

### 3.4 Removing the last app process
- Deleting the only `appProcess` leaves an empty `shared-components/app-processes.apx`; delete the file
  (the export omits it when there are none) — an empty `.apx` is not a valid component file.

### 3.5 Static files that only exist in the export
- `theme_styles/*.png`, `pwa/*`, `demo/*` have no source under `static-files/`; `sync-static.sh` only prunes
  `css/` and `js/`. Remove such files **and** their `file "…" ( )` entry in `static-files.apx` by hand.

### 3.6 Static files as data
- `apex_application_static_files.file_content` is a BLOB; `json_value(file_content FORMAT JSON, '$.title')`
  works (23ai), so a list or Cards SQL can discover packages from `css/themes/<name>/theme.json`. `#APP_FILES#`
  substitutes inside Cards media URLs and list targets. Query the view with
  `apex_session_state.get_number('APP_ID')` (lists) or `:APP_ID` (regions).

### 3.7 `apex import` is a full replace
- Whatever is on disk gets shipped — including another agent's untracked files — and files absent from the
  export are removed from the app. Never import from a worktree that lacks the working tree's untracked
  packages; export → diff → import.

### 3.8 APEXLang comment lines never come back from `apex export`
- **Symptom (found 2026-09-16 review):** the installer marked its Page 0 regions and list entries with
  `// APEX_THEME_FACTORY_MANAGED:BEGIN/END` comment lines and treated a managed region *without* the
  markers as a foreign collision. APEX has no place to store APEXLang comments, so the first real
  re-export was comment-free and every reinstall/upgrade/uninstall was refused.
- **Fix:** ownership lives in data APEX keeps — region Static ID (`advanced { htmlDomId }`), an HTML
  comment inside `htmlCode`, list-entry static ids (`entry <staticId> (` — the identifier *is* the
  static id and round-trips), `userDefinedAttributes`, and file digests in `registry.json`
  (`lib/theme_factory/apexlang.py`: `strip_bootstrap_regions`, `strip_switcher_entries`).
- Corollary: never compare a staged export with a re-export byte-for-byte. SQLcl re-indents fenced
  code to the fence column, sorts `file` blocks in `static-files.apx`, and names page files after the
  page name. Compare a semantic projection (`theme_factory_projection`). The offline fake `sql`
  (`tests/fixtures/bin/sql` + `apexlang_roundtrip.py`) reproduces these transforms on purpose.

### 3.9 Lists are exported into one `shared-components/lists.apx`
- SQLcl 26.2 writes every list into `lists.apx` (`list navigation-bar ( … )`); there is no
  `navigation/lists/navigation-bar.apx`. Resolve the navigation bar through
  `navigationBar { list: @alias }` in `application.apx`, and check the list is static — app 102's
  navigation bar is a SQL-query list and cannot host static switcher entries.
- Valid entry grammar: `layout { sequence, parentEntry: @id }`, `link { target: { type: url url: # } }`,
  `icon { imageIconCssClasses }`, `userDefinedAttributes { 2: <li classes> }`. `cssClasses` is not an
  entry property (`node ~/.claude/skills/apex/apexlang/tools/query-valid-props.mjs --component-type-id 3525`).
- `application.apx` may have no `javaScript {}` block at all (app 104); create it next to `css {}`.
