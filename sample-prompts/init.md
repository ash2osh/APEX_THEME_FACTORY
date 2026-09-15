Prepare this APEX Theme Factory workspace for a design session without changing it.

1. Read `AGENTS.md`, `docs/AGENT_SPEC.md`, `docs/PROJECT.md`, and `.agents/knowledge/pitfalls.md`; report the focused skills relevant to the requested work.
2. Run `git status --short --branch` and report existing changes without modifying them.
3. Run `scripts/apex-validate.sh`; state that this validation uses the configured saved SQLcl connection and report its real result.
4. Through this runtime's configured Chrome DevTools server, inspect the already-running APEX tab and report application ID, alias, APEX version (APEX_VERSION), and the Iris theme class (apex-theme-iris). Do not navigate or mutate the application.
5. Compare the page's referenced CSS and JavaScript assets with `static-files/` and report any drift.
6. Stop before editing files, importing APEXLang, committing, or changing browser/database state; stop and report readiness.

If a required runtime is unavailable, report that part as UNVERIFIED and continue with the remaining read-only checks.