from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from tools.life_data import intake


NOW = dt.datetime(2026, 6, 16, 12, 0, tzinfo=dt.timezone.utc)


class LifeDataIntakeTests(unittest.TestCase):
    def test_fixture_intake_normalizes_all_domains(self) -> None:
        run = intake.run_intake(now=NOW)

        self.assertTrue(run.dry_run)
        self.assertEqual(intake.counts_by_domain(run.records), {"financial": 4, "calendar": 2, "communications": 2})
        signals = intake.signal_counts(run.records)
        self.assertEqual(signals["financial_account"], 2)
        self.assertEqual(signals["calendar_event"], 2)
        self.assertEqual(signals["communication"], 2)
        self.assertIn("needs_reply", signals)
        self.assertIn("upcoming_commitment", signals)

    def test_records_are_secret_free_and_hash_source_ids(self) -> None:
        run = intake.run_intake(now=NOW)
        payload = json.dumps(run.to_dict(), sort_keys=True)

        self.assertNotIn("client@example.com", payload)
        self.assertNotIn("+15555550123", payload)
        self.assertNotIn("checking-123456789", payload)
        self.assertIn("[email]", payload)
        self.assertIn("[phone]", payload)
        self.assertIn("account_hash", payload)

    def test_write_outputs_only_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jsonl_path = root / "intake.jsonl"
            report_path = root / "report.md"

            dry = intake.run_intake(now=NOW, jsonl_path=jsonl_path, report_path=report_path)
            self.assertFalse(jsonl_path.exists())
            self.assertFalse(report_path.exists())
            self.assertIsNone(dry.jsonl_path)

            written = intake.run_intake(now=NOW, write=True, jsonl_path=jsonl_path, report_path=report_path)
            self.assertFalse(written.dry_run)
            self.assertTrue(jsonl_path.exists())
            self.assertTrue(report_path.exists())
            self.assertEqual(len(jsonl_path.read_text(encoding="utf-8").splitlines()), len(written.records))
            self.assertIn("no money movement", report_path.read_text(encoding="utf-8"))
            self.assertNotIn("Client payment", report_path.read_text(encoding="utf-8"))

    def test_live_provider_mode_refuses(self) -> None:
        with self.assertRaises(intake.LiveIntakeNotConfigured):
            intake.resolve_sources(live=True)

    def test_full_record_jsonl_refuses_repo_path_by_default(self) -> None:
        with self.assertRaisesRegex(ValueError, "refusing to write full life-data records"):
            intake.write_jsonl([], intake.REPO_ROOT / "core" / "STATE" / "life_data" / "intake.jsonl")

    def test_env_exports_use_local_files_without_provider_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial = root / "financial.json"
            financial.write_text('{"accounts": [], "transactions": []}', encoding="utf-8")
            with mock.patch.dict("os.environ", {"FPAI_LIFE_FINANCIAL_EXPORT": str(financial)}, clear=False):
                sources = intake.resolve_sources(fixture_dir=None, use_env_exports=True)
        self.assertEqual(sources, {"financial": financial})


if __name__ == "__main__":
    unittest.main()
