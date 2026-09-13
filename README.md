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
