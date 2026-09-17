"""Tests for lib/theme_factory/gitstate.py's instruction-Markdown binding (plan Task 3).

`source_equivalent`/`last_source_commit` treat all Markdown as non-source, which is right for
prose and evidence but wrong for Layer E: the agent smokes measure what a runtime does after
reading AGENTS.md, .agents/rules/*.md and .agents/skills/**. Editing those leaves Layer E's
artifacts claiming a binding they no longer have.

Choice recorded here (plan Task 3's "cost to know before starting"): a *separate* Layer-E-only
binding, not a change to the shared source_equivalent. Coupling C/D to instruction edits would be
over-strict - those layers depend on code and package bytes, not on what an agent reads - and
would force a full live re-capture (an hour, per pitfalls.md 5.x) for a wording change in a skill
file. The extra code here is `last_instruction_commit`/`instruction_equivalent`, used only for
Layer E's raw-artifact binding in release.py.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class InstructionCommitBindingTests(unittest.TestCase):
    def make_repo(self):
        temp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(temp, ignore_errors=True))
        root = Path(temp)

        def git(*args):
            return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()

        git("init", "-q")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        (root / "AGENTS.md").write_text("# instructions v1\n", encoding="utf-8")
        (root / "README.md").write_text("# readme v1\n", encoding="utf-8")
        (root / "lib.py").write_text("print(1)\n", encoding="utf-8")
        (root / ".agents" / "rules").mkdir(parents=True)
        (root / ".agents" / "rules" / "apex-theme-factory.md").write_text("rule v1\n", encoding="utf-8")
        (root / ".agents" / "skills" / "example").mkdir(parents=True)
        (root / ".agents" / "skills" / "example" / "SKILL.md").write_text("skill v1\n", encoding="utf-8")
        git("add", "-A"); git("commit", "-q", "-m", "baseline")
        baseline = git("rev-parse", "HEAD")

        (root / "README.md").write_text("# readme v2\n", encoding="utf-8")
        git("add", "-A"); git("commit", "-q", "-m", "readme only")
        readme_commit = git("rev-parse", "HEAD")

        (root / "AGENTS.md").write_text("# instructions v2\n", encoding="utf-8")
        git("add", "-A"); git("commit", "-q", "-m", "agents.md changed")
        agents_commit = git("rev-parse", "HEAD")

        git("checkout", "-q", readme_commit)
        (root / ".agents" / "rules" / "apex-theme-factory.md").write_text("rule v2\n", encoding="utf-8")
        git("add", "-A"); git("commit", "-q", "-m", "rule changed")
        rule_commit = git("rev-parse", "HEAD")

        git("checkout", "-q", readme_commit)
        (root / ".agents" / "skills" / "example" / "SKILL.md").write_text("skill v2\n", encoding="utf-8")
        git("add", "-A"); git("commit", "-q", "-m", "skill changed")
        skill_commit = git("rev-parse", "HEAD")

        git("checkout", "-q", "main" if "main" in git("branch") else "master")
        return root, baseline, readme_commit, agents_commit, rule_commit, skill_commit

    def test_instruction_equivalent_is_false_across_an_agents_md_edit(self):
        from lib.theme_factory.gitstate import instruction_equivalent
        root, baseline, readme_commit, agents_commit, rule_commit, skill_commit = self.make_repo()
        self.assertFalse(instruction_equivalent(baseline, agents_commit, cwd=root))

    def test_instruction_equivalent_is_false_across_a_rules_edit(self):
        from lib.theme_factory.gitstate import instruction_equivalent
        root, baseline, readme_commit, agents_commit, rule_commit, skill_commit = self.make_repo()
        self.assertFalse(instruction_equivalent(baseline, rule_commit, cwd=root))

    def test_instruction_equivalent_is_false_across_a_skill_edit(self):
        from lib.theme_factory.gitstate import instruction_equivalent
        root, baseline, readme_commit, agents_commit, rule_commit, skill_commit = self.make_repo()
        self.assertFalse(instruction_equivalent(baseline, skill_commit, cwd=root))

    def test_instruction_equivalent_is_true_across_a_readme_edit(self):
        from lib.theme_factory.gitstate import instruction_equivalent
        root, baseline, readme_commit, agents_commit, rule_commit, skill_commit = self.make_repo()
        self.assertTrue(instruction_equivalent(baseline, readme_commit, cwd=root))

    def test_instruction_equivalent_is_true_for_the_same_commit(self):
        from lib.theme_factory.gitstate import instruction_equivalent
        root, baseline, *_ = self.make_repo()
        self.assertTrue(instruction_equivalent(baseline, baseline, cwd=root))

    def test_last_instruction_commit_ignores_readme_only_commits(self):
        from lib.theme_factory.gitstate import last_instruction_commit
        root, baseline, readme_commit, agents_commit, rule_commit, skill_commit = self.make_repo()
        subprocess.run(["git", "checkout", "-q", readme_commit], cwd=root, check=True)
        self.assertEqual(last_instruction_commit(root), baseline)

    def test_last_instruction_commit_advances_on_agents_md_edit(self):
        from lib.theme_factory.gitstate import last_instruction_commit
        root, baseline, readme_commit, agents_commit, rule_commit, skill_commit = self.make_repo()
        subprocess.run(["git", "checkout", "-q", agents_commit], cwd=root, check=True)
        self.assertEqual(last_instruction_commit(root), agents_commit)


class LayerEBindingUsesInstructionEquivalenceTests(unittest.TestCase):
    """Proves the wiring in release.py, not just instruction_equivalent() in isolation:
    _load_bound_raw_artifact's Layer E call sites pass commit_equivalence=instruction_equivalent,
    so a raw Layer E artifact captured before an AGENTS.md edit is rejected at the new commit, while
    the same artifact captured before a README-only edit still binds."""

    def _write_raw_artifact(self, root, git_commit):
        import hashlib
        import json
        raw_dir = root / "raw"
        raw_dir.mkdir(exist_ok=True)
        document = {
            "schemaVersion": 1, "theme": "linen", "evidenceType": "agent-runtime",
            "runtime": "claude", "status": "PASS",
            "gitCommit": git_commit, "packageSha256": "d" * 64,
            "capturedAt": "2026-09-17T00:00:00Z",
        }
        path = raw_dir / "agent-runtime-claude.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return {"path": "raw/agent-runtime-claude.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def _git_repo(self):
        # _load_bound_raw_artifact's git-diff-based equivalence check has no cwd parameter (it
        # matches the rest of release.py, which always runs from the repo root in production), so
        # exercising it against a scratch repo means actually chdir-ing into one, and back after.
        temp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(temp, ignore_errors=True))
        original_cwd = os.getcwd()
        self.addCleanup(os.chdir, original_cwd)
        root = Path(temp)

        def git(*args):
            return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()

        git("init", "-q")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        os.chdir(root)
        return root, git

    def test_an_agents_md_edit_since_capture_is_rejected(self):
        from lib.theme_factory.gitstate import instruction_equivalent
        from lib.theme_factory.release import _load_bound_raw_artifact
        from lib.theme_factory.errors import PackageError

        root, git = self._git_repo()
        (root / "AGENTS.md").write_text("v1\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "baseline")
        baseline = git("rev-parse", "HEAD")
        (root / "AGENTS.md").write_text("v2\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "agents.md changed")
        after_edit = git("rev-parse", "HEAD")

        evidence_dir = root / ".agents/evaluations/runtime/2026-09-17-release-linen"
        evidence_dir.mkdir(parents=True)
        reference = self._write_raw_artifact(evidence_dir, baseline)

        with self.assertRaises(PackageError):
            _load_bound_raw_artifact(
                evidence_dir, reference, "linen", after_edit, "d" * 64,
                "Layer E runtime claude", commit_equivalence=instruction_equivalent,
            )

    def test_a_readme_only_edit_since_capture_still_binds(self):
        from lib.theme_factory.gitstate import instruction_equivalent
        from lib.theme_factory.release import _load_bound_raw_artifact

        root, git = self._git_repo()
        (root / "AGENTS.md").write_text("v1\n", encoding="utf-8")
        (root / "README.md").write_text("v1\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "baseline")
        baseline = git("rev-parse", "HEAD")
        (root / "README.md").write_text("v2\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "readme changed")
        after_edit = git("rev-parse", "HEAD")

        evidence_dir = root / ".agents/evaluations/runtime/2026-09-17-release-linen"
        evidence_dir.mkdir(parents=True)
        reference = self._write_raw_artifact(evidence_dir, baseline)

        raw = _load_bound_raw_artifact(
            evidence_dir, reference, "linen", after_edit, "d" * 64,
            "Layer E runtime claude", commit_equivalence=instruction_equivalent,
        )
        self.assertEqual(raw["runtime"], "claude")


class AssertCleanSourceTests(unittest.TestCase):
    """Task 4 (verification-integrity-defects plan): tools/live_matrix.py and
    tools/browser_matrix.py each checked git status --porcelain once, at startup. A tree that goes
    dirty mid-run (e.g. re-running the agent smokes mid-pipeline, which writes
    tests/agent-smoke/runs/*.json) passed the theme in flight and only failed the *next* one.
    assert_clean_source is meant to be called before each unit of live capture work, not once.
    """

    def _git_repo(self):
        temp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(temp, ignore_errors=True))
        root = Path(temp)

        def git(*args):
            return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()

        git("init", "-q")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        (root / "lib.py").write_text("print(1)\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "baseline")
        return root

    def test_a_clean_tree_passes_silently(self):
        from lib.theme_factory.gitstate import assert_clean_source
        root = self._git_repo()
        assert_clean_source(root)  # must not raise

    def test_a_dirty_tracked_file_raises_and_names_it(self):
        from lib.theme_factory.gitstate import assert_clean_source
        root = self._git_repo()
        (root / "lib.py").write_text("print(2)\n", encoding="utf-8")
        with self.assertRaises(RuntimeError) as ctx:
            assert_clean_source(root)
        self.assertIn("lib.py", str(ctx.exception))

    def test_an_untracked_file_outside_the_evidence_root_raises_and_names_it(self):
        # exactly the 2026-09-17 incident: re-running a smoke mid-pipeline wrote a new, untracked
        # dated run directory under an already-tracked tests/agent-smoke/runs/.
        from lib.theme_factory.gitstate import assert_clean_source
        root = self._git_repo()
        import subprocess as sp
        (root / "tests" / "agent-smoke" / "runs" / "2026-09-16").mkdir(parents=True)
        (root / "tests" / "agent-smoke" / "runs" / "2026-09-16" / "claude.json").write_text("{}", encoding="utf-8")
        sp.run(["git", "add", "-A"], cwd=root, check=True)
        sp.run(["git", "commit", "-q", "-m", "existing runs"], cwd=root, check=True)
        (root / "tests" / "agent-smoke" / "runs" / "2026-09-17").mkdir(parents=True)
        (root / "tests" / "agent-smoke" / "runs" / "2026-09-17" / "claude.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(RuntimeError) as ctx:
            assert_clean_source(root)
        self.assertIn("claude.json", str(ctx.exception))

    def test_evidence_root_changes_do_not_raise(self):
        from lib.theme_factory.gitstate import assert_clean_source, EVIDENCE_ROOT
        root = self._git_repo()
        evidence = root / EVIDENCE_ROOT / "2026-09-17-release-linen"
        evidence.mkdir(parents=True)
        (evidence / "evidence.json").write_text("{}", encoding="utf-8")
        assert_clean_source(root)  # must not raise

    def test_markdown_only_changes_do_not_raise(self):
        from lib.theme_factory.gitstate import assert_clean_source
        root = self._git_repo()
        (root / "README.md").write_text("# notes\n", encoding="utf-8")
        assert_clean_source(root)  # must not raise

    def test_a_tree_that_goes_dirty_between_two_calls_aborts_on_the_second(self):
        """The property the plan actually cares about: catching dirt introduced *between*
        operations, not just at the start of the whole run."""
        from lib.theme_factory.gitstate import assert_clean_source
        root = self._git_repo()
        assert_clean_source(root)  # first operation: tree is clean, proceeds
        (root / "lib.py").write_text("print(2)\n", encoding="utf-8")  # something writes mid-run
        with self.assertRaises(RuntimeError):
            assert_clean_source(root)  # second operation: must abort now, not after it runs


if __name__ == "__main__":
    unittest.main()

