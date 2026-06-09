import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .models import Config, DayRecord, FinancialSnapshot, Ticket

DATA_DIR = Path(__file__).parent.parent / "data"
DAYS_DIR = DATA_DIR / "days"


def _ensure_dirs():
    DAYS_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def _write_json(path: Path, data):
    _ensure_dirs()
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def get_day(dt: Optional[str] = None) -> DayRecord:
    _ensure_dirs()
    dt = dt or date.today().isoformat()
    path = DAYS_DIR / f"{dt}.json"
    raw = _read_json(path)
    if raw:
        return DayRecord(**raw)
    return DayRecord(date=dt)


def save_day(record: DayRecord):
    path = DAYS_DIR / f"{record.date}.json"
    _write_json(path, record.model_dump())


def list_days(limit: int = 30) -> list[DayRecord]:
    _ensure_dirs()
    files = sorted(DAYS_DIR.glob("*.json"), reverse=True)[:limit]
    days = []
    for f in files:
        raw = _read_json(f)
        if raw:
            days.append(DayRecord(**raw))
    return days


def get_tickets() -> list[Ticket]:
    path = DATA_DIR / "tickets.json"
    raw = _read_json(path, [])
    return [Ticket(**t) for t in raw]


def save_tickets(tickets: list[Ticket]):
    path = DATA_DIR / "tickets.json"
    _write_json(path, [t.model_dump() for t in tickets])


def add_ticket(ticket: Ticket) -> Ticket:
    tickets = get_tickets()
    tickets.append(ticket)
    save_tickets(tickets)
    return ticket


def update_ticket(ticket_id: str, updates: dict) -> Optional[Ticket]:
    tickets = get_tickets()
    for i, t in enumerate(tickets):
        if t.id == ticket_id:
            data = t.model_dump()
            data.update(updates)
            if updates.get("status") == "done" and not data.get("completed_at"):
                data["completed_at"] = datetime.now().isoformat()
            tickets[i] = Ticket(**data)
            save_tickets(tickets)
            return tickets[i]
    return None


def get_finances() -> FinancialSnapshot:
    path = DATA_DIR / "finances.json"
    raw = _read_json(path)
    if raw:
        return FinancialSnapshot(**raw)
    return FinancialSnapshot()


def save_finances(snapshot: FinancialSnapshot):
    path = DATA_DIR / "finances.json"
    _write_json(path, snapshot.model_dump())


def get_config() -> Config:
    path = DATA_DIR / "config.json"
    raw = _read_json(path)
    if raw:
        return Config(**raw)
    return Config()


def save_config(config: Config):
    path = DATA_DIR / "config.json"
    _write_json(path, config.model_dump())


def get_streaks() -> dict:
    days = list_days(30)
    ritual_streak = 0
    content_streak = 0
    for d in days:
        if d.morning and d.sunset and d.day_complete:
            ritual_streak += 1
        else:
            break
    for d in days:
        if d.sunset and d.sunset.content:
            c = d.sunset.content
            if c.clarity_transmission and c.proof_post and c.invitation:
                content_streak += 1
            else:
                break
        else:
            break
    shipped_this_week = sum(d.tickets_shipped for d in days[:7])
    golden_hours_this_week = sum(
        1 for d in days[:7] if d.sunset and d.sunset.golden_hour_logged
    )
    return {
        "ritual_streak": ritual_streak,
        "content_streak": content_streak,
        "tickets_shipped_7d": shipped_this_week,
        "golden_hours_7d": golden_hours_this_week,
        "days_tracked": len(days),
    }
