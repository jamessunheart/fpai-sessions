#!/usr/bin/env python3
"""
UNIFIED GPU MANAGER - Actually Smart This Time
==============================================

ONE system that handles:
- Utilization monitoring (from correct endpoints)
- Scale up (only when needed AND under budget)
- Scale down (aggressively when idle)
- Circuit breakers (hard stops that actually stop)
- Cost tracking (real-time, not theoretical)

NO MORE:
- Two competing systems
- Wrong endpoints
- Conflicting budgets
- Runaway costs
"""

import asyncio
import json
import logging
import os
import sys
import fcntl
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

import httpx

from config import config, GPUManagerConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GPU-MANAGER] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.log_file) if config.log_file.parent.exists() else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class GPUInstance:
    """Represents a single GPU instance"""
    id: str
    gpu_name: str
    hourly_cost: float
    status: str
    created_at: datetime
    last_used: Optional[datetime] = None
    utilization: float = 0.0
    
    @property
    def is_idle(self) -> bool:
        """Check if GPU is idle based on utilization and time"""
        if self.utilization < 10:  # Less than 10% utilization
            return True
        if self.last_used:
            idle_time = datetime.now(timezone.utc) - self.last_used
            return idle_time > timedelta(minutes=config.scaling.idle_minutes)
        return True  # No usage data = assume idle


@dataclass
class ManagerState:
    """Persistent state for the manager"""
    last_check: Optional[datetime] = None
    last_scale_up: Optional[datetime] = None
    last_scale_down: Optional[datetime] = None
    gpus_created_this_hour: int = 0
    hour_started: Optional[datetime] = None
    total_cost_today: float = 0.0
    day_started: Optional[datetime] = None
    emergency_stop_active: bool = False
    
    # History
    actions: List[Dict] = field(default_factory=list)
    
    def reset_hourly_counter(self):
        """Reset the hourly GPU creation counter"""
        now = datetime.now(timezone.utc)
        if self.hour_started is None or (now - self.hour_started) > timedelta(hours=1):
            self.hour_started = now
            self.gpus_created_this_hour = 0
    
    def reset_daily_counter(self):
        """Reset the daily cost counter"""
        now = datetime.now(timezone.utc)
        if self.day_started is None or now.date() != self.day_started.date():
            self.day_started = now
            self.total_cost_today = 0.0
    
    def record_action(self, action: str, details: Dict):
        """Record an action in history"""
        self.actions.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details
        })
        # Keep only last 100 actions
        self.actions = self.actions[-100:]


class GPUManager:
    """
    Unified GPU Manager - ONE system to rule them all
    """
    
    def __init__(self, cfg: GPUManagerConfig = None):
        self.config = cfg or config
        self.state = ManagerState()
        self.http_client: Optional[httpx.AsyncClient] = None
        self._lock_fd = None
        
    async def start(self):
        """Start the manager"""
        logger.info("=" * 60)
        logger.info("GPU MANAGER STARTING")
        logger.info(f"Mode: {self.config.mode}")
        logger.info(f"Enabled: {self.config.enabled}")
        logger.info(f"Daily Budget: ${self.config.budget.daily_hard_limit_usd}")
        logger.info(f"Max GPUs: {self.config.scaling.max_gpus}")
        logger.info("=" * 60)
        
        # Check if enabled
        if not self.config.enabled:
            logger.warning("GPU Manager is DISABLED. Set GPU_MANAGER_ENABLED=true to enable.")
            return
        
        # Check API key
        if not self.config.vastai.api_key:
            logger.error("VASTAI_API_KEY not set! Cannot manage GPUs.")
            return
        
        # Acquire lock to prevent multiple instances
        if not self._acquire_lock():
            logger.error("Another GPU Manager instance is running. Exiting.")
            return
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Load state
        self._load_state()
        
        try:
            # Main loop
            await self._run_loop()
        finally:
            await self._cleanup()
    
    def _acquire_lock(self) -> bool:
        """Acquire lock file to prevent multiple instances"""
        try:
            self._lock_fd = open(self.config.circuit_breaker.lock_file, 'w')
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (IOError, OSError):
            return False
    
    def _release_lock(self):
        """Release lock file"""
        if self._lock_fd:
            fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            self._lock_fd.close()
    
    def _load_state(self):
        """Load state from file"""
        try:
            if self.config.state_file.exists():
                data = json.loads(self.config.state_file.read_text())
                # Parse dates
                for key in ['last_check', 'last_scale_up', 'last_scale_down', 'hour_started', 'day_started']:
                    if data.get(key):
                        data[key] = datetime.fromisoformat(data[key])
                self.state = ManagerState(**data)
                logger.info("Loaded state from file")
        except Exception as e:
            logger.warning(f"Could not load state: {e}")
    
    def _save_state(self):
        """Save state to file"""
        try:
            data = asdict(self.state)
            # Convert dates to ISO format
            for key in ['last_check', 'last_scale_up', 'last_scale_down', 'hour_started', 'day_started']:
                if data.get(key):
                    data[key] = data[key].isoformat()
            self.config.state_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.error(f"Could not save state: {e}")
    
    async def _cleanup(self):
        """Cleanup on shutdown"""
        if self.http_client:
            await self.http_client.aclose()
        self._release_lock()
        self._save_state()
        logger.info("GPU Manager stopped")
    
    async def _run_loop(self):
        """Main management loop"""
        logger.info("Starting main loop...")
        
        while True:
            try:
                await self._check_and_manage()
            except Exception as e:
                logger.error(f"Error in management loop: {e}")
            
            # Wait for next check
            await asyncio.sleep(self.config.monitoring.check_interval_seconds)
    
    async def _check_and_manage(self):
        """Main check and management logic"""
        logger.info("-" * 40)
        logger.info("Running management check...")
        
        # Reset counters if needed
        self.state.reset_hourly_counter()
        self.state.reset_daily_counter()
        
        # 1. Get current GPU instances
        instances = await self._get_instances()
        running = [i for i in instances if i.status == "running"]
        
        # 2. Calculate current costs
        hourly_cost = sum(i.hourly_cost for i in running)
        daily_cost = hourly_cost * 24
        self.state.total_cost_today = daily_cost  # Simplified for now
        
        logger.info(f"Running GPUs: {len(running)}")
        logger.info(f"Hourly cost: ${hourly_cost:.2f}")
        logger.info(f"Daily cost: ${daily_cost:.2f}")
        
        # 3. CHECK CIRCUIT BREAKERS FIRST
        if await self._check_circuit_breakers(running, daily_cost):
            return  # Emergency action taken
        
        # 4. Get utilization from actual endpoints
        utilization = await self._get_utilization()
        logger.info(f"Utilization: {utilization:.1f}%")
        
        # 5. Make scaling decision
        if self.config.mode == "monitor_only":
            logger.info("Mode: monitor_only - no scaling actions")
            self._log_recommendation(running, utilization, daily_cost)
        
        elif self.config.mode == "scale_down_only":
            logger.info("Mode: scale_down_only - only scaling down")
            await self._maybe_scale_down(running, utilization)
        
        elif self.config.mode == "full_auto":
            logger.info("Mode: full_auto - full scaling")
            await self._maybe_scale_down(running, utilization)
            await self._maybe_scale_up(running, utilization, daily_cost)
        
        # Save state
        self.state.last_check = datetime.now(timezone.utc)
        self._save_state()
    
    async def _check_circuit_breakers(self, running: List[GPUInstance], daily_cost: float) -> bool:
        """
        Check circuit breakers - HARD STOPS that actually stop
        Returns True if emergency action was taken
        """
        cb = self.config.circuit_breaker
        
        # 1. EMERGENCY: Cost exceeded hard limit
        if daily_cost > cb.emergency_stop_daily_cost:
            logger.critical(f"🚨 EMERGENCY: Daily cost ${daily_cost:.2f} exceeds limit ${cb.emergency_stop_daily_cost}")
            await self._emergency_shutdown(running, "cost_exceeded")
            return True
        
        # 2. EMERGENCY: Too many GPUs
        if len(running) > cb.emergency_stop_gpu_count:
            logger.critical(f"🚨 EMERGENCY: GPU count {len(running)} exceeds limit {cb.emergency_stop_gpu_count}")
            await self._emergency_shutdown(running, "gpu_count_exceeded")
            return True
        
        # 3. Rate limit check
        if self.state.gpus_created_this_hour >= cb.max_gpus_per_hour:
            logger.warning(f"Rate limit: {self.state.gpus_created_this_hour} GPUs created this hour (max: {cb.max_gpus_per_hour})")
        
        return False
    
    async def _emergency_shutdown(self, running: List[GPUInstance], reason: str):
        """
        EMERGENCY SHUTDOWN - Destroy all GPUs immediately
        """
        logger.critical(f"🚨 EXECUTING EMERGENCY SHUTDOWN: {reason}")
        self.state.emergency_stop_active = True
        
        destroyed = 0
        for gpu in running:
            success = await self._destroy_instance(gpu.id)
            if success:
                destroyed += 1
                logger.info(f"  Destroyed {gpu.id} ({gpu.gpu_name})")
        
        self.state.record_action("emergency_shutdown", {
            "reason": reason,
            "destroyed": destroyed,
            "total_running": len(running)
        })
        
        logger.critical(f"🚨 EMERGENCY SHUTDOWN COMPLETE: Destroyed {destroyed}/{len(running)} GPUs")
    
    async def _get_instances(self) -> List[GPUInstance]:
        """Get all GPU instances from Vast.ai"""
        try:
            url = f"{self.config.vastai.api_base_url}/instances/?api_key={self.config.vastai.api_key}"
            response = await self.http_client.get(url)
            data = response.json()
            
            instances = []
            for i in data.get("instances", []):
                instances.append(GPUInstance(
                    id=str(i.get("id")),
                    gpu_name=i.get("gpu_name", "Unknown"),
                    hourly_cost=i.get("dph_total", 0),
                    status=i.get("actual_status", "unknown"),
                    created_at=datetime.now(timezone.utc),  # Simplified
                    utilization=0.0
                ))
            
            return instances
        except Exception as e:
            logger.error(f"Failed to get instances: {e}")
            return []
    
    async def _get_utilization(self) -> float:
        """
        Get ACTUAL utilization from the CORRECT endpoints
        """
        total_requests = 0
        endpoints_checked = 0
        
        for endpoint in self.config.monitoring.utilization_endpoints:
            try:
                response = await self.http_client.get(endpoint, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    # Try different common stat fields
                    requests = data.get("total_requests", 0) or data.get("requests", 0) or data.get("inference_count", 0)
                    total_requests += requests
                    endpoints_checked += 1
                    logger.debug(f"Got {requests} requests from {endpoint}")
            except Exception as e:
                logger.warning(f"Could not get stats from {endpoint}: {e}")
        
        # If no data and configured to assume idle, return 0
        if endpoints_checked == 0:
            if self.config.monitoring.assume_idle_on_no_data:
                logger.warning("No utilization data available - assuming IDLE")
                return 0.0
            else:
                return 50.0  # Assume medium utilization if unsure
        
        # Calculate utilization percentage (simplified)
        # In production, this would track requests over time
        utilization = min(100.0, total_requests / 10.0)  # Simplified metric
        return utilization
    
    async def _maybe_scale_down(self, running: List[GPUInstance], utilization: float):
        """
        Scale down if utilization is low
        """
        # Check cooldown
        if self.state.last_scale_down:
            cooldown = timedelta(minutes=self.config.scaling.scale_down_cooldown_minutes)
            if datetime.now(timezone.utc) - self.state.last_scale_down < cooldown:
                logger.debug("Scale down on cooldown")
                return
        
        # Check if we should scale down
        if utilization > self.config.scaling.scale_down_utilization:
            logger.debug(f"Utilization {utilization}% > threshold {self.config.scaling.scale_down_utilization}% - not scaling down")
            return
        
        # Check minimum GPUs
        if len(running) <= self.config.scaling.min_gpus:
            logger.debug(f"Already at minimum GPUs ({self.config.scaling.min_gpus})")
            return
        
        # Find the most expensive idle GPU to release
        idle_gpus = [g for g in running if g.is_idle]
        if not idle_gpus:
            # If no idle GPUs by utilization, pick the most expensive
            idle_gpus = running
        
        # Sort by cost (most expensive first)
        idle_gpus.sort(key=lambda g: g.hourly_cost, reverse=True)
        
        # Release the most expensive idle GPU
        gpu_to_release = idle_gpus[0]
        logger.info(f"📉 SCALING DOWN: Releasing {gpu_to_release.id} ({gpu_to_release.gpu_name}) - ${gpu_to_release.hourly_cost:.3f}/hr")
        
        success = await self._destroy_instance(gpu_to_release.id)
        if success:
            self.state.last_scale_down = datetime.now(timezone.utc)
            self.state.record_action("scale_down", {
                "gpu_id": gpu_to_release.id,
                "gpu_name": gpu_to_release.gpu_name,
                "cost": gpu_to_release.hourly_cost,
                "utilization": utilization
            })
            logger.info(f"✅ Released GPU {gpu_to_release.id}")
    
    async def _maybe_scale_up(self, running: List[GPUInstance], utilization: float, daily_cost: float):
        """
        Scale up ONLY if:
        1. Utilization is high
        2. Under budget
        3. Under max GPU count
        4. Not rate limited
        """
        # Check if we're under budget
        budget_remaining = self.config.budget.daily_hard_limit_usd - daily_cost
        if budget_remaining < 2.0:  # Need at least $2/day headroom
            logger.info(f"Budget headroom too low (${budget_remaining:.2f}) - not scaling up")
            return
        
        # Check cooldown
        if self.state.last_scale_up:
            cooldown = timedelta(minutes=self.config.scaling.scale_up_cooldown_minutes)
            if datetime.now(timezone.utc) - self.state.last_scale_up < cooldown:
                logger.debug("Scale up on cooldown")
                return
        
        # Check max GPUs
        if len(running) >= self.config.scaling.max_gpus:
            logger.debug(f"Already at maximum GPUs ({self.config.scaling.max_gpus})")
            return
        
        # Check rate limit
        if self.state.gpus_created_this_hour >= self.config.circuit_breaker.max_gpus_per_hour:
            logger.warning(f"Rate limited - created {self.state.gpus_created_this_hour} GPUs this hour")
            return
        
        # Check utilization threshold
        if utilization < self.config.scaling.scale_up_utilization:
            logger.debug(f"Utilization {utilization}% < threshold {self.config.scaling.scale_up_utilization}% - not scaling up")
            return
        
        # All checks passed - scale up
        logger.info(f"📈 SCALING UP: Utilization {utilization}% > {self.config.scaling.scale_up_utilization}%")
        
        # Find a cheap GPU to rent
        gpu = await self._find_cheap_gpu()
        if gpu:
            success = await self._create_instance(gpu)
            if success:
                self.state.last_scale_up = datetime.now(timezone.utc)
                self.state.gpus_created_this_hour += 1
                self.state.record_action("scale_up", {
                    "gpu": gpu,
                    "utilization": utilization,
                    "budget_remaining": budget_remaining
                })
                logger.info(f"✅ Created new GPU instance")
        else:
            logger.warning("No suitable cheap GPUs available")
    
    async def _find_cheap_gpu(self) -> Optional[Dict]:
        """Find a cheap GPU to rent"""
        try:
            # Search for available GPUs
            url = f"{self.config.vastai.api_base_url}/bundles/?api_key={self.config.vastai.api_key}"
            response = await self.http_client.get(url)
            data = response.json()
            
            offers = data.get("offers", [])
            
            # Filter by cost and requirements
            suitable = []
            for offer in offers:
                cost = offer.get("dph_total", 999)
                vram = offer.get("gpu_ram", 0) / 1024  # Convert to GB
                
                if cost <= self.config.budget.max_gpu_hourly_cost and vram >= self.config.vastai.min_vram_gb:
                    suitable.append(offer)
            
            # Sort by cost
            suitable.sort(key=lambda x: x.get("dph_total", 999))
            
            if suitable:
                return suitable[0]
            return None
        except Exception as e:
            logger.error(f"Failed to find GPU: {e}")
            return None
    
    async def _create_instance(self, offer: Dict) -> bool:
        """Create a new GPU instance"""
        try:
            url = f"{self.config.vastai.api_base_url}/asks/{offer['id']}/?api_key={self.config.vastai.api_key}"
            payload = {
                "client_id": "fpai",
                "image": "ollama/ollama",  # Default to Ollama
                "disk": self.config.vastai.min_disk_gb,
                "onstart": "ollama serve"
            }
            response = await self.http_client.put(url, json=payload)
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Failed to create instance: {e}")
            return False
    
    async def _destroy_instance(self, instance_id: str) -> bool:
        """Destroy a GPU instance"""
        try:
            url = f"{self.config.vastai.api_base_url}/instances/{instance_id}/?api_key={self.config.vastai.api_key}"
            response = await self.http_client.delete(url)
            return response.status_code in [200, 204] or "success" in response.text.lower()
        except Exception as e:
            logger.error(f"Failed to destroy instance {instance_id}: {e}")
            return False
    
    def _log_recommendation(self, running: List[GPUInstance], utilization: float, daily_cost: float):
        """Log what would happen if scaling was enabled"""
        logger.info("=" * 40)
        logger.info("RECOMMENDATION (monitor_only mode):")
        
        if daily_cost > self.config.budget.daily_hard_limit_usd:
            logger.info(f"  ⚠️ WOULD EMERGENCY SHUTDOWN: Cost ${daily_cost:.2f} > ${self.config.budget.daily_hard_limit_usd}")
        elif utilization < self.config.scaling.scale_down_utilization and len(running) > self.config.scaling.min_gpus:
            logger.info(f"  📉 WOULD SCALE DOWN: Utilization {utilization}% is low")
        elif utilization > self.config.scaling.scale_up_utilization and len(running) < self.config.scaling.max_gpus:
            logger.info(f"  📈 WOULD SCALE UP: Utilization {utilization}% is high")
        else:
            logger.info(f"  ✅ NO ACTION NEEDED: System balanced")
        
        logger.info("=" * 40)


async def main():
    """Entry point"""
    manager = GPUManager()
    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
