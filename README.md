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
# run from the extracted package directory (the bundled lib/ is on PYTHONPATH)
PYTHONPATH=. python3 -m lib.theme_factory.cli restore --connection <SAVED_CONNECTION> --workspace <WORKSPACE> --app-id <APP_ID> --backup ./theme-factory-backups/<WORKSPACE>-<APP_ID>/<BACKUP_DIR> --apply
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
> CI validates **Layer A (Repository Source)** and **Layer B (Package Artifact)** only. A passing CI run does **NOT** prove live database installation (Layer C), browser runtime correctness and consumer portability (Layer D), or agent behavior (Layer E). Layers C-E require retained local evidence as defined in [tests/live/RELEASE-MATRIX.md](tests/live/RELEASE-MATRIX.md).

#### Live Evidence (Layers C, D, E) and the Release Report
Evidence is captured against a committed source state and bound to the package SHA-256 and the last *source* commit (evidence and Markdown commits do not count — see `lib/theme_factory/gitstate.py`).

```bash
# disposable consumers (IDs 9000–9099 only; dry-run first, then confirm)
scripts/provision-consumer-fixtures.sh --connection docker-demo --workspace DEMO --minimal-id 9010 --business-id 9011 --apply --confirm-ids 9010,9011

# Layer C: install → stale-restore guard → reinstall → switcher on → second package → switcher off → uninstall ×2 → unrelated files → restore
python3 tools/live_matrix.py --connection docker-demo --workspace DEMO --minimal-id 9010 --business-id 9011   --primary dist/linen/linen-1.0.0.zip --secondary dist/solarized-dark/solarized-dark-1.0.0.zip --apply

# Layer D: both consumers × 1440/1024/768/375 through the Chrome MCP daemon (python3 tools/chrome_mcp_daemon.py must be running)
python3 tools/browser_matrix.py --theme linen --package dist/linen/linen-1.0.0.zip   --minimal-url http://localhost:8181/ords/r/demo/tf-consumer-minimal-9010/home   --business-url http://localhost:8181/ords/r/demo/tf-consumer-business-9011/home   --business-extra-urls http://localhost:8181/ords/r/demo/tf-consumer-business-9011/reports,http://localhost:8181/ords/r/demo/tf-consumer-business-9011/widgets

# Layer E: read-only agent smokes (each consumes that runtime's quota)
python3 tools/agent_smoke.py codex && python3 tools/agent_smoke.py claude && python3 tools/agent_smoke.py antigravity

# report: dist/<theme>/RELEASE-REPORT.md, exit 0 only when every layer is PASS
scripts/release-check.sh linen
```

Every `PASS` in the report is backed by a digest-bound JSON artifact under `.agents/evaluations/runtime/<date>-release-<theme>/`; missing or failed checks stay `UNVERIFIED`/`FAIL` and the verdict stays `UNVERIFIED`/`FAIL`.
