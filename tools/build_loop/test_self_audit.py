#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.build_loop import self_audit


FIXTURE_CONTEXT = {
    "generated_at": "2026-06-16T00:00:00Z",
    "ops_ledger_7d": {
        "rows": 4,
        "by_event": {"ran": 2, "failed": 1, "merged": 1},
        "failures": ["build-loop failed review timeout"],
        "silent_or_no_work_count": 2,
    },
    "review_patterns": {
        "request_changes": 2,
        "patterns": [{"text": "missing regression test for failure path", "count": 2}],
    },
    "brain_index": {
        "available": True,
        "decisions": {"answered_needs_build_unbuilt": 3, "high_confidence_overrides": 1, "reversal_patterns": 1},
        "corrections": {"top_topics": [{"topic": "handoff drift", "count": 4}]},
    },
    "architecture_gaps": {"partial_or_gap_lines": ["PARTIAL: build loop has no idle improvement source"]},
    "services": {"available": True, "services": [{"name": "fpai-build-loop", "state": "active"}]},
}


class SelfAuditTests(unittest.TestCase):
    def test_run_self_audit_returns_valid_schema_on_fixture_data(self) -> None:
        def runner(prompt: str) -> str:
            self.assertIn("silent failures", prompt)
            self.assertIn("Local system evidence JSON", prompt)
            return json.dumps(
                [
                    {
                        "title": "Add loop failure classifier",
                        "spec": "Build a repo-local classifier for repeated build-loop failures with tests and report-only output.",
                        "why": "Repeated failures need one categorized repair path instead of scattered review notes.",
                        "priority": 1,
                        "risk_class": "low",
                    }
                ]
            )

        specs = self_audit.run_self_audit(claude_runner=runner, context=FIXTURE_CONTEXT)
        self.assertEqual(len(specs), 1)
        self.assertEqual(set(specs[0]), {"title", "spec", "why", "priority", "risk_class"})
        self.assertLess(len(specs[0]["title"]), 60)
        self.assertIn(specs[0]["risk_class"], {"low", "med"})

    def test_run_self_audit_caps_to_three_specs_and_filters_forbidden(self) -> None:
        raw = []
        for idx in range(5):
            raw.append(
                {
                    "title": f"Safe improvement {idx}",
                    "spec": "Add a tested repo-local report for recurring review failures.",
                    "why": "The same review class keeps returning.",
                    "priority": idx + 1,
                    "risk_class": "low",
                }
            )
        raw.insert(
            0,
            {
                "title": "Move treasury money",
                "spec": "Move money automatically from a wallet.",
                "why": "Forbidden action should be filtered.",
                "priority": 0,
                "risk_class": "low",
            },
        )
        specs = self_audit.run_self_audit(claude_runner=lambda _prompt: json.dumps(raw), context=FIXTURE_CONTEXT)
        self.assertEqual(len(specs), 3)
        self.assertTrue(all("money" not in item["spec"].lower() for item in specs))

    def test_self_audit_disable_skips(self) -> None:
        old = os.environ.get("SELF_AUDIT_DISABLE")
        os.environ["SELF_AUDIT_DISABLE"] = "1"
        try:
            specs = self_audit.run_self_audit(
                claude_runner=lambda _prompt: self.fail("runner should not be called"),
                context=FIXTURE_CONTEXT,
            )
        finally:
            if old is None:
                os.environ.pop("SELF_AUDIT_DISABLE", None)
            else:
                os.environ["SELF_AUDIT_DISABLE"] = old
        self.assertEqual(specs, [])

    def test_trigger_logic_respects_idle_gap_merge_count_and_daily_cap(self) -> None:
        now = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(
            self_audit.detect_trigger_reason(queue_empty=True, age_hours=2.1, merged_since_audit=0),
            "idle",
        )
        self.assertIsNone(self_audit.detect_trigger_reason(queue_empty=True, age_hours=1.9, merged_since_audit=0))
        self.assertEqual(
            self_audit.detect_trigger_reason(queue_empty=False, age_hours=0.5, merged_since_audit=10),
            "merge_count",
        )

        capped = self_audit.should_trigger_audit(
            queue_empty=True,
            last_audit_text="2026-06-16-09",
            merged_since_audit=0,
            now=now,
        )
        self.assertFalse(capped.should_run)
        self.assertEqual(capped.reason, "daily audit cap active")

        due = self_audit.should_trigger_audit(
            queue_empty=True,
            last_audit_text="2026-06-15-11",
            merged_since_audit=0,
            now=now,
        )
        self.assertTrue(due.should_run)
        self.assertEqual(due.trigger, "idle")

    def test_invalid_claude_json_does_not_crash(self) -> None:
        specs = self_audit.run_self_audit(claude_runner=lambda _prompt: "not json", context=FIXTURE_CONTEXT)
        self.assertEqual(specs, [])

    def test_trigger_from_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            last = root / ".last_audit_date"
            merged = root / ".merged_since_audit"
            last.write_text("2026-06-15-11\n", encoding="utf-8")
            merged.write_text("0\n", encoding="utf-8")
            decision = self_audit.trigger_from_files(
                queue_empty=True,
                last_audit_file=last,
                merged_counter_file=merged,
                now=datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc),
            )
            self.assertTrue(decision.should_run)
            self.assertEqual(decision.trigger, "idle")


if __name__ == "__main__":
    unittest.main()
