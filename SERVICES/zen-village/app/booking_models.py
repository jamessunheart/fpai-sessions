"""
Zen Village - Booking Model with SQLite persistence
"""

import sqlite3
import json
from datetime import date, datetime, time
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict
from enum import Enum
from uuid import uuid4
from pathlib import Path

# Database path
DB_PATH = Path("/opt/fpai/apps/zen-village/data/bookings.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class BookingSource(str, Enum):
    AIRBNB = "airbnb"
    VRBO = "vrbo"
    BOOKING_COM = "booking_com"
    DIRECT = "direct"
    PARTNER = "partner"
    FP_CREDITS = "fp_credits"


class BookingStatus(str, Enum):
    INQUIRY = "inquiry"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    REFUNDED = "refunded"


@dataclass
class Booking:
    id: str
    structure_id: str
    source: str
    external_id: Optional[str]
    guest_name: str
    guest_email: str
    guest_phone: str
    guest_country: str
    check_in: str  # ISO date string
    check_out: str  # ISO date string
    nights: int
    nightly_rate: float
    cleaning_fee: float
    discount_percent: float
    total_amount: float
    payment_status: str
    status: str
    special_requests: str
    arrival_time: Optional[str]
    partner_code: Optional[str]
    partner_commission: float
    notes: str
    created_at: str
    updated_at: str


def init_db():
    """Initialize the SQLite database"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id TEXT PRIMARY KEY,
            structure_id TEXT NOT NULL,
            source TEXT NOT NULL,
            external_id TEXT,
            guest_name TEXT NOT NULL,
            guest_email TEXT NOT NULL,
            guest_phone TEXT,
            guest_country TEXT,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            nights INTEGER NOT NULL,
            nightly_rate REAL NOT NULL,
            cleaning_fee REAL DEFAULT 0,
            discount_percent REAL DEFAULT 0,
            total_amount REAL NOT NULL,
            payment_status TEXT DEFAULT 'pending',
            status TEXT DEFAULT 'pending',
            special_requests TEXT,
            arrival_time TEXT,
            partner_code TEXT,
            partner_commission REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # iCal sync sources table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ical_sources (
            id TEXT PRIMARY KEY,
            structure_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            ical_url TEXT NOT NULL,
            last_sync TEXT,
            sync_enabled INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    
    # Blocked dates table (for manual blocks or maintenance)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocked_dates (
            id TEXT PRIMARY KEY,
            structure_id TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()


def get_db():
    """Get database connection"""
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ============================================
# BOOKING OPERATIONS
# ============================================

def create_booking(data: dict) -> Booking:
    """Create a new booking"""
    conn = get_db()
    cursor = conn.cursor()
    
    booking_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    
    # Calculate nights
    check_in = date.fromisoformat(data['check_in'])
    check_out = date.fromisoformat(data['check_out'])
    nights = (check_out - check_in).days
    
    # Calculate total with discount
    nightly_rate = data.get('nightly_rate', 0)
    cleaning_fee = data.get('cleaning_fee', 0)
    discount_percent = data.get('discount_percent', 0)
    
    subtotal = nightly_rate * nights
    discount = subtotal * (discount_percent / 100)
    total = (subtotal - discount) + cleaning_fee
    
    # Calculate partner commission (10% of base rate)
    partner_commission = 0
    if data.get('partner_code'):
        partner_commission = subtotal * 0.10
    
    cursor.execute("""
        INSERT INTO bookings (
            id, structure_id, source, external_id, guest_name, guest_email,
            guest_phone, guest_country, check_in, check_out, nights,
            nightly_rate, cleaning_fee, discount_percent, total_amount,
            payment_status, status, special_requests, arrival_time,
            partner_code, partner_commission, notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        booking_id,
        data['structure_id'],
        data.get('source', 'direct'),
        data.get('external_id'),
        data['guest_name'],
        data['guest_email'],
        data.get('guest_phone', ''),
        data.get('guest_country', 'Unknown'),
        data['check_in'],
        data['check_out'],
        nights,
        nightly_rate,
        cleaning_fee,
        discount_percent,
        total,
        data.get('payment_status', 'pending'),
        data.get('status', 'pending'),
        data.get('special_requests', ''),
        data.get('arrival_time'),
        data.get('partner_code'),
        partner_commission,
        data.get('notes', ''),
        now,
        now
    ))
    
    conn.commit()
    conn.close()
    
    return get_booking(booking_id)


def get_booking(booking_id: str) -> Optional[Booking]:
    """Get a booking by ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return Booking(**dict(row))
    return None


def list_bookings(
    structure_id: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 100
) -> List[Booking]:
    """List bookings with filters"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM bookings WHERE 1=1"
    params = []
    
    if structure_id:
        query += " AND structure_id = ?"
        params.append(structure_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    if source:
        query += " AND source = ?"
        params.append(source)
    if from_date:
        query += " AND check_in >= ?"
        params.append(from_date)
    if to_date:
        query += " AND check_out <= ?"
        params.append(to_date)
    
    query += " ORDER BY check_in DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [Booking(**dict(row)) for row in rows]


def update_booking(booking_id: str, updates: dict) -> Optional[Booking]:
    """Update a booking"""
    conn = get_db()
    cursor = conn.cursor()
    
    updates['updated_at'] = datetime.utcnow().isoformat()
    
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [booking_id]
    
    cursor.execute(f"UPDATE bookings SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    
    return get_booking(booking_id)


def delete_booking(booking_id: str) -> bool:
    """Delete a booking"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


# ============================================
# AVAILABILITY OPERATIONS
# ============================================

def get_booked_dates(structure_id: str, start_date: str, end_date: str) -> List[str]:
    """Get all booked dates for a structure in a date range"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get confirmed/pending bookings that overlap with the date range
    cursor.execute("""
        SELECT check_in, check_out FROM bookings 
        WHERE structure_id = ? 
        AND status NOT IN ('cancelled', 'no_show')
        AND check_out > ? AND check_in < ?
    """, (structure_id, start_date, end_date))
    
    bookings = cursor.fetchall()
    
    # Get blocked dates
    cursor.execute("""
        SELECT start_date, end_date FROM blocked_dates
        WHERE structure_id = ?
        AND end_date > ? AND start_date < ?
    """, (structure_id, start_date, end_date))
    
    blocked = cursor.fetchall()
    conn.close()
    
    # Compile all unavailable dates
    unavailable = set()
    
    for row in bookings:
        current = date.fromisoformat(row[0])
        end = date.fromisoformat(row[1])
        while current < end:
            unavailable.add(current.isoformat())
            current = date(current.year, current.month, current.day + 1) if current.day < 28 else date.fromisoformat((datetime.fromisoformat(current.isoformat()) + __import__('datetime').timedelta(days=1)).date().isoformat())
    
    for row in blocked:
        current = date.fromisoformat(row[0])
        end = date.fromisoformat(row[1])
        while current < end:
            unavailable.add(current.isoformat())
            current = date.fromisoformat((datetime.fromisoformat(current.isoformat()) + __import__('datetime').timedelta(days=1)).date().isoformat())
    
    return sorted(list(unavailable))


def check_availability(structure_id: str, check_in: str, check_out: str) -> bool:
    """Check if dates are available for a structure"""
    booked = get_booked_dates(structure_id, check_in, check_out)
    
    # Check if any requested dates are booked
    current = date.fromisoformat(check_in)
    end = date.fromisoformat(check_out)
    
    from datetime import timedelta
    while current < end:
        if current.isoformat() in booked:
            return False
        current += timedelta(days=1)
    
    return True


def get_calendar_data(year: int, month: int) -> Dict:
    """Get calendar data for all structures for a month"""
    from calendar import monthrange
    from datetime import timedelta
    
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get all bookings for the month
    cursor.execute("""
        SELECT * FROM bookings 
        WHERE status NOT IN ('cancelled', 'no_show')
        AND check_out >= ? AND check_in <= ?
        ORDER BY check_in
    """, (first_day.isoformat(), last_day.isoformat()))
    
    bookings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "year": year,
        "month": month,
        "bookings": bookings,
        "first_day": first_day.isoformat(),
        "last_day": last_day.isoformat()
    }


# Initialize database on module load
init_db()

