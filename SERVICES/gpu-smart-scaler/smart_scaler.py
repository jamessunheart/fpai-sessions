#!/usr/bin/env python3
"""
SMART GPU SCALER v1.0
=====================

Philosophy:
- SCALE DOWN: Automatic (saving money = always good)
- SCALE UP: Request approval with reasoning (spending money = needs justification)

How it works:
1. Monitors build queue and GPU utilization
2. When scaling UP is needed, creates a REQUEST with reasoning
3. Human approves/denies via API or Telegram
4. Scales DOWN automatically when GPUs are idle
"""

import os
import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
import httpx
import sqlite3

# Config
VAST_API_KEY = os.environ.get("VAST_API_KEY", "")  # scrubbed 2026-05-18 — service ARCHIVED
BUILD_QUEUE_DB = "/opt/fpai/ai-brain/v2/thinking_v2.db"
STATE_FILE = Path("/opt/fpai/gpu-smart-scaler/state.json")
REQUESTS_FILE = Path("/opt/fpai/gpu-smart-scaler/requests.json")

# Thresholds
MIN_GPUS = 1  # Always keep at least 1 for quick response
MAX_GPUS = 5  # Hard cap
IDLE_MINUTES_TO_SCALE_DOWN = 10  # Scale down after 10 min idle
QUEUE_DEPTH_TO_REQUEST_SCALEUP = 3  # Request more GPUs if 3+ tasks pending

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SMART-SCALER] %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ScaleRequest:
    """A request to scale up GPUs"""
    id: str
    created_at: str
    reason: str
    current_gpus: int
    requested_gpus: int
    queue_depth: int
    estimated_cost_hr: float
    status: str = "pending"  # pending, approved, denied, expired
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None


@dataclass 
class GPUState:
    """Current GPU fleet state"""
    running_gpus: int
    hourly_cost: float
    last_activity: str
    idle_minutes: int
    instances: List[Dict]


class SmartScaler:
    def __init__(self):
        self.state_file = STATE_FILE
        self.requests_file = REQUESTS_FILE
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.pending_requests: List[ScaleRequest] = []
        self.load_state()
    
    def load_state(self):
        """Load pending requests from disk"""
        if self.requests_file.exists():
            try:
                data = json.loads(self.requests_file.read_text())
                self.pending_requests = [
                    ScaleRequest(**r) for r in data 
                    if r.get("status") == "pending"
                ]
            except:
                self.pending_requests = []
    
    def save_state(self):
        """Save pending requests to disk"""
        data = [asdict(r) for r in self.pending_requests]
        self.requests_file.write_text(json.dumps(data, indent=2))
    
    async def get_vast_instances(self) -> List[Dict]:
        """Get running Vast.ai instances"""
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"https://console.vast.ai/api/v0/instances/?api_key={VAST_API_KEY}"
            )
            instances = r.json().get("instances", [])
            return [i for i in instances if i.get("actual_status") == "running"]
    
    async def get_gpu_state(self) -> GPUState:
        """Get current GPU fleet state"""
        instances = await self.get_vast_instances()
        hourly_cost = sum(i.get("dph_total", 0) for i in instances)
        
        # Check last activity from GPU Bridge
        last_activity = datetime.now()
        idle_minutes = 0
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get("http://localhost:8400/health")
                # Could parse last request time from stats
        except:
            pass
        
        return GPUState(
            running_gpus=len(instances),
            hourly_cost=hourly_cost,
            last_activity=last_activity.isoformat(),
            idle_minutes=idle_minutes,
            instances=[{
                "id": i.get("id"),
                "gpu": i.get("gpu_name"),
                "cost": i.get("dph_total", 0)
            } for i in instances]
        )
    
    def get_queue_depth(self) -> int:
        """Get number of pending tasks in build queue"""
        try:
            conn = sqlite3.connect(BUILD_QUEUE_DB)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM build_queue WHERE status = 'pending'")
            count = c.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def get_running_tasks(self) -> int:
        """Get number of currently running tasks"""
        try:
            conn = sqlite3.connect(BUILD_QUEUE_DB)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM build_queue WHERE status = 'running'")
            count = c.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    async def check_scale_down(self, state: GPUState) -> bool:
        """Check if we should scale down (automatic)"""
        queue_depth = self.get_queue_depth()
        running_tasks = self.get_running_tasks()
        
        # Don't scale below minimum
        if state.running_gpus <= MIN_GPUS:
            return False
        
        # Scale down if:
        # 1. No pending tasks AND no running tasks
        # 2. OR way more GPUs than needed
        if queue_depth == 0 and running_tasks == 0:
            logger.info(f"📉 Auto-scaling DOWN: Queue empty, {state.running_gpus} GPUs running")
            await self.scale_down(state, target=MIN_GPUS)
            return True
        
        # If we have more GPUs than pending+running tasks, scale down
        needed = max(MIN_GPUS, running_tasks + min(queue_depth, 2))
        if state.running_gpus > needed + 1:
            logger.info(f"📉 Auto-scaling DOWN: Have {state.running_gpus}, need {needed}")
            await self.scale_down(state, target=needed)
            return True
        
        return False
    
    async def check_scale_up(self, state: GPUState) -> Optional[ScaleRequest]:
        """Check if we should REQUEST to scale up"""
        queue_depth = self.get_queue_depth()
        running_tasks = self.get_running_tasks()
        
        # Don't exceed max
        if state.running_gpus >= MAX_GPUS:
            return None
        
        # Check if there's already a pending request
        if any(r.status == "pending" for r in self.pending_requests):
            return None
        
        # Request scale up if:
        # Queue is deep AND we don't have enough GPUs
        if queue_depth >= QUEUE_DEPTH_TO_REQUEST_SCALEUP:
            requested = min(state.running_gpus + 2, MAX_GPUS)
            estimated_cost = state.hourly_cost + 0.10  # Assume $0.10/hr per new GPU
            
            reason = self._generate_reason(queue_depth, running_tasks, state)
            
            request = ScaleRequest(
                id=f"scale_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_at=datetime.now().isoformat(),
                reason=reason,
                current_gpus=state.running_gpus,
                requested_gpus=requested,
                queue_depth=queue_depth,
                estimated_cost_hr=estimated_cost
            )
            
            self.pending_requests.append(request)
            self.save_state()
            
            logger.info(f"📤 SCALE-UP REQUEST: {request.reason}")
            await self.notify_request(request)
            
            return request
        
        return None
    
    def _generate_reason(self, queue_depth: int, running: int, state: GPUState) -> str:
        """Generate human-readable reason for scale-up"""
        reasons = []
        
        if queue_depth >= 5:
            reasons.append(f"🔥 High queue depth: {queue_depth} tasks waiting")
        elif queue_depth >= 3:
            reasons.append(f"📋 Queue building: {queue_depth} tasks pending")
        
        if running > 0:
            reasons.append(f"⚙️ Currently processing {running} task(s)")
        
        if state.running_gpus < 2:
            reasons.append(f"💡 Only {state.running_gpus} GPU(s) available")
        
        reasons.append(f"💰 Current cost: ${state.hourly_cost:.2f}/hr")
        
        return " | ".join(reasons)
    
    async def notify_request(self, request: ScaleRequest):
        """Notify about scale-up request (Telegram, etc.)"""
        message = f"""
🖥️ GPU SCALE-UP REQUEST

{request.reason}

📊 Current: {request.current_gpus} GPUs
📈 Requested: {request.requested_gpus} GPUs  
💵 Est. cost: ${request.estimated_cost_hr:.2f}/hr

Reply with:
• /approve_gpu {request.id}
• /deny_gpu {request.id}
"""
        # Try to send to Telegram
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    "http://162.0.208.88:8710/notify",
                    json={"message": message, "priority": "high"}
                )
        except:
            logger.info(f"Telegram notification failed, request logged to file")
    
    async def scale_down(self, state: GPUState, target: int):
        """Scale down to target number of GPUs"""
        to_stop = state.running_gpus - target
        if to_stop <= 0:
            return
        
        # Sort by cost (stop most expensive first)
        instances = sorted(state.instances, key=lambda x: x.get("cost", 0), reverse=True)
        
        stopped = 0
        async with httpx.AsyncClient(timeout=15) as client:
            for inst in instances[:to_stop]:
                try:
                    await client.put(
                        f"https://console.vast.ai/api/v0/instances/{inst['id']}/?api_key={VAST_API_KEY}",
                        json={"state": "stopped"}
                    )
                    logger.info(f"  ✅ Stopped {inst['gpu']} (${inst['cost']:.3f}/hr)")
                    stopped += 1
                except Exception as e:
                    logger.error(f"  ❌ Failed to stop {inst['id']}: {e}")
        
        logger.info(f"📉 Scaled down: Stopped {stopped} GPUs")
    
    async def scale_up(self, target: int):
        """Scale up to target number of GPUs (only called after approval)"""
        state = await self.get_gpu_state()
        to_add = target - state.running_gpus
        
        if to_add <= 0:
            return
        
        # Find cheap GPUs on Vast.ai
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"https://console.vast.ai/api/v0/bundles/?api_key={VAST_API_KEY}"
            )
            offers = r.json().get("offers", [])
            
            # Filter: cheap, single GPU, good reliability
            good_offers = [
                o for o in offers
                if o.get("dph_total", 999) < 0.10  # Under $0.10/hr
                and o.get("num_gpus", 0) == 1
                and o.get("reliability", 0) > 0.95
            ]
            
            # Sort by cost
            good_offers.sort(key=lambda x: x.get("dph_total", 999))
            
            added = 0
            for offer in good_offers[:to_add]:
                try:
                    # Rent the GPU
                    r = await client.put(
                        f"https://console.vast.ai/api/v0/asks/{offer['id']}/?api_key={VAST_API_KEY}",
                        json={
                            "client_id": "fpai",
                            "image": "ollama/ollama",
                            "disk": 20,
                            "env": {"OLLAMA_HOST": "0.0.0.0:11434"},
                            "onstart": "ollama pull llama3.1:8b && ollama pull qwen2.5-coder:7b"
                        }
                    )
                    if r.status_code == 200:
                        logger.info(f"  ✅ Added {offer.get('gpu_name')} (${offer['dph_total']:.3f}/hr)")
                        added += 1
                except Exception as e:
                    logger.error(f"  ❌ Failed to rent: {e}")
            
            logger.info(f"📈 Scaled up: Added {added} GPUs")
    
    async def approve_request(self, request_id: str, approved_by: str = "user"):
        """Approve a scale-up request"""
        for req in self.pending_requests:
            if req.id == request_id and req.status == "pending":
                req.status = "approved"
                req.approved_at = datetime.now().isoformat()
                req.approved_by = approved_by
                self.save_state()
                
                logger.info(f"✅ Request {request_id} APPROVED by {approved_by}")
                await self.scale_up(req.requested_gpus)
                return True
        return False
    
    async def deny_request(self, request_id: str, denied_by: str = "user"):
        """Deny a scale-up request"""
        for req in self.pending_requests:
            if req.id == request_id and req.status == "pending":
                req.status = "denied"
                self.save_state()
                logger.info(f"❌ Request {request_id} DENIED by {denied_by}")
                return True
        return False
    
    async def run_check(self):
        """Run a single scaling check"""
        logger.info("🔍 Running scaling check...")
        
        state = await self.get_gpu_state()
        queue_depth = self.get_queue_depth()
        
        logger.info(f"  GPUs: {state.running_gpus} | Queue: {queue_depth} | Cost: ${state.hourly_cost:.2f}/hr")
        
        # Always check scale-down first (automatic)
        scaled_down = await self.check_scale_down(state)
        
        # Then check if we need to REQUEST scale-up
        if not scaled_down:
            request = await self.check_scale_up(state)
            if request:
                logger.info(f"  📤 Scale-up request created: {request.id}")
    
    async def run(self, interval: int = 60):
        """Main loop"""
        logger.info("🚀 Smart GPU Scaler starting...")
        logger.info(f"  Min GPUs: {MIN_GPUS}")
        logger.info(f"  Max GPUs: {MAX_GPUS}")
        logger.info(f"  Check interval: {interval}s")
        
        while True:
            try:
                await self.run_check()
            except Exception as e:
                logger.error(f"Check failed: {e}")
            
            await asyncio.sleep(interval)


# FastAPI for approvals
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Smart GPU Scaler", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

scaler = SmartScaler()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "smart-gpu-scaler"}


@app.get("/status")
async def status():
    state = await scaler.get_gpu_state()
    return {
        "gpus": state.running_gpus,
        "hourly_cost": state.hourly_cost,
        "queue_depth": scaler.get_queue_depth(),
        "pending_requests": [asdict(r) for r in scaler.pending_requests if r.status == "pending"],
        "min_gpus": MIN_GPUS,
        "max_gpus": MAX_GPUS
    }


@app.get("/requests")
async def get_requests():
    return {"requests": [asdict(r) for r in scaler.pending_requests]}


@app.post("/approve/{request_id}")
async def approve(request_id: str):
    success = await scaler.approve_request(request_id)
    if success:
        return {"status": "approved", "request_id": request_id}
    raise HTTPException(404, "Request not found or already processed")


@app.post("/deny/{request_id}")
async def deny(request_id: str):
    success = await scaler.deny_request(request_id)
    if success:
        return {"status": "denied", "request_id": request_id}
    raise HTTPException(404, "Request not found or already processed")


@app.post("/force-check")
async def force_check():
    await scaler.run_check()
    return {"status": "check completed"}


if __name__ == "__main__":
    import uvicorn
    import threading
    
    # Run scaler in background
    def run_scaler():
        asyncio.run(scaler.run(interval=60))
    
    threading.Thread(target=run_scaler, daemon=True).start()
    
    # Run API
    uvicorn.run(app, host="0.0.0.0", port=8450)


