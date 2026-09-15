# APEX Theme Factory

Design-engineering workbench for **Oracle APEX 26.1 / Universal Theme / Iris**: turn Figma, Stitch,
screenshot or written designs into maintainable APEX implementations (APEXLang + repo CSS + Alpine.js),
verified against the running app through Chrome DevTools.

| Start here | |
|---|---|
| Agent spec (the rules) | [docs/AGENT_SPEC.md](docs/AGENT_SPEC.md) |
| Target app, constraints, tooling | [docs/PROJECT.md](docs/PROJECT.md) |
| Design tokens / conventions | [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) |
| Component registry | [docs/COMPONENTS.md](docs/COMPONENTS.md) |
| Chrome DevTools MCP | [docs/CHROME_DEVTOOLS_MCP.md](docs/CHROME_DEVTOOLS_MCP.md) |
| APEXLang export/validate/import | [docs/APEXLANG_ROUNDTRIP.md](docs/APEXLANG_ROUNDTRIP.md) |
| Agent skills / knowledge / findings / evals | [.agents/README.md](.agents/README.md) |

```bash
scripts/apex-export.sh     # refresh applications/ut from app 102 (SQLcl docker-demo)
scripts/apex-validate.sh   # compile-check the APEXLang source
scripts/apex-import.sh     # validate + import (asks first)
```

---

## Portable Single-Theme Packages

Every theme package built by the factory is a standalone, self-contained distribution ZIP that targets Oracle APEX 26.1.x, Universal Theme 42, and theme style **Iris**.

### Guarantee & Isolation
- **Single-theme guarantee**: Each ZIP package contains exactly one theme. Multi-theme bundles and external font URLs are strictly forbidden.
- **Custom fonts**: Any custom fonts must be package-local licensed WOFF2 files declared in `theme.json` under `fonts` with non-empty licenses. Themes without custom fonts (e.g. Linen, Solarized Dark) inherit Oracle Sans with zero font assets.
- **Deterministic builds**: Build outputs are byte-reproducible with fixed timestamps and sorted archives.

### Building Theme Packages

```bash
# Package a theme from sample-themes/<name> into dist/
scripts/package-theme.sh linen dist/
scripts/package-theme.sh solarized-dark dist/
```

### Installing into Target Applications

Extract the package ZIP:
```bash
unzip dist/linen-1.0.0.zip -d /tmp/linen-pkg
cd /tmp/linen-pkg/linen-1.0.0
```

> [!IMPORTANT]
> Replace `<SAVED_CONNECTION>`, `<WORKSPACE>`, and `<APP_ID>` with your real target environment parameters before executing.

#### 1. Automated Dry-Run (Default)
Inspect compatibility, export staging, and preview changes without modifying the database:
```bash
./install.sh --connection <SAVED_CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID>
```

#### 2. Automated Apply with Switcher
Install the theme and enable the native navigation-bar theme switcher:
```bash
./install.sh --connection <SAVED_CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --with-switcher --apply
```

#### 3. Automated Apply Fixed (Without Switcher)
Install the theme as fixed without the switcher widget:
```bash
./install.sh --connection <SAVED_CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --without-switcher --apply
```

### Uninstallation & Restore

To safely remove an installed theme and cleanly fallback to remaining themes or bare Iris:
```bash
./uninstall.sh --connection <SAVED_CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --apply
```

To restore from an immutable pre-install backup:
```bash
python3 -m theme_factory.cli restore --connection <SAVED_CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --backup ./theme-factory-backups/<WORKSPACE>-<APP_ID>/<BACKUP_DIR> --apply
```

### Manual Installation
Every built package includes `MANUAL-INSTALL.md` with comprehensive step-by-step instructions for installing via the Oracle APEX App Builder interface.

### Verification & Testing

#### Credential-Free Offline Gate (Layers A & B)
Run offline syntax checks, unit tests, agent compatibility assertions, and package verification gates:
```bash
bash tests/run-offline.sh
```

#### Continuous Integration Boundary
The GitHub Actions workflow (`.github/workflows/verify.yml`) executes `tests/run-offline.sh` and packages release ZIPs.
> [!NOTE]
> CI validates **Layer A (Repository Source)** and **Layer B (Package Portability)** only. A passing CI run does **NOT** prove live database installation (Layer C), browser runtime correctness (Layer D), or consumer application portability (Layer E). Layers C-E require local execution with SQLcl and Chrome DevTools MCP as defined in [tests/live/RELEASE-MATRIX.md](tests/live/RELEASE-MATRIX.md).

