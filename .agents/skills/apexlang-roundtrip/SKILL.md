---
name: apexlang-roundtrip
description: Use when exporting app 102 from the DEMO workspace, validating edited .apx files, or importing APEXLang back into APEX via the SQLcl saved connection docker-demo — including "refresh the export", "does this compile", "push the page change to the app"
---

# apexlang-roundtrip

Reference: `docs/APEXLANG_ROUNDTRIP.md`. Global grammar/compiler tooling: the `apex` skill (`apexlang`).

## Commands
| Task | Command |
|---|---|
| Export (refresh source from live app) | `scripts/apex-export.sh` |
| Validate edited source | `scripts/apex-validate.sh` |
| Validate + import in one session | `scripts/apex-import.sh` (asks for confirmation) |

Underlying: `sql -S -name docker-demo` then
`apex export -applicationid 102 -exptype APEXLANG -split -dir <abs>/applications -skipexportdate`,
`apex validate -input <abs>/applications/ut -workspace DEMO`,
`apex import -input <abs>/applications/ut -workspace DEMO`.

## Discipline
1. Export before editing if the live app may have changed (Builder edits by the user). Diff.
2. Edit the smallest span in the relevant `pages/pNNNNN-*.apx` / shared component file. Preserve formatting and IDs (spec §40). LF line endings.
3. `apex validate` — must print `Validation successful.` The known warning `p00000-global-page.apx:95 Slot regionBody is deprecated` is pre-existing; any *new* warning is yours.
4. Import only on explicit user request; validate and import run in the **same** SQLcl session (the script does this).
5. After import: reload in Chrome, check console, verify visually (`chrome-devtools-mcp`).

## Common mistakes
- Importing without a fresh validate → compile failure mid-import.
- `-dir applications/ut` (creates `applications/ut/ut`). Pass the parent: `-dir …/applications`.
- Forgetting `-workspace DEMO` if the connection ever gains a second workspace (ambiguity error).
- Rewriting a whole file with a generator to change one property (spec §40).
