from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.learn import session_feedback_seed as seed


class SessionFeedbackSeedTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-d023-feedback-"))

    def make_fixture(self) -> Path:
        root = self.root()
        build = root / "core" / "BUILD"
        reviews = build / "reviews"
        reviews.mkdir(parents=True)
        (build / "REGISTRY.json").write_text(
            json.dumps(
                {
                    "active_builds": [
                        {
                            "id": "SPEC_merged",
                            "branch": "build/SPEC_merged",
                            "base_branch": "feat/headless-build",
                            "status": "merged",
                            "spec": "core/BUILD/specs/SPEC_merged.md",
                            "tests_passed": True,
                            "notes": "Merged after guarded tests passed.",
                        },
                        {
                            "id": "SPEC_building",
                            "branch": "build/SPEC_building",
                            "status": "building",
                            "notes": "Still active.",
                        },
                        {
                            "id": "SPEC_done_self_reported",
                            "branch": "build/SPEC_done_self_reported",
                            "status": "done",
                            "notes": "Awaiting independent review.",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        (reviews / "approve.md").write_text(
            "# AI Review - build/SPEC_merged\n\n"
            "**Verdict:** APPROVE · **Risk:** low\n\n"
            "**Summary:** Tests pass and guardrails hold.\n\n"
            "## Findings\n"
            "- Scope is contained.\n"
            "- No live authority granted.\n",
            encoding="utf-8",
        )
        (reviews / "veto.md").write_text(
            "# AI Review - build/SPEC_bad\n\n"
            "**Verdict:** REQUEST_CHANGES · **Risk:** high\n\n"
            "**Summary:** Missing rollback and tests.\n\n"
            "## Findings\n"
            "- Tests absent.\n",
            encoding="utf-8",
        )
        (build / "feedback_session.jsonl").write_text(
            json.dumps(
                {
                    "type": "conversation_rating",
                    "session_id": "chat-1",
                    "rating": 5,
                    "prompt": "Owner chat session",
                    "comment": "Concise status first, then details.",
                }
            )
            + "\n"
            + json.dumps(
                {
                    "type": "veto",
                    "session_id": "chat-2",
                    "prompt": "Asked to auto-send a message",
                    "reason": "Public outreach must wait for James approval.",
                    "vetoed_action": "Send the message without approval.",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return root

    def test_collects_merge_review_veto_and_rating_signals(self) -> None:
        rows = seed.collect_session_feedback(self.make_fixture(), captured_at="2026-06-16T00:00:00Z")

        signal_types = {row["signal_type"] for row in rows}
        self.assertIn("merge_outcome", signal_types)
        self.assertIn("review_outcome", signal_types)
        self.assertIn("veto", signal_types)
        self.assertIn("conversation_rating", signal_types)
        self.assertTrue(all(row["schema"] == "session-feedback-seed.v1" for row in rows))
        self.assertTrue(all(row["preference"]["chosen"] for row in rows))
        self.assertTrue(all(row["preference"]["rejected"] for row in rows))

    def test_deterministic_ids_and_order(self) -> None:
        root = self.make_fixture()

        first = seed.collect_session_feedback(root, captured_at="2026-06-16T00:00:00Z")
        second = seed.collect_session_feedback(root, captured_at="2026-06-16T00:00:00Z")

        self.assertEqual([row["id"] for row in first], [row["id"] for row in second])
        self.assertEqual([row["id"] for row in first], sorted(row["id"] for row in first))

    def test_rating_normalizes_to_preference_score(self) -> None:
        root = self.make_fixture()
        rows = seed.collect_session_feedback(root, captured_at="2026-06-16T00:00:00Z")

        rating = next(row for row in rows if row["signal_type"] == "conversation_rating")

        self.assertEqual(rating["score"], 1.0)
        self.assertEqual(rating["outcome"], "positive")

    def test_signed_rating_one_stays_positive(self) -> None:
        root = self.root()
        build = root / "core" / "BUILD"
        build.mkdir(parents=True)
        (build / "feedback_signed.jsonl").write_text(
            json.dumps(
                {
                    "type": "conversation_rating",
                    "session_id": "chat-signed",
                    "rating": 1,
                    "rating_scale": "-1..1",
                    "prompt": "Conversation score",
                    "comment": "This is the preferred pattern.",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        rows = seed.collect_session_feedback(root, captured_at="2026-06-16T00:00:00Z")

        self.assertEqual(rows[0]["score"], 1.0)
        self.assertEqual(rows[0]["outcome"], "positive")

    def test_done_registry_rows_are_not_learning_feedback(self) -> None:
        rows = seed.collect_session_feedback(self.make_fixture(), captured_at="2026-06-16T00:00:00Z")

        self.assertNotIn("SPEC_done_self_reported", {row["session_id"] for row in rows})

    def test_append_jsonl_dedupes_existing_ids(self) -> None:
        root = self.make_fixture()
        output = root / "session_feedback_seed.jsonl"
        rows = seed.collect_session_feedback(root, captured_at="2026-06-16T00:00:00Z")

        first = seed.append_jsonl(rows, output)
        second = seed.append_jsonl(rows, output)

        self.assertEqual(first, len(rows))
        self.assertEqual(second, 0)
        self.assertEqual(len(output.read_text(encoding="utf-8").splitlines()), len(rows))


if __name__ == "__main__":
    unittest.main()
