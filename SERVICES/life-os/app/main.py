from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import storage
from .models import (
    Config,
    DayRecord,
    FinancialSnapshot,
    MorningRitual,
    SunsetClose,
    Ticket,
)

app = FastAPI(title="Life OS", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/health")
def health():
    streaks = storage.get_streaks()
    return {"status": "alive", "service": "life-os", "streaks": streaks}


@app.get("/")
def serve_dashboard():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Daily Command Center ---


@app.get("/api/today")
def get_today():
    day = storage.get_day()
    streaks = storage.get_streaks()
    config = storage.get_config()
    return {
        "day": day.model_dump(),
        "streaks": streaks,
        "config": config.model_dump(),
    }


@app.post("/api/morning")
def submit_morning(ritual: MorningRitual):
    today = date.today().isoformat()
    day = storage.get_day(today)
    ritual.completed_at = datetime.now().isoformat()
    day.morning = ritual
    storage.save_day(day)
    return {"ok": True, "day": day.model_dump()}


@app.post("/api/sunset")
def submit_sunset(close: SunsetClose):
    today = date.today().isoformat()
    day = storage.get_day(today)
    close.completed_at = datetime.now().isoformat()
    day.sunset = close
    day.day_complete = True
    tickets = storage.get_tickets()
    day.tickets_shipped = sum(
        1 for t in tickets
        if t.completed_at and t.completed_at.startswith(today)
    )
    storage.save_day(day)
    return {"ok": True, "day": day.model_dump()}


@app.get("/api/days/{dt}")
def get_day(dt: str):
    return storage.get_day(dt).model_dump()


@app.get("/api/days")
def list_days(limit: int = 30):
    return [d.model_dump() for d in storage.list_days(limit)]


# --- Tickets (O System) ---


@app.get("/api/tickets")
def get_tickets():
    return [t.model_dump() for t in storage.get_tickets()]


@app.post("/api/tickets")
def create_ticket(ticket: Ticket):
    return storage.add_ticket(ticket).model_dump()


@app.patch("/api/tickets/{ticket_id}")
def update_ticket(ticket_id: str, updates: dict):
    result = storage.update_ticket(ticket_id, updates)
    if not result:
        raise HTTPException(404, "Ticket not found")
    return result.model_dump()


# --- Financial Cockpit ---


@app.get("/api/finances")
def get_finances():
    return storage.get_finances().model_dump()


@app.post("/api/finances")
def update_finances(snapshot: FinancialSnapshot):
    storage.save_finances(snapshot)
    return {"ok": True, "finances": snapshot.model_dump()}


# --- Config ---


@app.get("/api/config")
def get_config():
    return storage.get_config().model_dump()


@app.post("/api/config")
def update_config(config: Config):
    storage.save_config(config)
    return {"ok": True, "config": config.model_dump()}


# --- Streaks ---


@app.get("/api/streaks")
def get_streaks():
    return storage.get_streaks()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8190)
