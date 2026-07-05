from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.growth import process_leads
from tools.growth import sales_followup as sf


def _lead_file(root: Path) -> Path:
    path = root / "alex-rivera.md"
    path.write_text(
        "---\n"
        "name: Alex Rivera\n"
        "email: alex@example.com\n"
        "company: Rivera Studio\n"
        "bottleneck: Manual spreadsheet handoffs are eating 8 hours a week\n"
        "---\n",
        encoding="utf-8",
    )
    return path


def _deliverable_file(root: Path) -> Path:
    path = root / "alex-rivera.deliverable.md"
    path.write_text(
        "# Your Full Potential Assessment - Rivera Studio\n\n"
        "## Allocation Score: **58/100**\n\n"
        "Your weakest dimension - **time** - is where the most capability is trapped.\n\n"
        "## Your 3 highest-value opportunities\n\n"
        "1. **Automate intake handoffs** _(weak: time)_ - manual spreadsheet work · **$18k/yr**\n"
        "2. **Route quote follow-up** _(weak: attention)_ - leads wait too long · **$12k/yr**\n"
        "3. **Reuse proof assets** _(weak: knowledge)_ - case studies are underused · **$8k/yr**\n",
        encoding="utf-8",
    )
    return path


class SalesFollowupTests(unittest.TestCase):
    def test_plan_for_real_lead_drafts_full_sequence_with_signature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = sf.plan_for_lead(
                _lead_file(root),
                _deliverable_file(root),
                model_runner=lambda _prompt: (_ for _ in ()).throw(RuntimeError("no model")),
            )

        self.assertEqual(plan["lead"]["name"], "Alex Rivera")
        self.assertEqual(plan["lead"]["allocation_score"], 58)
        self.assertEqual(plan["lead"]["weakest_dimension"], "time")
        self.assertEqual(plan["stage"], "delivered")
        self.assertEqual([item["kind"] for item in plan["sequence"]], list(sf.TOUCH_KINDS))
        self.assertIn("James Sunheart + AI", plan["sequence"][0]["body"])
        self.assertIn("Reply unsubscribe to stop", plan["sequence"][0]["body"])
        self.assertIn("payment", " ".join(plan["reserved_walls"]).lower())

    def test_default_stage_writes_lane_and_send_approval_gates_without_sending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = sf.plan_for_lead(
                _lead_file(root),
                _deliverable_file(root),
                model_runner=lambda _prompt: (_ for _ in ()).throw(RuntimeError("no model")),
            )
            sender = mock.Mock(return_value=(True, "sent"))
            result = sf.stage_plan(
                plan,
                lane_path=root / "lane.md",
                queue_path=root / "queue.json",
                state_path=root / "state.json",
                ledger_path=root / "touches.jsonl",
                brain_index_dsn="",
                sender=sender,
                live=True,
            )

            queue = json.loads((root / "queue.json").read_text(encoding="utf-8"))
            state = json.loads((root / "state.json").read_text(encoding="utf-8"))
            ledger = (root / "touches.jsonl").read_text(encoding="utf-8")
            lane_text = (root / "lane.md").read_text(encoding="utf-8")

        sender.assert_not_called()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["gates"]), 4)
        self.assertEqual(len(queue["gates"]), 4)
        self.assertEqual(state["alex-rivera"]["stage"], "delivered")
        self.assertIn("Draft Sequence", lane_text)
        self.assertIn('"action": "drafted"', ledger)

    def test_reply_with_blueprint_price_escalates_close_wall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            replies = [{"id": "m1", "subject": "Blueprint", "body": "What does the Blueprint cost and how do we proceed?"}]
            plan = sf.plan_for_lead(
                _lead_file(root),
                _deliverable_file(root),
                replies=replies,
                model_runner=lambda _prompt: (_ for _ in ()).throw(RuntimeError("no model")),
            )
            result = sf.stage_plan(
                plan,
                lane_path=root / "lane.md",
                queue_path=root / "queue.json",
                state_path=root / "state.json",
                ledger_path=root / "touches.jsonl",
                brain_index_dsn="",
            )
            queue = json.loads((root / "queue.json").read_text(encoding="utf-8"))

        self.assertEqual(plan["stage"], "proposed")
        self.assertTrue(any(gate["id"] == "sales-close-alex-rivera" for gate in result["gates"]))
        self.assertTrue(any("Close/payment wall" in gate["question"] for gate in queue["gates"]))
        self.assertIn("before talking payment", plan["reply_drafts"][0]["body"])

    def test_sales_autosend_sends_one_touch_then_rate_limits_remaining(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = sf.plan_for_lead(
                _lead_file(root),
                _deliverable_file(root),
                model_runner=lambda _prompt: (_ for _ in ()).throw(RuntimeError("no model")),
            )
            sender = mock.Mock(return_value=(True, "sent"))
            with mock.patch.dict(os.environ, {"SALES_AUTOSEND": "1"}):
                result = sf.stage_plan(
                    plan,
                    lane_path=root / "lane.md",
                    queue_path=root / "queue.json",
                    state_path=root / "state.json",
                    ledger_path=root / "touches.jsonl",
                    brain_index_dsn="",
                    sender=sender,
                    live=True,
                )
            queue_exists = (root / "queue.json").exists()
            ledger = (root / "touches.jsonl").read_text(encoding="utf-8")

        self.assertEqual(len(result["gates"]), 0)
        self.assertFalse(queue_exists)
        self.assertEqual(sender.call_count, 1)
        self.assertEqual(len(result["sent"]), 1)
        self.assertIn("rate-limited", ledger)

    def test_engagement_updates_stage_counts_and_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = sf.update_engagement(
                "lead-1",
                "click",
                state_path=root / "state.json",
                ledger_path=root / "touches.jsonl",
                brain_index_dsn="",
            )

        self.assertEqual(state["stage"], "engaged")
        self.assertEqual(state["engagement"]["click"], 1)

    def test_process_leads_stages_followup_after_successful_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lead = _lead_file(root)
            deliverable = _deliverable_file(root)
            with mock.patch.object(process_leads, "stage_sales_followup_for_delivered_lead", wraps=process_leads.stage_sales_followup_for_delivered_lead) as wrapped, \
                 mock.patch.object(sf, "plan_for_lead", return_value={"lead": {"lead_id": "alex-rivera"}, "stage": "delivered", "sequence": [], "reply_drafts": []}), \
                 mock.patch.object(sf, "stage_plan", return_value={"status": "ok", "gates": [{"id": "g1"}]}):
                ok, detail = process_leads.stage_sales_followup_for_delivered_lead(lead, deliverable)

        self.assertTrue(ok)
        self.assertIn("1 gate", detail)
        wrapped.assert_called_once()


if __name__ == "__main__":
    unittest.main()
