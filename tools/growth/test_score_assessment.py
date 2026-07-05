import tempfile
import unittest
from unittest import mock
from pathlib import Path

from tools.growth import score_assessment as score


class UrlFirstAssessmentTests(unittest.TestCase):
    def test_run_claude_uses_model_router_and_lenient_json(self):
        with mock.patch(
            "tools.intelligence.model_router.call_model",
            return_value={"response": '```json\n{"scores":{"capital":50}}\n```', "provider": "claude"},
        ) as call_model, mock.patch.object(score, "_run_claude_cli") as cli:
            self.assertEqual(score.run_claude("prompt"), {"scores": {"capital": 50}})

        call_model.assert_called_once_with("prompt", "assessment-scorer")
        cli.assert_not_called()

    def test_run_claude_falls_back_to_direct_cli_when_router_unavailable(self):
        with mock.patch(
            "tools.intelligence.model_router.call_model",
            side_effect=RuntimeError("router unavailable"),
        ), mock.patch.object(score, "_run_claude_cli", return_value='prose {"ok": true} trailing') as cli:
            self.assertEqual(score.run_claude("prompt"), {"ok": True})

        cli.assert_called_once_with("prompt")

    def test_normalize_url_rejects_non_public_or_login_urls(self):
        self.assertEqual(score.normalize_url("example.com"), "https://example.com/")
        with self.assertRaises(ValueError):
            score.normalize_url("ftp://example.com")
        with self.assertRaises(ValueError):
            score.normalize_url("https://user:pass@example.com")

    def test_fetch_public_site_respects_robots_and_builds_prefill_context(self):
        calls = []

        def fake_fetch(url, timeout):
            calls.append(url)
            if url.endswith("/robots.txt"):
                return 200, {"content-type": "text/plain"}, "User-agent: *\nDisallow: /pricing\n"
            body = {
                "https://acme.test/": """
                  <html><head><title>Acme Automation Studio</title></head>
                  <body><script>ignore()</script>
                    Acme is a creative agency and automation studio. Book a discovery call.
                    Case studies show results for operations teams. Schedule a consultation.
                  </body></html>
                """,
                "https://acme.test/about": """
                  <html><head><title>About Acme</title></head>
                  <body>Our team includes a founder, strategists, and implementation staff.
                  We work with operators who need clearer systems, better handoffs, and less manual coordination.</body></html>
                """,
                "https://acme.test/services": """
                  <html><head><title>Services</title></head>
                  <body>Services include AI workflow automation, HubSpot cleanup, and Zapier support.
                  Clients usually arrive with repeated intake work, scattered spreadsheets, and a sales process that needs cleaner follow-up.</body></html>
                """,
            }.get(url)
            if body is None:
                return 404, {"content-type": "text/html"}, "<html><body>missing</body></html>"
            return 200, {"content-type": "text/html; charset=utf-8"}, body

        with tempfile.TemporaryDirectory() as tmp:
            site = score.fetch_public_site(
                "acme.test",
                cache_dir=Path(tmp),
                fetcher=fake_fetch,
                summary_runner=lambda _prompt: (_ for _ in ()).throw(RuntimeError("no model")),
            )

        self.assertIn("https://acme.test/robots.txt", calls)
        self.assertIn({"url": "https://acme.test/pricing", "status": "robots_disallowed", "title": "", "text": ""}, site["pages"])
        self.assertEqual(site["summary"]["business_type"], "agency or services firm")
        self.assertIn("HubSpot", site["summary"]["apparent_tools_stack"])
        self.assertIn("Zapier", site["summary"]["apparent_tools_stack"])
        self.assertIn("booking/scheduling", site["intake_context"])
        self.assertIn("Public pages read: https://acme.test/, https://acme.test/about, https://acme.test/services", site["intake_context"])

    def test_fetch_public_site_uses_domain_cache(self):
        calls = {"count": 0}

        def fake_fetch(url, timeout):
            calls["count"] += 1
            if url.endswith("/robots.txt"):
                return 404, {"content-type": "text/plain"}, ""
            return 200, {"content-type": "text/html"}, (
                "<html><head><title>Shop Site</title></head>"
                "<body>Shop online with cart checkout shipping collection testimonials support faq "
                "pricing plans membership schedule appointment founder team Shopify Stripe Mailchimp."
                "</body></html>"
            )

        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            first = score.fetch_public_site(
                "https://shop.test/pricing",
                cache_dir=cache_dir,
                fetcher=fake_fetch,
                summary_runner=lambda _prompt: (_ for _ in ()).throw(RuntimeError("no model")),
            )
            calls_after_first = calls["count"]
            second = score.fetch_public_site(
                "https://shop.test/services",
                cache_dir=cache_dir,
                fetcher=fake_fetch,
                summary_runner=lambda _prompt: (_ for _ in ()).throw(RuntimeError("no model")),
            )

        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(first["domain"], second["domain"])
        self.assertGreater(calls["count"], 0)
        self.assertEqual(calls["count"], calls_after_first)

    def test_render_includes_draft_next_step_with_url_placeholder_by_default(self):
        md = score.render(
            "Taylor",
            "Acme",
            {dim: 60 for dim in score.DIMENSIONS},
            60,
            "time",
            [{"title": "Automate intake", "dimension": "time", "why": "manual handoffs", "est_annual_value": "$18k/yr"}],
            {"next_step": "DRAFT: Want help turning this into a Blueprint?"},
        )

        self.assertIn("## Next step (DRAFT - James approval required)", md)
        self.assertIn("DRAFT: Want help turning this into a Blueprint?", md)
        self.assertIn("[Booking/Blueprint link placeholder](ASSESSMENT_CTA_URL)", md)
        self.assertIn("James provides final invitation copy", md)

    def test_render_uses_approved_cta_copy_and_url_when_configured(self):
        with mock.patch.dict(
            "os.environ",
            {
                "ASSESSMENT_CTA_COPY": "Approved James invitation copy.",
                "ASSESSMENT_CTA_URL": "https://fullpotential.com/blueprint",
            },
        ):
            md = score.render(
                "Taylor",
                "Acme",
                {dim: 60 for dim in score.DIMENSIONS},
                60,
                "time",
                [{"title": "Automate intake", "dimension": "time", "why": "manual handoffs", "est_annual_value": "$18k/yr"}],
                {"next_step": "DRAFT: Placeholder copy."},
            )

        self.assertIn("## Your next step", md)
        self.assertIn("Approved James invitation copy.", md)
        self.assertIn("[Book or view the Blueprint next step](https://fullpotential.com/blueprint)", md)
        self.assertNotIn("DRAFT - James approval required", md)
        self.assertNotIn("ASSESSMENT_CTA_URL", md)

    def test_score_data_returns_structured_result_for_chat(self):
        fake = {
            "scores": {dim: 50 for dim in score.DIMENSIONS},
            "archetype": "Time-Trapped Operator",
            "archetype_line": "The business is useful but handoff-heavy.",
            "surprise": "The constraint is not demand; it is repeat work.",
            "opportunities": [
                {"title": "Automate intake", "dimension": "time", "why": "manual handoffs", "est_annual_value": "$18k/yr"},
            ],
            "monday_move": "Write the three repeated handoffs.",
            "share_line": "I found the bottleneck.",
            "next_step": "DRAFT: Blueprint invite.",
        }
        fake["scores"]["time"] = 20

        with mock.patch.object(score, "run_claude", return_value=fake):
            data, scores, total, weakest = score.score_data("intake")

        self.assertEqual(data["archetype"], "Time-Trapped Operator")
        self.assertEqual(scores["time"], 20)
        self.assertEqual(weakest, "time")
        self.assertLess(total, 50)


if __name__ == "__main__":
    unittest.main()
