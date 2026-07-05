import datetime as dt
import importlib.util
import types
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


APP_DIR = Path(__file__).resolve().parent
SERVICE_DIR = APP_DIR.parent
REPO = APP_DIR.parents[2]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

config_mod = types.ModuleType("app.config")
config_mod.settings = types.SimpleNamespace(COCKPIT_ROOT=str(REPO))
sys.modules.setdefault("app.config", config_mod)

storage_mod = types.ModuleType("app.intelligence.storage")
storage_mod.signal_storage = types.SimpleNamespace(signal_history=[])
intelligence_mod = types.ModuleType("app.intelligence")
intelligence_mod.storage = storage_mod
sys.modules.setdefault("app.intelligence", intelligence_mod)
sys.modules.setdefault("app.intelligence.storage", storage_mod)

patterns_mod = types.ModuleType("app.intelligence.patterns")
patterns_mod.PatternDetector = lambda signals: types.SimpleNamespace(
    detect_automation_opportunities=lambda: [],
    detect_trends=lambda hours: {"by_category": {}, "total_signals": 0, "top_sources": []},
)
intelligence_mod.patterns = patterns_mod
sys.modules.setdefault("app.intelligence.patterns", patterns_mod)

from app.models import DailyDigest
from tools.allocation import capability_ledger as ledger


DIGEST_SPEC = importlib.util.spec_from_file_location("chief_digest", APP_DIR / "digest.py")
chief_digest = importlib.util.module_from_spec(DIGEST_SPEC)
sys.modules["chief_digest"] = chief_digest
DIGEST_SPEC.loader.exec_module(chief_digest)

CAPABILITY_SPEC = importlib.util.spec_from_file_location("chief_capability", APP_DIR / "capability.py")
chief_capability = importlib.util.module_from_spec(CAPABILITY_SPEC)
sys.modules["chief_capability"] = chief_capability
CAPABILITY_SPEC.loader.exec_module(chief_capability)

OPPORTUNITIES_SPEC = importlib.util.spec_from_file_location("chief_opportunities", APP_DIR / "opportunities.py")
chief_opportunities = importlib.util.module_from_spec(OPPORTUNITIES_SPEC)
sys.modules["chief_opportunities"] = chief_opportunities
OPPORTUNITIES_SPEC.loader.exec_module(chief_opportunities)


class ChiefCapabilityTest(unittest.TestCase):
    def test_capability_view_reads_configured_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            ledger.append_row(
                path,
                ledger.capability_row(
                    source_type="build",
                    source_id="SPEC_d185",
                    title="Capability ledger",
                    scores={"knowledge_gained": 1, "automation": 2},
                    reusable_intelligence="core/BUILD/results/SPEC_d185_capability-created-ledger.result.md",
                    ts="2026-07-05T00:10:00Z",
                ),
            )

            with patch.dict(os.environ, {"FPAI_CAPABILITY_LEDGER": str(path)}), patch.object(
                chief_digest, "datetime", _FixedDateTime
            ), patch.object(ledger, "dt", dt):
                view = chief_capability.build_capability_view()

            self.assertEqual(view["today"]["total_capability_gain"], 3.0)
            self.assertEqual(len(view["trend_30d"]), 30)

    def test_digest_formats_capability_as_headline_metric(self) -> None:
        digest = DailyDigest(
            key_metrics={
                "signals_processed": 2,
                "capability_created_line": "capability created today: +4 (time+0 knowledge+1 cash+0 trust+1 auto+2).",
                "capability_created_7d": 4,
                "capability_created_30d": 4,
            }
        )

        text = chief_digest.DigestGenerator().format_for_telegram(digest)

        self.assertIn("*CAPABILITY CREATED*", text)
        self.assertIn("capability created today: +4", text)
        self.assertIn("7d: +4", text)
        self.assertNotIn("Capability Created Line", text)

    def test_opportunities_view_reads_configured_portfolio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opportunities.json"

            with patch.dict(os.environ, {"FPAI_OPPORTUNITY_LEDGER": str(path)}):
                view = chief_opportunities.build_opportunities_view()

            self.assertGreaterEqual(view["count"], 5)
            self.assertEqual(view["top_allocation"][0]["title"], "Resource Optimization Audit")

    def test_digest_formats_opportunities_as_headline_metric(self) -> None:
        digest = DailyDigest(
            key_metrics={
                "signals_processed": 2,
                "opportunities_line": "opportunities: do-now Resource Optimization Audit (26.5); closest-cash Resource Optimization Audit (15).",
                "opportunities_count": 5,
            }
        )

        text = chief_digest.DigestGenerator().format_for_telegram(digest)

        self.assertIn("*OPPORTUNITIES*", text)
        self.assertIn("do-now Resource Optimization Audit", text)
        self.assertIn("rows: 5", text)
        self.assertNotIn("Opportunities Line", text)


class _FixedDateTime(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return dt.datetime(2026, 7, 5, 12, 0, tzinfo=tz or dt.timezone.utc)


if __name__ == "__main__":
    unittest.main()
