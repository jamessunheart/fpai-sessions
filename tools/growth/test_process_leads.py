import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.growth import process_leads


class MetaLeadEventTests(unittest.TestCase):
    def test_meta_payload_hashes_normalized_email_and_uses_lead_id(self):
        payload = process_leads.meta_lead_payload(
            lead_id="lead-20260705-abc123",
            email="  PERSON@Example.COM ",
            event_time=1234567890,
        )

        event = payload["data"][0]
        expected_hash = hashlib.sha256(b"person@example.com").hexdigest()
        self.assertEqual(event["event_name"], "Lead")
        self.assertEqual(event["event_time"], 1234567890)
        self.assertEqual(event["event_id"], "lead-20260705-abc123")
        self.assertEqual(event["action_source"], "website")
        self.assertEqual(event["event_source_url"], "https://fullpotential.com/assessment")
        self.assertEqual(event["user_data"], {"em": [expected_hash]})

    def test_send_meta_lead_event_posts_to_pixel_events_endpoint(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"events_received":1}'

        with mock.patch.object(process_leads.urllib.request, "urlopen", return_value=Response()) as urlopen:
            ok, detail = process_leads.send_meta_lead_event(
                lead_id="lead-file",
                email="person@example.com",
                access_token="meta-token",
                pixel_id="110851475615838",
            )

        self.assertTrue(ok)
        self.assertIn("HTTP 200", detail)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://graph.facebook.com/v20.0/110851475615838/events?access_token=meta-token")
        self.assertEqual(request.method, "POST")
        self.assertIn(b'"event_id": "lead-file"', request.data)
        self.assertIn(b'"action_source": "website"', request.data)

    def test_missing_meta_token_skips_without_network(self):
        with mock.patch.object(process_leads.urllib.request, "urlopen") as urlopen:
            ok, detail = process_leads.send_meta_lead_event(
                lead_id="lead-file",
                email="person@example.com",
                access_token="",
            )

        self.assertFalse(ok)
        self.assertEqual(detail, "missing Meta access token")
        urlopen.assert_not_called()

    def test_meta_token_can_come_from_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "meta.env"
            env_file.write_text('META_ACCESS_TOKEN="from-file"\n', encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(process_leads, "META_ENV", env_file):
                self.assertEqual(process_leads.meta_access_token(), "from-file")


class ProcessLeadFlowTests(unittest.TestCase):
    def test_successful_email_triggers_meta_capi_before_marking_processed(self):
        lead_text = "---\nemail: real@example.com\nname: Real Person\n---\nbody\n"

        def fake_run(cmd, **kwargs):
            out_path = Path(cmd[cmd.index("--out") + 1])
            out_path.write_text("deliverable", encoding="utf-8")
            return mock.Mock(returncode=0, stderr="", stdout="")

        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "processed.txt"
            work = Path(tmp) / "work"
            brevo_env = Path(tmp) / "brevo.env"
            brevo_env.write_text("BREVO_API_KEY=brevo\n", encoding="utf-8")
            with (
                mock.patch.object(process_leads, "STATE", state),
                mock.patch.object(process_leads, "WORK", work),
                mock.patch.object(process_leads, "KILL", Path(tmp) / "disabled"),
                mock.patch.object(process_leads, "BREVO_ENV", brevo_env),
                mock.patch.object(process_leads, "list_remote_leads", return_value=["/remote/lead-1.md"]),
                mock.patch.object(process_leads, "fetch_lead", return_value=lead_text),
                mock.patch.object(process_leads.subprocess, "run", side_effect=fake_run),
                mock.patch.object(process_leads, "send_email", return_value=(True, "HTTP 201")),
                mock.patch.object(process_leads, "send_meta_lead_event", return_value=(True, "HTTP 200")) as send_meta,
                mock.patch.object(process_leads, "tg_alert"),
                mock.patch.dict(os.environ, {"META_ACCESS_TOKEN": "meta-token"}, clear=True),
            ):
                code = process_leads.main(["--live"])

            self.assertEqual(code, 0)
            self.assertEqual(state.read_text(encoding="utf-8"), "lead-1")
            send_meta.assert_called_once_with(
                lead_id="lead-1",
                email="real@example.com",
                access_token="meta-token",
            )
