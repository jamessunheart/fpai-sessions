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
    "activation_audit": {
        "available": True,
        "total": 4,
        "counts": {"auto-activated": 1, "library": 1, "INERT": 2},
        "unexplained_inert_count": 1,
        "inert_capability_builds": [
            {
                "spec_id": "SPEC_d099_unused",
                "classification": "INERT",
                "explained": False,
                "explicit_build_kind": "",
            }
        ],
    },
    "awareness_probe": {
        "available": True,
        "source": "/tmp/ops.jsonl",
        "timestamp": "2026-06-16T00:00:00Z",
        "score_percent": 62.5,
        "ok": False,
        "successes": 5,
        "total": 8,
        "reason": "last build missing from bot context",
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
    "recent_user_messages": {
        "available": True,
        "source": "brain_index.thread + brain_index.tg_messages",
        "messages": [
            {"at": "2026-06-16T00:03:00Z", "surface": "telegram", "role": "user", "text": "what is queued?"},
            {"at": "2026-06-16T00:02:00Z", "surface": "laptop", "role": "james", "text": "current awareness score?"},
            {"at": "2026-06-16T00:01:00Z", "surface": "phone", "role": "james", "text": "last three messages"},
        ],
    },
    "queue_state": {
        "pending_specs_count": 2,
        "pending_specs": ["SPEC_d128_probe", "SPEC_d129_next"],
        "registry_status_counts": {"building": 1, "done": 3},
        "active_requests": [{"id": "SPEC_d128_probe", "branch": "build/SPEC_d128_probe", "status": "building"}],
    },
    "architecture_gaps": {"partial_or_gap_lines": ["PARTIAL: build loop has no idle improvement source"]},
    "services": {"available": True, "services": [{"name": "fpai-build-loop", "state": "active"}]},
    "available_resources": "# Available Resources\n\n## CLIs\n\n- git: /usr/bin/git\n",
}


class SelfAuditTests(unittest.TestCase):
    def test_run_self_audit_returns_valid_schema_on_fixture_data(self) -> None:
        def runner(prompt: str) -> str:
            self.assertIn("silent failures", prompt)
            self.assertIn("standard audit probes", prompt)
            self.assertIn("awareness_probe", prompt)
            self.assertIn("activation_audit", prompt)
            self.assertIn("SPEC_d099_unused", prompt)
            self.assertIn("recent_user_messages", prompt)
            self.assertIn("queue_state", prompt)
            self.assertIn("Local system evidence JSON", prompt)
            self.assertIn("available_resources", prompt)
            self.assertIn("git: /usr/bin/git", prompt)
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

    def test_collect_awareness_probe_uses_latest_ops_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ops.jsonl"
            rows = [
                {
                    "ts": "2026-06-16T10:00:00Z",
                    "event": "awareness_reliability_probe",
                    "source": "timer",
                    "ok": True,
                    "reliability": 1.0,
                    "successes": 8,
                    "total": 8,
                    "threshold": 0.95,
                    "reason": "ok",
                },
                {
                    "ts": "2026-06-16T11:00:00Z",
                    "event": "awareness_reliability_probe",
                    "source": "self_diagnostic",
                    "ok": False,
                    "reliability": 0.625,
                    "successes": 5,
                    "total": 8,
                    "threshold": 0.95,
                    "reason": "latest title missing",
                    "latest_title": "d127 visible",
                },
            ]
            ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

            probe = self_audit.collect_awareness_probe(ledger)

            self.assertTrue(probe["available"])
            self.assertEqual(probe["score_percent"], 62.5)
            self.assertFalse(probe["ok"])
            self.assertEqual(probe["probe_source"], "self_diagnostic")
            self.assertEqual(probe["reason"], "latest title missing")

    def test_collect_queue_state_reports_pending_and_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs = root / "specs"
            results = root / "results"
            specs.mkdir()
            results.mkdir()
            (specs / "SPEC_pending.md").write_text("# pending\n", encoding="utf-8")
            (specs / "SPEC_done.md").write_text("# done\n", encoding="utf-8")
            (results / "SPEC_done.result.md").write_text("# done result\n", encoding="utf-8")
            registry = root / "REGISTRY.json"
            registry.write_text(
                json.dumps(
                    {
                        "active_builds": [
                            {"id": "SPEC_pending", "branch": "build/SPEC_pending", "status": "building"},
                            {"id": "SPEC_done", "branch": "build/SPEC_done", "status": "done"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            state = self_audit.collect_queue_state(registry_path=registry, specs_dir=specs, results_dir=results)

            self.assertEqual(state["pending_specs_count"], 1)
            self.assertEqual(state["pending_specs"], ["SPEC_pending"])
            self.assertEqual(state["registry_status_counts"]["building"], 1)
            self.assertEqual(state["registry_status_counts"]["done"], 1)
        self.assertEqual(state["active_requests"][0]["id"], "SPEC_pending")

    def test_collect_recent_user_messages_has_missing_dsn_shape(self) -> None:
        old = {
            "BRAIN_INDEX_DB_URL": os.environ.pop("BRAIN_INDEX_DB_URL", None),
            "DATABASE_URL": os.environ.pop("DATABASE_URL", None),
            "DB_URL": os.environ.pop("DB_URL", None),
        }
        try:
            messages = self_audit.collect_recent_user_messages()
        finally:
            for key, value in old.items():
                if value is not None:
                    os.environ[key] = value

        self.assertFalse(messages["available"])
        self.assertEqual(messages["messages"], [])
        self.assertIn("missing local DB DSN", messages["reason"])


if __name__ == "__main__":
    unittest.main()
