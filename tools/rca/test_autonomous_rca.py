from __future__ import annotations

import unittest

from tools.rca import autonomous_rca as rca


class AutonomousRcaTest(unittest.TestCase):
    def test_normalize_collapses_variants_to_one_signature(self) -> None:
        a = rca.normalize_signature({"event": "build", "detail": "SPEC_d143_foo (rejected) at 2026-07-03T14:00Z line 42"})
        b = rca.normalize_signature({"event": "build", "detail": "SPEC_d144_bar (rejected) at 2026-07-02T09:11Z line 9"})
        self.assertEqual(a, b)  # same bug class -> same signature

    def test_is_error_event_detects_by_name_and_detail(self) -> None:
        self.assertTrue(rca.is_error_event({"event": "diagnostic_error", "detail": ""}))
        self.assertTrue(rca.is_error_event({"event": "note", "detail": "cannot import name 'telegram'"}))
        self.assertFalse(rca.is_error_event({"event": "merge", "detail": "auto-merged clean"}))

    def test_group_and_count(self) -> None:
        rows = [
            {"event": "diagnostic_error", "detail": "cannot import name 'telegram'", "ts": "2026-06-18T21:00Z", "loop": "council"},
            {"event": "diagnostic_error", "detail": "cannot import name 'telegram'", "ts": "2026-06-18T21:43Z", "loop": "council"},
            {"event": "merge", "detail": "clean"},
        ]
        groups = rca.group_errors(rows)
        self.assertEqual(len(groups), 1)
        sig = next(iter(groups.values()))
        self.assertEqual(sig.count, 2)
        self.assertEqual(sig.first_ts, "2026-06-18T21:00Z")
        self.assertEqual(sig.last_ts, "2026-06-18T21:43Z")

    def test_flag_new_and_recurring(self) -> None:
        rows = [{"event": "x_error", "detail": "boom"} for _ in range(10)]
        groups = rca.group_errors(rows)
        sig_key = next(iter(groups))
        # NEW signature -> flagged
        self.assertEqual(len(rca.flag_signatures(groups, {}, recur_threshold=5)), 1)
        # already analyzed at count 10, no recurrence -> not flagged
        self.assertEqual(len(rca.flag_signatures(groups, {sig_key: 10}, recur_threshold=5)), 0)
        # analyzed at 4, now 10 (=6 more >= threshold 5) -> flagged again (fix didn't land)
        self.assertEqual(len(rca.flag_signatures(groups, {sig_key: 4}, recur_threshold=5)), 1)


if __name__ == "__main__":
    unittest.main()
