"""
Zen Village - iCal Sync Module
Imports from Airbnb/VRBO/Booking.com and exports for reverse sync
"""

import httpx
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from icalendar import Calendar, Event
from uuid import uuid4
import sqlite3
from pathlib import Path

DB_PATH = Path("/opt/fpai/apps/zen-village/data/bookings.db")


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ============================================
# iCAL SOURCE MANAGEMENT
# ============================================

def add_ical_source(structure_id: str, platform: str, ical_url: str) -> dict:
    """Add a new iCal source for a structure"""
    conn = get_db()
    cursor = conn.cursor()
    
    source_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    
    cursor.execute("""
        INSERT INTO ical_sources (id, structure_id, platform, ical_url, sync_enabled, created_at)
        VALUES (?, ?, ?, ?, 1, ?)
    """, (source_id, structure_id, platform, ical_url, now))
    
    conn.commit()
    conn.close()
    
    return {
        "id": source_id,
        "structure_id": structure_id,
        "platform": platform,
        "ical_url": ical_url,
        "message": "iCal source added successfully"
    }


def list_ical_sources(structure_id: Optional[str] = None) -> List[dict]:
    """List all iCal sources"""
    conn = get_db()
    cursor = conn.cursor()
    
    if structure_id:
        cursor.execute("SELECT * FROM ical_sources WHERE structure_id = ?", (structure_id,))
    else:
        cursor.execute("SELECT * FROM ical_sources")
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def delete_ical_source(source_id: str) -> bool:
    """Delete an iCal source"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ical_sources WHERE id = ?", (source_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


# ============================================
# iCAL IMPORT (from Airbnb, etc.)
# ============================================

async def fetch_ical(url: str) -> Optional[str]:
    """Fetch iCal data from a URL"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30, follow_redirects=True)
            if response.status_code == 200:
                return response.text
    except Exception as e:
        print(f"Error fetching iCal from {url}: {e}")
    return None


def parse_ical(ical_data: str, structure_id: str, platform: str) -> List[dict]:
    """Parse iCal data and extract events/bookings"""
    events = []
    
    try:
        cal = Calendar.from_ical(ical_data)
        
        for component in cal.walk():
            if component.name == "VEVENT":
                dtstart = component.get('dtstart')
                dtend = component.get('dtend')
                summary = str(component.get('summary', 'Reserved'))
                uid = str(component.get('uid', str(uuid4())))
                
                if dtstart and dtend:
                    # Convert to date objects
                    start = dtstart.dt
                    end = dtend.dt
                    
                    # Handle datetime vs date
                    if isinstance(start, datetime):
                        start = start.date()
                    if isinstance(end, datetime):
                        end = end.date()
                    
                    # Parse guest name from summary (Airbnb format: "Guest Name - Reserved")
                    guest_name = summary.replace(" - Reserved", "").replace("Reserved", "Guest").strip()
                    if not guest_name:
                        guest_name = "External Booking"
                    
                    events.append({
                        "external_id": uid,
                        "structure_id": structure_id,
                        "source": platform,
                        "check_in": start.isoformat(),
                        "check_out": end.isoformat(),
                        "guest_name": guest_name,
                        "status": "confirmed"
                    })
    except Exception as e:
        print(f"Error parsing iCal data: {e}")
    
    return events


async def sync_ical_source(source_id: str) -> dict:
    """Sync a single iCal source"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM ical_sources WHERE id = ?", (source_id,))
    source = cursor.fetchone()
    conn.close()
    
    if not source:
        return {"error": "Source not found"}
    
    source = dict(source)
    ical_data = await fetch_ical(source['ical_url'])
    
    if not ical_data:
        return {"error": "Failed to fetch iCal data"}
    
    events = parse_ical(ical_data, source['structure_id'], source['platform'])
    
    # Import events as bookings
    imported = 0
    skipped = 0
    
    conn = get_db()
    cursor = conn.cursor()
    
    for event in events:
        # Check if booking already exists (by external_id)
        cursor.execute(
            "SELECT id FROM bookings WHERE external_id = ? AND source = ?",
            (event['external_id'], event['source'])
        )
        existing = cursor.fetchone()
        
        if existing:
            skipped += 1
            continue
        
        # Create new booking
        booking_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        
        # Calculate nights
        check_in = date.fromisoformat(event['check_in'])
        check_out = date.fromisoformat(event['check_out'])
        nights = (check_out - check_in).days
        
        cursor.execute("""
            INSERT INTO bookings (
                id, structure_id, source, external_id, guest_name, guest_email,
                guest_phone, guest_country, check_in, check_out, nights,
                nightly_rate, cleaning_fee, discount_percent, total_amount,
                payment_status, status, special_requests, notes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            booking_id,
            event['structure_id'],
            event['source'],
            event['external_id'],
            event['guest_name'],
            f"imported-{event['source']}@zenvillage.local",  # Placeholder email
            '',
            'Unknown',
            event['check_in'],
            event['check_out'],
            nights,
            0,  # Rate unknown for external
            0,
            0,
            0,  # Total unknown for external
            'paid',  # Assume paid through platform
            event['status'],
            '',
            f"Imported from {event['source']}",
            now,
            now
        ))
        
        imported += 1
    
    # Update last sync time
    cursor.execute(
        "UPDATE ical_sources SET last_sync = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), source_id)
    )
    
    conn.commit()
    conn.close()
    
    return {
        "source_id": source_id,
        "platform": source['platform'],
        "structure_id": source['structure_id'],
        "events_found": len(events),
        "imported": imported,
        "skipped": skipped,
        "last_sync": datetime.utcnow().isoformat()
    }


async def sync_all_ical() -> dict:
    """Sync all iCal sources"""
    sources = list_ical_sources()
    results = []
    
    for source in sources:
        if source.get('sync_enabled'):
            result = await sync_ical_source(source['id'])
            results.append(result)
    
    return {
        "synced": len(results),
        "results": results,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# iCAL EXPORT (for others to import)
# ============================================

def generate_ical_export(structure_id: Optional[str] = None) -> str:
    """Generate iCal export of all bookings for external platforms to import"""
    cal = Calendar()
    cal.add('prodid', '-//Zen Village CR//Booking Calendar//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-calname', 'Zen Village Bookings')
    
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT * FROM bookings 
        WHERE status NOT IN ('cancelled', 'no_show')
    """
    params = []
    
    if structure_id:
        query += " AND structure_id = ?"
        params.append(structure_id)
    
    # Only export future bookings and recent past (30 days)
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    query += " AND check_out >= ?"
    params.append(cutoff)
    
    cursor.execute(query, params)
    bookings = cursor.fetchall()
    conn.close()
    
    for booking in bookings:
        booking = dict(booking)
        event = Event()
        
        # Use booking ID as UID
        event.add('uid', f"{booking['id']}@zenvillagecr.com")
        event.add('dtstart', date.fromisoformat(booking['check_in']))
        event.add('dtend', date.fromisoformat(booking['check_out']))
        
        # Summary format: "Guest Name - Reserved" (Airbnb style)
        summary = f"{booking['guest_name']} - Reserved"
        if booking['source'] != 'direct':
            summary = f"{booking['guest_name']} ({booking['source'].upper()})"
        
        event.add('summary', summary)
        event.add('description', f"Booking via {booking['source']}")
        event.add('status', 'CONFIRMED')
        event.add('transp', 'OPAQUE')  # Blocks time
        
        if booking.get('created_at'):
            event.add('dtstamp', datetime.fromisoformat(booking['created_at']))
        else:
            event.add('dtstamp', datetime.utcnow())
        
        cal.add_component(event)
    
    # Also add blocked dates
    cursor = get_db().cursor()
    query = "SELECT * FROM blocked_dates WHERE end_date >= ?"
    params = [(date.today() - timedelta(days=30)).isoformat()]
    
    if structure_id:
        query += " AND structure_id = ?"
        params.append(structure_id)
    
    cursor.execute(query, params)
    blocked = cursor.fetchall()
    
    for block in blocked:
        block = dict(block)
        event = Event()
        event.add('uid', f"block-{block['id']}@zenvillagecr.com")
        event.add('dtstart', date.fromisoformat(block['start_date']))
        event.add('dtend', date.fromisoformat(block['end_date']))
        event.add('summary', f"Blocked - {block.get('reason', 'Maintenance')}")
        event.add('status', 'CONFIRMED')
        event.add('transp', 'OPAQUE')
        event.add('dtstamp', datetime.utcnow())
        cal.add_component(event)
    
    return cal.to_ical().decode('utf-8')


def add_blocked_dates(structure_id: str, start_date: str, end_date: str, reason: str = "") -> dict:
    """Add blocked dates for a structure"""
    conn = get_db()
    cursor = conn.cursor()
    
    block_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    
    cursor.execute("""
        INSERT INTO blocked_dates (id, structure_id, start_date, end_date, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (block_id, structure_id, start_date, end_date, reason, now))
    
    conn.commit()
    conn.close()
    
    return {
        "id": block_id,
        "structure_id": structure_id,
        "start_date": start_date,
        "end_date": end_date,
        "reason": reason,
        "message": "Dates blocked successfully"
    }


def remove_blocked_dates(block_id: str) -> bool:
    """Remove blocked dates"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blocked_dates WHERE id = ?", (block_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

