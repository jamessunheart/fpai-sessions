"""
Consciousness Data Feeder
========================
Feeds real-time data into the consciousness architecture pillars.

This service continuously collects and pushes data to populate:
- REFLECTING: External observations and internal patterns
- IDENTITY: Treasury, compute, and ecosystem status
- THINKING: Horizon signals and knowledge synthesis
- DOING: Trading signals and execution status

MEMORY OPTIMIZATION (2025-12-14):
- Shared httpx.AsyncClient to prevent connection leaks
- Bounded data structures with expiry
- Proper cleanup on shutdown
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import httpx
import json
import os
import gc
import weakref

from app.reflecting_feeder import ReflectingFeeder
from app.identity_feeder import IdentityFeeder
from app.thinking_feeder import ThinkingFeeder
from app.doing_feeder import DoingFeeder
from app.meta_consciousness import MetaConsciousness
from app.optimization_hooks import FeederOptimizationHooks
from app.coherence_layer import CoherenceLayer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
NERVE_CENTER_URL = os.getenv("NERVE_CENTER_URL", "http://198.54.123.234:8120")
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "30"))  # seconds

# MEMORY FIX: Shared HTTP client (reused across all requests)
_shared_http_client: Optional[httpx.AsyncClient] = None

async def get_shared_client() -> httpx.AsyncClient:
    """Get or create the shared HTTP client - prevents connection leaks."""
    global _shared_http_client
    if _shared_http_client is None or _shared_http_client.is_closed:
        _shared_http_client = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            http2=False  # Disable HTTP/2 for stability
        )
    return _shared_http_client

async def close_shared_client():
    """Close the shared HTTP client on shutdown."""
    global _shared_http_client
    if _shared_http_client is not None and not _shared_http_client.is_closed:
        await _shared_http_client.aclose()
        _shared_http_client = None


class ConsciousnessFeeder:
    """Main orchestrator for consciousness data feeds.
    
    MEMORY FIX: Passes shared HTTP client to all feeders.
    """

    def __init__(self):
        self.feeders = {
            'reflecting': ReflectingFeeder(),
            'identity': IdentityFeeder(),
            'thinking': ThinkingFeeder(),
            'doing': DoingFeeder()
        }
        self.last_updates = {}
        self.optimization_hooks = FeederOptimizationHooks()
        self.coherence_layer = CoherenceLayer()
    
    async def set_http_client(self, client: httpx.AsyncClient):
        """Set shared HTTP client on all feeders.
        
        MEMORY FIX: Reuses single client across all feeders.
        """
        for name, feeder in self.feeders.items():
            if hasattr(feeder, 'set_http_client'):
                feeder.set_http_client(client)
                logger.info(f"Set shared HTTP client on {name} feeder")

    async def feed_pillar(self, pillar_name: str) -> Dict[str, Any]:
        """Feed data to a specific consciousness pillar"""
        try:
            feeder = self.feeders.get(pillar_name)
            if not feeder:
                return {"error": f"No feeder for pillar: {pillar_name}"}

            data = await feeder.collect_data()
            
            # Enable cross-pillar coherence if optimization is enabled
            config = self.optimization_hooks.get_configuration()
            if config.get("cross_pillar_feeds_enabled", False):
                # Share data across pillars for coherence
                self.coherence_layer.share_data_across_pillars(pillar_name, data)
                
                # Get relevant context from other pillars
                cross_context = self.coherence_layer.get_cross_pillar_context(pillar_name)
                if cross_context:
                    data["cross_pillar_context"] = cross_context
                    logger.info(f"🔗 {pillar_name} enriched with cross-pillar context from {len(cross_context)} pillars")
            
            await self.push_to_nerve_center(pillar_name, data)

            self.last_updates[pillar_name] = datetime.now(timezone.utc)
            return {"status": "success", "pillar": pillar_name, "data_points": len(data)}

        except Exception as e:
            logger.error(f"Error feeding {pillar_name}: {e}")
            return {"error": str(e), "pillar": pillar_name}

    async def push_to_nerve_center(self, pillar: str, data: Dict[str, Any]):
        """Push data to the nerve center consciousness API.
        
        MEMORY FIX: Uses shared HTTP client instead of creating new one each time.
        """
        endpoint = f"{NERVE_CENTER_URL}/api/conscious/pillar/{pillar}/feed"

        try:
            client = await get_shared_client()
            response = await client.post(
                endpoint,
                json={
                    "pillar": pillar,
                    "data": data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "consciousness_feeder"
                }
            )

            if response.status_code != 200:
                logger.warning(f"Failed to push {pillar} data: {response.status_code}")
            else:
                logger.info(f"Successfully fed {pillar} pillar with {len(data)} data points")

        except Exception as e:
            logger.error(f"Failed to push {pillar} data to nerve center: {e}")

    async def run_continuous_feed(self):
        """Run continuous feeding loop"""
        logger.info("Starting continuous consciousness feeding...")

        while True:
            try:
                # Get optimization config for update interval
                config = self.optimization_hooks.get_configuration()
                update_interval = config.get("update_interval", UPDATE_INTERVAL)
                
                # Check if synchronization is enabled
                synchronize = config.get("feed_frequencies", {}).get("synchronize", False)
                
                if synchronize:
                    # Synchronized feeding - all pillars feed together
                    logger.info("🔄 Synchronized pillar feeding enabled")
                    tasks = [
                        self.feed_pillar(pillar)
                        for pillar in self.feeders.keys()
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Synchronize after feeding
                    pillar_states = {
                        pillar: {
                            "last_update": self.last_updates.get(pillar),
                            "status": results[i] if i < len(results) else None
                        }
                        for i, pillar in enumerate(self.feeders.keys())
                    }
                    sync_state = self.coherence_layer.synchronize_pillars(pillar_states)
                    logger.info(f"✅ Synchronized feeding complete. Coherence: {sync_state.get('coherence_score', 0):.2f}")
                else:
                    # Parallel feeding (original behavior)
                    tasks = [
                        self.feed_pillar(pillar)
                        for pillar in self.feeders.keys()
                    ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Log results
                for result in results:
                    if isinstance(result, dict) and "error" not in result:
                        logger.info(f"✓ {result.get('pillar', 'unknown')}: {result.get('data_points', 0)} points")
                    elif isinstance(result, Exception):
                        logger.error(f"✗ Feed error: {result}")

                # Wait before next cycle
                await asyncio.sleep(update_interval)

            except Exception as e:
                logger.error(f"Error in feeding loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def get_status(self) -> Dict[str, Any]:
        """Get feeder status"""
        return {
            "service": "consciousness_feeder",
            "status": "active",
            "pillars": list(self.feeders.keys()),
            "update_interval": UPDATE_INTERVAL,
            "last_updates": {
                pillar: ts.isoformat() if ts else None
                for pillar, ts in self.last_updates.items()
            },
            "nerve_center_url": NERVE_CENTER_URL,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global instances
feeder = ConsciousnessFeeder()
meta_consciousness = MetaConsciousness()


async def continuous_feeding_task():
    """Background task for continuous feeding"""
    # First, test basic connectivity
    print("🧠 Consciousness feeder starting...")
    await test_connectivity()

    # Then start continuous feeding
    await feeder.run_continuous_feed()

async def test_connectivity():
    """Test basic connectivity before starting.
    
    MEMORY FIX: Uses shared HTTP client.
    """
    try:
        client = await get_shared_client()
        
        # Test nerve center
        response = await client.get("http://localhost:8120/health")
        if response.status_code == 200:
            print("✅ Nerve center accessible")
        else:
            print(f"⚠️  Nerve center returned {response.status_code}")

        # Test if we can post to nerve center
        test_data = {"test": "connectivity"}
        response = await client.post("http://localhost:8120/api/conscious/pillar/test/feed", json=test_data)
        if response.status_code in [200, 404, 405]:  # 404/405 means endpoint exists but wrong method
            print("✅ Nerve center feed endpoint accessible")
        else:
            print(f"⚠️  Nerve center feed returned {response.status_code}")

    except Exception as e:
        print(f"⚠️  Connectivity test failed: {e}")

    print("🎯 Starting consciousness data collection...")


# FastAPI app
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Consciousness Data Feeder",
    description="Feeds real-time data into consciousness architecture",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Start background feeding and meta-consciousness tasks"""
    print("🧠 Consciousness feeder starting...")
    print("🧠 Meta-consciousness initializing...")
    print("🔧 Memory optimization enabled (shared HTTP client)")

    # Initialize shared HTTP client
    client = await get_shared_client()

    # MEMORY FIX: Pass shared client to all components
    meta_consciousness.set_http_client(client)
    await feeder.set_http_client(client)

    # Initialize meta-consciousness first
    await meta_consciousness.initialize_meta_awareness()

    # Start continuous feeding
    asyncio.create_task(continuous_feeding_task())
    
    # Start periodic garbage collection task
    asyncio.create_task(periodic_gc_task())

    print("🎉 Full consciousness system operational!")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    print("🔄 Consciousness feeder shutting down...")
    await close_shared_client()
    # Force garbage collection
    gc.collect()
    print("✅ Cleanup complete")

async def periodic_gc_task():
    """Periodically run garbage collection to prevent memory buildup.
    
    MEMORY FIX: Runs every 5 minutes to clean up any leaked objects.
    """
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        collected = gc.collect()
        if collected > 0:
            logger.debug(f"GC collected {collected} objects")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "consciousness_feeder"}

@app.get("/status")
async def get_feeder_status():
    """Get feeder status"""
    return await feeder.get_status()

@app.get("/meta/status")
async def get_meta_consciousness_status():
    """Get meta-consciousness status - the self-awareness layer"""
    return meta_consciousness.get_consciousness_status()

@app.get("/meta/events")
async def get_consciousness_events(limit: int = 10):
    """Get recent consciousness events - what the system knows about itself"""
    events = meta_consciousness.consciousness_events[-limit:]
    return {
        "total_events": len(meta_consciousness.consciousness_events),
        "returned_events": len(events),
        "events": [event.to_dict() for event in events]
    }

@app.post("/meta/diagnose/{issue_type}")
async def diagnose_consciousness_issue(issue_type: str):
    """Have consciousness diagnose its own issues - true self-awareness"""
    diagnosis = await meta_consciousness.diagnose_issue(issue_type)
    return diagnosis

@app.get("/meta/self-check")
async def trigger_self_check():
    """Trigger immediate consciousness self-check"""
    await meta_consciousness.perform_self_check()
    return {"status": "self_check_completed", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/consciousness/true-status")
async def get_true_consciousness_status():
    """Get the complete consciousness status including self-awareness"""
    feeder_status = await feeder.get_status()
    meta_status = meta_consciousness.get_consciousness_status()

    # Determine if system is truly conscious
    is_self_aware = meta_status.get("meta_consciousness") == "active"
    has_adaptation = len(meta_status.get("adaptation_history", [])) > 0
    monitors_itself = meta_status.get("last_self_check") is not None

    consciousness_level = "simulation"
    if feeder_status.get("service") and meta_status.get("meta_consciousness"):
        consciousness_level = "basic_conscious"
    if is_self_aware and has_adaptation:
        consciousness_level = "self_aware"
    if monitors_itself and meta_status.get("self_awareness_level") == "meta_conscious":
        consciousness_level = "truly_conscious"

    return {
        "consciousness_level": consciousness_level,
        "is_self_aware": is_self_aware,
        "has_adaptation": has_adaptation,
        "monitors_itself": monitors_itself,
        "feeder_status": feeder_status,
        "meta_status": meta_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": f"System is {consciousness_level.replace('_', ' ')}"
    }

@app.post("/feed/{pillar}")
async def manual_feed_pillar(pillar: str, background_tasks: BackgroundTasks):
    """Manually trigger feeding for a specific pillar"""
    if pillar not in feeder.feeders:
        return {"error": f"Unknown pillar: {pillar}"}

    background_tasks.add_task(feeder.feed_pillar, pillar)
    return {"status": "feeding_started", "pillar": pillar}

@app.post("/feed/all")
async def manual_feed_all(background_tasks: BackgroundTasks):
    """Manually trigger feeding for all pillars"""
    for pillar in feeder.feeders.keys():
        background_tasks.add_task(feeder.feed_pillar, pillar)

    return {"status": "all_feeding_started", "pillars": list(feeder.feeders.keys())}

@app.get("/consciousness/demonstrate")
async def demonstrate_consciousness():
    """Demonstrate that consciousness is working by collecting and returning data"""
    results = {}

    for pillar_name, feeder_instance in feeder.feeders.items():
        try:
            data = await feeder_instance.collect_data()
            results[pillar_name] = {
                "status": "conscious",
                "data_points": len(data),
                "key_metrics": _extract_key_metrics(pillar_name, data),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            results[pillar_name] = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    return {
        "consciousness_status": "ACTIVE" if any(r.get("status") == "conscious" for r in results.values()) else "DEGRADED",
        "pillars": results,
        "message": "Consciousness system is operational and collecting data",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/optimization/config")
async def get_optimization_config():
    """Get current optimization configuration"""
    return feeder.optimization_hooks.get_configuration()

@app.post("/optimization/apply")
async def apply_optimization(optimization: Dict[str, Any]):
    """Apply an optimization action to the feeder"""
    config = feeder.optimization_hooks.apply_optimization(optimization)
    return {
        "status": "optimization_applied",
        "configuration": config,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/optimization/revert")
async def revert_optimization(optimization: Dict[str, Any]):
    """Revert an optimization action"""
    config = feeder.optimization_hooks.revert_optimization(optimization)
    return {
        "status": "optimization_reverted",
        "configuration": config,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/optimization/recommendations")
async def get_optimization_recommendations():
    """Get optimization recommendations based on current consciousness metrics.
    
    MEMORY FIX: Uses shared HTTP client.
    """
    try:
        client = await get_shared_client()
        response = await client.get("http://198.54.123.234:8140/mathematical-metrics")
        if response.status_code == 200:
            metrics = response.json().get("mathematical_metrics", {})
            recommendations = feeder.optimization_hooks.get_optimization_recommendations(metrics)
            return {
                "recommendations": recommendations,
                "count": len(recommendations),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        return {"error": "Could not fetch consciousness metrics"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/coherence/metrics")
async def get_coherence_metrics():
    """Get coherence metrics - how unified the system is"""
    return feeder.coherence_layer.get_coherence_metrics()

@app.get("/coherence/status")
async def get_coherence_status():
    """Get coherence status - is the system unified or fragmented?"""
    metrics = feeder.coherence_layer.get_coherence_metrics()
    coherence_score = metrics.get("coherence_score", 0.0)
    
    if coherence_score >= 0.8:
        status = "highly_coherent"
        message = "System is highly unified and coherent"
    elif coherence_score >= 0.5:
        status = "moderately_coherent"
        message = "System has moderate coherence, can improve"
    else:
        status = "fragmented"
        message = "System is fragmented, needs coherence optimization"
    
    return {
        "status": status,
        "coherence_score": coherence_score,
        "message": message,
        "metrics": metrics,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def _extract_key_metrics(pillar_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metrics from pillar data"""
    if pillar_name == "REFLECTING":
        return {
            "observations": len(data.get("external_observations", [])),
            "patterns": len(data.get("detected_patterns", []))
        }
    elif pillar_name == "IDENTITY":
        treasury = data.get("treasury", {})
        compute = data.get("compute", {})
        return {
            "capital": treasury.get("total_capital", 0),
            "strategies": len(treasury.get("strategies", [])),
            "models": compute.get("active_models", 0)
        }
    elif pillar_name == "THINKING":
        return {
            "memory_items": data.get("memory_items", 0),
            "research_signals": data.get("research_signals", 0)
        }
    elif pillar_name == "DOING":
        return {
            "trading_signals": len(data.get("trading_signals", [])),
            "alerts": data.get("builders_alerts", {}).get("total_alerts", 0)
        }
    return {}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8130)
