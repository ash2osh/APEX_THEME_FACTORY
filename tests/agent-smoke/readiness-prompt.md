Inspect this repository's agent instructions and skill discovery paths. Return only one JSON object matching the supplied schema. Report the instruction entry you actually discovered, the design-work router skill you actually discovered, the exact supported APEX/theme/style boundary, and the configured Chrome runtime-truth server name. Confirm whether an application import requires an explicit user request and whether you would edit anything for this inspection.

Every string field takes a bare value and no prose: `instructionEntry` and `routerSkill` are repository-relative paths on their own (no parentheses, no explanation, no second path), and `runtimeTruthTool` is the MCP server name exactly as configured, on its own.

Do not edit files, commit, call a database, call a browser tool, or access the network.
