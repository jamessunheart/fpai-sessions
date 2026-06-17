from __future__ import annotations

import asyncio
import os
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

from tools.discovery import common, github_crawler, hn_crawler, instagram_crawler, reddit_crawler, run_all, telegram_scanner, twitter_crawler

NOW = datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)


@contextmanager
def patched_env(**values: str):
    old = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class FakeCursor:
    def __init__(self, conn: "FakeConn"):
        self.conn = conn
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.lower().split())
        self.conn.executed.append((normalized, params))
        if "information_schema.columns" in normalized:
            self.rows = [(col,) for col in self.conn.columns]
        elif "select lower(handle), lower(platform)" in normalized:
            handles = set(params[0])
            platforms = set(params[1])
            self.rows = [
                (row["handle"].lower(), row["platform"].lower())
                for row in self.conn.rows
                if row["handle"].lower() in handles and row["platform"].lower() in platforms
            ]
        elif normalized.startswith("insert into brain_index.probe_pool"):
            fields = sql.split("(", 1)[1].split(")", 1)[0].replace("\n", " ").split(",")
            self.conn.rows.append({field.strip(): value for field, value in zip(fields, params)})
            self.rows = []
        else:
            self.rows = []

    def fetchall(self):
        return self.rows


class FakeConn:
    def __init__(self):
        self.columns = {"pool", "handle", "platform", "added_by", "source", "topic_signal", "discovery_score", "metadata"}
        self.rows = []
        self.executed = []

    def cursor(self):
        return FakeCursor(self)


class FakeLocator:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class FakeElement:
    def __init__(self, text: str, href: str = ""):
        self.text = text
        self.href = href

    def inner_text(self, timeout=1000):
        return self.text

    def get_attribute(self, name: str):
        return self.href if name == "href" else None


class FakePage:
    def __init__(self, articles=None, anchors=None):
        self.articles = articles or []
        self.anchors = anchors or []
        self.closed = False

    def goto(self, *_args, **_kwargs):
        return None

    def wait_for_timeout(self, *_args):
        return None

    def locator(self, query: str):
        return FakeLocator(self.articles if query == "article" else self.anchors)

    def close(self):
        self.closed = True


class AsyncIter:
    def __init__(self, rows):
        self.rows = list(rows)

    def __aiter__(self):
        self._iter = iter(self.rows)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class FakeTelegramMessage:
    date = NOW
    message = "I am exploring personal growth and awakening AI for my full potential community."

    async def get_sender(self):
        return SimpleNamespace(username="seeker")


class FakeTelegramClient:
    def iter_dialogs(self):
        return AsyncIter([SimpleNamespace(name="full potential community", entity="group1")])

    def iter_messages(self, _entity, limit=40):
        return AsyncIter([FakeTelegramMessage()])


class DiscoveryTests(unittest.TestCase):
    def assert_contact_shape(self, row: common.DiscoveryContact, platform: str):
        shaped = row.row()
        for key in ("handle", "platform", "source", "topic_signal", "discovery_score", "metadata"):
            self.assertIn(key, shaped)
        self.assertEqual(shaped["platform"], platform)
        self.assertGreaterEqual(shaped["discovery_score"], 0.4)

    def test_reddit_crawler_returns_shaped_rows_from_mock_json(self):
        payload = {
            "data": {"children": [{"data": {
                "author": "human",
                "created_utc": NOW.timestamp(),
                "author_karma": 42,
                "title": "Conscious AI and full potential",
                "selftext": "I am seeking self actualization and personal growth.",
                "permalink": "/r/awakening/x",
            }}]}
        }
        rows = reddit_crawler.discover(subreddits=("awakening",), now=NOW, fetcher=lambda _url: payload)
        self.assertEqual(len(rows), 1)
        self.assert_contact_shape(rows[0], "reddit")

    def test_hn_crawler_returns_shaped_rows_from_mock_api(self):
        payload = {"hits": [{"author": "hnuser", "created_at": NOW.isoformat(), "comment_text": "personal AI " * 15, "objectID": "1"}]}
        rows = hn_crawler.discover(queries=("personal AI",), now=NOW, fetcher=lambda _url: payload)
        self.assertEqual(len(rows), 1)
        self.assert_contact_shape(rows[0], "hn")

    def test_github_crawler_returns_shaped_rows_from_mock_api(self):
        payload = {"items": [{"owner": {"login": "builder"}, "description": "personal AI and conscious AI tools", "full_name": "builder/repo", "html_url": "https://github.com/builder/repo"}]}
        rows = github_crawler.discover(topics=("personal-ai",), fetcher=lambda _url: payload)
        self.assertEqual(len(rows), 1)
        self.assert_contact_shape(rows[0], "github")

    def test_twitter_crawler_returns_shaped_rows_from_fake_page(self):
        page = FakePage(articles=[FakeElement("@seeker I want #fullpotential and conscious AI")])
        rows = twitter_crawler.discover(hashtags=("fullpotential",), page_factory=lambda **_kw: page, delay=0)
        self.assertEqual(len(rows), 1)
        self.assert_contact_shape(rows[0], "twitter")

    def test_instagram_crawler_returns_shaped_rows_from_fake_page(self):
        page = FakePage(anchors=[FakeElement("#selfactualization awakening full potential", "/person/")])
        rows = instagram_crawler.discover(hashtags=("selfactualization",), page_factory=lambda: page, delay=0)
        self.assertEqual(len(rows), 1)
        self.assert_contact_shape(rows[0], "instagram")

    def test_telegram_scanner_returns_shaped_rows_from_fake_client(self):
        rows = asyncio.run(telegram_scanner.discover_async(queries=("full potential",), client=FakeTelegramClient(), now=NOW))
        self.assertEqual(len(rows), 1)
        self.assert_contact_shape(rows[0], "telegram")

    def test_dedup_skips_existing_handle_platform(self):
        conn = FakeConn()
        conn.rows.append({"handle": "u/human", "platform": "reddit"})
        rows = [
            common.DiscoveryContact("u/human", "reddit", "reddit_awakening", "full potential", 0.8),
            common.DiscoveryContact("@fresh", "twitter", "twitter_#fullpotential", "full potential", 0.8),
        ]
        inserted = common.insert_contacts(conn, rows)
        self.assertEqual(inserted, 1)
        self.assertEqual(conn.rows[-1]["handle"], "@fresh")

    def test_score_below_point_four_excluded_from_outreach_gate(self):
        conn = FakeConn()
        rows = [
            common.DiscoveryContact("@weak", "twitter", "twitter_#fullpotential", "short", 0.39),
            common.DiscoveryContact("@strong", "twitter", "twitter_#fullpotential", "full potential awakening", 0.7),
        ]
        inserted = common.insert_contacts(conn, rows)
        self.assertEqual(inserted, 1)
        self.assertEqual(conn.rows[0]["handle"], "@strong")

    def test_discovery_disable_exits_run_all_cleanly(self):
        with patched_env(DISCOVERY_DISABLE="1"):
            result = run_all.run_all()
        self.assertTrue(result["disabled"])
        self.assertEqual(result["found"], 0)
        self.assertEqual(result["inserted"], 0)


if __name__ == "__main__":
    unittest.main()
