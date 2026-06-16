from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.council import self_diagnostic


class SelfDiagnosticTests(unittest.TestCase):
    def test_questions_are_sent_to_telegram(self) -> None:
        sent: list[str] = []

        def runner(_prompt: str) -> str:
            return json.dumps(
                [
                    {
                        "title": "Improve uncertainty answers",
                        "spec": "Add a tested uncertainty-recall surface for recent owner-chat misses.",
                        "why": "The bot named recent questions it could not answer confidently.",
                        "priority": 1,
                    }
                ]
            )

        with tempfile.TemporaryDirectory() as tmp:
            specs = self_diagnostic.run_diagnostic_dialogue(
                send_func=sent.append,
                read_messages_func=lambda _since: [],
                claude_runner=runner,
                queue_func=lambda _spec: True,
                sleep_func=lambda _seconds: None,
                ops_ledger=Path(tmp) / "ops.jsonl",
                last_diagnostic_file=Path(tmp) / ".last",
                context_file=Path(tmp) / ".context.json",
                now=datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc),
                response_timeout_seconds=0,
                question_pause_seconds=0,
            )

        self.assertEqual(len(specs), 1)
        self.assertIn("System self-diagnostic [diag-20260616120000]", sent[0])
        self.assertTrue(any("What questions has James asked recently" in item for item in sent))
        self.assertTrue(any("What have you been corrected on most" in item for item in sent))
        self.assertTrue(any("What capability do you most wish" in item for item in sent))
        self.assertTrue(sent[-1].startswith("Self-diagnostic complete. Queued 1 improvements"))

    def test_bot_responses_collected_from_tg_messages(self) -> None:
        base = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
        rows = [
            {"role": "bot", "text": "I could not answer the build queue state confidently.", "at": base + timedelta(seconds=5)},
            {"role": "bot", "text": "I keep getting live status wrong.", "at": base + timedelta(seconds=10)},
            {"role": "bot", "text": "I wish I had rejected-build context.", "at": base + timedelta(seconds=15)},
        ]
        captured_prompt = ""

        def runner(prompt: str) -> str:
            nonlocal captured_prompt
            captured_prompt = prompt
            return json.dumps(
                [
                    {"title": f"Spec {idx}", "spec": "Build a focused diagnostic repair with tests.", "why": "Because the bot asked for it.", "priority": idx}
                    for idx in range(1, 4)
                ]
            )

        queued: list[dict] = []
        with tempfile.TemporaryDirectory() as tmp:
            specs = self_diagnostic.run_diagnostic_dialogue(
                send_func=lambda _text: None,
                read_messages_func=lambda _since: rows,
                claude_runner=runner,
                queue_func=lambda spec: not queued.append(spec),
                sleep_func=lambda _seconds: None,
                ops_ledger=Path(tmp) / "ops.jsonl",
                last_diagnostic_file=Path(tmp) / ".last",
                context_file=Path(tmp) / ".context.json",
                now=base,
                response_timeout_seconds=0,
                question_pause_seconds=0,
            )

        self.assertEqual(len(specs), 3)
        self.assertIn("build queue state", captured_prompt)
        self.assertIn("live status wrong", captured_prompt)
        self.assertIn("rejected-build context", captured_prompt)
        self.assertEqual([item["title"] for item in queued], ["Spec 1", "Spec 2", "Spec 3"])

    def test_james_redirect_overrides_bot_answers_in_synthesis(self) -> None:
        base = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
        rows = [
            {"role": "bot", "text": "I want more generic metrics.", "at": base + timedelta(seconds=5)},
            {"role": "user", "text": "Stop. The real gap is that rejected builds are invisible.", "at": base + timedelta(seconds=6)},
        ]
        prompts: list[str] = []

        def runner(prompt: str) -> str:
            prompts.append(prompt)
            return json.dumps(
                [
                    {
                        "title": "Surface rejected builds",
                        "spec": "Add rejected-build evidence to bot context and diagnostic summaries with tests.",
                        "why": "James redirected the audit to rejected-build visibility.",
                        "priority": 1,
                    }
                ]
            )

        queued: list[dict] = []
        with tempfile.TemporaryDirectory() as tmp:
            self_diagnostic.run_diagnostic_dialogue(
                send_func=lambda _text: None,
                read_messages_func=lambda _since: rows,
                claude_runner=runner,
                queue_func=lambda spec: not queued.append(spec),
                sleep_func=lambda _seconds: None,
                ops_ledger=Path(tmp) / "ops.jsonl",
                last_diagnostic_file=Path(tmp) / ".last",
                context_file=Path(tmp) / ".context.json",
                now=base,
                response_timeout_seconds=0,
                question_pause_seconds=0,
            )

        self.assertIn("weight=2.0", prompts[0])
        self.assertIn("Stop. The real gap is that rejected builds are invisible.", prompts[0])
        self.assertEqual(queued[0]["title"], "Surface rejected builds")

    def test_max_three_specs_generated(self) -> None:
        raw = [
            {"title": f"Spec {idx}", "spec": "Build a bounded improvement with focused tests.", "why": "It is high leverage.", "priority": idx}
            for idx in range(1, 6)
        ]
        specs = self_diagnostic.validate_specs(raw)
        self.assertEqual(len(specs), 3)
        self.assertEqual(specs[-1]["title"], "Spec 3")

    def test_48h_cooldown_respected(self) -> None:
        now = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
        blocked = self_diagnostic.should_trigger_diagnostic(
            last_diagnostic_text="2026-06-15T12:00:00Z",
            queue_empty=True,
            queue_empty_age_hours=8,
            merged_since_last=20,
            now=now,
        )
        due = self_diagnostic.should_trigger_diagnostic(
            last_diagnostic_text="2026-06-14T11:00:00Z",
            queue_empty=True,
            queue_empty_age_hours=4.1,
            merged_since_last=0,
            now=now,
        )
        self.assertFalse(blocked.should_run)
        self.assertEqual(blocked.reason, "48h cooldown active")
        self.assertTrue(due.should_run)
        self.assertEqual(due.trigger, "idle_queue")

    def test_self_diagnostic_disable_skips(self) -> None:
        old = os.environ.get("SELF_DIAGNOSTIC_DISABLE")
        os.environ["SELF_DIAGNOSTIC_DISABLE"] = "1"
        try:
            result = self_diagnostic.should_trigger_diagnostic(
                last_diagnostic_text=None,
                queue_empty=True,
                queue_empty_age_hours=8,
                merged_since_last=20,
                now=datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc),
            )
            specs = self_diagnostic.run_diagnostic_dialogue(
                send_func=lambda _text: self.fail("send should not be called"),
                read_messages_func=lambda _since: [],
                claude_runner=lambda _prompt: "[]",
                queue_func=lambda _spec: True,
            )
        finally:
            if old is None:
                os.environ.pop("SELF_DIAGNOSTIC_DISABLE", None)
            else:
                os.environ["SELF_DIAGNOSTIC_DISABLE"] = old
        self.assertFalse(result.should_run)
        self.assertEqual(specs, [])

    def test_trigger_from_files_tracks_queue_empty_age(self) -> None:
        now = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            last = root / ".last"
            empty_since = root / ".empty"
            ops = root / "ops.jsonl"
            last.write_text("2026-06-14T10:00:00Z\n", encoding="utf-8")
            empty_since.write_text("2026-06-16T07:30:00Z\n", encoding="utf-8")
            decision = self_diagnostic.trigger_from_files(
                queue_empty=True,
                last_diagnostic_file=last,
                queue_empty_since_file=empty_since,
                ops_ledger=ops,
                now=now,
            )
        self.assertTrue(decision.should_run)
        self.assertEqual(decision.trigger, "idle_queue")


if __name__ == "__main__":
    unittest.main()
