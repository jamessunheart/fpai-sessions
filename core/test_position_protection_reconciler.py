from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from core import position_protection_reconciler as reconciler


class FakeAdapter:
    def __init__(self, positions=None, orders=None, confirm=True):
        self.positions = positions or []
        self.orders = orders or []
        self.confirm = confirm
        self.placed = []
        self.open_position_calls = []

    def get_positions(self):
        return list(self.positions)

    def list_open_orders(self):
        return list(self.orders)

    def place_stop_loss(self, symbol, side, size, trigger_price):
        self.placed.append(("stop", symbol, side, size, trigger_price))
        if self.confirm:
            self.orders.append({"coin": symbol, "orderType": "Stop Market", "triggerPx": trigger_price})
        return {"status": "ok"}

    def place_take_profit(self, symbol, side, size, trigger_price):
        self.placed.append(("target", symbol, side, size, trigger_price))
        if self.confirm:
            self.orders.append({"coin": symbol, "orderType": "Take Profit Market", "triggerPx": trigger_price})
        return {"status": "ok"}

    def open_position(self, *args, **kwargs):
        self.open_position_calls.append((args, kwargs))


class PositionProtectionReconcilerTest(unittest.TestCase):
    def audit_log(self, rows=None) -> Path:
        path = Path(tempfile.mkdtemp(prefix="fpai-protect-test-")) / "audit.jsonl"
        if rows:
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        return path

    def test_position_without_stop_places_stop_and_target(self) -> None:
        adapter = FakeAdapter(
            positions=[{"coin": "ETH", "szi": "-0.1", "entryPx": "3600"}],
            orders=[],
        )
        audit = self.audit_log([
            {"phase": "entry", "symbol": "ETH", "stop": 3672, "target": 3420},
        ])

        summary = reconciler.reconcile_once(adapter, audit_log=audit)

        self.assertTrue(summary.ok)
        self.assertEqual(summary.stops_placed, 1)
        self.assertEqual(summary.targets_placed, 1)
        self.assertEqual(adapter.placed[0], ("stop", "ETH", "buy", 0.1, 3672.0))
        self.assertEqual(adapter.placed[1], ("target", "ETH", "buy", 0.1, 3420.0))

    def test_position_with_existing_stop_and_target_is_idempotent(self) -> None:
        adapter = FakeAdapter(
            positions=[{"coin": "SOL", "szi": "2", "entryPx": "150"}],
            orders=[
                {"coin": "SOL", "orderType": {"trigger": {"tpsl": "sl", "triggerPx": "146"}}},
                {"coin": "SOL", "orderType": {"trigger": {"tpsl": "tp", "triggerPx": "160"}}},
            ],
        )

        summary = reconciler.reconcile_once(adapter, audit_log=self.audit_log())

        self.assertTrue(summary.ok)
        self.assertEqual(summary.skipped, 1)
        self.assertEqual(adapter.placed, [])

    def test_kill_switch_zero_still_protects_and_never_opens(self) -> None:
        old_value = os.environ.get("SWEEP_LIVE")
        os.environ["SWEEP_LIVE"] = "0"
        try:
            adapter = FakeAdapter(
                positions=[{"coin": "SOL", "szi": "-1.5", "entryPx": "150"}],
                orders=[],
            )
            summary = reconciler.reconcile_once(adapter, audit_log=self.audit_log())
        finally:
            if old_value is None:
                os.environ.pop("SWEEP_LIVE", None)
            else:
                os.environ["SWEEP_LIVE"] = old_value

        self.assertTrue(summary.ok)
        self.assertEqual(summary.stops_placed, 1)
        self.assertEqual(summary.targets_placed, 1)
        self.assertEqual(adapter.open_position_calls, [])

    def test_unconfirmed_stop_is_audited_loudly(self) -> None:
        events = []
        adapter = FakeAdapter(
            positions=[{"coin": "BTC", "szi": "0.01", "entryPx": "100000"}],
            orders=[],
            confirm=False,
        )

        summary = reconciler.reconcile_once(
            adapter,
            audit_log=self.audit_log(),
            audit_writer=events.append,
        )

        self.assertFalse(summary.ok)
        self.assertEqual(summary.unconfirmed, 2)
        self.assertIn("stop_unconfirmed", {event["phase"] for event in events})
        self.assertIn("target_unconfirmed", {event["phase"] for event in events})


class FrontendOpenOrdersFallbackTestCase(unittest.TestCase):
    def test_adapter_without_listing_method_uses_info_client(self) -> None:
        class FakeInfo:
            def frontend_open_orders(self, account):
                assert account == "0xMAIN"
                return [{"coin": "SOL", "isTrigger": True, "orderType": "Stop Market",
                         "triggerPx": "150.0", "reduceOnly": True, "sz": "1.0"}]

        class ProductionLikeAdapter:  # has info+main_account, no list_* methods
            info = FakeInfo()
            main_account = "0xMAIN"

        orders = reconciler.list_trigger_orders(ProductionLikeAdapter())
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].symbol, "SOL")
        self.assertEqual(orders[0].kind, "stop")

    def test_adapter_without_info_still_raises(self) -> None:
        class BareAdapter:
            pass

        with self.assertRaises(AttributeError):
            reconciler.list_trigger_orders(BareAdapter())


if __name__ == "__main__":
    unittest.main()
