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

### 3.10 Translations and `apex import`: two methods, two versions
- **Text Message-Based** (`globalization { translationMethod: textMessages }`, new in 26.1): messages live in
  `shared-components/messages.apx`, so they are in every export and survive every import. Nothing special to do.
- **Application-Based on APEX 26.1:** `apex export -exptype APEXLANG` fails with ORA-20987 ("translated text in the
  Translation Repository, which is not supported by the APEXlang format"), with or without `-exptranslations`. No
  APEXLang round trip is possible, so `SqlclClient` turns this into exit 3 with the options. Nothing has changed by then.
- **Application-Based on APEX 26.2:** a plain export succeeds and keeps the mapping, but an import empties the repository
  (5,555 rows to 0). `-exptranslations` adds `generated-artifacts/translations.sql`, which SQLcl 26.3 splits every
  10,000 lines or so, sometimes between `if ... then` and its body, so the import fails with `PLS-00103`.
  `repair_translation_script` moves those `if` lines into the next block.
- **`-exptranslations` silently leaves rows out.** With every row translated (3,138), 13 never reached the file: page
  item prompts on Faceted Search and Smart Filters pages (`APEX_PAGE_ITEMS`), and `APEX_PAGE_ITEM_HELP`. A backup of that
  file can't bring them back, so `save_translations` writes the translated rows to `translations.json` beside the backup
  (its digest is in `target.json`). `restore_translations` then seeds, puts back what differs, publishes, and compares
  every saved row by `from_id`, column, JSON path and language. Those keys are stable across an import.
- After a good import the mapping needs seeding and publishing again (`requires_synchronization = Yes`), and about 20
  untranslated attribute rows only return with the seed. Seeding keeps translated text. Untranslated rows follow the
  source, so the bootstrap regions don't go stale in the translated app on an upgrade.
- **Dynamic translations** live in `shared-components/dynamic-translations.apx`, and survive an import. Two languages
  work: each has its own repository rows, and the installer loops over the mappings.
- **Test scripts:** a `&x.` in a script fed to SQLcl stops at a substitution prompt forever if stdin stays open, with
  no CPU use and no output. `set define off` and `</dev/null`. A `dbms_output` line of `set serveroutput on size
  unlimited feedback off` still hit the 1 MB limit: call `dbms_output.enable(null)` in the block.
- **`apex import` exits 0 when it fails.** It prints `APEXlang Import Errors:` and changes nothing. Require
  `Import successful.` in the output (`SqlclClient.import_apexlang`). An import that only *appears* to keep data may
  simply not have run: this misled a before/after comparison on 2026-11-04.
- **Other effects of an import, measured on 26.2:** private saved reports and ACL role assignments survive with the
  same IDs, and every session of the app ends. `-expsavedreports`, `-exppubreports` and `-expaclassignments` add nothing
  to an APEXLang export, so a backup can't hold those.
