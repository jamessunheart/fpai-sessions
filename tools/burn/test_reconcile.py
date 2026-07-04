from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.burn import reconcile


ANTHROPIC_FIXTURE = {
    "data": [
        {
            "starting_at": "2026-07-01T00:00:00Z",
            "results": [
                {
                    "grouping": {"api_key_id": "key_fp_index", "api_key_name": "fp-index production"},
                    "cost": {"amount": "0.03", "currency": "USD"},
                },
                {
                    "grouping": {"api_key_id": "key_zombie", "api_key_name": "zombie curator"},
                    "cost": {"amount": "3.50", "currency": "USD"},
                },
            ],
        }
    ]
}

META_FIXTURE = {
    "data": [
        {
            "date_start": "2026-07-01",
            "date_stop": "2026-07-01",
            "account_name": "act_71883338 FP Ads",
            "spend": "9.25",
        }
    ]
}


class BurnReconcileTests(unittest.TestCase):
    def test_expected_daily_parser_uses_day_amounts(self) -> None:
        self.assertEqual(reconcile.expected_daily_usd("<$0.05/day (~1 call/day)"), 0.05)
        self.assertEqual(
            reconcile.expected_daily_usd("$0 marginal watcher; ad delivery capped by campaign action hard ceiling <=$20/day"),
            20.0,
        )
        self.assertEqual(reconcile.expected_daily_usd("free tier"), 0.0)
        self.assertIsNone(reconcile.expected_daily_usd("$0.50/audit"))

    def test_fixture_parsers_normalize_anthropic_and_meta_rows(self) -> None:
        anthropic = reconcile.anthropic_spends(ANTHROPIC_FIXTURE)
        meta = reconcile.meta_spends(META_FIXTURE)
        self.assertEqual(anthropic[0].provider, "anthropic")
        self.assertEqual(anthropic[0].consumer_name, "fp-index production")
        self.assertEqual(anthropic[0].amount_usd, 0.03)
        self.assertEqual(meta[0].provider, "meta")
        self.assertEqual(meta[0].amount_usd, 9.25)

    def test_seeded_alert_path_fires_for_unregistered_provider_spend(self) -> None:
        consumers = [
            reconcile.RegistryConsumer(
                name="fp-index (198)",
                provider="anthropic",
                expected_daily_usd=0.05,
                raw_expected="<$0.05/day",
                unit="fpai-fp-index",
                output="semantic index refresh",
            )
        ]
        rows, alerts = reconcile.analyze(reconcile.anthropic_spends(ANTHROPIC_FIXTURE), consumers)
        self.assertEqual(rows[0]["status"], "green")
        red_rows = [row for row in rows if row["status"] == "red"]
        self.assertEqual(len(red_rows), 1)
        self.assertIn("no BURN_REGISTRY row", alerts[0])
        self.assertEqual(red_rows[0]["consumer_name"], "zombie curator")

    def test_alert_path_fires_for_more_than_2x_expected(self) -> None:
        spends = [reconcile.ProviderSpend("anthropic", "2026-07-01", 0.11, "key_fp_index", "fp-index production")]
        consumers = [
            reconcile.RegistryConsumer(
                name="fp-index (198)",
                provider="anthropic",
                expected_daily_usd=0.05,
                raw_expected="<$0.05/day",
                unit="fpai-fp-index",
                output="semantic index refresh",
            )
        ]
        rows, alerts = reconcile.analyze(spends, consumers)
        self.assertEqual(rows[0]["status"], "red")
        self.assertIn(">2x expected", alerts[0])

    def test_run_reconciliation_writes_reports_ledger_heartbeats_and_tg(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            anthropic_fixture = root / "anthropic.json"
            meta_fixture = root / "meta.json"
            anthropic_fixture.write_text(json.dumps(ANTHROPIC_FIXTURE), encoding="utf-8")
            meta_fixture.write_text(json.dumps(META_FIXTURE), encoding="utf-8")
            vault = root / "vault"
            heartbeat = vault / "02_CONTEXT/Memory/HEARTBEATS.md"
            heartbeat.parent.mkdir(parents=True)
            heartbeat.write_text("# HEARTBEATS\n", encoding="utf-8")
            messages: list[str] = []

            report = reconcile.run_reconciliation(
                start=reconcile.parse_date("2026-07-01"),
                end=reconcile.parse_date("2026-07-02"),
                report_dir=root / "reports",
                allocation_ledger=root / "allocation/ledger.jsonl",
                vault=vault,
                repo_root=root,
                notify=True,
                anthropic_fixture=anthropic_fixture,
                meta_fixture=meta_fixture,
                notifier=messages.append,
            )

            self.assertGreaterEqual(len(report["alerts"]), 1)
            self.assertTrue(Path(report["report_json"]).exists())
            self.assertTrue(Path(report["report_md"]).exists())
            ledger_rows = [
                json.loads(line)
                for line in (root / "allocation/ledger.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(ledger_rows[0]["source"], "burn_reconciliation")
            self.assertIn("PROVIDER BURN RECONCILIATION", heartbeat.read_text(encoding="utf-8"))
            self.assertEqual(len(messages), 1)
            self.assertNotIn("secret", json.dumps(report).lower())

    def test_fetch_clients_do_not_log_tokens_in_errors(self) -> None:
        with mock.patch.dict("os.environ", {"ANTHROPIC_ADMIN_API_KEY": "secret-admin"}, clear=False):
            def opener(_req, _timeout=45):
                raise RuntimeError("provider unavailable")

            with self.assertRaises(RuntimeError) as ctx:
                reconcile.fetch_anthropic_costs(
                    reconcile.parse_date("2026-07-01"),
                    reconcile.parse_date("2026-07-02"),
                    opener=opener,
                )
            self.assertNotIn("secret-admin", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
