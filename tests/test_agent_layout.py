import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REQUIRED_PROJECT_PHRASES = (
    "APEX 26.1.x", "Universal Theme 42", "Iris", "Chrome DevTools",
    "Import only when the user asks", "sample-themes/<name>", "WOFF2",
    "external font URLs",
)


class AgentLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / ".agents/skills/design-to-apex").mkdir(parents=True)
        (self.tmp / ".agents/rules").mkdir(parents=True)
        (self.tmp / ".claude/skills").mkdir(parents=True)
        (self.tmp / ".agent").mkdir(parents=True)
        (self.tmp / "scripts").mkdir()
        shutil.copy("scripts/check-agent-layout.sh", self.tmp / "scripts/check-agent-layout.sh")

        # Set up a minimal passing structure by default
        self.agents_md = self.tmp / "AGENTS.md"
        self.agents_md.write_text(
            "# Rules\n"
            "APEX 26.1.x / Universal Theme 42 / Iris only\n"
            "Chrome DevTools MCP\n"
            "Import only when the user asks\n"
            "sample-themes/<name>\n"
            "WOFF2\n"
            "external font URLs forbidden\n",
            encoding="utf-8",
        )
        os.symlink("AGENTS.md", self.tmp / "CLAUDE.md")

        self.rule_file = self.tmp / ".agents/rules/apex-theme-factory.md"
        self.rule_file.write_text(
            "---\n"
            "trigger: always_on\n"
            "description: Mandatory Oracle APEX Theme Factory architecture and safety boundaries.\n"
            "---\n"
            "# Rule\n"
            "APEX 26.1.x / Universal Theme 42 / Iris\n"
            "Chrome DevTools\n"
            "Import only when the user asks\n"
            "sample-themes/<name>\n"
            "WOFF2\n"
            "external font URLs forbidden\n",
            encoding="utf-8",
        )

        skill = self.tmp / ".agents/skills/design-to-apex/SKILL.md"
        skill.write_text("---\nname: design-to-apex\ndescription: route design work\n---\n", encoding="utf-8")
        os.symlink("../../.agents/skills/design-to-apex", self.tmp / ".claude/skills/design-to-apex")
        os.symlink("../.agents/skills", self.tmp / ".agent/skills")

        (self.tmp / ".agents/README.md").write_text(
            ".agents/skills .claude/skills .agent/skills .agents/rules\n", encoding="utf-8"
        )

    def run_check(self):
        return subprocess.run(
            ["bash", str(self.tmp / "scripts/check-agent-layout.sh"), str(self.tmp)],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_valid_layout_passes(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
        self.assertIn("AGENT_LAYOUT status=PASS", result.stdout)

    def test_missing_claude_md_fails(self):
        (self.tmp / "CLAUDE.md").unlink()
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGENT_LAYOUT status=FAIL", result.stdout)
        self.assertIn("CLAUDE.md", result.stdout)

    def test_broken_claude_md_fails(self):
        (self.tmp / "CLAUDE.md").unlink()
        os.symlink("nonexistent.md", self.tmp / "CLAUDE.md")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGENT_LAYOUT status=FAIL", result.stdout)

    def test_oversized_agents_md_fails(self):
        self.agents_md.write_text("x" * 33000, encoding="utf-8")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("32 KiB limit", result.stdout)

    def test_missing_antigravity_rule_fails(self):
        self.rule_file.unlink()
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("apex-theme-factory.md", result.stdout)

    def test_oversized_antigravity_rule_fails(self):
        self.rule_file.write_text(
            "---\ntrigger: always_on\ndescription: rule\n---\n" + ("x" * 12050),
            encoding="utf-8",
        )
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exceeds 12000 limit", result.stdout)

    def test_missing_trigger_always_on_fails(self):
        self.rule_file.write_text(
            "---\ndescription: rule\n---\n# Rule\n",
            encoding="utf-8",
        )
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing 'trigger: always_on'", result.stdout)

    def test_missing_skill_frontmatter_fails(self):
        skill = self.tmp / ".agents/skills/design-to-apex/SKILL.md"
        skill.write_text("# No frontmatter\n", encoding="utf-8")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing opening '---'", result.stdout)

    def test_duplicate_skill_names_fails(self):
        (self.tmp / ".agents/skills/another-skill").mkdir(parents=True)
        (self.tmp / ".agents/skills/another-skill/SKILL.md").write_text(
            "---\nname: design-to-apex\ndescription: another\n---\n", encoding="utf-8"
        )
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate skill name", result.stdout)

    def test_skill_name_directory_mismatch_fails(self):
        skill = self.tmp / ".agents/skills/design-to-apex/SKILL.md"
        skill.write_text("---\nname: mismatch\ndescription: desc\n---\n", encoding="utf-8")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match directory", result.stdout)

    def test_missing_claude_link_fails(self):
        (self.tmp / ".claude/skills/design-to-apex").unlink()
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing symlink", result.stdout)

    def test_wrong_claude_target_fails(self):
        (self.tmp / ".claude/skills/design-to-apex").unlink()
        os.symlink("../..", self.tmp / ".claude/skills/design-to-apex")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected", result.stdout)

    def test_wrong_legacy_target_fails(self):
        (self.tmp / ".agent/skills").unlink()
        os.symlink("..", self.tmp / ".agent/skills")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected .agents/skills", result.stdout)

    def test_documentation_drift_fails(self):
        (self.tmp / ".agents/README.md").write_text("No paths mentioned\n", encoding="utf-8")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("documentation missing path", result.stdout)

    def test_contract_assertions(self):
        # Real repository contract tests
        repo_root = Path(__file__).resolve().parent.parent
        agents_text = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
        for phrase in REQUIRED_PROJECT_PHRASES:
            self.assertIn(phrase, agents_text)
        rule_path = repo_root / ".agents/rules/apex-theme-factory.md"
        if rule_path.exists():
            rule_text = rule_path.read_text(encoding="utf-8")
            for phrase in REQUIRED_PROJECT_PHRASES:
                self.assertIn(phrase, rule_text)


if __name__ == "__main__":
    unittest.main()
