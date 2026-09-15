# Release Verification Matrix

Comprehensive multi-device, multi-state verification matrix for theme releases across minimal and business consumer applications.

## Row Contract

```markdown
| Theme | Consumer | Page/component | State/action | Width | Expected | Screenshot/JSON | Console | Network | Contrast | Status |
|---|---|---|---|---:|---|---|---|---|---|---|
```

## Matrix Entries

### Linen Theme

| Theme | Consumer | Page/component | State/action | Width | Expected | Screenshot/JSON | Console | Network | Contrast | Status |
|---|---|---|---|---:|---|---|---|---|---|---|
| linen | minimal | Shell / Navigation | Initial load | 1440 | Warm linen canvas, tree navigation rendered, neutral text | `tests/live/evidence/linen/minimal/shell-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | minimal | Shell / Navigation | Collapsed nav | 1024 | Collapsed side nav, icon-only rail, full responsive reflow | `tests/live/evidence/linen/minimal/shell-1024.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | minimal | Shell / Navigation | Drawer open | 768 | Hamburger toggle opens slide-out nav, focus trapped | `tests/live/evidence/linen/minimal/shell-768.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | minimal | Shell / Navigation | Mobile drawer | 375 | Full-width slide-out nav, tap targets >= 44px, no overflow | `tests/live/evidence/linen/minimal/shell-375.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | minimal | Page 1 (Home) | Initial render | 1440 | Hero title, standard region container, warm borders | `tests/live/evidence/linen/minimal/p1-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | minimal | Page 1 (Home) | Tablet view | 768 | Responsive padding, breadcrumb collapse | `tests/live/evidence/linen/minimal/p1-768.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | minimal | Page 1 (Home) | Mobile view | 375 | Single-column reflow, zero horizontal scroll | `tests/live/evidence/linen/minimal/p1-375.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | business | Shell / Global Banner | Initial load | 1440 | Global banner styled with linen token border/background | `tests/live/evidence/linen/business/shell-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | business | Page 1 (Form) | Focus state | 1440 | Focus ring on text field, halo visible, high contrast | `tests/live/evidence/linen/business/p1-form-focus-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | business | Page 1 (Form) | Validation error | 1440 | Inline error message styled with warning/danger token | `tests/live/evidence/linen/business/p1-form-error-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | business | Page 1 (Cards) | Hover state | 1440 | Card elevation/border highlight, readable text on linen | `tests/live/evidence/linen/business/p1-cards-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | business | Page 1 (Drawer) | Open drawer | 1440 | Slide-in drawer with overlay backdrop, focus management | `tests/live/evidence/linen/business/p1-drawer-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | business | Page 2 (IR) | Filter search | 1440 | Search bar, column header sort, row hover, pagination | `tests/live/evidence/linen/business/p2-ir-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | business | Page 2 (IG) | Editable cell edit | 1440 | Cell active edit mode, toolbar buttons, save action | `tests/live/evidence/linen/business/p2-ig-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | business | Page 3 (Calendar) | Month view | 1440 | Calendar grid, event badges, navigation buttons | `tests/live/evidence/linen/business/p3-calendar-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | business | Page 3 (Chart) | JET chart render | 1440 | SVG chart bars styled with linen palette series colors | `tests/live/evidence/linen/business/p3-chart-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | business | Page 10 (Modal) | Open dialog | 1440 | Centered modal dialog, backdrop overlay, Esc closes | `tests/live/evidence/linen/business/p10-modal-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | business | Page 2 (IR) | Tablet reflow | 768 | Interactive report horizontal scroll container active | `tests/live/evidence/linen/business/p2-ir-768.json` | 0 errors | 200 OK | PASS | VERIFIED |
| linen | business | Page 2 (IG) | Mobile view | 375 | Grid toolbar wraps cleanly, horizontal pan available | `tests/live/evidence/linen/business/p2-ig-375.json` | 0 errors | 200 OK | PASS | VERIFIED |

### Solarized Dark Theme

| Theme | Consumer | Page/component | State/action | Width | Expected | Screenshot/JSON | Console | Network | Contrast | Status |
|---|---|---|---|---:|---|---|---|---|---|---|
| solarized-dark | minimal | Shell / Navigation | Initial load | 1440 | Solarized base03/base02 surfaces, cyan accent, crisp text | `tests/live/evidence/solarized-dark/minimal/shell-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | minimal | Shell / Navigation | Collapsed nav | 1024 | Rail nav, dark surface contrast >= 4.5:1 | `tests/live/evidence/solarized-dark/minimal/shell-1024.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | minimal | Shell / Navigation | Drawer open | 768 | Responsive nav drawer, solarized base03 background | `tests/live/evidence/solarized-dark/minimal/shell-768.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | minimal | Shell / Navigation | Mobile drawer | 375 | Clean mobile header, hamburger trigger, 0 overflow | `tests/live/evidence/solarized-dark/minimal/shell-375.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | minimal | Page 1 (Home) | Initial render | 1440 | Dark card surfaces, cyan link highlights | `tests/live/evidence/solarized-dark/minimal/p1-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | minimal | Page 1 (Home) | Tablet view | 768 | Responsive padding, dark background preserved | `tests/live/evidence/solarized-dark/minimal/p1-768.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | minimal | Page 1 (Home) | Mobile view | 375 | Single column, readable font contrast | `tests/live/evidence/solarized-dark/minimal/p1-375.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | business | Shell / Global Banner | Initial load | 1440 | Solarized cyan/blue accent banner, dark surface | `tests/live/evidence/solarized-dark/business/shell-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | business | Page 1 (Form) | Focus state | 1440 | Cyan focus ring halo (`--app-focus-halo-color`), dark input bg | `tests/live/evidence/solarized-dark/business/p1-form-focus-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | business | Page 1 (Form) | Validation error | 1440 | Solarized red badge/alert text (`--app-badge-danger-text`) | `tests/live/evidence/solarized-dark/business/p1-form-error-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | business | Page 1 (Cards) | Hover state | 1440 | Card overlay (`--app-card-media-overlay`), cyan border | `tests/live/evidence/solarized-dark/business/p1-cards-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | business | Page 1 (Drawer) | Open drawer | 1440 | Dark backdrop overlay (`--app-overlay-background`), focus trapped | `tests/live/evidence/solarized-dark/business/p1-drawer-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | business | Page 2 (IR) | Filter search | 1440 | Dark search toolbar, dark table headers, no white flash | `tests/live/evidence/solarized-dark/business/p2-ir-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | business | Page 2 (IG) | Editable cell edit | 1440 | Dark IG grid cells, cyan active cell border, save active | `tests/live/evidence/solarized-dark/business/p2-ig-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | business | Page 3 (Calendar) | Month view | 1440 | Dark calendar grid, solarized yellow/green event tags | `tests/live/evidence/solarized-dark/business/p3-calendar-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | business | Page 3 (Chart) | JET chart render | 1440 | Dark chart background, cyan/yellow/magenta series bars | `tests/live/evidence/solarized-dark/business/p3-chart-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | business | Page 10 (Modal) | Open dialog | 1440 | Modal dialog on solarized dark overlay, Esc dismissal | `tests/live/evidence/solarized-dark/business/p10-modal-1440.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | business | Page 2 (IR) | Tablet reflow | 768 | Dark table scrolls cleanly within container | `tests/live/evidence/solarized-dark/business/p2-ir-768.json` | 0 errors | 200 OK | PASS | VERIFIED |
| solarized-dark | business | Page 2 (IG) | Mobile view | 375 | Responsive toolbar wrap, dark background, legible text | `tests/live/evidence/solarized-dark/business/p2-ig-375.json` | 0 errors | 200 OK | PASS | VERIFIED |
