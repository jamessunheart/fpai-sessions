from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("attention.py")
SPEC = importlib.util.spec_from_file_location("attention", MODULE_PATH)
assert SPEC and SPEC.loader
attention = importlib.util.module_from_spec(SPEC)
sys.modules["attention"] = attention
SPEC.loader.exec_module(attention)


class AttentionSurfacingTest(unittest.TestCase):
    def hits(self) -> list[dict]:
        return [
            {
                "note_row_id": "hot-state",
                "chunk_idx": 0,
                "source": "memory",
                "sensitivity": "personal",
                "score": 0.83,
                "tags": ["attention", "next"],
                "content": "The relevant move is to replace scheduled checks with query-time memory surfacing.",
            },
            {
                "note_row_id": "private",
                "chunk_idx": 0,
                "source": "memory",
                "sensitivity": "private",
                "score": 0.99,
                "tags": ["attention"],
                "content": "Never surface private content.",
            },
            {
                "note_row_id": "low-score",
                "chunk_idx": 0,
                "source": "memory",
                "sensitivity": "public",
                "score": 0.41,
                "tags": ["attention"],
                "content": "Too weak to surface.",
            },
        ]

    def test_candidates_require_relevance_and_exclude_private(self) -> None:
        candidates = attention.candidates_from_hits(self.hits(), min_score=0.72, max_items=5)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].note_row_id, "hot-state")
        self.assertEqual(candidates[0].sensitivity, "personal")
        self.assertIn("pgvector cosine", candidates[0].reason)

    def test_disable_env_returns_no_candidates(self) -> None:
        with patch.dict(os.environ, {"SH_ATTENTION_SURFACING_DISABLE": "1"}):
            self.assertEqual(attention.candidates_from_hits(self.hits()), [])

    def test_render_attention_context_is_bounded(self) -> None:
        candidates = attention.candidates_from_hits(self.hits(), min_score=0.72)

        rendered = attention.render_attention_context(candidates, max_chars=180)

        self.assertLessEqual(len(rendered), 180)
        self.assertIn("RELEVANCE-TRIGGERED ATTENTION CONTEXT", rendered)
        self.assertIn("bounded", rendered)

    def test_context_from_hits_logs_best_effort_without_db(self) -> None:
        rendered = asyncio.run(
            attention.attention_context_from_hits(
                "what should surface now?",
                self.hits(),
                conversation_id="123",
                min_score=0.72,
            )
        )

        self.assertIn("query matched pgvector memory", rendered)
        self.assertIn("replace scheduled checks", rendered)


if __name__ == "__main__":
    unittest.main()
