# Release Verification Matrix

This is the required live matrix, not a record of completed tests. A row may become `PASS` only when its referenced screenshot/JSON artifact exists and validates against the runtime evidence contract.

## Current evidence status

| Theme | Consumer | Required coverage | Retained evidence | Status |
|---|---|---|---|---|
| linen | minimal | Shell/navigation and Home at 1440, 1024, 768, and 375 CSS px | None | UNVERIFIED |
| linen | business | Forms/errors, Cards, IR, editable IG, dialog/drawer, Calendar, JET chart, keyboard, fonts, console, network, contrast, and persistence | None | UNVERIFIED |
| solarized-dark | minimal | Shell/navigation and Home at 1440, 1024, 768, and 375 CSS px | None | UNVERIFIED |
| solarized-dark | business | Forms/errors, Cards, IR, editable IG, dialog/drawer, Calendar, JET chart, keyboard, fonts, console, network, contrast, and persistence | None | UNVERIFIED |

The live Page 409 artifact proves a narrow App 102 lifecycle observation only. It does not prove either theme package, either disposable consumer topology, the complete responsive matrix, custom-font behavior, uninstall, or restore.

## Row contract for future runs

| Theme | Consumer | App ID/alias | URL | Page/component | State/action | Width | Expected | Screenshot/JSON | Console | Network | Contrast | Status |
|---|---|---:|---|---|---|---:|---|---|---|---|---|---|

Every completed row must name the exact disposable application, action, viewport, artifact path, console result, failed-request result, contrast result, and cleanup/retention status. Missing evidence remains `UNVERIFIED`; it is never inferred from source tests or prose.
