import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query
from .config import settings
from .monitor import StateMonitor
from .logic import IntelligenceEngine
from .dispatcher import MissionDispatcher
from .signals import signal_store

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StrategicIntelligence")

# Components
monitor = StateMonitor()
brain = IntelligenceEngine()
dispatcher = MissionDispatcher()

app = FastAPI(
    title="Strategic Intelligence Service",
    description="The Brain of the Assembly Line",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    logger.info("🧠 Strategic Brain Online")
    asyncio.create_task(run_intelligence_loop())

async def run_intelligence_loop():
    """Continuous cycle of observation and decision."""
    while True:
        try:
            # 1. Observe
            world = await monitor.update()
            
            # 2. Decide
            priorities = brain.analyze(world)
            
            # 3. Act
            await dispatcher.dispatch(priorities)
            
        except Exception as e:
            logger.error(f"Error in loop: {e}")
            
        await asyncio.sleep(settings.monitor_interval_seconds)

@app.get("/health")
async def health():
    return {"status": "active", "brain": "functioning"}


# -----------------------------------------------------------------------------
# Signal ingestion (Data Service / Nerve Center → Strategic Intelligence)
# -----------------------------------------------------------------------------


@app.post("/api/v1/signals")
async def ingest_signals(payload: Dict[str, Any] = Body(...)):
    """
    Accept external signals and persist them for the intelligence loop.

    Supported payload formats:
    - {"source": "...", "signal": {...}}
    - {"source": "...", "signals": [{...}, {...}]}
    - (optionally) include {"digest": {...}} metadata
    """
    source = str(payload.get("source") or "unknown")
    signals: Optional[List[Dict[str, Any]]] = None

    if isinstance(payload.get("signal"), dict):
        signals = [payload["signal"]]
    elif isinstance(payload.get("signals"), list):
        signals = [s for s in payload["signals"] if isinstance(s, dict)]

    if not signals:
        raise HTTPException(status_code=400, detail="Payload must include 'signal' (object) or 'signals' (list)")

    result = signal_store.add_many(source=source, signals=signals, kind="signal")
    return {"status": "ok", "result": result}


@app.get("/api/v1/signals/recent")
async def recent_signals(limit: int = Query(default=50, ge=1, le=500), kind: Optional[str] = Query(default=None)):
    return {"status": "ok", "signals": signal_store.recent(limit=limit, kind=kind), "stats": signal_store.stats()}


@app.post("/api/v1/patterns")
async def ingest_patterns(payload: Dict[str, Any] = Body(...)):
    """
    Accept a detected pattern payload.
    Common format: {"source": "...", "pattern": {...}}
    """
    source = str(payload.get("source") or "unknown")
    pattern = payload.get("pattern")
    if not isinstance(pattern, dict):
        raise HTTPException(status_code=400, detail="Payload must include 'pattern' (object)")
    result = signal_store.add_many(source=source, signals=[pattern], kind="pattern")
    return {"status": "ok", "result": result}


@app.post("/api/v1/synthesis")
async def ingest_synthesis(payload: Dict[str, Any] = Body(...)):
    """
    Accept a synthesis payload.
    Common format: {"source": "...", "synthesis": {...}}
    """
    source = str(payload.get("source") or "unknown")
    synthesis = payload.get("synthesis")
    if not isinstance(synthesis, dict):
        raise HTTPException(status_code=400, detail="Payload must include 'synthesis' (object)")
    result = signal_store.add_many(source=source, signals=[synthesis], kind="synthesis")
    return {"status": "ok", "result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)

