from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.build_loop import post_merge_reality_check, session_persistence_reality_repair


class SessionPersistenceRealityRepairTest(unittest.TestCase):
    def test_appends_rows_that_satisfy_post_merge_reality_checker(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-session-repair-"))
        repo = root / "repo"
        ledger = root / "ops.jsonl"
        (repo / "tools" / "continuity").mkdir(parents=True)
        (repo / "SERVICES" / "sunheart-brain" / "curator").mkdir(parents=True)
        (repo / "core" / "BUILD").mkdir(parents=True)
        (repo / "core" / "BUILD" / "REGISTRY.json").write_text('{"active_builds": []}\n', encoding="utf-8")
        (repo / "tools" / "continuity" / "session_persistence.py").write_text(
            """
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("command")
parser.add_argument("--repo-root")
parser.add_argument("--state-dir")
parser.add_argument("--session-id", default="unknown")
parser.add_argument("--progress-note", default="")
parser.add_argument("--json", action="store_true")
args = parser.parse_args()
state = Path(args.state_dir)
state.mkdir(parents=True, exist_ok=True)
path = state / "latest.json"
if args.command == "save":
    payload = {"schema": "fpai-session-snapshot.v1", "session_id": args.session_id}
    path.write_text(json.dumps(payload), encoding="utf-8")
    print(json.dumps(payload))
elif args.command == "show":
    print(path.read_text(encoding="utf-8"))
""".lstrip(),
            encoding="utf-8",
        )
        (repo / "SERVICES" / "sunheart-brain" / "curator" / "build_context.py").write_text("# integration\n", encoding="utf-8")

        result = session_persistence_reality_repair.append_repair_proof(ledger, repo_root=repo)

        self.assertTrue(result["ok"])
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["event"] for row in rows], ["liveness:pass", "feature_outcome"])
        decision = post_merge_reality_check.MergedDecision(
            decision_id="36a73161-fb6c-42c8-98b7-f5d479dfa08e",
            question="Session Persistence",
            build_branch=session_persistence_reality_repair.ORIGINAL_BRANCH,
            build_spec=session_persistence_reality_repair.ORIGINAL_SPEC_ID,
            proof_expected="liveness:pass and feature_outcome verdict=improved",
            liveness="",
            merged_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        evidence = post_merge_reality_check.collect_evidence(rows, decision)
        self.assertTrue(evidence.live)
        self.assertTrue(evidence.metric_moved)

    def test_returns_failure_without_improved_outcome_when_smoke_fails(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-session-repair-fail-"))
        ledger = root / "ops.jsonl"

        result = session_persistence_reality_repair.append_repair_proof(ledger, repo_root=root)

        self.assertFalse(result["ok"])
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event"], "liveness:fail")


if __name__ == "__main__":
    unittest.main()
