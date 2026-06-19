from __future__ import annotations

import unittest

from tools.synthesis.context_router import (
    ALL_CONTEXT_BLOCKS,
    classify_question,
    context_blocks_for_route,
)


class ContextRouterTest(unittest.TestCase):
    def test_classifies_ops_status_question(self) -> None:
        self.assertEqual(classify_question("What is the current build status on the server?"), "ops")

    def test_classifies_treasury_question(self) -> None:
        self.assertEqual(classify_question("What is treasury runway and wallet balance?"), "treasury")

    def test_classifies_memory_question(self) -> None:
        self.assertEqual(classify_question("What did I say about Josh last week?"), "memory")

    def test_ambiguous_question_falls_back_to_general(self) -> None:
        self.assertEqual(classify_question("What is the status of treasury?"), "general")

    def test_proof_messages_reduce_context_blocks_vs_baseline(self) -> None:
        baseline = len(ALL_CONTEXT_BLOCKS)
        cases = [
            ("What is the current build status?", "ops", 2),
            ("What is treasury runway and wallet balance?", "treasury", 2),
            ("What did I say about Josh last week?", "memory", baseline),
        ]

        for question, expected_route, expected_blocks in cases:
            with self.subTest(question=question):
                route = classify_question(question)
                blocks = context_blocks_for_route(route)
                self.assertEqual(route, expected_route)
                self.assertEqual(len(blocks), expected_blocks)
                self.assertLessEqual(len(blocks), baseline)


if __name__ == "__main__":
    unittest.main()
