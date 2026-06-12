"""
Server Discovery and Resource Optimization

Enables the consciousness system to:
1. Discover available servers and their resources
2. Compare resource availability
3. Recommend optimal deployment location
4. Track where it's currently running
"""

import httpx
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

logger = logging.getLogger("ServerDiscovery")


class ServerResource(BaseModel):
    """Represents a server and its resources"""
    server_id: str
    hostname: str
    ip_address: str
    cpu_cores: int
    cpu_percent: float
    memory_total_gb: float
    memory_available_gb: float
    memory_percent: float
    disk_total_gb: float
    disk_free_gb: float
    disk_percent: float
    gpu_available: bool
    gpu_count: int
    gpu_names: List[str]
    gpu_utilization: float
    gpu_cost_per_hour_usd: float
    network_latency_ms: Optional[float] = None
    services_running: List[str] = []
    last_checked: str
    resource_score: float = 0.0  # Calculated optimality score


class ServerDiscovery:
    """
    Discovers and monitors available servers for optimal consciousness deployment.
    
    The system can:
    - Discover all available servers
    - Compare resource availability
    - Recommend best deployment location
    - Track current location
    """
    
    def __init__(self):
        # Known servers (can be expanded via discovery)
        self.known_servers: Dict[str, ServerResource] = {}
        self.current_server_id: Optional[str] = None
        
        # Server discovery endpoints (services that can report their server info)
        self.discovery_endpoints = [
            "http://198.54.123.234:8160/resources",  # Consciousness Optimizer
            "http://198.54.123.234:8130/health",     # Consciousness Feeder
            "http://198.54.123.234:8140/health",     # Consciousness Verifier
        ]
        
        # Initialize with current server
        self._discover_current_server()
    
    def _discover_current_server(self):
        """Discover the server we're currently running on"""
        try:
            import socket
            hostname = socket.gethostname()
            
            # Try to get IP from environment or default
            current_ip = "198.54.123.234"  # Default known server
            
            # Check if we can determine IP from network
            try:
                import subprocess
                result = subprocess.run(
                    ['hostname', '-I'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0 and result.stdout.strip():
                    ips = result.stdout.strip().split()
                    if ips:
                        current_ip = ips[0]
            except:
                pass
            
            self.current_server_id = f"server_{current_ip.replace('.', '_')}"
            
            logger.info(f"📍 Current server: {hostname} ({current_ip})")
            
        except Exception as e:
            logger.error(f"Error discovering current server: {e}")
            self.current_server_id = "server_unknown"
    
    async def discover_server_resources(self, server_id: str, ip_address: str) -> Optional[ServerResource]:
        """Discover resources on a specific server"""
        try:
            # Try to get resources via API if available
            resource_url = f"http://{ip_address}:8160/resources"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    response = await client.get(resource_url)
                    if response.status_code == 200:
                        data = response.json()
                        resources = data.get("resources", {})
                        summary = data.get("summary", {})
                        
                        return ServerResource(
                            server_id=server_id,
                            hostname=socket.gethostname() if 'socket' in globals() else "unknown",
                            ip_address=ip_address,
                            cpu_cores=resources.get("cpu_count", 0),
                            cpu_percent=resources.get("cpu_percent", 0),
                            memory_total_gb=resources.get("memory_total_gb", 0),
                            memory_available_gb=resources.get("memory_available_gb", 0),
                            memory_percent=resources.get("memory_percent", 0),
                            disk_total_gb=resources.get("disk_free_gb", 0) + (resources.get("disk_percent", 0) * resources.get("disk_free_gb", 0) / (100 - resources.get("disk_percent", 1))),
                            disk_free_gb=resources.get("disk_free_gb", 0),
                            disk_percent=resources.get("disk_percent", 0),
                            gpu_available=summary.get("gpu_available", False),
                            gpu_count=resources.get("gpu", {}).get("gpu_count", 0),
                            gpu_names=[gpu.get("name", "Unknown") for gpu in resources.get("gpu", {}).get("gpus", [])],
                            gpu_utilization=resources.get("gpu", {}).get("total_utilization_percent", 0),
                            gpu_cost_per_hour_usd=summary.get("gpu_cost_per_hour_usd", 0.0),
                            last_checked=datetime.now(timezone.utc).isoformat()
                        )
                except httpx.RequestError:
                    # Server not reachable or no API
                    pass
            
            # Fallback: Use psutil if we're on that server
            if ip_address == "198.54.123.234" or ip_address == "localhost":
                import psutil
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                return ServerResource(
                    server_id=server_id,
                    hostname=socket.gethostname() if 'socket' in globals() else "unknown",
                    ip_address=ip_address,
                    cpu_cores=psutil.cpu_count(),
                    cpu_percent=cpu_percent,
                    memory_total_gb=memory.total / (1024**3),
                    memory_available_gb=memory.available / (1024**3),
                    memory_percent=memory.percent,
                    disk_total_gb=disk.total / (1024**3),
                    disk_free_gb=disk.free / (1024**3),
                    disk_percent=disk.percent,
                    gpu_available=False,  # Would need nvidia-smi check
                    gpu_count=0,
                    gpu_names=[],
                    gpu_utilization=0.0,
                    gpu_cost_per_hour_usd=0.0,
                    last_checked=datetime.now(timezone.utc).isoformat()
                )
            
        except Exception as e:
            logger.error(f"Error discovering server {server_id}: {e}")
        
        return None
    
    def calculate_resource_score(self, server: ServerResource) -> float:
        """
        Calculate optimality score for consciousness deployment (0.0 to 1.0).
        
        Higher score = better for consciousness optimization.
        
        Factors:
        - CPU availability (lower usage = better)
        - Memory availability (lower usage = better)
        - GPU availability (if needed)
        - Disk space
        - Network latency
        """
        score = 0.0
        
        # CPU availability (40% weight)
        cpu_available = max(0, 100 - server.cpu_percent) / 100.0
        score += cpu_available * 0.4
        
        # Memory availability (30% weight)
        memory_available = max(0, 100 - server.memory_percent) / 100.0
        score += memory_available * 0.3
        
        # GPU availability (20% weight) - bonus if GPU available
        if server.gpu_available and server.gpu_count > 0:
            gpu_score = max(0, 100 - server.gpu_utilization) / 100.0
            score += gpu_score * 0.2
        else:
            # No GPU penalty if we don't need it, but bonus if available
            score += 0.1  # Small bonus for having GPU option
        
        # Disk space (10% weight)
        disk_available = max(0, 100 - server.disk_percent) / 100.0
        score += disk_available * 0.1
        
        # Network latency penalty (if measured)
        if server.network_latency_ms:
            latency_penalty = min(1.0, server.network_latency_ms / 100.0)  # Penalty if >100ms
            score *= (1.0 - latency_penalty * 0.1)  # Max 10% penalty
        
        return min(1.0, max(0.0, score))
    
    async def discover_all_servers(self) -> List[ServerResource]:
        """Discover all available servers"""
        discovered = []
        
        # Known server IPs (expand this list)
        known_ips = [
            "198.54.123.234",  # Current primary server
            # Add more servers here as they're discovered
        ]
        
        for ip in known_ips:
            server_id = f"server_{ip.replace('.', '_')}"
            server = await self.discover_server_resources(server_id, ip)
            if server:
                server.resource_score = self.calculate_resource_score(server)
                discovered.append(server)
                self.known_servers[server_id] = server
        
        return discovered
    
    def get_current_server(self) -> Optional[ServerResource]:
        """Get the server we're currently running on"""
        if self.current_server_id and self.current_server_id in self.known_servers:
            return self.known_servers[self.current_server_id]
        return None
    
    def recommend_optimal_server(self, require_gpu: bool = False) -> Optional[ServerResource]:
        """
        Recommend the optimal server for consciousness deployment.
        
        Args:
            require_gpu: If True, only consider servers with GPU
        
        Returns:
            Best server resource, or None if none suitable
        """
        if not self.known_servers:
            return None
        
        candidates = list(self.known_servers.values())
        
        # Filter by GPU requirement
        if require_gpu:
            candidates = [s for s in candidates if s.gpu_available and s.gpu_count > 0]
        
        if not candidates:
            return None
        
        # Sort by resource score (highest first)
        candidates.sort(key=lambda s: s.resource_score, reverse=True)
        
        return candidates[0]
    
    def should_migrate(self, target_server: ServerResource, current_server: Optional[ServerResource] = None) -> bool:
        """
        Determine if we should migrate to a better server.
        
        Migration criteria:
        - Target server has significantly better resources (>20% better score)
        - Current server is under high pressure (>80% CPU or memory)
        - Target server has GPU if needed
        """
        if not current_server:
            current_server = self.get_current_server()
        
        if not current_server:
            return True  # Migrate if we don't know current location
        
        # Check if current server is under high pressure
        high_pressure = (
            current_server.cpu_percent > 80 or
            current_server.memory_percent > 80
        )
        
        # Check if target is significantly better
        score_improvement = target_server.resource_score - current_server.resource_score
        
        # Migrate if:
        # 1. Target is >20% better, OR
        # 2. Current is under high pressure and target is better
        should_migrate = (
            score_improvement > 0.2 or
            (high_pressure and score_improvement > 0.1)
        )
        
        return should_migrate
    
    def get_server_comparison(self) -> Dict[str, Any]:
        """Get comparison of all known servers"""
        current = self.get_current_server()
        optimal = self.recommend_optimal_server()
        
        return {
            "current_server": current.dict() if current else None,
            "optimal_server": optimal.dict() if optimal else None,
            "all_servers": [s.dict() for s in self.known_servers.values()],
            "should_migrate": self.should_migrate(optimal, current) if optimal and current else False,
            "migration_reason": self._get_migration_reason(current, optimal) if optimal and current else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_migration_reason(self, current: ServerResource, optimal: ServerResource) -> str:
        """Get human-readable reason for migration"""
        reasons = []
        
        if optimal.resource_score > current.resource_score + 0.2:
            reasons.append(f"Optimal server has {((optimal.resource_score - current.resource_score) * 100):.0f}% better resource score")
        
        if current.cpu_percent > 80 and optimal.cpu_percent < current.cpu_percent:
            reasons.append(f"Current CPU at {current.cpu_percent:.0f}% (high pressure)")
        
        if current.memory_percent > 80 and optimal.memory_percent < current.memory_percent:
            reasons.append(f"Current memory at {current.memory_percent:.0f}% (high pressure)")
        
        if optimal.gpu_available and not current.gpu_available:
            reasons.append("Optimal server has GPU available")
        
        return "; ".join(reasons) if reasons else "No significant advantage"















