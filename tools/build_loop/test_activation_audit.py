#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.build_loop import activation_audit


class ActivationAuditTests(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-activation-audit-"))
        (root / "core" / "BUILD" / "activate").mkdir(parents=True)
        (root / "core" / "BUILD" / "results").mkdir(parents=True)
        (root / "core" / "BUILD" / "specs").mkdir(parents=True)
        (root / "SERVICES").mkdir()
        (root / "tools").mkdir()
        return root

    def test_classifies_activated_library_and_inert_builds(self) -> None:
        root = self.make_repo()
        (root / "core" / "BUILD" / "activate" / "SPEC_d001_auto.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        (root / "core" / "BUILD" / "results" / "SPEC_d002_library.result.md").write_text(
            "## Files Changed\n- `tools/library_mod.py`\n",
            encoding="utf-8",
        )
        (root / "tools" / "library_mod.py").write_text("def run(): pass\n", encoding="utf-8")
        (root / "SERVICES" / "live.py").write_text("from tools.library_mod import run\n", encoding="utf-8")
        (root / "core" / "BUILD" / "specs" / "SPEC_d003_inert.md").write_text(
            "# d003\n\nbuild_kind=inert\n",
            encoding="utf-8",
        )
        ledger = root / "ops.jsonl"
        ledger.write_text(
            json.dumps(
                {
                    "event": "activated",
                    "detail": "SPEC_d001_auto (guarded activate + smoke passed)",
                    "artifact": "build/SPEC_d001_auto",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        records = [
            activation_audit.BuildRecord("SPEC_d001_auto", branch="build/SPEC_d001_auto", sources=["fixture"]),
            activation_audit.BuildRecord("SPEC_d002_library", branch="build/SPEC_d002_library", sources=["fixture"]),
            activation_audit.BuildRecord("SPEC_d003_inert", branch="build/SPEC_d003_inert", sources=["fixture"]),
            activation_audit.BuildRecord("SPEC_d004_unknown", branch="build/SPEC_d004_unknown", sources=["fixture"]),
        ]

        payload = activation_audit.audit(root, ops_ledger=ledger, records=records)
        rows = {row["spec_id"]: row for row in payload["rows"]}

        self.assertEqual(rows["SPEC_d001_auto"]["classification"], "auto-activated")
        self.assertEqual(rows["SPEC_d002_library"]["classification"], "library")
        self.assertIn("SERVICES/live.py references", rows["SPEC_d002_library"]["reference_evidence"][0])
        self.assertEqual(rows["SPEC_d003_inert"]["classification"], "INERT")
        self.assertTrue(rows["SPEC_d003_inert"]["explained"])
        self.assertEqual(rows["SPEC_d004_unknown"]["classification"], "INERT")
        self.assertFalse(rows["SPEC_d004_unknown"]["explained"])
        self.assertEqual(payload["unexplained_inert"], ["SPEC_d004_unknown"])

    def test_discovers_merged_builds_from_registry_proof_and_ops(self) -> None:
        root = self.make_repo()
        (root / "core" / "BUILD" / "REGISTRY.json").write_text(
            json.dumps(
                {
                    "active_builds": [
                        {"id": "SPEC_d010_reg", "branch": "build/SPEC_d010_reg", "status": "merged"},
                        {"id": "SPEC_d011_done", "branch": "build/SPEC_d011_done", "status": "done"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        (root / "core" / "BUILD" / "PROOF_LOG.md").write_text(
            "- 2026-07-05 · SPEC_d012_proof · build/SPEC_d012_proof · merged · spec:x\n",
            encoding="utf-8",
        )
        ledger = root / "ops.jsonl"
        ledger.write_text(json.dumps({"event": "auto-merged", "detail": "SPEC_d013_ops (AI-approved)"}) + "\n")

        records = activation_audit.discover_merged_builds(root, ops_ledger=ledger)
        ids = [record.spec_id for record in records]

        self.assertEqual(ids, ["SPEC_d010_reg", "SPEC_d012_proof", "SPEC_d013_ops"])

    def test_legacy_declaration_explains_inert_without_activating(self) -> None:
        root = self.make_repo()
        (root / "core" / "BUILD" / "activation_declarations.json").write_text(
            json.dumps({"declarations": {"SPEC_legacy": {"build_kind": "inert", "reason": "legacy"}}}),
            encoding="utf-8",
        )
        records = [activation_audit.BuildRecord("SPEC_legacy", branch="build/SPEC_legacy", sources=["fixture"])]

        payload = activation_audit.audit(root, ops_ledger=root / "ops.jsonl", records=records)
        row = payload["rows"][0]

        self.assertEqual(row["classification"], "INERT")
        self.assertTrue(row["explained"])
        self.assertEqual(row["explicit_build_kind"], "inert")
        self.assertEqual(payload["unexplained_inert_count"], 0)

    def test_changed_file_parser_ignores_backticked_transcript_outside_section(self) -> None:
        root = self.make_repo()
        (root / "core" / "BUILD" / "results" / "SPEC_transcript.result.md").write_text(
            "# Result\n\n"
            "Transcript mentioned `docs/codex/README.md` and `signal -> intent`.\n\n"
            "## Files Changed\n"
            "- `tools/build_loop/activation_audit.py`\n"
            "## Tests\n"
            "- `python3 -m unittest`\n",
            encoding="utf-8",
        )

        changed = activation_audit.changed_files_for_spec(root, "SPEC_transcript")

        self.assertEqual(changed, ["tools/build_loop/activation_audit.py"])


if __name__ == "__main__":
    unittest.main()
