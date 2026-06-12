"""
Opportunity Queue - Prioritized list of improvements Aria can make.

Ranks opportunities by value/effort ratio and tracks execution.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .sensors import SensorFinding, SensorPriority, SensorCategory

logger = logging.getLogger("aria.proactive.opportunity")


class OpportunityType(Enum):
    """Types of opportunities."""
    BUG_FIX = "bug_fix"
    OPTIMIZATION = "optimization"
    FEATURE = "feature"
    SECURITY = "security"
    CLEANUP = "cleanup"
    DOCUMENTATION = "documentation"


class Effort(Enum):
    """Effort levels."""
    TRIVIAL = 1      # < 5 minutes
    SMALL = 2        # 5-30 minutes
    MEDIUM = 3       # 30 min - 2 hours
    LARGE = 4        # 2+ hours


class Impact(Enum):
    """Impact levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Opportunity:
    """A potential improvement opportunity."""
    id: str
    type: OpportunityType
    title: str
    description: str
    
    # Scoring
    effort: Effort
    impact: Impact
    confidence: float  # How sure we are this is valuable
    
    # Execution
    auto_executable: bool
    execution_plan: Optional[str] = None
    
    # Source
    source: str = "sensor"  # "sensor", "user", "proactive"
    sensor_finding: Optional[SensorFinding] = None
    
    # Context
    file_path: Optional[str] = None
    related_files: List[str] = field(default_factory=list)
    
    # Status
    status: str = "pending"  # "pending", "in_progress", "completed", "rejected", "deferred"
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def value_score(self) -> float:
        """Calculate value score (impact / effort)."""
        return (self.impact.value * self.confidence) / self.effort.value
    
    @property
    def priority_score(self) -> float:
        """Calculate priority score for sorting."""
        # Factor in age (older items get slight boost)
        age_days = (datetime.now() - self.created_at).days
        age_factor = min(1.2, 1.0 + (age_days * 0.02))
        
        # Auto-executable gets a boost
        auto_factor = 1.3 if self.auto_executable else 1.0
        
        return self.value_score * age_factor * auto_factor


class OpportunityQueue:
    """
    Manages the queue of improvement opportunities.
    
    Prioritizes by value/effort ratio, handles deduplication,
    and tracks completion.
    """
    
    def __init__(self, persistence_path: str = None):
        self.opportunities: Dict[str, Opportunity] = {}
        self.completed: List[Opportunity] = []
        self.persistence_path = persistence_path or "/tmp/aria_opportunities.json"
        
        self._load_state()
    
    def add(self, opportunity: Opportunity) -> bool:
        """Add an opportunity to the queue."""
        # Check for duplicates
        if self._is_duplicate(opportunity):
            logger.debug(f"Duplicate opportunity: {opportunity.title}")
            return False
        
        self.opportunities[opportunity.id] = opportunity
        self._save_state()
        
        logger.info(f"Added opportunity: {opportunity.title} (score: {opportunity.value_score:.2f})")
        return True
    
    def add_from_finding(self, finding: SensorFinding) -> Optional[Opportunity]:
        """Create and add an opportunity from a sensor finding."""
        # Map sensor priority to impact
        priority_to_impact = {
            SensorPriority.LOW: Impact.LOW,
            SensorPriority.MEDIUM: Impact.MEDIUM,
            SensorPriority.HIGH: Impact.HIGH,
            SensorPriority.CRITICAL: Impact.CRITICAL
        }
        
        # Determine type based on category
        category_to_type = {
            SensorCategory.CODE: OpportunityType.CLEANUP,
            SensorCategory.PERFORMANCE: OpportunityType.OPTIMIZATION,
            SensorCategory.BUSINESS: OpportunityType.FEATURE,
            SensorCategory.INFRASTRUCTURE: OpportunityType.BUG_FIX,
            SensorCategory.SECURITY: OpportunityType.SECURITY
        }
        
        opp_type = category_to_type.get(finding.category, OpportunityType.CLEANUP)
        impact = priority_to_impact.get(finding.priority, Impact.MEDIUM)
        
        # Generate unique ID
        import hashlib
        opp_id = hashlib.md5(f"{finding.title}:{finding.file_path}:{finding.timestamp}".encode()).hexdigest()[:12]
        
        opportunity = Opportunity(
            id=opp_id,
            type=opp_type,
            title=finding.title,
            description=finding.description,
            effort=Effort.SMALL if finding.auto_fixable else Effort.MEDIUM,
            impact=impact,
            confidence=finding.confidence,
            auto_executable=finding.auto_fixable,
            execution_plan=finding.suggested_action,
            source="sensor",
            sensor_finding=finding,
            file_path=finding.file_path
        )
        
        if self.add(opportunity):
            return opportunity
        return None
    
    def get_top(self, n: int = 10) -> List[Opportunity]:
        """Get top N opportunities by priority score."""
        pending = [o for o in self.opportunities.values() if o.status == "pending"]
        sorted_opps = sorted(pending, key=lambda o: o.priority_score, reverse=True)
        return sorted_opps[:n]
    
    def get_auto_executable(self) -> List[Opportunity]:
        """Get opportunities that can be auto-executed."""
        return [o for o in self.opportunities.values() 
                if o.status == "pending" and o.auto_executable]
    
    def get_by_type(self, opp_type: OpportunityType) -> List[Opportunity]:
        """Get opportunities of a specific type."""
        return [o for o in self.opportunities.values() 
                if o.type == opp_type and o.status == "pending"]
    
    def start(self, opp_id: str) -> bool:
        """Mark an opportunity as in progress."""
        if opp_id in self.opportunities:
            self.opportunities[opp_id].status = "in_progress"
            self._save_state()
            return True
        return False
    
    def complete(self, opp_id: str, success: bool = True) -> bool:
        """Mark an opportunity as completed."""
        if opp_id in self.opportunities:
            opp = self.opportunities[opp_id]
            opp.status = "completed" if success else "failed"
            opp.completed_at = datetime.now()
            
            self.completed.append(opp)
            del self.opportunities[opp_id]
            
            self._save_state()
            return True
        return False
    
    def defer(self, opp_id: str) -> bool:
        """Defer an opportunity for later."""
        if opp_id in self.opportunities:
            self.opportunities[opp_id].status = "deferred"
            self._save_state()
            return True
        return False
    
    def reject(self, opp_id: str) -> bool:
        """Reject an opportunity."""
        if opp_id in self.opportunities:
            opp = self.opportunities[opp_id]
            opp.status = "rejected"
            
            self.completed.append(opp)
            del self.opportunities[opp_id]
            
            self._save_state()
            return True
        return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get queue summary."""
        pending = [o for o in self.opportunities.values() if o.status == "pending"]
        
        return {
            "total_pending": len(pending),
            "auto_executable": len([o for o in pending if o.auto_executable]),
            "by_type": {
                t.value: len([o for o in pending if o.type == t])
                for t in OpportunityType
            },
            "by_impact": {
                i.name: len([o for o in pending if o.impact == i])
                for i in Impact
            },
            "total_completed": len(self.completed),
            "top_opportunity": pending[0].title if pending else None
        }
    
    def _is_duplicate(self, opportunity: Opportunity) -> bool:
        """Check if an opportunity is a duplicate."""
        for existing in self.opportunities.values():
            # Same file and similar title
            if (existing.file_path == opportunity.file_path and
                existing.title == opportunity.title):
                return True
        return False
    
    def _save_state(self):
        """Persist queue state."""
        try:
            state = {
                "opportunities": {
                    opp_id: {
                        "id": opp.id,
                        "type": opp.type.value,
                        "title": opp.title,
                        "description": opp.description,
                        "effort": opp.effort.value,
                        "impact": opp.impact.value,
                        "confidence": opp.confidence,
                        "auto_executable": opp.auto_executable,
                        "execution_plan": opp.execution_plan,
                        "file_path": opp.file_path,
                        "status": opp.status,
                        "created_at": opp.created_at.isoformat()
                    }
                    for opp_id, opp in self.opportunities.items()
                },
                "saved_at": datetime.now().isoformat()
            }
            
            with open(self.persistence_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save opportunity state: {e}")
    
    def _load_state(self):
        """Load queue state."""
        try:
            if not Path(self.persistence_path).exists():
                return
            
            with open(self.persistence_path, 'r') as f:
                state = json.load(f)
            
            for opp_id, data in state.get("opportunities", {}).items():
                try:
                    opp = Opportunity(
                        id=data["id"],
                        type=OpportunityType(data["type"]),
                        title=data["title"],
                        description=data["description"],
                        effort=Effort(data["effort"]),
                        impact=Impact(data["impact"]),
                        confidence=data["confidence"],
                        auto_executable=data["auto_executable"],
                        execution_plan=data.get("execution_plan"),
                        file_path=data.get("file_path"),
                        status=data["status"],
                        created_at=datetime.fromisoformat(data["created_at"])
                    )
                    self.opportunities[opp_id] = opp
                except Exception as e:
                    logger.warning(f"Failed to load opportunity {opp_id}: {e}")
            
            logger.info(f"Loaded {len(self.opportunities)} opportunities")
        except Exception as e:
            logger.error(f"Failed to load opportunity state: {e}")


# Singleton instance
_queue: Optional[OpportunityQueue] = None

def get_opportunity_queue() -> OpportunityQueue:
    """Get or create opportunity queue instance."""
    global _queue
    if _queue is None:
        _queue = OpportunityQueue()
    return _queue


