import importlib.util
import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from fastapi import BackgroundTasks


DAY0 = {
    "physical": [6, 5],
    "mental": [7, 4],
    "spiritual": [8, 7],
    "social": [5, 4],
    "emotional": [6, 6],
    "financial": [4, 5],
    "environmental": [8, 8],
}


def load_champion_module(tmp: str):
    os.environ["CHAMPION_DATA_DIR"] = str(Path(tmp) / "champions")
    os.environ["PROOFS_DATA_DIR"] = str(Path(tmp) / "proofs")
    os.environ["CARDS_DATA_DIR"] = str(Path(tmp) / "cards")
    os.environ["LEADS_DATA_DIR"] = str(Path(tmp) / "leads")
    os.environ["MIRRORS_DATA_DIR"] = str(Path(tmp) / "mirrors")
    os.environ["TIERS_DATA_DIR"] = str(Path(tmp) / "tiers")
    os.environ["RETREAT_DATA_DIR"] = str(Path(tmp) / "retreat")
    os.environ["GOALS_DATA_DIR"] = str(Path(tmp) / "goals")
    os.environ["CREDITS_DATA_DIR"] = str(Path(tmp) / "credits")
    os.environ["STORE_DATA_DIR"] = str(Path(tmp) / "store")
    os.environ["FPAI_REPO_ROOT"] = str(Path(__file__).resolve().parents[3])
    os.environ["META_COMMENT_AUTOMATION_ENABLED"] = "0"
    os.environ["META_PUBLIC_REPLY_APPROVED"] = "0"
    os.environ["META_DM_REPLY_APPROVED"] = "0"
    os.environ["META_WEBHOOK_VERIFY_TOKEN"] = "verify-test"
    os.environ.pop("HERMES_THREAD_APPEND_ENABLED", None)
    module_path = Path(__file__).resolve().parents[3] / "SERVICES/champion-sign/main.py"
    spec = importlib.util.spec_from_file_location("champion_sign_life_test", module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ChampionLifeLeadTests(unittest.TestCase):
    def test_scores_life_lead_with_existing_score_life_math(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = load_champion_module(tmp)
            req = SimpleNamespace(
                name="Lia",
                email="lia@example.test",
                phone=None,
                timezone=None,
                preferred_contact=None,
                interest="life-assessment",
                lens="life",
                bottleneck="I want a clearer aim and steadier daily practice.",
                seven_areas=None,
                life_answers=DAY0,
                life_context={"spiritual": "Build the village that shows paradise is practical."},
            )
            result, deliverable = mod._score_life_lead(req)
            md = mod._render_lead_md(req, "2026-07-04", life_result=result, life_deliverable=deliverable)

        self.assertEqual(result["allocation_score"], 59.3)
        self.assertEqual(result["practice_target"], "social")
        self.assertIn("Life lens Allocation Score", md)
        self.assertIn("life_allocation_score: 59.3", md)
        self.assertIn("Your named AIM", md)

    def test_life_assessment_email_contains_delivery_contract_without_income_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = load_champion_module(tmp)
            req = SimpleNamespace(
                name="Lia",
                email="lia@example.test",
                bottleneck="I want a clearer aim and steadier daily practice.",
                life_answers=DAY0,
                life_context={"spiritual": "Build the village that shows paradise is practical."},
            )
            result, _deliverable = mod._score_life_lead(req)
            subject, body = mod._life_assessment_email(req, result)

        self.assertIn("59.3/100", subject)
        self.assertIn("Allocation archetype: Connection Rebuilder", body)
        self.assertIn("One surprise insight:", body)
        self.assertIn("Your free Monday move:", body)
        self.assertIn("Share line:", body)
        self.assertIn("paid Blueprint", body)
        lowered = body.lower()
        for forbidden in ("passive income", "guarantee", "guaranteed", "replace your salary", "roi", "profit-sharing", "risk-free"):
            self.assertNotIn(forbidden, lowered)

    def test_send_assessment_email_uses_fullpotential_mail_stack(self):
        sent = []

        class FakeSMTP:
            def __init__(self, host, port, timeout):
                self.host = host
                self.port = port
                self.timeout = timeout

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def send_message(self, msg):
                sent.append((self.host, self.port, self.timeout, msg))

        with tempfile.TemporaryDirectory() as tmp:
            mod = load_champion_module(tmp)
            ok, reason = mod._send_assessment_email(
                "lia@example.test",
                "Your score",
                "Score body",
                smtp_factory=FakeSMTP,
            )

        self.assertTrue(ok)
        self.assertEqual(reason, "sent")
        host, port, timeout, msg = sent[0]
        self.assertEqual(host, "mail.fullpotential.com")
        self.assertEqual(port, 25)
        self.assertEqual(timeout, 20)
        self.assertEqual(msg["To"], "lia@example.test")
        self.assertEqual(msg["Reply-To"], "james@fullpotential.com")

    def test_founder_alert_reports_success_for_telegram_post(self):
        calls = []

        class Response:
            status = 200

        def fake_urlopen(request, timeout):
            calls.append((request, timeout))
            return Response()

        with tempfile.TemporaryDirectory() as tmp:
            mod = load_champion_module(tmp)
            req = SimpleNamespace(
                name="Lia",
                email="lia@example.test",
                phone=None,
                preferred_contact="email",
                interest="life-assessment",
                bottleneck="I want a clearer aim and steadier daily practice.",
            )
            status = mod._send_founder_lead_alert(req, urlopen=fake_urlopen)

        self.assertEqual(status, {"ok": True, "status": 200})
        self.assertEqual(calls[0][1], 2)

    def test_submit_life_lead_queues_deliverable_email_and_returns_inbox_ack(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = load_champion_module(tmp)
            tasks = BackgroundTasks()
            req = SimpleNamespace(
                name="Lia",
                email="lia@example.test",
                phone=None,
                timezone=None,
                preferred_contact=None,
                interest="life-assessment",
                lens="life",
                bottleneck="I want a clearer aim and steadier daily practice.",
                seven_areas=None,
                life_answers=DAY0,
                life_context={"spiritual": "Build the village that shows paradise is practical."},
                company=None,
            )
            request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.8"))
            with mock.patch.object(mod, "_send_founder_lead_alert", return_value={"ok": True, "status": 200}):
                response = asyncio.run(mod.submit_lead(req, request, tasks))

        self.assertTrue(response["ok"])
        self.assertEqual(response["deliverable_status"], "queued")
        self.assertIn("Allocation Score is on its way to your inbox", response["message"])
        self.assertEqual(response["life_result"]["allocation_score"], 59.3)
        self.assertEqual(len(tasks.tasks), 1)

    def test_assessment_chat_captures_lead_then_returns_live_score_public_mode(self):
        score = {
            "allocation_score": 62,
            "weakest_dimension": "time",
            "scores": {"capital": 70, "time": 30, "attention": 55, "people": 60, "ai": 50, "knowledge": 65},
            "archetype": "Time-Trapped Operator",
            "archetype_line": "Useful business, too many manual handoffs.",
            "surprise": "The constraint is repeat work, not demand.",
            "opportunities": [
                {"title": "Automate intake", "dimension": "time", "why": "manual copy/paste", "est_annual_value": "$18k/yr"},
                {"title": "Consolidate tools", "dimension": "capital", "why": "overlap", "est_annual_value": "$6k/yr"},
                {"title": "AI follow-up", "dimension": "ai", "why": "unused leverage", "est_annual_value": "$12k/yr"},
            ],
            "monday_move": "List the three repeated handoffs.",
            "reserved_next_step": "DRAFT: Blueprint invite.",
        }
        with tempfile.TemporaryDirectory() as tmp:
            mod = load_champion_module(tmp)
            request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.9"))
            tasks = BackgroundTasks()
            state = {}
            session_id = ""

            def turn(field, message):
                nonlocal state, session_id, tasks
                req = SimpleNamespace(session_id=session_id, field=field, message=message, state=state, variant="chat-test")
                response = mod.assessment_chat(req, request, tasks)
                state = response["state"]
                session_id = response["session_id"]
                return response

            first = turn(None, None)
            self.assertEqual(first["next_field"], "business")
            turn("business", "Acme helps operators automate client intake.")
            turn("bottleneck", "Too much founder time is stuck in handoffs.")
            turn("name", "Taylor")
            invalid = turn("email", "not-an-email")
            self.assertFalse(invalid["lead_captured"])
            self.assertEqual(invalid["next_field"], "email")
            self.assertEqual(len(tasks.tasks), 0)
            captured = turn("email", "taylor@example.test")
            self.assertTrue(captured["lead_captured"])
            self.assertIn("Perfect. I have the lead captured.", captured["reply"])
            self.assertEqual(len(tasks.tasks), 1)

            turn("tools", "HubSpot, Zapier, Airtable, ChatGPT Team.")
            with mock.patch.object(mod, "_score_assessment_chat_state", return_value=score):
                final = turn("team", "Founder plus two contractors.")

            lead_path = Path(tmp) / "leads" / final["filename"]
            lead_md = lead_path.read_text(encoding="utf-8")

        self.assertTrue(final["public_mode"])
        self.assertFalse(final["private_context_used"])
        self.assertEqual(final["score"]["allocation_score"], 62)
        self.assertIn("Your Allocation Score is 62/100", final["reply"])
        self.assertIn("allocation_score: 62", lead_md)
        self.assertIn("public_mode: true", lead_md)
        self.assertIn("private_context_used: false", lead_md)

    def test_meta_comment_webhook_stages_public_reply_and_private_reply_without_live_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = load_champion_module(tmp)
            tasks = BackgroundTasks()
            payload = mod.MetaWebhookPayload(**{
                "object": "page",
                "entry": [{
                    "changes": [{
                        "field": "feed",
                        "value": {
                            "item": "comment",
                            "verb": "add",
                            "comment_id": "c_123",
                            "post_id": "p_456",
                            "message": "yes, send me the AI assessment score",
                            "from": {"id": "u_1", "name": "Taylor Visitor"},
                        },
                    }],
                }],
            })

            result = mod.meta_comment_webhook(payload, tasks)
            duplicate = mod.meta_comment_webhook(payload, tasks)
            audit = (Path(tmp) / "leads" / "meta_funnel_audit.jsonl").read_text(encoding="utf-8")

        self.assertTrue(result["ok"])
        self.assertEqual(result["events"], 1)
        row = result["results"][0]
        self.assertEqual(row["status"], "processed")
        self.assertIn("Taylor", row["public_reply"])
        self.assertEqual(row["public_action"]["status"], "would_send")
        self.assertEqual(row["dm_action"]["status"], "would_send")
        self.assertEqual(duplicate["results"][0]["reason"], "duplicate comment")
        self.assertIn('"comment_id": "c_123"', audit)

    def test_meta_comment_webhook_holds_comments_without_assessment_trigger(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod = load_champion_module(tmp)
            payload = mod.MetaWebhookPayload(**{
                "object": "page",
                "entry": [{
                    "changes": [{
                        "field": "feed",
                        "value": {
                            "item": "comment",
                            "verb": "add",
                            "comment_id": "c_999",
                            "post_id": "p_456",
                            "message": "nice post",
                            "from": {"id": "u_2", "name": "Morgan"},
                        },
                    }],
                }],
            })

            result = mod.meta_comment_webhook(payload, BackgroundTasks())

        self.assertEqual(result["results"][0]["status"], "held")
        self.assertEqual(result["results"][0]["reason"], "no assessment trigger phrase")

    def test_meta_messenger_webhook_runs_public_assessment_and_writes_lead(self):
        score = {
            "allocation_score": 71,
            "weakest_dimension": "attention",
            "scores": {"capital": 60, "time": 55, "attention": 25, "people": 70, "ai": 65, "knowledge": 80},
            "archetype": "Attention-Leveraged Builder",
            "archetype_line": "Strong raw capacity, scattered signal.",
            "surprise": "The fastest unlock is a tighter intake loop.",
            "opportunities": [
                {"title": "Messenger intake loop", "dimension": "attention", "why": "captures demand in-thread", "est_annual_value": "$20k/yr"},
            ],
            "monday_move": "Post one offer piece and invite comments.",
            "reserved_next_step": "DRAFT: Blueprint invite.",
        }
        with tempfile.TemporaryDirectory() as tmp:
            mod = load_champion_module(tmp)
            tasks = BackgroundTasks()

            def send(text):
                payload = mod.MetaWebhookPayload(**{
                    "object": "page",
                    "entry": [{
                        "messaging": [{
                            "sender": {"id": "psid_123"},
                            "message": {"mid": f"m_{len(text)}", "text": text},
                        }],
                    }],
                })
                return mod.meta_comment_webhook(payload, tasks)["results"][0]

            first = send("Acme helps service businesses automate client intake.")
            self.assertEqual(first["chat"]["next_field"], "bottleneck")
            send("Founder time is trapped in repetitive DMs and spreadsheets.")
            send("Taylor")
            captured = send("taylor@example.test")
            self.assertTrue(captured["chat"]["lead_captured"])
            self.assertEqual(len(tasks.tasks), 1)
            send("HubSpot, Zapier, Airtable, ChatGPT Team.")
            with mock.patch.object(mod, "_score_assessment_chat_state", return_value=score):
                final = send("Founder plus two contractors.")

            lead_path = Path(tmp) / "leads" / final["chat"]["filename"]
            lead_md = lead_path.read_text(encoding="utf-8")

        self.assertEqual(final["chat"]["score"]["allocation_score"], 71)
        self.assertEqual(final["reply_action"]["status"], "would_send")
        self.assertIn("source: assessment-chat", lead_md)
        self.assertIn("variant: meta-messenger", lead_md)
        self.assertIn("allocation_score: 71", lead_md)


if __name__ == "__main__":
    unittest.main()
