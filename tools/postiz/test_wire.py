import json
import tempfile
import unittest
from pathlib import Path

from tools.postiz.wire import (
    html_paragraphs,
    main,
    mcp_config_fragment,
    mcp_url,
    schedule_post_payload,
    validate_schedule_payload,
)


class PostizWireTests(unittest.TestCase):
    def test_mcp_url_uses_self_hosted_backend(self):
        self.assertEqual(
            mcp_url("https://postiz.fullpotential.ai/", "${POSTIZ_API_KEY}"),
            "https://postiz.fullpotential.ai/mcp/${POSTIZ_API_KEY}",
        )

    def test_config_fragment_has_no_secret_value(self):
        fragment = mcp_config_fragment(base_url="https://postiz.fullpotential.ai")
        encoded = json.dumps(fragment)
        self.assertIn("${POSTIZ_API_KEY}", encoded)
        self.assertIn("transport", encoded)
        self.assertNotIn("your-api-key", encoded)

    def test_schedule_payload_escapes_content_and_matches_postiz_shape(self):
        payload = schedule_post_payload(
            integration_id="mastodon-proof",
            platform="mastodon",
            content="FPOS proof <ready>\nSecond line",
            date="2026-06-19T10:00:00.000Z",
        )
        post = payload["socialPost"][0]
        self.assertEqual(post["integrationId"], "mastodon-proof")
        self.assertEqual(post["type"], "schedule")
        self.assertEqual(post["postsAndComments"][0]["content"], "<p>FPOS proof &lt;ready&gt;</p><p>Second line</p>")
        validate_schedule_payload(payload)

    def test_x_default_reply_setting(self):
        payload = schedule_post_payload(
            integration_id="x-proof",
            platform="x",
            content="Hello",
            date="2026-06-19T10:00:00Z",
        )
        self.assertEqual(payload["socialPost"][0]["settings"], [{"key": "who_can_reply_post", "value": "everyone"}])

    def test_rejects_unsafe_or_bad_payloads(self):
        with self.assertRaises(ValueError):
            html_paragraphs("")
        with self.assertRaises(ValueError):
            schedule_post_payload(
                integration_id="mastodon-proof",
                platform="mastodon",
                content="Hello",
                date="2026-06-19 10:00",
            )
        with self.assertRaises(ValueError):
            validate_schedule_payload(
                {
                    "socialPost": [
                        {
                            "type": "schedule",
                            "date": "2026-06-19T10:00:00Z",
                            "postsAndComments": [{"content": "<script>alert(1)</script>"}],
                        }
                    ]
                }
            )

    def test_cli_writes_payload_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "payload.json"
            rc = main(
                [
                    "schedule-payload",
                    "--integration-id",
                    "mastodon-proof",
                    "--platform",
                    "mastodon",
                    "--content",
                    "Proof post",
                    "--date",
                    "2026-06-19T10:00:00Z",
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(rc, 0)
            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(written["socialPost"][0]["integrationId"], "mastodon-proof")


if __name__ == "__main__":
    unittest.main()

