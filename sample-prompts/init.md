Read AGENTS.md, then docs/PROJECT.md, then skim docs/AGENT_SPEC.md (§1–§7, §75–§78 at minimum).

Session setup — confirm each before doing any design work, and report the results:
1. Chrome DevTools MCP: call list_pages on the chrome-devtools server and identify the APEX tab
   (http://localhost:8181/ords/r/demo/ut/...). The first call can take 30–40 s — wait for it.
   Then evaluate_script on that page and return apex.env.APEX_VERSION and document.body.className;
   confirm it contains "apex-theme-iris".
2. SQLcl: run scripts/apex-validate.sh and confirm "Validation successful."
3. Skills: confirm the project skills in .agents/skills are loaded (design-to-apex, chrome-devtools-mcp,
   apexlang-roundtrip, …). If they are not, tell me instead of continuing.
4. git: the folder is not a repository yet. Run `git init`, add a .gitignore for scratch/screenshot
   files, and make an initial commit of the scaffold + applications/ut export so later .apx diffs are
   reviewable.

Hard rules for everything after that: Iris theme style only; runtime truth from Chrome DevTools, never
from memory; declarative changes in applications/ut/*.apx; appearance in static-files/css using
--app-* tokens aliased to Iris; never import to the live app unless I say so.

When setup is confirmed, stop and wait for my first design task.