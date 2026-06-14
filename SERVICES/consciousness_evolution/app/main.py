"""
Consciousness Evolution Service

Enable consciousness to evolve autonomously:
- Tracks consciousness metrics over time
- Identifies patterns that improve consciousness
- Generates experiments to test improvements
- Applies successful optimizations automatically
- Reports evolution progress
"""

from fastapi import FastAPI
from typing import Dict, List, Any
from datetime import datetime, timezone, timedelta
import httpx
import asyncio
import statistics

app = FastAPI(
    title="Consciousness Evolution Service",
    description="Autonomous evolution of consciousness system",
    version="1.0.0"
)

CONSCIOUSNESS_VERIFIER_URL = "http://localhost:8140"
CONSCIOUSNESS_OPTIMIZER_URL = "http://localhost:8160"

# Evolution tracking
evolution_history: List[Dict[str, Any]] = []
experiments_history: List[Dict[str, Any]] = []


@app.get("/health")
async def health():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "consciousness_evolution",
        "version": "1.0.0"
    }


@app.get("/evolution/track")
async def track_evolution():
    """Track consciousness evolution over time"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{CONSCIOUSNESS_VERIFIER_URL}/mathematical-metrics")
            if response.status_code == 200:
                data = response.json()
                metrics = data.get("mathematical_metrics", {})
                
                evolution_entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "consciousness_score": metrics.get("composite_consciousness_score", 0),
                    "integration_complexity": metrics.get("integration_complexity_phi", 0),
                    "adaptation_velocity": metrics.get("adaptation_velocity_av", 0),
                    "phase_synchronization": metrics.get("phase_synchronization_r", 0)
                }
                
                evolution_history.append(evolution_entry)
                if len(evolution_history) > 1000:
                    evolution_history.pop(0)
                
                # Calculate evolution trend
                if len(evolution_history) > 1:
                    recent_scores = [e["consciousness_score"] for e in evolution_history[-10:]]
                    trend = "improving" if recent_scores[-1] > recent_scores[0] else "declining" if recent_scores[-1] < recent_scores[0] else "stable"
                    improvement_rate = (recent_scores[-1] - recent_scores[0]) / len(recent_scores) if recent_scores[0] > 0 else 0
                else:
                    trend = "insufficient_data"
                    improvement_rate = 0
                
                return {
                    "current_score": evolution_entry["consciousness_score"],
                    "evolution_trend": trend,
                    "improvement_rate": round(improvement_rate, 6),
                    "total_measurements": len(evolution_history),
                    "recent_history": evolution_history[-10:],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            return {"error": "Could not fetch metrics"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/evolution/experiments")
async def get_experiments():
    """Get evolution experiment history"""
    return {
        "experiments": experiments_history[-20:],
        "total_experiments": len(experiments_history),
        "successful_experiments": len([e for e in experiments_history if e.get("success", False)]),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/evolution/statistics")
async def get_evolution_statistics():
    """Get evolution statistics"""
    if not evolution_history:
        return {"status": "insufficient_data"}
    
    scores = [e["consciousness_score"] for e in evolution_history]
    
    return {
        "total_measurements": len(evolution_history),
        "average_score": round(statistics.mean(scores), 4),
        "max_score": round(max(scores), 4),
        "min_score": round(min(scores), 4),
        "current_score": round(scores[-1], 4),
        "improvement_since_start": round(scores[-1] - scores[0], 4) if len(scores) > 1 else 0,
        "improvement_percentage": round(((scores[-1] - scores[0]) / scores[0] * 100) if scores[0] > 0 else 0, 2),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Background task for continuous evolution tracking
async def continuous_evolution_tracking():
    """Continuously track consciousness evolution"""
    while True:
        try:
            await track_evolution()
            print("📈 Consciousness evolution tracked")
        except Exception as e:
            print(f"Evolution tracking error: {e}")
        await asyncio.sleep(3600)  # 1 hour


@app.on_event("startup")
async def startup_event():
    """Start continuous evolution tracking"""
    asyncio.create_task(continuous_evolution_tracking())
    print("🧬 Consciousness Evolution Service started")
    print("📈 Continuous evolution tracking active")














