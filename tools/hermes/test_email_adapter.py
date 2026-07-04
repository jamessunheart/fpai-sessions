from __future__ import annotations

import json
import unittest

from tools.hermes import email_adapter


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def read(self):
        return b'{"messageId":"brevo-123"}'


class EmailAdapterTests(unittest.TestCase):
    def test_manual_outreach_email_is_retired_by_default(self):
        result = email_adapter.send_outreach_email(to_email="alex@example.com", to_name="Alex", env={})
        self.assertFalse(result.sent)
        self.assertFalse(result.dry_run)
        self.assertTrue(result.disabled)
        self.assertEqual(result.reason, email_adapter.RETIRED_REASON)
        self.assertEqual(result.payload["subject"], "What does your full potential actually look like?")
        self.assertEqual(result.payload["sender"]["email"], "james@fullpotential.com")
        self.assertIn("Hi Alex,", result.payload["textContent"])
        self.assertIn("full potential actually look like", result.payload["textContent"])
        self.assertIn("@sunheartbrain_bot", result.payload["textContent"])
        self.assertIn("Reply STOP to opt out", result.payload["textContent"])
        self.assertIn("-- Sunheart AI", result.payload["textContent"])
        self.assertNotIn("features", result.payload["textContent"].lower())

    def test_live_send_posts_brevo_transactional_payload(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["timeout"] = timeout
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        result = email_adapter.send_outreach_email(
            to_email="sam@example.com",
            to_name="Sam",
            env={"MANUAL_OUTREACH_LIVE": "1", "OUTREACH_LIVE": "1", "DRY_RUN": "0", "BREVO_API_KEY": "key"},
            urlopen=fake_urlopen,
        )
        self.assertTrue(result.sent)
        self.assertEqual(result.message_id, "brevo-123")
        self.assertEqual(captured["url"], email_adapter.BREVO_TRANSACTIONAL_URL)
        self.assertEqual(captured["payload"]["to"], [{"email": "sam@example.com", "name": "Sam"}])
        self.assertEqual(captured["payload"]["replyTo"]["email"], "james@fullpotential.com")
        self.assertEqual(captured["headers"]["Api-key"], "key")

    def test_disable_switch_blocks_before_live_send(self):
        result = email_adapter.send_outreach_email(
            to_email="sam@example.com",
            env={"MANUAL_OUTREACH_LIVE": "1", "OUTREACH_LIVE": "1", "DRY_RUN": "0", "BREVO_API_KEY": "key", "OUTREACH_EMAIL_DISABLE": "1"},
            urlopen=lambda *_args, **_kwargs: self.fail("should not call Brevo"),
        )
        self.assertFalse(result.sent)
        self.assertTrue(result.disabled)


if __name__ == "__main__":
    unittest.main()
