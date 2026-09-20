import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from lib.theme_factory.evidence_cache import (
    EVIDENCE_CONTRACT_VERSION,
    EvidenceIdentity,
    checkpoint_valid,
    common_check_artifact_valid,
    write_common_check_artifact,
    write_checkpoint,
)


class EvidenceCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.path = self.root / "row.json"
        self.identity = EvidenceIdentity(
            source_commit="a" * 40,
            package_sha256="b" * 64,
            apex_version="26.1.4",
            browser_version="Chrome/140.0.7339.81",
            consumer="business",
            page="1",
            viewport=1440,
            scenario="browser-runtime",
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_exact_identity_is_a_hit(self):
        write_checkpoint(self.path, self.identity, {"status": "PASS"})
        diagnostics = []
        self.assertTrue(checkpoint_valid(self.path, self.identity, diagnostics))
        self.assertEqual(diagnostics, [])
        document = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(document["evidenceContractVersion"], EVIDENCE_CONTRACT_VERSION)

    def test_every_identity_field_is_required_for_a_hit(self):
        write_checkpoint(self.path, self.identity, {"status": "PASS"})
        mutations = {
            "source_commit": "c" * 40,
            "package_sha256": "d" * 64,
            "apex_version": "26.1.5",
            "browser_version": "Chrome/141.0.1.2",
            "consumer": "minimal",
            "page": "2",
            "viewport": 375,
            "scenario": "theme-lab",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                diagnostics = []
                self.assertFalse(checkpoint_valid(
                    self.path, replace(self.identity, **{field: value}), diagnostics
                ))
                self.assertTrue(any(field in message for message in diagnostics), diagnostics)

    def test_contract_version_mismatch_is_a_miss(self):
        write_checkpoint(self.path, self.identity, {"status": "PASS"})
        document = json.loads(self.path.read_text(encoding="utf-8"))
        document["evidenceContractVersion"] -= 1
        self.path.write_text(json.dumps(document), encoding="utf-8")
        diagnostics = []
        self.assertFalse(checkpoint_valid(self.path, self.identity, diagnostics))
        self.assertTrue(any("contract" in item.lower() for item in diagnostics))

    def test_malformed_json_is_a_diagnostic_miss(self):
        self.path.write_text("{not json", encoding="utf-8")
        diagnostics = []
        self.assertFalse(checkpoint_valid(self.path, self.identity, diagnostics))
        self.assertTrue(any("json" in item.lower() for item in diagnostics))

    def test_schema_failure_is_a_diagnostic_miss(self):
        self.path.write_text(json.dumps({"evidenceContractVersion": EVIDENCE_CONTRACT_VERSION}),
                             encoding="utf-8")
        diagnostics = []
        self.assertFalse(checkpoint_valid(self.path, self.identity, diagnostics))
        self.assertTrue(any("missing" in item.lower() for item in diagnostics))

    def test_browser_payload_must_satisfy_runtime_schema_and_identity(self):
        write_checkpoint(self.path, self.identity, {"evidenceType": "browser-runtime"})
        diagnostics = []
        self.assertFalse(checkpoint_valid(self.path, self.identity, diagnostics))
        self.assertTrue(any("runtime" in item.lower() for item in diagnostics), diagnostics)

    def test_symlink_checkpoint_is_never_followed(self):
        target = self.root / "outside.json"
        write_checkpoint(target, self.identity, {"status": "PASS"})
        self.path.symlink_to(target)
        diagnostics = []
        self.assertFalse(checkpoint_valid(self.path, self.identity, diagnostics))
        self.assertTrue(any("symlink" in item.lower() for item in diagnostics))

    def test_common_check_artifact_is_bound_to_current_source_identity(self):
        artifact = self.root / "common.json"
        with patch(
            "lib.theme_factory.evidence_cache.current_source_identity",
            return_value=("a" * 40, "b" * 40),
        ):
            write_common_check_artifact(artifact)
            self.assertTrue(common_check_artifact_valid(artifact))
        with patch(
            "lib.theme_factory.evidence_cache.current_source_identity",
            return_value=("c" * 40, "d" * 40),
        ):
            diagnostics = []
            self.assertFalse(common_check_artifact_valid(artifact, diagnostics=diagnostics))
            self.assertTrue(any("source" in item.lower() for item in diagnostics))


if __name__ == "__main__":
    unittest.main()
