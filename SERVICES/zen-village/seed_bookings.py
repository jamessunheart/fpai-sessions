#!/usr/bin/env python3
"""Seed current bookings into the Zen Village booking database."""

import sys
sys.path.insert(0, '/opt/fpai/apps/zen-village')

from app.booking_models import get_db, init_db
from uuid import uuid4
from datetime import datetime

init_db()
conn = get_db()
cur = conn.cursor()

now = datetime.utcnow().isoformat()

bookings = [
    {
        "id": str(uuid4()),
        "structure_id": "astro-sol",
        "source": "direct",
        "external_id": None,
        "guest_name": "Paul",
        "guest_email": "guest-paul@zenvillagecr.com",
        "guest_phone": "",
        "guest_country": "Unknown",
        "check_in": "2026-03-26",
        "check_out": "2026-03-30",
        "nights": 4,
        "nightly_rate": 130.0,
        "cleaning_fee": 0,
        "discount_percent": 0,
        "total_amount": 520.0,
        "payment_status": "pending",
        "status": "checked_in",
        "special_requests": "",
        "arrival_time": None,
        "partner_code": None,
        "partner_commission": 0,
        "notes": "Nightly guest. Hasn't locked in long-term but likely staying at least through Monday. May extend.",
        "created_at": now,
        "updated_at": now,
    },
    {
        "id": str(uuid4()),
        "structure_id": "zen-casa",
        "source": "direct",
        "external_id": None,
        "guest_name": "Elizabeth",
        "guest_email": "guest-elizabeth@zenvillagecr.com",
        "guest_phone": "",
        "guest_country": "Unknown",
        "check_in": "2026-03-26",
        "check_out": "2026-04-01",
        "nights": 6,
        "nightly_rate": 30.0,
        "cleaning_fee": 0,
        "discount_percent": 0,
        "total_amount": 180.0,
        "payment_status": "pending",
        "status": "checked_in",
        "special_requests": "",
        "arrival_time": None,
        "partner_code": None,
        "partner_commission": 0,
        "notes": "One room of Zen Casa at $30/night.",
        "created_at": now,
        "updated_at": now,
    },
    {
        "id": str(uuid4()),
        "structure_id": "zen-casa",
        "source": "direct",
        "external_id": None,
        "guest_name": "Gia",
        "guest_email": "guest-gia@zenvillagecr.com",
        "guest_phone": "",
        "guest_country": "Unknown",
        "check_in": "2026-03-28",
        "check_out": "2026-04-01",
        "nights": 4,
        "nightly_rate": 30.0,
        "cleaning_fee": 0,
        "discount_percent": 0,
        "total_amount": 120.0,
        "payment_status": "pending",
        "status": "confirmed",
        "special_requests": "",
        "arrival_time": None,
        "partner_code": None,
        "partner_commission": 0,
        "notes": "One room of Zen Casa at $30/night. Arrives Saturday March 28.",
        "created_at": now,
        "updated_at": now,
    },
    {
        "id": str(uuid4()),
        "structure_id": "zen-casa",
        "source": "direct",
        "external_id": None,
        "guest_name": "Artur",
        "guest_email": "guest-artur@zenvillagecr.com",
        "guest_phone": "",
        "guest_country": "Unknown",
        "check_in": "2026-04-01",
        "check_out": "2026-04-04",
        "nights": 3,
        "nightly_rate": 130.0,
        "cleaning_fee": 0,
        "discount_percent": 0,
        "total_amount": 390.0,
        "payment_status": "pending",
        "status": "confirmed",
        "special_requests": "",
        "arrival_time": None,
        "partner_code": None,
        "partner_commission": 0,
        "notes": "Full Zen Casa rental, 3 nights at $130/night.",
        "created_at": now,
        "updated_at": now,
    },
    {
        "id": str(uuid4()),
        "structure_id": "zen-casa",
        "source": "direct",
        "external_id": None,
        "guest_name": "Lloyd (Group Event - 30 people)",
        "guest_email": "guest-lloyd@zenvillagecr.com",
        "guest_phone": "",
        "guest_country": "Unknown",
        "check_in": "2026-04-28",
        "check_out": "2026-04-29",
        "nights": 1,
        "nightly_rate": 500.0,
        "cleaning_fee": 0,
        "discount_percent": 0,
        "total_amount": 500.0,
        "payment_status": "partial",
        "status": "confirmed",
        "special_requests": "Day event 12-5pm. 30 people. Main house + kitchen area.",
        "arrival_time": "12:00",
        "partner_code": None,
        "partner_commission": 0,
        "notes": "Day event, not overnight. 30 people, 12-5pm. Main house/kitchen. $500 total, $250 deposit already paid.",
        "created_at": now,
        "updated_at": now,
    },
]

cols = [
    "id", "structure_id", "source", "external_id", "guest_name", "guest_email",
    "guest_phone", "guest_country", "check_in", "check_out", "nights",
    "nightly_rate", "cleaning_fee", "discount_percent", "total_amount",
    "payment_status", "status", "special_requests", "arrival_time",
    "partner_code", "partner_commission", "notes", "created_at", "updated_at"
]
placeholders = ", ".join(["?"] * len(cols))
col_names = ", ".join(cols)

for b in bookings:
    values = [b[c] for c in cols]
    cur.execute(f"INSERT INTO bookings ({col_names}) VALUES ({placeholders})", values)
    print(f"  Created: {b['guest_name']} — {b['structure_id']} — {b['check_in']} to {b['check_out']} — ${b['total_amount']}")

conn.commit()
conn.close()
print(f"\nDone! {len(bookings)} bookings seeded.")
