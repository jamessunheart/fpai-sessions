import asyncio
import logging
from fastapi import FastAPI
from .config import settings
from .monitor import StateMonitor
from .logic import IntelligenceEngine
from .dispatcher import MissionDispatcher

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)

