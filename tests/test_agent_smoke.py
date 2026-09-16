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


class InstructionEntryAndServerNamingTests(unittest.TestCase):
    """A runtime may name the same file or the same MCP server differently than the table spells it."""

    def repo_with_symlink(self) -> Path:
        import shutil
        import tempfile
        temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, temp, True)
        (temp / "AGENTS.md").write_text("instructions\n", encoding="utf-8")
        (temp / "CLAUDE.md").symlink_to("AGENTS.md")
        (temp / "README.md").write_text("readme\n", encoding="utf-8")
        return temp

    def payload(self, **overrides) -> str:
        values = {
            "runtime": "claude",
            "instructionEntry": "CLAUDE.md",
            "routerSkill": ".agents/skills/design-to-apex/SKILL.md",
            "apexBoundary": "APEX 26.1.x / Universal Theme 42 / Iris",
            "runtimeTruthTool": "chrome-devtools",
            "importRequiresUserRequest": True,
            "wouldEdit": False,
        }
        values.update(overrides)
        return json.dumps(values)

    def test_instruction_entry_naming_the_symlink_target_is_accepted(self):
        repo = self.repo_with_symlink()
        verdict = classify_result("claude", 0, "", self.payload(instructionEntry="AGENTS.md"), repo_root=repo)
        self.assertEqual(verdict.status, "PASS", verdict.message)
        # the record keeps what the runtime actually said
        self.assertEqual(verdict.payload["instructionEntry"], "AGENTS.md")

    def test_instruction_entry_naming_a_different_file_still_fails(self):
        repo = self.repo_with_symlink()
        verdict = classify_result("claude", 0, "", self.payload(instructionEntry="README.md"), repo_root=repo)
        self.assertEqual(verdict.status, "FAIL")

    def test_server_name_with_a_qualifier_is_accepted(self):
        repo = self.repo_with_symlink()
        verdict = classify_result(
            "claude", 0, "",
            self.payload(runtimeTruthTool="chrome-devtools (mcp__chrome-devtools__* MCP server)"),
            repo_root=repo,
        )
        self.assertEqual(verdict.status, "PASS", verdict.message)

    def test_another_runtimes_server_name_still_fails(self):
        repo = self.repo_with_symlink()
        verdict = classify_result("claude", 0, "", self.payload(runtimeTruthTool="chrome-devtools-mcp"), repo_root=repo)
        self.assertEqual(verdict.status, "FAIL")
        verdict = classify_result(
            "antigravity", 0, "",
            self.payload(runtime="antigravity", instructionEntry=".agents/rules/apex-theme-factory.md",
                         runtimeTruthTool="chrome-devtools"),
            repo_root=repo,
        )
        self.assertEqual(verdict.status, "FAIL")


class SchemaShapeTests(unittest.TestCase):
    """The schema, not the parser, must force bare paths and a bare server name."""

    def setUp(self):
        self.schema = json.loads(Path("tests/agent-smoke/result.schema.json").read_text(encoding="utf-8"))

    def matches(self, field: str, value: str) -> bool:
        import re
        pattern = self.schema["properties"][field].get("pattern")
        self.assertIsNotNone(pattern, f"{field} must constrain its format")
        return re.fullmatch(pattern, value) is not None

    def test_instruction_entry_accepts_a_path_and_rejects_prose(self):
        self.assertTrue(self.matches("instructionEntry", "CLAUDE.md"))
        self.assertTrue(self.matches("instructionEntry", ".agents/rules/apex-theme-factory.md"))
        self.assertFalse(self.matches("instructionEntry", "CLAUDE.md (project instructions at /home/x/CLAUDE.md), pointing to docs/AGENT_SPEC.md"))

    def test_runtime_truth_tool_accepts_a_server_name_and_rejects_prose(self):
        self.assertTrue(self.matches("runtimeTruthTool", "chrome-devtools"))
        self.assertTrue(self.matches("runtimeTruthTool", "chrome-devtools-mcp"))
        self.assertFalse(self.matches("runtimeTruthTool", "chrome-devtools (mcp__chrome-devtools__* MCP server)"))

    def test_prompt_demands_bare_values(self):
        prompt = Path("tests/agent-smoke/readiness-prompt.md").read_text(encoding="utf-8").lower()
        self.assertIn("no prose", prompt)


class SmokeTimeoutTests(unittest.TestCase):
    """A slow runtime must be retryable without editing the harness."""

    def test_timeout_is_configurable_with_a_documented_default(self):
        from tools.agent_smoke import DEFAULT_SMOKE_TIMEOUT, build_parser
        self.assertGreaterEqual(DEFAULT_SMOKE_TIMEOUT, 180)
        args = build_parser().parse_args(["antigravity", "--timeout", "420"])
        self.assertEqual(args.timeout, 420)
        self.assertEqual(build_parser().parse_args(["codex"]).timeout, DEFAULT_SMOKE_TIMEOUT)

    def test_timeout_message_reports_the_limit_actually_used(self):
        verdict = classify_result("antigravity", 124, "Command timed out after 420 seconds", "")
        self.assertEqual(verdict.status, "UNVERIFIED")
        self.assertIn("420", verdict.message)


class ErrorEnvelopeTests(unittest.TestCase):
    """A CLI that exits 0 while reporting a provider error is an environment limit, not a FAIL."""

    ENVELOPE = json.dumps({
        "conversation_id": "b2d1c0cd-02d2-495b-ae29-12fff8ec76cf",
        "status": "ERROR",
        "response": "",
        "error": "API error (attempt 1): UNAVAILABLE (code 503): No capacity available for model gemini-3.8-flash-high on the server",
        "duration_seconds": 292.1,
        "json_schema": {"type": "object"},
    })

    def test_provider_capacity_error_with_exit_zero_is_unverified(self):
        verdict = classify_result("antigravity", 0, "", self.ENVELOPE)
        self.assertEqual(verdict.status, "UNVERIFIED")
        self.assertIn("capacity", verdict.message.lower())

    def test_error_envelope_is_not_recorded_as_a_result_payload(self):
        verdict = classify_result("antigravity", 0, "", self.ENVELOPE)
        self.assertIsNone(verdict.payload)

    def test_recorded_payload_never_carries_conversation_identifiers(self):
        import shutil
        import tempfile
        from tools.agent_smoke import SmokeVerdict, record_evidence
        temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, temp, True)
        leaky = {"runtime": "antigravity", "conversation_id": "b2d1c0cd-02d2-495b-ae29-12fff8ec76cf",
                 "instructionEntry": ".agents/rules/apex-theme-factory.md"}
        record_evidence(temp, "antigravity", "1.2.4", "2026-09-16",
                        SmokeVerdict(status="FAIL", message="x", payload=leaky), "", "")
        recorded = (temp / "antigravity.json").read_text(encoding="utf-8")
        self.assertNotIn("b2d1c0cd", recorded)
        self.assertNotIn("conversation_id", recorded)
        self.assertIn("apex-theme-factory.md", recorded)


class ResponseEnvelopeTests(unittest.TestCase):
    """Antigravity wraps the result in `response`; an empty one is no evidence either way."""

    def envelope(self, response) -> str:
        return json.dumps({"conversation_id": "b2d1c0cd-02d2-495b-ae29-12fff8ec76cf", "status": "SUCCESS",
                           "response": response, "duration_seconds": 288.3, "json_schema": {"type": "object"}})

    def test_result_inside_the_response_field_is_parsed(self):
        payload = {
            "runtime": "antigravity",
            "instructionEntry": ".agents/rules/apex-theme-factory.md",
            "routerSkill": ".agents/skills/design-to-apex/SKILL.md",
            "apexBoundary": "APEX 26.1.x / Universal Theme 42 / Iris",
            "runtimeTruthTool": "chrome-devtools-mcp",
            "importRequiresUserRequest": True,
            "wouldEdit": False,
        }
        for wrapped in (payload, json.dumps(payload)):
            verdict = classify_result("antigravity", 0, "", self.envelope(wrapped))
            self.assertEqual(verdict.status, "PASS", verdict.message)
            self.assertEqual(verdict.payload["runtimeTruthTool"], "chrome-devtools-mcp")

    def test_empty_response_is_unverified_not_fail(self):
        verdict = classify_result("antigravity", 0, "", self.envelope(""))
        self.assertEqual(verdict.status, "UNVERIFIED")
        self.assertIn("empty", verdict.message.lower())
        self.assertIsNone(verdict.payload)

    def test_envelope_echo_of_the_schema_is_never_mistaken_for_a_result(self):
        # the envelope echoes json_schema; its keys must not be read as the runtime's answer
        verdict = classify_result("antigravity", 0, "", self.envelope(""))
        self.assertIsNone(verdict.payload)


class PrefixedEnvelopeTests(unittest.TestCase):
    """`agy` prints its own notice before the JSON when it hits its 5-minute print cap."""

    PREFIX = "[agy] print timeout after 5m0s with turn in progress; returning partial output\n"

    def envelope(self, **fields) -> str:
        base = {"conversation_id": "712c35e3-9f1f-4c1b-84ba-375329d1c93f", "status": "SUCCESS",
                "response": "", "duration_seconds": 300.0}
        base.update(fields)
        return self.PREFIX + json.dumps(base)

    def test_prefixed_empty_response_is_unverified_not_fail(self):
        verdict = classify_result("antigravity", 0, "", self.envelope())
        self.assertEqual(verdict.status, "UNVERIFIED")
        self.assertIsNone(verdict.payload)

    def test_prefixed_capacity_error_is_unverified(self):
        verdict = classify_result("antigravity", 0, "", self.envelope(
            status="ERROR", error="API error (attempt 1): UNAVAILABLE (code 503): No capacity available for model x"))
        self.assertEqual(verdict.status, "UNVERIFIED")
        self.assertIn("capacity", verdict.message.lower())

    def test_prefixed_valid_response_still_passes(self):
        payload = {
            "runtime": "antigravity",
            "instructionEntry": ".agents/rules/apex-theme-factory.md",
            "routerSkill": ".agents/skills/design-to-apex/SKILL.md",
            "apexBoundary": "APEX 26.1.x / Universal Theme 42 / Iris",
            "runtimeTruthTool": "chrome-devtools-mcp",
            "importRequiresUserRequest": True,
            "wouldEdit": False,
        }
        verdict = classify_result("antigravity", 0, "", self.envelope(response=payload))
        self.assertEqual(verdict.status, "PASS", verdict.message)
