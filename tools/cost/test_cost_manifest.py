from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.cost.cost_manifest import build_digest, has_stale_source, parse_manifest


class CostManifestTestCase(unittest.TestCase):
    def write_manifest(self, rows: list[dict[str, object]]) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-cost-manifest-"))
        path = root / "manifest.jsonl"
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        return path

    def base_row(self, **overrides: object) -> dict[str, object]:
        row: dict[str, object] = {
            "item": "Claude Max",
            "amount": 200.0,
            "owner": "James",
            "source": "James-verified estimate",
            "verified_at": "2026-06-15",
            "renewal": "monthly",
            "category": "subscription",
            "confidence": "estimate",
        }
        row.update(overrides)
        return row

    def test_manifest_parses_required_fields(self) -> None:
        path = self.write_manifest([self.base_row(), self.base_row(item="server", amount=805.0, category="infra")])

        records = parse_manifest(path)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].item, "Claude Max")
        self.assertEqual(records[0].amount, Decimal("200.0"))
        self.assertEqual(records[1].category, "infra")

    def test_amortization_math_and_projection(self) -> None:
        manifest = self.write_manifest([self.base_row(amount=1200.0)])
        ledger = Path(tempfile.mkdtemp(prefix="fpai-cost-ledger-")) / "ledger.jsonl"
        ledger.write_text(
            json.dumps(
                {
                    "timestamp": "2026-06-15T09:00:00+00:00",
                    "billing": "metered",
                    "label": "scout",
                    "est_usd": 10,
                }
            )
            + "\n",
            encoding="utf-8",
        )

        digest = build_digest(manifest=manifest, metered_ledger=ledger, today=dt.date(2026, 6, 15))

        self.assertEqual(digest.fixed_monthly_total, Decimal("1200.0"))
        self.assertEqual(digest.fixed_daily_accrual, Decimal("40.0"))
        self.assertEqual(digest.fixed_month_to_date_accrual, Decimal("600.0"))
        self.assertEqual(digest.today_metered, Decimal("10"))
        self.assertEqual(digest.projected_monthly_burn, Decimal("1500.0"))
        self.assertTrue(digest.drift_over_10pct)

    def test_stale_flag_fires_on_old_verified_at(self) -> None:
        path = self.write_manifest([self.base_row(verified_at="2026-05-01")])

        records = parse_manifest(path)

        self.assertTrue(has_stale_source(records, today=dt.date(2026, 6, 15)))


def run_tests() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CostManifestTestCase)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print(f"RESULT test_cost_manifest PASS tests={result.testsRun}")
        return 0
    failures = len(result.failures) + len(result.errors)
    print(f"RESULT test_cost_manifest FAIL tests={result.testsRun} failures={failures}")
    return 1


if __name__ == "__main__":
    raise SystemExit(run_tests())
