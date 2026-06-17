from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools.hermes import contact_loader


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, _sql, params=()):
        self.conn.rows.append(params)


class FakeConn:
    def __init__(self):
        self.rows = []

    def cursor(self):
        return FakeCursor(self)


class ContactLoaderTests(unittest.TestCase):
    def test_csv_load_creates_contact_pool_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contacts.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["name", "channel", "contact", "notes"])
                writer.writeheader()
                writer.writerow({"name": "Alex", "channel": "wa", "contact": "+1 555 123 4567", "notes": "Warm friend"})
            records = contact_loader.load_contacts_from_csv(path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].channel, "whatsapp")
        self.assertEqual(records[0].wa_id, "+1 555 123 4567")
        self.assertEqual(records[0].status, "pending")

    def test_manual_load_and_insert_writes_private_notes_json(self):
        records = contact_loader.load_contacts_manual([
            {"name": "Sam", "channel": "email", "contact": "sam@example.com", "notes": "Private context"},
        ])
        conn = FakeConn()
        inserted = contact_loader.insert_contact_pool(conn, records)
        self.assertEqual(inserted, 1)
        params = conn.rows[0]
        self.assertEqual(params[2], None)
        self.assertEqual(params[3], "sam@example.com")
        self.assertEqual(json.loads(params[7]), {"private_notes": "Private context"})

    def test_csv_requires_contract_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contacts.csv"
            path.write_text("name,channel\nAlex,whatsapp\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                contact_loader.load_contacts_from_csv(path)


if __name__ == "__main__":
    unittest.main()
