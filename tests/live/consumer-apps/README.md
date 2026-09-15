# Disposable APEX Consumer Fixtures

Isolated, non-production test applications used to verify portable theme package installation, switching, persistence, uninstallation, and restore across different APEX application topologies.

## Fixture Topologies

### 1. Minimal Consumer (`tests/live/consumer-apps/minimal`)
- **Theme**: Universal Theme 42 / base `ut-26.1`, style `Iris`.
- **Navigation**: Side navigation menu (`t-TreeNav--styleA`).
- **Pages**: One public standard page (Page 1 `Home`), no Global Page (Page 0).
- **Static files**: Zero application static files or custom CSS/JS.
- **Purpose**: Verifies that the installer creates Page 0 when missing, registers static files, adds switcher markup/scripts cleanly, and uninstalls back to zero footprint.

### 2. Business Consumer (`tests/live/consumer-apps/business`)
- **Theme**: Universal Theme 42 / base `ut-26.1`, style `Iris`.
- **Navigation**: Side navigation menu with multi-page hierarchy and navigation bar.
- **Global Page (Page 0)**: Existing pre-installed notification banner (`business_global_banner`).
- **Static files**: Existing unrelated files (`js/business-util.js`, `css/business-brand.css`) referenced in `application.apx`.
- **Components & Pages**:
  - Page 1 (`Home`): Form with items (`P1_NAME`, `P1_AMOUNT`), submit button, PL/SQL expression validation, Cards region (`business_cards`), and inline drawer (`business_drawer`).
  - Page 2 (`Reports`): Interactive Report (`business_ir`) and Editable Interactive Grid (`business_ig`).
  - Page 3 (`Widgets`): Calendar (`business_calendar`) and Oracle JET Chart (`business_chart`).
  - Page 10 (`Modal Dialog`): Modal dialog page (`business_modal_dialog`).
- **Data Source**: Self-contained `dual connect by level <= 12` queries; zero supporting tables or database schema installations required.
- **Purpose**: Verifies coexistence with existing Page 0 content, pre-existing CSS/JS files, complex widget layouts, and digest immutability of unrelated components after theme installation and uninstallation.

## Safety & Governance
- **Application ID Range**: Strictly reserved to `9000`–`9099`.
- **Application Aliases**: `TF-CONSUMER-MINIMAL-<id>` and `TF-CONSUMER-BUSINESS-<id>`.
- **Dry-run First**: Scripts print proposed targets and commands without modifying the database unless explicitly invoked with `--apply`.
- **Explicit Confirmation**: Applying requires typing exact application IDs; cleanup requires typing exact aliases.
