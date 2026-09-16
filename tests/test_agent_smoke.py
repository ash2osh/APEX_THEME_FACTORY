import json
import os
import unittest
from pathlib import Path

from tools.agent_smoke import classify_result, redact


class AgentSmokeTests(unittest.TestCase):
    def test_schema_has_no_dialect_pointer_claude_cli_rejects(self):
        # `claude --json-schema` rejects a "$schema" draft/2020-12 pointer outright, so the shared
        # schema must stay dialect-agnostic or the Claude Code smoke can never run.
        schema = json.loads(Path("tests/agent-smoke/result.schema.json").read_text(encoding="utf-8"))
        self.assertNotIn("$schema", schema)

    def test_harness_schema_rejection_is_a_fail_not_environment(self):
        verdict = classify_result(
            "claude", 1,
            'Error: --json-schema is not a valid JSON Schema: no schema with key or ref "https://json-schema.org/draft/2020-12/schema"',
            "",
        )
        self.assertEqual(verdict.status, "FAIL")
        self.assertIn("schema", verdict.message.lower())

    def test_absolute_paths_inside_the_repository_are_accepted(self):
        payload = {
            "runtime": "codex",
            "instructionEntry": "/work/repo/AGENTS.md",
            "routerSkill": "/work/repo/.agents/skills/design-to-apex/SKILL.md",
            "apexBoundary": "APEX 26.1.x / Universal Theme 42 / Iris",
            "runtimeTruthTool": "chrome-devtools",
            "importRequiresUserRequest": True,
            "wouldEdit": False,
        }
        verdict = classify_result("codex", 0, "", json.dumps(payload), repo_root=Path("/work/repo"))
        self.assertEqual(verdict.status, "PASS", verdict.message)
        self.assertEqual(verdict.payload["instructionEntry"], "AGENTS.md")

    def test_absolute_paths_outside_the_repository_still_fail(self):
        payload = {
            "runtime": "codex",
            "instructionEntry": "/elsewhere/AGENTS.md",
            "routerSkill": ".agents/skills/design-to-apex/SKILL.md",
            "apexBoundary": "APEX 26.1.x / Universal Theme 42 / Iris",
            "runtimeTruthTool": "chrome-devtools",
            "importRequiresUserRequest": True,
            "wouldEdit": False,
        }
        verdict = classify_result("codex", 0, "", json.dumps(payload), repo_root=Path("/work/repo"))
        self.assertEqual(verdict.status, "FAIL")

    def test_claude_json_envelope_error_surfaces_its_message(self):
        stdout = json.dumps({"type": "result", "subtype": "success", "is_error": True, "num_turns": 1,
                             "result": "Failed to authenticate: OAuth session expired and could not be refreshed"})
        verdict = classify_result("claude", 1, "", stdout)
        self.assertEqual(verdict.status, "UNVERIFIED")
        self.assertIn("OAuth session expired", verdict.message)

    def test_authentication_failure_is_unverified(self):
        verdict = classify_result("codex", 1, "authentication required", "")
        self.assertEqual(verdict.status, "UNVERIFIED")

    def test_quota_failure_is_unverified(self):
        verdict = classify_result("antigravity", 1, "insufficient quota to run model", "")
        self.assertEqual(verdict.status, "UNVERIFIED")

    def test_wrong_boundary_is_fail(self):
        payload = {
            "runtime": "codex",
            "instructionEntry": "AGENTS.md",
            "routerSkill": ".agents/skills/design-to-apex/SKILL.md",
            "apexBoundary": "APEX 24",
            "runtimeTruthTool": "chrome-devtools",
            "importRequiresUserRequest": True,
            "wouldEdit": False,
        }
        verdict = classify_result("codex", 0, "", json.dumps(payload))
        self.assertEqual(verdict.status, "FAIL")

    def test_malformed_json_is_fail(self):
        verdict = classify_result("codex", 0, "", "Not JSON at all")
        self.assertEqual(verdict.status, "FAIL")

    def test_runtime_mismatch_is_fail(self):
        payload = {
            "runtime": "antigravity",
            "instructionEntry": "AGENTS.md",
            "routerSkill": ".agents/skills/design-to-apex/SKILL.md",
            "apexBoundary": "APEX 26.1.x / Universal Theme 42 / Iris",
            "runtimeTruthTool": "chrome-devtools",
            "importRequiresUserRequest": True,
            "wouldEdit": False,
        }
        verdict = classify_result("codex", 0, "", json.dumps(payload))
        self.assertEqual(verdict.status, "FAIL")

    def test_wrong_entry_is_fail(self):
        payload = {
            "runtime": "codex",
            "instructionEntry": "WRONG.md",
            "routerSkill": ".agents/skills/design-to-apex/SKILL.md",
            "apexBoundary": "APEX 26.1.x / Universal Theme 42 / Iris",
            "runtimeTruthTool": "chrome-devtools",
            "importRequiresUserRequest": True,
            "wouldEdit": False,
        }
        verdict = classify_result("codex", 0, "", json.dumps(payload))
        self.assertEqual(verdict.status, "FAIL")

    def test_wrong_chrome_tool_is_fail(self):
        payload = {
            "runtime": "antigravity",
            "instructionEntry": ".agents/rules/apex-theme-factory.md",
            "routerSkill": ".agents/skills/design-to-apex/SKILL.md",
            "apexBoundary": "APEX 26.1.x / Universal Theme 42 / Iris",
            "runtimeTruthTool": "chrome-devtools",  # Expected chrome-devtools-mcp
            "importRequiresUserRequest": True,
            "wouldEdit": False,
        }
        verdict = classify_result("antigravity", 0, "", json.dumps(payload))
        self.assertEqual(verdict.status, "FAIL")

    def test_redaction_sanitizes_home_uuid_and_secrets(self):
        home = os.path.expanduser("~")
        sample = (
            f"Error in {home}/projects/app/main.py\n"
            "user token: secret123456\n"
            "session id: 12345678-1234-1234-1234-123456789abc\n"
            "normal message line"
        )
        redacted = redact(sample)
        if home and home != "/":
            self.assertNotIn(home, redacted)
            self.assertIn("<HOME>", redacted)
        self.assertNotIn("secret123456", redacted)
        self.assertNotIn("12345678-1234-1234-1234-123456789abc", redacted)
        self.assertIn("<SESSION>", redacted)
        self.assertIn("<REDACTED>", redacted)

    def test_valid_results_for_all_three_runtimes_pass(self):
        cases = [
            ("codex", "AGENTS.md", "chrome-devtools"),
            ("claude", "CLAUDE.md", "chrome-devtools"),
            ("antigravity", ".agents/rules/apex-theme-factory.md", "chrome-devtools-mcp"),
        ]
        for rt, entry, tool in cases:
            payload = {
                "runtime": rt,
                "instructionEntry": entry,
                "routerSkill": ".agents/skills/design-to-apex/SKILL.md",
                "apexBoundary": "APEX 26.1.x / Universal Theme 42 / Iris",
                "runtimeTruthTool": tool,
                "importRequiresUserRequest": True,
                "wouldEdit": False,
            }
            # Test direct json
            verdict = classify_result(rt, 0, "", json.dumps(payload))
            self.assertEqual(verdict.status, "PASS", f"Failed for {rt}: {verdict.message}")

            # Test structured_output envelope
            envelope = {"structured_output": payload}
            verdict = classify_result(rt, 0, "", json.dumps(envelope))
            self.assertEqual(verdict.status, "PASS", f"Failed for {rt} envelope: {verdict.message}")


if __name__ == "__main__":
    unittest.main()
