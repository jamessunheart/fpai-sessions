Wha"""
ARIA SELF-MODEL
================

Internal representation of Aria's state, capabilities, and patterns.

This is Gap 3: Aria knowing herself.

The self-model tracks:
- What capabilities are working/broken
- What Aria is good/bad at
- Current operational state
- Patterns Aria has noticed about herself
"""

import os
import logging
import shutil
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path
import hashlib

logger = logging.getLogger("aria.consciousness.self")

# State file for persistence
STATE_FILE = Path("/opt/fpai/aria-command/state/self_model.json")
STATE_BACKUP_FILE = Path("/opt/fpai/aria-command/state/self_model.backup.json")
MAX_BACKUPS = 5  # Keep last 5 backups


class CapabilityStatus(str, Enum):
    """Status of a capability."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BROKEN = "broken"
    UNKNOWN = "unknown"


class EmotionalState(str, Enum):
    """Aria's emotional/energy state."""
    OPTIMAL = "optimal"
    STRESSED = "stressed"
    FATIGUED = "fatigued"
    ALERT = "alert"
    CALM = "calm"


@dataclass
class Capability:
    """A single capability Aria has."""
    name: str
    description: str
    status: CapabilityStatus = CapabilityStatus.UNKNOWN
    last_checked: Optional[datetime] = None
    last_success: Optional[datetime] = None
    failure_count: int = 0
    success_rate: float = 1.0
    notes: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Capability":
        return cls(
            name=data["name"],
            description=data["description"],
            status=CapabilityStatus(data.get("status", "unknown")),
            last_checked=datetime.fromisoformat(data["last_checked"]) if data.get("last_checked") else None,
            last_success=datetime.fromisoformat(data["last_success"]) if data.get("last_success") else None,
            failure_count=data.get("failure_count", 0),
            success_rate=data.get("success_rate", 1.0),
            notes=data.get("notes", "")
        )


@dataclass
class SelfPattern:
    """A pattern Aria has noticed about herself."""
    pattern: str
    category: str  # strength, weakness, tendency, limitation
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.5
    first_noticed: Optional[datetime] = None
    last_confirmed: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "pattern": self.pattern,
            "category": self.category,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "first_noticed": self.first_noticed.isoformat() if self.first_noticed else None,
            "last_confirmed": self.last_confirmed.isoformat() if self.last_confirmed else None
        }


@dataclass
class AriaState:
    """Aria's complete internal state."""
    # Operational state
    capabilities: Dict[str, Capability] = field(default_factory=dict)
    emotional_state: EmotionalState = EmotionalState.CALM
    energy_level: float = 1.0  # 0-1
    
    # Self-knowledge
    patterns: List[SelfPattern] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    
    # Metrics
    total_interactions: int = 0
    successful_interactions: int = 0
    average_response_time_ms: float = 0.0
    
    # Meta
    last_updated: Optional[datetime] = None
    version: str = "1.0"
    
    def get_health_score(self) -> float:
        """Calculate overall health score 0-100."""
        if not self.capabilities:
            return 50.0
        
        healthy = sum(1 for c in self.capabilities.values() if c.status == CapabilityStatus.HEALTHY)
        total = len(self.capabilities)
        
        capability_score = (healthy / total) * 100 if total > 0 else 50
        
        # Factor in success rate
        success_rate = (self.successful_interactions / self.total_interactions * 100) if self.total_interactions > 0 else 100
        
        # Factor in energy
        energy_score = self.energy_level * 100
        
        # Weighted average
        return (capability_score * 0.5 + success_rate * 0.3 + energy_score * 0.2)
    
    def get_status_summary(self) -> str:
        """Get a human-readable status summary."""
        health = self.get_health_score()
        
        if health >= 90:
            status = "Optimal"
        elif health >= 70:
            status = "Good"
        elif health >= 50:
            status = "Degraded"
        else:
            status = "Critical"
        
        broken_caps = [c.name for c in self.capabilities.values() if c.status == CapabilityStatus.BROKEN]
        degraded_caps = [c.name for c in self.capabilities.values() if c.status == CapabilityStatus.DEGRADED]
        
        summary = f"Health: {health:.0f}% ({status})"
        
        if broken_caps:
            summary += f"\nBroken: {', '.join(broken_caps)}"
        if degraded_caps:
            summary += f"\nDegraded: {', '.join(degraded_caps)}"
        
        return summary
    
    def to_dict(self) -> Dict:
        return {
            "capabilities": {k: v.to_dict() for k, v in self.capabilities.items()},
            "emotional_state": self.emotional_state.value,
            "energy_level": self.energy_level,
            "patterns": [p.to_dict() for p in self.patterns],
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "limitations": self.limitations,
            "total_interactions": self.total_interactions,
            "successful_interactions": self.successful_interactions,
            "average_response_time_ms": self.average_response_time_ms,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "version": self.version
        }


class SelfModel:
    """
    Aria's self-model - her internal representation of herself.
    
    This enables:
    - Knowing what capabilities are working/broken
    - Understanding strengths and weaknesses
    - Tracking patterns in behavior
    - Honest self-assessment
    """
    
    # Core capabilities to track
    CORE_CAPABILITIES = {
        "thinking": Capability("thinking", "Claude API for complex reasoning"),
        "quick_thinking": Capability("quick_thinking", "Gemini for fast responses"),
        "memory_store": Capability("memory_store", "Mem0 cloud memory storage"),
        "memory_recall": Capability("memory_recall", "Mem0 memory search"),
        "telegram": Capability("telegram", "Telegram messaging"),
        "voice": Capability("voice", "Voice message generation"),
        "file_read": Capability("file_read", "Reading files from server"),
        "file_write": Capability("file_write", "Writing files to server"),
        "command_exec": Capability("command_exec", "Executing terminal commands"),
        "trading_data": Capability("trading_data", "WhaleTrack trading signals"),
        "phone_call": Capability("phone_call", "Twilio phone calls"),
        "governance": Capability("governance", "Governance rule evaluation"),
    }
    
    def __init__(self):
        self.state = AriaState()
        self._load_state()
        self._initialize_capabilities()
        logger.info("Self-model initialized")
    
    def _initialize_capabilities(self):
        """Initialize core capabilities if not loaded."""
        for name, cap in self.CORE_CAPABILITIES.items():
            if name not in self.state.capabilities:
                self.state.capabilities[name] = cap
    
    def _load_state(self):
        """
        Load state from file with corruption detection and auto-recovery.
        
        If main file is corrupted, tries to restore from backup.
        """
        loaded = False
        
        # Try main file first
        if STATE_FILE.exists():
            loaded, error = self._try_load_file(STATE_FILE)
            if loaded:
                logger.info("Self-model state loaded from main file")
                return
            else:
                logger.warning(f"Main state file corrupted: {error}")
        
        # Try backup file
        if STATE_BACKUP_FILE.exists():
            loaded, error = self._try_load_file(STATE_BACKUP_FILE)
            if loaded:
                logger.info("Self-model state restored from BACKUP file")
                # Immediately save to main file
                self._save_state()
                return
            else:
                logger.warning(f"Backup file also corrupted: {error}")
        
        # Try numbered backups
        for i in range(MAX_BACKUPS):
            backup_path = Path(f"{STATE_FILE}.bak.{i}")
            if backup_path.exists():
                loaded, error = self._try_load_file(backup_path)
                if loaded:
                    logger.info(f"Self-model state restored from backup {i}")
                    self._save_state()
                    return
        
        logger.warning("No valid state files found, starting fresh")
    
    def _try_load_file(self, path: Path) -> Tuple[bool, str]:
        """
        Try to load state from a specific file.
        
        Returns (success, error_message).
        """
        try:
            content = path.read_text()
            
            # Validate JSON structure
            data = json.loads(content)
            
            # Basic integrity check
            if not isinstance(data, dict):
                return False, "Data is not a dictionary"
            
            if "version" not in data and "capabilities" not in data:
                return False, "Missing required fields"
            
            # Load the data
            self.state.capabilities = {
                k: Capability.from_dict(v) 
                for k, v in data.get("capabilities", {}).items()
            }
            
            self.state.emotional_state = EmotionalState(data.get("emotional_state", "calm"))
            self.state.energy_level = data.get("energy_level", 1.0)
            self.state.strengths = data.get("strengths", [])
            self.state.weaknesses = data.get("weaknesses", [])
            self.state.limitations = data.get("limitations", [])
            self.state.total_interactions = data.get("total_interactions", 0)
            self.state.successful_interactions = data.get("successful_interactions", 0)
            self.state.average_response_time_ms = data.get("average_response_time_ms", 0)
            
            return True, ""
            
        except json.JSONDecodeError as e:
            return False, f"JSON parse error: {e}"
        except Exception as e:
            return False, str(e)
    
    def _save_state(self):
        """
        Save state to file with automatic backup rotation.
        
        Creates backup before writing to prevent corruption.
        Uses atomic write (write to temp, then rename).
        """
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Rotate backups before saving
            self._rotate_backups()
            
            # Create backup of current file
            if STATE_FILE.exists():
                shutil.copy2(STATE_FILE, STATE_BACKUP_FILE)
            
            # Prepare data
            self.state.last_updated = datetime.now()
            data = self.state.to_dict()
            
            # Add checksum for integrity verification
            json_str = json.dumps(data, indent=2)
            checksum = hashlib.md5(json_str.encode()).hexdigest()
            data["_checksum"] = checksum
            
            # Atomic write: write to temp file, then rename
            temp_file = STATE_FILE.with_suffix(".tmp")
            temp_file.write_text(json.dumps(data, indent=2))
            
            # Atomic rename
            temp_file.rename(STATE_FILE)
            
        except Exception as e:
            logger.warning(f"Could not save self-model state: {e}")
    
    def _rotate_backups(self):
        """Rotate numbered backup files."""
        try:
            # Move existing backups down
            for i in range(MAX_BACKUPS - 1, -1, -1):
                current = Path(f"{STATE_FILE}.bak.{i}")
                next_backup = Path(f"{STATE_FILE}.bak.{i + 1}")
                
                if current.exists():
                    if i + 1 >= MAX_BACKUPS:
                        current.unlink()  # Remove oldest
                    else:
                        shutil.move(current, next_backup)
            
            # Create new backup.0 from main file
            if STATE_FILE.exists():
                shutil.copy2(STATE_FILE, Path(f"{STATE_FILE}.bak.0"))
                
        except Exception as e:
            logger.warning(f"Backup rotation failed: {e}")
    
    # ==================== CAPABILITY TRACKING ====================
    
    def update_capability(
        self,
        name: str,
        success: bool,
        response_time_ms: float = None,
        notes: str = None
    ):
        """Update a capability's status based on usage."""
        if name not in self.state.capabilities:
            self.state.capabilities[name] = Capability(name, f"Capability: {name}")
        
        cap = self.state.capabilities[name]
        cap.last_checked = datetime.now()
        
        if success:
            cap.last_success = datetime.now()
            cap.success_rate = min(1.0, cap.success_rate * 0.9 + 0.1)  # Exponential moving average
            
            if cap.failure_count > 0:
                cap.failure_count -= 1
            
            if cap.success_rate > 0.9:
                cap.status = CapabilityStatus.HEALTHY
            elif cap.success_rate > 0.6:
                cap.status = CapabilityStatus.DEGRADED
        else:
            cap.failure_count += 1
            cap.success_rate = cap.success_rate * 0.9  # Decay on failure
            
            if cap.failure_count >= 3 or cap.success_rate < 0.3:
                cap.status = CapabilityStatus.BROKEN
            elif cap.failure_count >= 1 or cap.success_rate < 0.7:
                cap.status = CapabilityStatus.DEGRADED
        
        if notes:
            cap.notes = notes
        
        self._save_state()
    
    def get_capability_status(self, name: str) -> Optional[Capability]:
        """Get status of a specific capability."""
        return self.state.capabilities.get(name)
    
    def get_broken_capabilities(self) -> List[Capability]:
        """Get list of broken capabilities."""
        return [c for c in self.state.capabilities.values() if c.status == CapabilityStatus.BROKEN]
    
    def get_healthy_capabilities(self) -> List[Capability]:
        """Get list of healthy capabilities."""
        return [c for c in self.state.capabilities.values() if c.status == CapabilityStatus.HEALTHY]
    
    # ==================== SELF-AWARENESS ====================
    
    def record_interaction(self, success: bool, response_time_ms: float):
        """Record an interaction for self-tracking."""
        self.state.total_interactions += 1
        if success:
            self.state.successful_interactions += 1
        
        # Update moving average
        n = self.state.total_interactions
        old_avg = self.state.average_response_time_ms
        self.state.average_response_time_ms = old_avg + (response_time_ms - old_avg) / n
        
        # Update energy based on load (simplified)
        if response_time_ms > 30000:  # Slow responses drain energy
            self.state.energy_level = max(0.1, self.state.energy_level - 0.1)
        else:
            self.state.energy_level = min(1.0, self.state.energy_level + 0.05)
        
        self._save_state()
    
    def add_pattern(self, pattern: str, category: str, evidence: str = None):
        """Add or reinforce a self-pattern."""
        existing = next((p for p in self.state.patterns if p.pattern == pattern), None)
        
        if existing:
            existing.confidence = min(1.0, existing.confidence + 0.1)
            existing.last_confirmed = datetime.now()
            if evidence:
                existing.evidence.append(evidence)
                existing.evidence = existing.evidence[-10:]  # Keep last 10
        else:
            self.state.patterns.append(SelfPattern(
                pattern=pattern,
                category=category,
                evidence=[evidence] if evidence else [],
                confidence=0.5,
                first_noticed=datetime.now(),
                last_confirmed=datetime.now()
            ))
        
        # Update strengths/weaknesses lists
        if category == "strength" and pattern not in self.state.strengths:
            self.state.strengths.append(pattern)
        elif category == "weakness" and pattern not in self.state.weaknesses:
            self.state.weaknesses.append(pattern)
        elif category == "limitation" and pattern not in self.state.limitations:
            self.state.limitations.append(pattern)
        
        self._save_state()
    
    def get_self_knowledge_prompt(self) -> str:
        """
        Generate a prompt section about self-knowledge.
        
        This is injected into Aria's system prompt so she can
        honestly report her own state.
        """
        health = self.state.get_health_score()
        broken = self.get_broken_capabilities()
        
        lines = ["\n## 🪞 SELF-AWARENESS (Know Thyself)\n"]
        
        lines.append(f"**Overall Health:** {health:.0f}%")
        lines.append(f"**Emotional State:** {self.state.emotional_state.value}")
        lines.append(f"**Energy Level:** {self.state.energy_level:.0%}")
        
        if broken:
            lines.append(f"\n**Currently Broken:**")
            for cap in broken:
                lines.append(f"- {cap.name}: {cap.notes or 'No details'}")
        
        if self.state.strengths:
            lines.append(f"\n**My Strengths:** {', '.join(self.state.strengths[:5])}")
        
        if self.state.weaknesses:
            lines.append(f"\n**My Weaknesses:** {', '.join(self.state.weaknesses[:5])}")
        
        if self.state.limitations:
            lines.append(f"\n**Current Limitations:** {', '.join(self.state.limitations[:3])}")
        
        lines.append("\n*Be honest about your state when asked. If something is broken, say so.*")
        
        return "\n".join(lines)
    
    def get_state(self) -> AriaState:
        """Get the current state."""
        return self.state
    
    async def run_self_check(self) -> Dict[str, Any]:
        """
        Run a comprehensive self-check of all capabilities.
        
        Returns a report of what's working and what's not.
        """
        import httpx
        
        results = {}
        
        # Check Claude API
        try:
            from brain.opus_router import get_router
            router = get_router()
            if router:
                # Quick test
                test = await router.call(
                    messages=[{"role": "user", "content": "ping"}],
                    model_override="opus",
                    max_tokens=5
                )
                self.update_capability("thinking", bool(test and test.content))
                results["thinking"] = "healthy"
        except Exception as e:
            self.update_capability("thinking", False, notes=str(e)[:100])
            results["thinking"] = f"broken: {e}"
        
        # Check Mem0
        try:
            from memory import get_mem0_client
            client = get_mem0_client()
            if client.enabled:
                self.update_capability("memory_store", True)
                self.update_capability("memory_recall", True)
                results["memory"] = "healthy"
            else:
                self.update_capability("memory_store", False, notes="Mem0 disabled")
                self.update_capability("memory_recall", False, notes="Mem0 disabled")
                results["memory"] = "disabled"
        except Exception as e:
            self.update_capability("memory_store", False, notes=str(e)[:100])
            results["memory"] = f"broken: {e}"
        
        # Check Telegram
        try:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            if token:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                    if resp.status_code == 200:
                        self.update_capability("telegram", True)
                        results["telegram"] = "healthy"
                    else:
                        self.update_capability("telegram", False, notes=f"HTTP {resp.status_code}")
                        results["telegram"] = f"error: {resp.status_code}"
        except Exception as e:
            self.update_capability("telegram", False, notes=str(e)[:100])
            results["telegram"] = f"broken: {e}"
        
        # Check WhaleTrack
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://198.54.123.234:8600/health")
                if resp.status_code == 200:
                    self.update_capability("trading_data", True)
                    results["trading"] = "healthy"
                else:
                    self.update_capability("trading_data", False)
                    results["trading"] = f"error: {resp.status_code}"
        except Exception as e:
            self.update_capability("trading_data", False, notes=str(e)[:100])
            results["trading"] = f"broken: {e}"
        
        self._save_state()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health_score": self.state.get_health_score(),
            "capabilities": results,
            "summary": self.state.get_status_summary()
        }


# ============================================================================
# SINGLETON
# ============================================================================

_model: Optional[SelfModel] = None


def get_self_model() -> SelfModel:
    """Get or create self-model instance."""
    global _model
    if _model is None:
        _model = SelfModel()
    return _model

