from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.learn import sync_corrections_to_dataset as syncer


class SyncCorrectionsToDatasetTest(unittest.TestCase):
    def temp_root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-review-signals-"))

    def test_parse_ai_review_verdict_and_findings(self) -> None:
        root = self.temp_root()
        review = root / "build-SPEC_d123_example.md"
        review.write_text(
            "# AI Review - build/SPEC_d123_example\n\n"
            "**Verdict:** REQUEST_CHANGES · **Risk:** med\n\n"
            "**Summary:** Small fix but live prompt path can fail.\n\n"
            "## Findings\n"
            "- Wrap the DB read in try/except.\n"
            "- Respect max_chars on the combined suffix.\n",
            encoding="utf-8",
        )

        signal = syncer.parse_review_file(review)

        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal.spec_id, "SPEC_d123_example")
        self.assertEqual(signal.verdict, "request_changes")
        self.assertIn("live prompt path", signal.reasons)
        self.assertIn("try/except", signal.reasons)
        self.assertIn("#sha256=", signal.code_ref)

    def test_parse_council_and_protected_blocked_reviews(self) -> None:
        root = self.temp_root()
        council = root / "SPEC_d087_terms.council.md"
        council.write_text(
            "# SPEC_d087 Council Review\n\n"
            "## Council Lenses\n\n"
            "### Pragmatist\n\n"
            "The artifact is usable for review.\n\n"
            "## Verdict\n\n"
            "**Council verdict:** ready for independent AI merge review and counsel handoff.\n",
            encoding="utf-8",
        )
        blocked = root / "build-SPEC_d032_router.md"
        blocked.write_text(
            "# BLOCKED - touches the protected audit/improve layer\n\n"
            "Branch `build/SPEC_d032_router` modifies files that autonomous builds may NEVER touch:\n"
            "- `tools/decisions/debate.py`\n",
            encoding="utf-8",
        )

        council_signal = syncer.parse_review_file(council)
        blocked_signal = syncer.parse_review_file(blocked)

        self.assertIsNotNone(council_signal)
        self.assertIsNotNone(blocked_signal)
        assert council_signal is not None
        assert blocked_signal is not None
        self.assertEqual(council_signal.verdict, "council_ready")
        self.assertEqual(blocked_signal.verdict, "blocked")
        self.assertIn("NEVER touch", blocked_signal.reasons)

    def test_review_signal_pairs_append_and_dedupe_without_db(self) -> None:
        root = self.temp_root()
        reviews = root / "reviews"
        reviews.mkdir()
        (reviews / "build-SPEC_d010_ok.md").write_text(
            "# AI Review - build/SPEC_d010_ok\n\n"
            "**Verdict:** APPROVE · **Risk:** low\n\n"
            "**Summary:** In scope and tested.\n",
            encoding="utf-8",
        )
        (reviews / "build-SPEC_d011_hold.md").write_text(
            "# AI Review - build/SPEC_d011_hold\n\n"
            "**Verdict:** REQUEST_CHANGES · **Risk:** med\n\n"
            "**Summary:** Missing guard on live path.\n\n"
            "## Findings\n- Add a kill switch.\n",
            encoding="utf-8",
        )
        dataset = root / "pairs.jsonl"

        with mock.patch.dict(syncer.os.environ, {}, clear=True):
            first = syncer.sync(dataset=dataset, reviews_dir=reviews, include_corrections=False)
            second = syncer.sync(dataset=dataset, reviews_dir=reviews, include_corrections=False)

        self.assertEqual(first["review_signals_read"], 2)
        self.assertEqual(first["review_pairs_added"], 2)
        self.assertEqual(second["review_pairs_skipped_dupes"], 2)
        rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["source"] for row in rows}, {"brain_index.review_signals"})
        self.assertEqual({row["metadata"]["training_signal"] for row in rows}, {"review_approved", "review_rejected"})

    def test_real_review_corpus_has_100_labeled_rows(self) -> None:
        signals = syncer.harvest_review_signals(syncer.DEFAULT_REVIEWS_DIR)

        self.assertGreaterEqual(len(signals), 100)
        self.assertTrue(all(signal.spec_id for signal in signals))
        self.assertTrue(all(signal.verdict for signal in signals))
        self.assertTrue(all(signal.reasons for signal in signals))
        self.assertTrue(all(signal.code_ref.startswith("core/BUILD/reviews/") for signal in signals))


if __name__ == "__main__":
    unittest.main()
