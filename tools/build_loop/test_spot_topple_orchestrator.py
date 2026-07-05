#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.build_loop import spot_topple_orchestrator as orch


class SpotToppleOrchestratorTests(unittest.TestCase):
    def make_config(self, root: Path) -> orch.CycleConfig:
        (root / "core" / "BUILD" / "activate").mkdir(parents=True)
        (root / "core" / "BUILD" / "results").mkdir(parents=True)
        (root / "core" / "BUILD" / "specs").mkdir(parents=True)
        (root / "core" / "STATE").mkdir(parents=True)
        (root / "core" / "BUILD" / "signals").mkdir(parents=True)
        (root / "core" / "STATE" / "TREASURY_TODAY.md").write_text("Treasury: no autonomous spend.", encoding="utf-8")
        (root / "core" / "BUILD" / "signals" / "funnel_metrics.json").write_text(
            json.dumps({"assessment_leads": 1, "delivery_proof": "pending"}),
            encoding="utf-8",
        )
        hot = root / "HOT_STATE.md"
        hot.write_text("HOT_STATE: d193 assessment delivery proof is the next funnel domino.", encoding="utf-8")
        return orch.CycleConfig(
            repo_root=root,
            opportunity_ledger=root / "opportunities.json",
            opportunity_scan_ledger=root / "opportunity_scans.jsonl",
            capability_path=root / "capability.jsonl",
            ops_ledger=root / "ops.jsonl",
            cycle_ledger=root / "spot_topple.jsonl",
            digest_path=root / "digest.txt",
            portfolio_review_path=root / "portfolio_review.md",
            kill_switch=root / ".spot_topple_disabled",
            hot_state_path=hot,
            treasury_signal_path=Path("core/STATE/TREASURY_TODAY.md"),
            funnel_signal_path=Path("core/BUILD/signals/funnel_metrics.json"),
            dry_run=True,
            queue=False,
        )

    def test_cycle_spots_d193_funnel_domino_and_logs_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)

            result = orch.run_cycle(cfg, now="2026-07-05T12:00:00Z")

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["domino"]["id"], "assessment-funnel-delivery-proof")
            self.assertTrue(result["gate"]["auto_topple_ready"])
            self.assertEqual(result["queue"]["reason"], "dry-run")
            self.assertIn("Assessment Funnel Delivery Proof", (root / "digest.txt").read_text(encoding="utf-8"))
            portfolio_review = (root / "portfolio_review.md").read_text(encoding="utf-8")
            self.assertIn("PORTFOLIO REVIEW", portfolio_review)
            self.assertIn("QUALITY", portfolio_review)
            self.assertIn("VALUE", portfolio_review)
            rows = [json.loads(line) for line in (root / "spot_topple.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[-1]["domino"]["id"], "assessment-funnel-delivery-proof")
            self.assertEqual(rows[-1]["proof"]["activation_audit"]["unexplained_inert_count"], 0)

    def test_queue_mode_builds_decision_payload_without_db_when_injected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            cfg = orch.CycleConfig(**{**cfg.__dict__, "dry_run": False, "queue": True})
            captured = {}

            def fake_queue(payload: dict) -> orch.QueueResult:
                captured.update(payload)
                return orch.QueueResult(True, decision_id="d999", reason="queued", payload=payload)

            result = orch.run_cycle(cfg, now="2026-07-05T12:00:00Z", queue_fn=fake_queue)

            self.assertTrue(result["queue"]["queued"])
            self.assertEqual(result["queue"]["decision_id"], "d999")
            self.assertIn("AUTO SPEC", captured["build_spec"])
            self.assertIn("no money movement", captured["build_spec"])
            self.assertIn("spot_topple_real_execution", json.dumps(captured["liveness"]))

    def test_recent_queue_suppresses_duplicate_topple(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            cfg.cycle_ledger.write_text(
                json.dumps(
                    {
                        "ts": "2026-07-05T11:00:00Z",
                        "domino": {"id": "assessment-funnel-delivery-proof"},
                        "queue": {"queued": True, "decision_id": "d998"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            cfg = orch.CycleConfig(**{**cfg.__dict__, "dry_run": False, "queue": True})

            result = orch.run_cycle(
                cfg,
                now="2026-07-05T12:00:00Z",
                queue_fn=lambda payload: orch.QueueResult(True, decision_id="should-not-run", payload=payload),
            )

            self.assertFalse(result["queue"]["queued"])
            self.assertIn("recently queued", result["queue"]["reason"])

    def test_reserved_or_missing_capability_domino_is_not_auto_queued(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            domino = {
                "id": "reserved",
                "title": "Move Money",
                "axes": {"topple_reversibility": 10},
                "topple": {
                    "gate": "ai_reversible",
                    "next_action": "move money from treasury",
                    "proof": "ledger",
                },
            }

            gate = orch.gate_domino(domino, config=cfg)

            self.assertFalse(gate["auto_topple_ready"])
            self.assertIn("reserved", gate["reason"].lower())

    def test_kill_switch_disables_cycle_without_spotting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = self.make_config(root)
            cfg.kill_switch.write_text("", encoding="utf-8")

            result = orch.run_cycle(cfg, now="2026-07-05T12:00:00Z")

            self.assertEqual(result["status"], "disabled")
            self.assertIn("disabled", (root / "digest.txt").read_text(encoding="utf-8"))
            self.assertFalse((root / "opportunities.json").exists())


if __name__ == "__main__":
    unittest.main()
