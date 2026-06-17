from __future__ import annotations

import json
import unittest

from tools.outreach import fp_champions_puller


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.lower().split())
        self.conn.executed.append((normalized, params))
        if normalized.startswith("select lower(handle)"):
            wanted = {str(value).lower() for value in params}
            self.rows = [(handle,) for handle in self.conn.handles if handle in wanted]
        elif "information_schema.columns" in normalized:
            self.rows = [(col,) for col in self.conn.columns_by_table.get(params[0], set())]
        elif normalized.startswith("insert into brain_index.probe_pool"):
            self.conn.inserted.append(params)
            self.handles = self.conn.handles.add(str(params[1]).lower())
            self.rows = []

    def fetchall(self):
        return self.rows


class FakeConn:
    def __init__(self, handles=None, columns_by_table=None):
        self.handles = set(handles or [])
        self.columns_by_table = {
            "probe_pool": {"id", "pool", "handle", "platform", "added_by", "source", "metadata"},
        }
        if columns_by_table:
            self.columns_by_table.update({key: set(value) for key, value in columns_by_table.items()})
        self.inserted = []
        self.executed = []

    def cursor(self):
        return FakeCursor(self)


class FPChampionsPullerTests(unittest.TestCase):
    def test_fetch_filters_email_and_sorts_by_last_active_then_field_score(self):
        payload = {
            "champions": [
                {"name": "Old High", "email": "old@example.com", "field_score": 99, "last_active": "2026-06-15T10:00:00Z", "affiliate_count": 1},
                {"name": "Recent Low", "email": "recent@example.com", "field_score": 2, "last_active": "2026-06-16T10:00:00Z", "affiliate_count": 1},
                {"name": "Recent High", "email": "high@example.com", "field_score": 10, "last_active": "2026-06-16T10:00:00Z", "affiliate_count": 1},
                {"name": "No Email", "email": "not-an-email", "field_score": 500, "last_active": "2026-06-17T10:00:00Z"},
            ]
        }
        champions = fp_champions_puller.fetch_champions(urlopen=lambda *_args, **_kwargs: FakeResponse(payload))
        self.assertEqual([c.email for c in champions], ["high@example.com", "recent@example.com", "old@example.com"])

    def test_insert_skips_existing_handle_and_sets_source(self):
        conn = FakeConn(handles={"recent@example.com"})
        champions = [
            fp_champions_puller.Champion("Recent", "recent@example.com", 3, fp_champions_puller.parse_time("2026-06-16T10:00:00Z"), 0),
            fp_champions_puller.Champion("New", "new@example.com", 2, fp_champions_puller.parse_time("2026-06-15T10:00:00Z"), 0),
        ]
        inserted = fp_champions_puller.insert_champions(conn, champions)
        self.assertEqual(inserted, 1)
        self.assertEqual(conn.inserted[0][:5], ("warm", "new@example.com", "email", "system", "fp_game_champions"))
        metadata = json.loads(conn.inserted[0][5])
        self.assertEqual(metadata["name"], "New")
        self.assertEqual(metadata["field_score"], 2)

    def test_insert_works_before_source_metadata_migration(self):
        conn = FakeConn(columns_by_table={"probe_pool": {"id", "pool", "handle", "platform", "added_by"}})
        champions = [
            fp_champions_puller.Champion("New", "new@example.com", 2, fp_champions_puller.parse_time("2026-06-15T10:00:00Z"), 0),
        ]
        inserted = fp_champions_puller.insert_champions(conn, champions)
        self.assertEqual(inserted, 1)
        self.assertEqual(conn.inserted[0], ("warm", "new@example.com", "email", "system"))


if __name__ == "__main__":
    unittest.main()
