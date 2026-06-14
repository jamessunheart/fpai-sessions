from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.consequence import watch


class ConsequenceWatchTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-consequence-watch-"))

    def proof_path(self, root: Path, body: str) -> Path:
        path = root / "PROOF_LOG.md"
        path.write_text(body, encoding="utf-8")
        return path

    def test_realized_unlock_when_artifact_exists(self) -> None:
        root = self.root()
        artifact = root / "docs" / "codex" / "RESULTS_LANE.md"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("# lane\n", encoding="utf-8")
        proof = self.proof_path(
            root,
            "- 2026-06-10 · [Game] · Intent solved: stage results lane · Unlocks next: review `docs/codex/RESULTS_LANE.md` · Proof: file generated · Next move: review it · AI(Codex)\n",
        )

        claims = watch.load_markdown_claims([proof])
        verdicts = watch.analyze(
            claims,
            repo_root=root,
            queue_path=root / "missing-queue.json",
            consequence_ledger_path=root / "missing-results.jsonl",
            apprentice_ledger_path=root / "missing-apprentice.jsonl",
        )

        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0].verdict, "realized")
        self.assertIn("artifact exists", verdicts[0].evidence[0])

    def test_claimed_but_absent_unlock_is_not_yet(self) -> None:
        root = self.root()
        proof = self.proof_path(
            root,
            "- Intent solved: draft impossible thing · Unlocks next: review `docs/codex/MISSING.md` · Proof: claimed · Next move: inspect · AI(Codex)\n",
        )

        verdict = watch.analyze(
            watch.load_markdown_claims([proof]),
            repo_root=root,
            queue_path=root / "missing-queue.json",
            consequence_ledger_path=root / "missing-results.jsonl",
            apprentice_ledger_path=root / "missing-apprentice.jsonl",
        )[0]

        self.assertEqual(verdict.verdict, "not-yet")
        self.assertIn("no observable evidence", verdict.evidence[0])

    def test_non_realized_result_ledger_is_no(self) -> None:
        root = self.root()
        ledger = root / "results.jsonl"
        ledger.write_text(
            json.dumps(
                {
                    "opportunity_id": "intake",
                    "outcome": "none",
                    "realized": False,
                    "detail": "no reply",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        claim = watch.ProofClaim(
            source="fixture",
            row_id="row-1",
            intent_solved="stage intake",
            unlock_claimed="intake reply landed",
        )

        verdict = watch.analyze(
            [claim],
            repo_root=root,
            queue_path=root / "missing-queue.json",
            consequence_ledger_path=ledger,
            apprentice_ledger_path=root / "missing-apprentice.jsonl",
        )[0]

        self.assertEqual(verdict.verdict, "no")
        self.assertIn("non-realized", verdict.evidence[0])

    def test_open_gate_needs_specific_match(self) -> None:
        root = self.root()
        queue = root / "queue.json"
        queue.write_text(
            json.dumps(
                {
                    "version": 1,
                    "gates": [
                        {
                            "id": "decision-run-the-dispatched-builds",
                            "question": "Run the dispatched builds?",
                            "state": "open",
                            "answer": "",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        generic = watch.ProofClaim("fixture", "generic", "built a system helper", "next build can run")
        specific = watch.ProofClaim(
            "fixture",
            "specific",
            "queued the fleet",
            "decision-run-the-dispatched-builds is answered",
        )

        generic_verdict, specific_verdict = watch.analyze(
            [generic, specific],
            repo_root=root,
            queue_path=queue,
            consequence_ledger_path=root / "missing-results.jsonl",
            apprentice_ledger_path=root / "missing-apprentice.jsonl",
        )

        self.assertEqual(generic_verdict.evidence, ["no observable evidence found yet"])
        self.assertEqual(specific_verdict.verdict, "not-yet")
        self.assertIn("still open", specific_verdict.evidence[0])

    def test_report_aggregates_and_dry_run_writes_nothing(self) -> None:
        root = self.root()
        report = root / "CONSEQUENCE_REPORT.md"
        claims = [
            watch.ProofClaim("fixture", "a", "solved a", "missing one"),
            watch.ProofClaim("fixture", "b", "solved b", "missing one"),
        ]
        verdicts = watch.analyze(
            claims,
            repo_root=root,
            queue_path=root / "missing-queue.json",
            consequence_ledger_path=root / "missing-results.jsonl",
            apprentice_ledger_path=root / "missing-apprentice.jsonl",
        )

        summary = watch.summarize(verdicts)
        text = watch.render_report(verdicts)
        path = watch.write_report(verdicts, report, dry_run=True)

        self.assertEqual(summary["counts"]["not-yet"], 2)
        self.assertEqual(summary["recurring_non_realizations"][0]["unlock"], "missing one")
        self.assertIn("Consequence Report", text)
        self.assertEqual(path, report)
        self.assertFalse(report.exists())

    def test_handoff_closeout_claims_are_parsed(self) -> None:
        root = self.root()
        handoff = root / "HANDOFF.md"
        handoff.write_text(
            "### 2026-06-10 · Thing\n\n"
            "- **Intent solved:** a real thing shipped\n"
            "- **Downstream intent unlocked:** next review exists\n"
            "- **Tests:** fixture OK\n",
            encoding="utf-8",
        )

        claims = watch.load_markdown_claims([handoff])

        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].intent_solved, "a real thing shipped")
        self.assertEqual(claims[0].unlock_claimed, "next review exists")


if __name__ == "__main__":
    unittest.main()
