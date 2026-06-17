from __future__ import annotations

import json
import unittest

from tools.outreach import pre_profiler


class FakeResponse:
    headers = {"content-type": "text/html"}

    def __init__(self, body: str):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def read(self, *_args):
        return self.body.encode("utf-8")


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.row = (42,)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, sql, params=()):
        self.conn.executed.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.row


class FakeConn:
    def __init__(self):
        self.executed = []

    def cursor(self):
        return FakeCursor(self)


class PreProfilerTests(unittest.TestCase):
    def test_profiler_fetches_and_summarizes_public_website(self):
        html = """
        <html><head><title>Cora Vida - Regenerative Cities</title></head>
        <body>
        <h1>Green cities builder</h1>
        <p>Josh builds regenerative city projects and community tools for conscious urban transformation.</p>
        <p>Recent work includes coordination software for neighborhood-scale climate action.</p>
        </body></html>
        """
        source = pre_profiler.fetch_public_source("https://coravida.com", urlopen=lambda *_args, **_kwargs: FakeResponse(html))
        self.assertIsNotNone(source)
        profile = pre_profiler.build_profile(
            {"id": 7, "name": "Josh Pasmore", "url_hints": ["coravida.com"]},
            fetcher=lambda _url: source,
        )
        self.assertIn("Josh Pasmore", profile.summary)
        self.assertIn("coravida.com", profile.sources["website"])
        self.assertGreaterEqual(profile.confidence, 0.45)
        self.assertIn("regenerative", json.dumps(profile.resonance_points).lower())

    def test_resonance_points_reject_generic_growth(self):
        generic = pre_profiler.resonance_from_text("Interested in growth", why_prefix="Public profile signal")
        specific = pre_profiler.resonance_from_text(
            "Builds regenerative community tools for conscious city coordination",
            why_prefix="Public profile signal",
        )
        self.assertIsNone(generic)
        self.assertIsNotNone(specific)

    def test_james_notes_override_public_info(self):
        public_source = pre_profiler.PublicSource(
            "website",
            "https://example.com",
            "Accounting Services",
            "Traditional accounting services for small business tax compliance.",
        )
        profile = pre_profiler.build_profile(
            {
                "id": 8,
                "name": "Maya Chen",
                "notes": "met at Zen retreat, knows about conscious cities",
                "url_hints": ["example.com"],
            },
            fetcher=lambda _url: public_source,
        )
        self.assertIn("Zen retreat", profile.summary)
        self.assertEqual(profile.resonance_points[0]["point"], "met at Zen retreat, knows about conscious cities")
        self.assertIn("Zen retreat", profile.suggested_body)

    def test_low_confidence_flag_when_public_info_sparse(self):
        profile = pre_profiler.build_profile({"id": 9, "name": "Sparse Person"}, fetcher=lambda _url: None)
        self.assertLess(profile.confidence, 0.4)
        self.assertEqual(profile.sources, {})
        self.assertEqual(profile.resonance_points, [])
        self.assertIn("sparse", profile.summary.lower())

    def test_private_network_url_hints_are_rejected(self):
        blocked = [
            "http://169.254.169.254/latest/meta-data",
            "http://10.0.0.1/private",
            "http://192.168.1.5/profile",
            "http://[::1]/profile",
            "http://2130706433/profile",
            "http://0177.0.0.1/profile",
            "http://0x7f.0.0.1/profile",
        ]
        for url in blocked:
            with self.subTest(url=url):
                self.assertFalse(pre_profiler.is_public_url(url))
                self.assertIsNone(pre_profiler.normalize_public_url(url))

    def test_public_fetch_rejects_hosts_that_resolve_private(self):
        calls = []

        def resolver(*_args, **_kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("100.64.0.1", 443))]

        def urlopen(*_args, **_kwargs):
            calls.append(True)
            return FakeResponse("<html></html>")

        import socket

        source = pre_profiler.fetch_public_source("https://public-looking.example", resolver=resolver)
        self.assertIsNone(source)
        self.assertEqual(calls, [])

    def test_store_inserts_private_contact_profile_row(self):
        conn = FakeConn()
        profile = pre_profiler.build_profile(
            {"id": 10, "name": "Ari Builder", "notes": "builds conscious community tools"},
            fetcher=lambda _url: None,
        )
        from tools.outreach import profile_store

        row_id = profile_store.insert_contact_profile(conn, profile=profile)
        self.assertEqual(row_id, 42)
        sql, params = conn.executed[0]
        self.assertIn("brain_index.contact_profiles", sql)
        self.assertEqual(params[0], 10)
        self.assertIn("conscious community tools", params[4])

    def test_seed_contact_handler_profiles_without_sending(self):
        from tools.outreach import contact_seed_api

        conn = FakeConn()
        payload = {
            "name": "Josh Pasmore",
            "email": "greenearthvision@example.com",
            "channel": "email",
            "notes": "green cities builder",
            "url_hints": ["coravida.com"],
        }

        def profiler(contact, *, conn: FakeConn):
            self.assertEqual(contact["id"], 42)
            self.assertIs(conn, db_conn)
            return pre_profiler.build_profile(contact, fetcher=lambda _url: None)

        db_conn = conn
        result = contact_seed_api.seed_and_profile(payload, conn=db_conn, profiler=profiler)
        self.assertEqual(result["contact_id"], 42)
        self.assertEqual(result["send_status"], "not_sent")
        self.assertIn("subject", result["draft"])


if __name__ == "__main__":
    unittest.main()
