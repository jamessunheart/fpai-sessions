from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.hermes import wa_sender


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def read(self):
        return b'{"messages":[{"id":"wamid.123"}]}'


class WhatsAppSenderTests(unittest.TestCase):
    def test_wa_link_generation_encodes_prefill_without_api_call(self):
        link = wa_sender.generate_wa_link(
            "Hi Alex, want to chat?",
            phone_number="+1 (555) 123-4567",
        )
        self.assertEqual(link, "https://wa.me/15551234567?text=Hi%20Alex%2C%20want%20to%20chat%3F")

    def test_session_message_defaults_to_dry_run(self):
        result = wa_sender.send_session_message("15551234567", "Hello there")
        self.assertFalse(result.sent)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.payload["type"], "text")
        self.assertEqual(result.payload["text"]["body"], "Hello there")

    def test_template_send_requires_whatsapp_live(self):
        result = wa_sender.send_template_message(
            "15551234567",
            "conscious_chat_invite",
            ["James"],
            env={"WA_ACCESS_TOKEN": "token", "WA_PHONE_NUMBER_ID": "phone", "DRY_RUN": "0"},
            urlopen=lambda *_args, **_kwargs: self.fail("should not call Meta"),
        )
        self.assertFalse(result.sent)
        self.assertTrue(result.dry_run)

    def test_live_session_posts_meta_payload_when_enabled(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["timeout"] = timeout
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        result = wa_sender.send_session_message(
            "15551234567",
            "Hello",
            env={"WHATSAPP_LIVE": "1", "DRY_RUN": "0", "WA_ACCESS_TOKEN": "token", "WA_PHONE_NUMBER_ID": "phone-id"},
            urlopen=fake_urlopen,
        )
        self.assertTrue(result.sent)
        self.assertEqual(result.message_id, "wamid.123")
        self.assertEqual(captured["url"], "https://graph.facebook.com/v19.0/phone-id/messages")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer token")
        self.assertEqual(captured["payload"]["to"], "15551234567")

    def test_unverified_template_rate_limit_blocks_more_than_ten_per_hour(self):
        now = datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)
        history = [now - timedelta(minutes=idx) for idx in range(10)]
        result = wa_sender.send_template_message(
            "15551234567",
            "conscious_chat_invite",
            ["James"],
            env={"WHATSAPP_LIVE": "1", "DRY_RUN": "0", "WA_ACCESS_TOKEN": "token", "WA_PHONE_NUMBER_ID": "phone"},
            template_history=history,
            now=now,
            urlopen=lambda *_args, **_kwargs: self.fail("should be rate limited"),
        )
        self.assertEqual(result.reason, "template_rate_limited")

    def test_template_rate_limit_reads_default_history_log(self):
        now = datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            rate_log = Path(tmp) / "wa-template.jsonl"
            rows = [
                {"sent_at": (now - timedelta(minutes=idx)).strftime("%Y-%m-%dT%H:%M:%SZ")}
                for idx in range(10)
            ]
            rate_log.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            rate_log.chmod(0o600)
            result = wa_sender.send_template_message(
                "15551234567",
                "conscious_chat_invite",
                ["James"],
                env={
                    "WHATSAPP_LIVE": "1",
                    "DRY_RUN": "0",
                    "WA_ACCESS_TOKEN": "token",
                    "WA_PHONE_NUMBER_ID": "phone",
                    "WA_TEMPLATE_RATE_LOG": str(rate_log),
                },
                now=now,
                urlopen=lambda *_args, **_kwargs: self.fail("should be rate limited from log"),
            )
        self.assertEqual(result.reason, "template_rate_limited")

    def test_successful_unverified_template_send_appends_rate_log(self):
        now = datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            private_dir = Path(tmp) / "private"
            private_dir.mkdir(mode=0o700)
            rate_log = private_dir / "wa-template.jsonl"
            result = wa_sender.send_template_message(
                "15551234567",
                "conscious_chat_invite",
                ["James"],
                env={
                    "WHATSAPP_LIVE": "1",
                    "DRY_RUN": "0",
                    "WA_ACCESS_TOKEN": "token",
                    "WA_PHONE_NUMBER_ID": "phone",
                    "WA_TEMPLATE_RATE_LOG": str(rate_log),
                },
                now=now,
                urlopen=lambda *_args, **_kwargs: FakeResponse(),
            )
            rows = [json.loads(line) for line in rate_log.read_text(encoding="utf-8").splitlines()]
            mode = rate_log.stat().st_mode & 0o777
        self.assertTrue(result.sent)
        self.assertEqual(rows[0], {"sent_at": "2026-06-17T10:00:00Z"})
        self.assertEqual(mode, 0o600)

    def test_custom_rate_log_fails_closed_on_shared_parent(self):
        now = datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            shared_dir = Path(tmp) / "shared"
            shared_dir.mkdir(mode=0o755)
            rate_log = shared_dir / "wa-template.jsonl"
            result = wa_sender.send_template_message(
                "15551234567",
                "conscious_chat_invite",
                ["James"],
                env={
                    "WHATSAPP_LIVE": "1",
                    "DRY_RUN": "0",
                    "WA_ACCESS_TOKEN": "token",
                    "WA_PHONE_NUMBER_ID": "phone",
                    "WA_TEMPLATE_RATE_LOG": str(rate_log),
                },
                now=now,
                urlopen=lambda *_args, **_kwargs: self.fail("unsafe rate log must block send"),
            )
            mode = shared_dir.stat().st_mode & 0o777
        self.assertEqual(result.reason, "unsafe_template_rate_log_parent")
        self.assertEqual(mode, 0o755)


if __name__ == "__main__":
    unittest.main()
