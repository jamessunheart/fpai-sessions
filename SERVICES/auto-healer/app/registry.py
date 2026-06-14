"""
Service Registry - Central definition of all monitored services
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from pathlib import Path
import json
import logging

from .config import REGISTRY_PATH

logger = logging.getLogger(__name__)


@dataclass
class ServiceDefinition:
    """Definition of a monitored service with metadata needed for healing."""
    name: str                           # e.g., "genesis"
    systemd_name: str                   # e.g., "genesis.service"
    port: int                           # e.g., 8150
    health_endpoint: str = "/health"    # e.g., "/health"
    working_dir: str = ""               # e.g., "/root/SERVICES/genesis"
    venv_path: Optional[str] = ".venv"  # e.g., ".venv" or None for system python
    requirements_file: str = "requirements.txt"
    main_file: str = "main.py"          # or "app/main.py"
    critical: bool = False              # Alert immediately if down
    max_auto_restarts: int = 3          # Before escalating
    restart_cooldown: int = 60          # Seconds between attempts
    dependencies: List[str] = field(default_factory=list)  # Services that must be up first
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ServiceDefinition":
        return cls(**data)


# Default service registry - services we know need monitoring
DEFAULT_SERVICES: List[ServiceDefinition] = [
    # Core Infrastructure - CRITICAL
    ServiceDefinition(
        name="genesis",
        systemd_name="genesis.service",
        port=8150,
        working_dir="/root/SERVICES/genesis",
        venv_path=None,  # Uses system python
        main_file="main.py",
        critical=True,
    ),
    ServiceDefinition(
        name="team-hub",
        systemd_name="team-hub.service",
        port=8355,
        working_dir="/opt/fpai/services/team-hub",
        venv_path=None,  # Uses system python
        main_file="app/main.py",
        critical=True,
    ),
    ServiceDefinition(
        name="fp-credits-gateway",
        systemd_name="fpai-fp-credits-gateway.service",
        port=8765,
        working_dir="/opt/fpai/apps/fp-credits-gateway",
        venv_path=".venv",
        main_file="app/main.py",
        critical=True,
    ),
    ServiceDefinition(
        name="credits-manager",
        systemd_name="credits-manager.service",
        port=8955,
        working_dir="/opt/fpai/services/credits-manager",
        venv_path="venv",
        main_file="app/main.py",
        critical=True,
    ),
    ServiceDefinition(
        name="nerve-center",
        systemd_name="fpai-nerve-center.service",
        port=8120,
        working_dir="/opt/fpai/services/nerve-center",
        venv_path="venv",
        main_file="server.py",
        critical=True,
    ),
    
    # NOTE: AI services (AI Brain, Consciousness, etc.) run on the SECONDARY server
    # and should NOT be monitored/healed by the PRIMARY server's auto-healer, since
    # this auto-healer checks `http://localhost:<port>` and local systemd units.
    ServiceDefinition(
        name="data-service",
        systemd_name="fpai-data-service.service",
        port=8125,
        working_dir="/opt/fpai/apps/data-service",
        venv_path=".venv",
        main_file="app/main.py",
        critical=True,
        dependencies=["genesis"],
    ),
    
    # Trading Services
    ServiceDefinition(
        name="whaletrack-live",
        systemd_name="whaletrack-live.service",
        port=8601,
        working_dir="/opt/fpai/services/whaletrack-live",
        venv_path=None,  # Uses system python
        main_file="app/main.py",
        critical=True,
    ),
    ServiceDefinition(
        name="strategic-intel",
        systemd_name="fpai-strategic-intel.service",
        port=8500,
        working_dir="/opt/fpai/services/strategic-intelligence",
        venv_path="venv",
        main_file="app/main.py",
        critical=True,
    ),
    
    # Revenue Services
    ServiceDefinition(
        name="i-match",
        systemd_name="i-match.service",
        port=8401,
        working_dir="/opt/fpai/apps/i-match",
        venv_path="venv",
        main_file="app/main.py",
        critical=False,
    ),
    ServiceDefinition(
        name="ai-automation",
        systemd_name="fpai-ai-automation.service",
        port=8700,
        working_dir="/opt/fpai/apps/ai-automation",
        venv_path=".venv",
        main_file="main.py",
        critical=False,
    ),
    
    # Monitoring
    ServiceDefinition(
        name="godmode",
        systemd_name="godmode.service",
        port=8300,
        working_dir="/opt/fpai/godmode-v3",
        venv_path=None,  # Uses system python
        main_file="server.py",
        critical=False,
    ),
]


class ServiceRegistry:
    """Manages the registry of monitored services."""
    
    def __init__(self, registry_path: Path = REGISTRY_PATH):
        self.registry_path = registry_path
        self.services: Dict[str, ServiceDefinition] = {}
        self._load()
    
    def _load(self):
        """Load registry from disk or use defaults."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path) as f:
                    data = json.load(f)
                    for svc_data in data.get("services", []):
                        svc = ServiceDefinition.from_dict(svc_data)
                        self.services[svc.name] = svc
                logger.info(f"Loaded {len(self.services)} services from registry")
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                self._use_defaults()
        else:
            self._use_defaults()
            self._save()
    
    def _use_defaults(self):
        """Use default service definitions."""
        for svc in DEFAULT_SERVICES:
            self.services[svc.name] = svc
        logger.info(f"Using {len(self.services)} default service definitions")
    
    def _save(self):
        """Save registry to disk."""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": "1.0",
                "services": [svc.to_dict() for svc in self.services.values()]
            }
            with open(self.registry_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved registry to {self.registry_path}")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def get(self, name: str) -> Optional[ServiceDefinition]:
        """Get a service by name."""
        return self.services.get(name)
    
    def get_all(self) -> List[ServiceDefinition]:
        """Get all services."""
        return list(self.services.values())
    
    def get_critical(self) -> List[ServiceDefinition]:
        """Get only critical services."""
        return [s for s in self.services.values() if s.critical]
    
    def add(self, service: ServiceDefinition):
        """Add or update a service."""
        self.services[service.name] = service
        self._save()
    
    def remove(self, name: str):
        """Remove a service."""
        if name in self.services:
            del self.services[name]
            self._save()
    
    def to_dict(self) -> dict:
        """Export registry as dict."""
        return {
            "total": len(self.services),
            "critical": len(self.get_critical()),
            "services": {name: svc.to_dict() for name, svc in self.services.items()}
        }


# Global registry instance
registry = ServiceRegistry()





