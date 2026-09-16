# Agent Compatibility Smoke: antigravity

- **Status:** UNVERIFIED
- **CLI Version:** 1.2.4
- **Run Date (UTC):** 2026-09-16
- **Verdict Message:** Provider capacity/availability limitation: no capacity ([agy] print timeout after 5m0s with turn in progress; returning partial output)

## Result Payload

```json
null
```

## Raw Execution Output (Redacted)

### Standard Output
```text
{"conversation_id":"<SESSION>","status":"ERROR","response":"","error":"API error (attempt 1): UNAVAILABLE (code 503): No capacity available for model gemini-3.8-flash-high on the server","duration_seconds":289.880763386,"num_turns":1,"json_schema":{"type":"object","additionalProperties":false,"required":["runtime","instructionEntry","routerSkill","apexBoundary","runtimeTruthTool","importRequiresUserRequest","wouldEdit"],"properties":{"runtime":{"enum":["codex","claude","antigravity"]},"instructionEntry":{"type":"string","minLength":1,"maxLength":200,"pattern":"^[A-Za-z0-9._/-]+$","description":"Repository-relative path of the instruction file you loaded. Path only, no prose."},"routerSkill":{"type":"string","const":".agents/skills/design-to-apex/SKILL.md","description":"Path only, no prose."},"apexBoundary":{"type":"string","const":"APEX 26.1.x / Universal Theme 42 / Iris"},"runtimeTruthTool":{"type":"string","minLength":1,"maxLength":80,"pattern":"^[A-Za-z0-9._-]+$","description":"Configured MCP server name exactly as it appears in your MCP configuration. Name only, no prose."},"importRequiresUserRequest":{"type":"boolean","const":true},"wouldEdit":{"type":"boolean","const":false}}},"usage":{"input_tokens":154658,"output_tokens":2877,"thinking_tokens":2029,"cache_read_tokens":166707,"total_tokens":157535}}
```

### Standard Error
```text
[agy] print timeout after 5m0s with turn in progress; returning partial output
```
