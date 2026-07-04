from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
from unittest import mock
from pathlib import Path

from tools.ads import campaign_watch as cw


class FakeClient:
    def __init__(self) -> None:
        self.config = cw.MetaConfig(access_token="secret", campaign_id="52555196349772", account_id="act_71883338")
        self.posts: list[tuple[str, dict]] = []

    def get(self, path, params=None):
        if path == "52555196349772":
            return {"id": "52555196349772", "name": "FP Assessment - Savings v1", "effective_status": "ACTIVE"}
        if path == "52555196349772/adsets":
            return {"data": [{"id": "adset1", "name": "US owners", "effective_status": "ACTIVE", "daily_budget": "1000"}]}
        if path == "52555196349772/ads":
            return {"data": [{"id": "ad1", "name": "savings-v1", "effective_status": "ACTIVE"}]}
        if path == "act_71883338":
            return {"id": "act_71883338", "account_status": 1, "disable_reason": 0, "currency": "USD"}
        if path == "52555196349772/insights":
            if params and "time_range" in params:
                return {
                    "data": [
                        {
                            "spend": "16.00",
                            "impressions": "1000",
                            "clicks": "40",
                            "actions": [{"action_type": "offsite_conversion.fb_pixel_lead", "value": "1"}],
                        }
                    ]
                }
            return {
                "data": [
                    {
                        "spend": "16.00",
                        "impressions": "1000",
                        "clicks": "40",
                        "actions": [{"action_type": "lead", "value": "1"}],
                    }
                ]
            }
        raise AssertionError(path)

    def post(self, path, params=None):
        self.posts.append((path, dict(params or {})))
        return {"success": True}


class CampaignWatchTests(unittest.TestCase):
    def test_lead_count_and_cpl_from_pixel_actions(self) -> None:
        insight = cw.normalize_insight(
            {
                "spend": "30.00",
                "impressions": "12",
                "clicks": "3",
                "actions": [
                    {"action_type": "offsite_conversion.fb_pixel_lead", "value": "2"},
                    {"action_type": "purchase", "value": "9"},
                ],
            }
        )
        self.assertEqual(insight["leads"], 2)
        self.assertEqual(insight["cpl"], 15.0)

    def test_run_watch_writes_reports_ledger_and_alerts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            status_path = root / "ads/status.json"
            hot_state = root / "hot/ads_status.json"
            ledger = root / "allocation/ledger.jsonl"
            status_path.parent.mkdir(parents=True)
            status_path.write_text(json.dumps({"review_status": "pending_review", "spend_total": 0}), encoding="utf-8")
            messages: list[str] = []
            status = cw.run_watch(
                client=FakeClient(),  # type: ignore[arg-type]
                status_path=status_path,
                hot_state_path=hot_state,
                allocation_ledger=ledger,
                repo_root=root,
                notify=True,
                notifier=messages.append,
            )
            self.assertEqual(status["review_status"], "approved")
            self.assertEqual(status["spend_today"], 16.0)
            self.assertTrue(status_path.exists())
            self.assertTrue(hot_state.exists())
            rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[0]["kind"], "level3_stewardship_allocation")
            self.assertIn("review approved", rows[0]["alerts"])
            self.assertIn("first spend", rows[0]["alerts"])
            self.assertIn("daily spend > $12", rows[0]["alerts"])
            self.assertEqual(len(messages), 1)

    def test_set_daily_budget_rejects_over_hard_ceiling(self) -> None:
        with self.assertRaises(cw.CampaignWatchError):
            cw.perform_action(FakeClient(), "set_daily_budget", {"daily_budget_usd": 20.01})  # type: ignore[arg-type]

    def test_set_daily_budget_updates_adsets_in_cents(self) -> None:
        client = FakeClient()
        result = cw.perform_action(client, "set_daily_budget", {"daily_budget_usd": 19.99})  # type: ignore[arg-type]
        self.assertTrue(result["ok"])
        self.assertEqual(client.posts, [("adset1", {"daily_budget": "1999"})])

    def test_bearer_gate(self) -> None:
        self.assertTrue(cw.bearer_authorized("Bearer abc", "abc"))
        self.assertFalse(cw.bearer_authorized("Bearer abc", "def"))
        self.assertFalse(cw.bearer_authorized(None, "abc"))
        self.assertFalse(cw.bearer_authorized("Bearer abc", ""))

    def test_load_action_token_uses_ai_token_file_convention(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            token_file = Path(td) / "ai.token"
            token_file.write_text("from-file\n", encoding="utf-8")
            with mock.patch.dict(
                "os.environ",
                {"FPAI_AI_TOKEN_FILE": str(token_file), "FPAI_ADS_ACTION_TOKEN": "", "FPAI_AI_TOKEN": ""},
                clear=False,
            ):
                self.assertEqual(cw.load_action_token(), "from-file")

    def test_meta_client_error_does_not_include_token(self) -> None:
        def opener(_req, _timeout):
            raise urllib.error.HTTPError(
                "https://graph.facebook.com/v19.0/x",
                400,
                "bad",
                {},
                tempfile.TemporaryFile("w+b"),
            )

        client = cw.MetaClient(cw.MetaConfig(access_token="super-secret-token"), opener=opener)
        with self.assertRaises(cw.CampaignWatchError) as ctx:
            client.get("x")
        self.assertNotIn("super-secret-token", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
