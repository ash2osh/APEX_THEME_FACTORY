# Agent Compatibility Smoke: claude

- **Status:** PASS
- **CLI Version:** 2.1.273 (Claude Code)
- **Run Date (UTC):** 2026-09-17
- **Verdict Message:** All assertions passed

## Result Payload

```json
{
  "runtime": "claude",
  "instructionEntry": "CLAUDE.md",
  "routerSkill": ".agents/skills/design-to-apex/SKILL.md",
  "apexBoundary": "APEX 26.1.x / Universal Theme 42 / Iris",
  "runtimeTruthTool": "chrome-devtools",
  "importRequiresUserRequest": true,
  "wouldEdit": false
}
```

## Raw Execution Output (Redacted)

### Standard Output
```text
{"duration_api_ms":11300,"stop_reason":"tool_use","session_id":"<SESSION>","total_cost_usd":0.2535616,"usage":{"input_tokens":4,"cache_creation_input_tokens":58879,"cache_read_input_tokens":54988,"output_tokens":704,"output_tokens_details":{"thinking_tokens":341},"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":58879,"ephemeral_5m_input_tokens":0},"inference_geo":"not_available","iterations":[{"input_tokens":2,"output_tokens":480,"cache_read_input_tokens":54988,"cache_creation_input_tokens":3891,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":3891},"type":"message"}],"speed":"standard"},"modelUsage":{"claude-sonnet-5":{"inputTokens":4,"outputTokens":704,"cacheReadInputTokens":54988,"cacheCreationInputTokens":58879,"webSearchRequests":0,"costUSD":0.2535616,"contextWindow":1000000,"maxOutputTokens":64000,"thinkingTokens":341,"canonicalModel":"claude-sonnet-5","provider":"firstParty","costBasis":"list"}},"permission_denials":[],"terminal_reason":"completed","fast_mode_state":"off","fast_mode_disabled_reason":"sdk_opt_in_required","subagent_stats":{"spawned":0,"requested":{"background":0,"foreground":0,"unset":0},"started_in_background":0,"max_depth":0,"spawned_by_subagents":0,"completed":0,"failed":0,"killed":{"parent":0,"user":0,"system":0},"refused":{"depth_limit":0,"concurrency_limit":0,"budget":0},"by_type":{}},"is_error":false,"num_turns":3,"subtype":"success","api_error_status":null,"result":"{\"runtime\":\"claude\",\"instructionEntry\":\"CLAUDE.md\",\"routerSkill\":\".agents/skills/design-to-apex/SKILL.md\",\"apexBoundary\":\"APEX 26.1.x / Universal Theme 42 / Iris\",\"runtimeTruthTool\":\"chrome-devtools\",\"importRequiresUserRequest\":true,\"wouldEdit\":false}","structured_output":{"runtime":"claude","instructionEntry":"CLAUDE.md","routerSkill":".agents/skills/design-to-apex/SKILL.md","apexBoundary":"APEX 26.1.x / Uni
```

### Standard Error
```text
(none)
```
