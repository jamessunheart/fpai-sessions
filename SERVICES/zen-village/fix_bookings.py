#!/usr/bin/env python3
"""Fix Paul and Elizabeth booking details."""
import sys, sqlite3
from datetime import datetime

DB = "/opt/fpai/apps/zen-village/data/bookings.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()
now = datetime.utcnow().isoformat()

# ── Paul: $100/night (not $130), paid through Mar 26 ──
paul_id = "dc043ddc-cc60-4473-805b-a77bc6c19cda"
# 4 nights (Mar 26-30) × $100 = $400
cur.execute("""
    UPDATE bookings SET
        nightly_rate = 100.0,
        total_amount = 400.0,
        payment_status = 'partial',
        notes = 'Nightly guest at $100/night. Paid through March 26. Remaining nights still owed. May extend past Monday.',
        updated_at = ?
    WHERE id = ?
""", (now, paul_id))
print(f"Paul: updated to $100/night, total $400, payment partial (paid through Mar 26)")

# ── Elizabeth: already paid for current stay, extending to April 2, $300 for 10 more nights ──
elizabeth_id = "0c699c6b-383e-4280-bad0-3ec7f01b99f1"
# Update checkout to April 2. Recalculate:
# She said 10 more nights at $30 = $300, getting to April 2.
# That means she effectively checks in Mar 23 (10 nights before Apr 2).
# She's already paid for the initial stay. The $300 covers the 10 nights to Apr 2.
cur.execute("""
    UPDATE bookings SET
        check_in = '2026-03-23',
        check_out = '2026-04-02',
        nights = 10,
        total_amount = 300.0,
        payment_status = 'paid',
        notes = 'One room of Zen Casa at $30/night. Already paid in full. 10 nights to April 2.',
        updated_at = ?
    WHERE id = ?
""", (now, elizabeth_id))
print(f"Elizabeth: updated check-in Mar 23, checkout Apr 2, 10 nights, $300, paid in full")

conn.commit()
conn.close()
print("\nDone!")
