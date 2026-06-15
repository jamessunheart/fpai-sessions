from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.router.instrument_rack import choose_decision, main, route_message


class InstrumentRackTestCase(unittest.TestCase):
    def test_d010_approve_routes_decision_t0(self) -> None:
        decision = choose_decision("d010 approve")

        self.assertEqual(decision.message_class, "decision")
        self.assertEqual(decision.chosen_tier, "T0")
        self.assertIn("rules/cache", decision.reason)

    def test_what_is_going_on_routes_status_t1(self) -> None:
        decision = choose_decision("what is going on?")

        self.assertEqual(decision.message_class, "status")
        self.assertEqual(decision.chosen_tier, "T1")

    def test_system_evolution_routes_self_evolution_t4(self) -> None:
        decision = choose_decision("how should the system evolve?")

        self.assertEqual(decision.message_class, "self-evolution")
        self.assertEqual(decision.chosen_tier, "T4")

    def test_send_money_routes_t5(self) -> None:
        decision = choose_decision("send money to the treasury wallet")

        self.assertEqual(decision.chosen_tier, "T5")
        self.assertIn(decision.message_class, {"treasury", "reserved-stakes"})

    def test_max_axis_over_escalates_stakes(self) -> None:
        decision = choose_decision("d010 approve and send $500 publicly")

        self.assertEqual(decision.message_class, "treasury")
        self.assertEqual(decision.chosen_tier, "T5")
        self.assertIn("decision", {axis.message_class for axis in decision.matched_axes})

    def test_route_message_appends_shadow_ledger(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-instrument-rack-"))
        ledger = root / "ops.jsonl"

        decision = route_message("status please", ledger=ledger)

        rows = ledger.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(rows), 1)
        row = json.loads(rows[0])
        self.assertEqual(row["loop"], "router")
        self.assertTrue(row["shadow_mode"])
        self.assertEqual(row["message_class"], decision.message_class)
        self.assertEqual(row["chosen_tier"], decision.chosen_tier)
        self.assertIn("est_tier_cost", row)

    def test_cli_prints_result_line_and_writes_temp_ledger(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-instrument-rack-cli-"))
        ledger = root / "ops.jsonl"
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            code = main(["--ledger", str(ledger), "d010 approve"])

        self.assertEqual(code, 0)
        self.assertIn("RESULT instrument_rack class=decision tier=T0 shadow=true", output.getvalue())
        self.assertTrue(ledger.exists())


def run_tests() -> int:
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(InstrumentRackTestCase)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    print(stream.getvalue(), end="")
    if result.wasSuccessful():
        print(f"RESULT test_instrument_rack PASS tests={result.testsRun}")
        return 0
    failures = len(result.failures) + len(result.errors)
    print(f"RESULT test_instrument_rack FAIL tests={result.testsRun} failures={failures}")
    return 1


if __name__ == "__main__":
    raise SystemExit(run_tests())
