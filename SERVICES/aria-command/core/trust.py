"""
Trust System - Learns from user approvals to build trust over time.

Tracks approval/rejection patterns and adjusts autonomy accordingly.
"""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("aria.core.trust")


class TrustDomain(Enum):
    """Domains where trust is tracked independently."""
    CODE = "code"             # Code changes
    DEPLOY = "deploy"         # Deployments
    TRADE = "trade"           # Trading decisions
    SERVER = "server"         # Server operations
    CONFIG = "config"         # Configuration changes
    GENERAL = "general"       # Everything else


@dataclass
class TrustEvent:
    """A trust-related event (approval or rejection)."""
    timestamp: datetime
    domain: TrustDomain
    action_type: str
    was_approved: bool
    confidence_at_time: float
    user_modified: bool = False  # Did user modify before approving?
    execution_success: Optional[bool] = None  # Did execution succeed?


@dataclass
class DomainTrust:
    """Trust level for a specific domain."""
    domain: TrustDomain
    level: float = 0.5  # 0.0 - 1.0
    total_actions: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    modified_count: int = 0
    success_after_approval: int = 0
    failure_after_approval: int = 0
    last_update: datetime = field(default_factory=datetime.now)
    
    @property
    def approval_rate(self) -> float:
        """Calculate approval rate."""
        if self.total_actions == 0:
            return 0.5
        return self.approved_count / self.total_actions
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate after approval."""
        total = self.success_after_approval + self.failure_after_approval
        if total == 0:
            return 1.0
        return self.success_after_approval / total


class TrustSystem:
    """
    Builds trust over time based on user behavior.
    
    Key behaviors tracked:
    - Approvals (builds trust)
    - Rejections (reduces trust)
    - Modifications before approval (slight trust reduction)
    - Execution success/failure (affects future trust)
    """
    
    # Trust adjustment parameters
    APPROVAL_BOOST = 0.02      # +2% per approval
    REJECTION_PENALTY = 0.05   # -5% per rejection
    MODIFY_PENALTY = 0.01      # -1% if user modified
    SUCCESS_BOOST = 0.01       # +1% after successful execution
    FAILURE_PENALTY = 0.03     # -3% after failed execution
    
    # Trust decay (without interaction)
    DECAY_RATE = 0.001         # 0.1% per day of inactivity
    DECAY_FLOOR = 0.3          # Minimum trust level
    
    # Trust bounds
    MIN_TRUST = 0.1
    MAX_TRUST = 0.95
    DEFAULT_TRUST = 0.5
    
    def __init__(self, persistence_path: str = None):
        self.domains: Dict[TrustDomain, DomainTrust] = {}
        self.event_history: List[TrustEvent] = []
        self.persistence_path = persistence_path or "/tmp/aria_trust.json"
        
        # Initialize all domains
        for domain in TrustDomain:
            self.domains[domain] = DomainTrust(domain=domain, level=self.DEFAULT_TRUST)
        
        # Load persisted state
        self._load_state()
    
    def get_trust(self, domain: TrustDomain = TrustDomain.GENERAL) -> float:
        """Get current trust level for a domain."""
        if domain not in self.domains:
            return self.DEFAULT_TRUST
        
        # Apply decay
        trust = self.domains[domain]
        self._apply_decay(trust)
        
        return trust.level
    
    def record_approval(
        self,
        domain: TrustDomain,
        action_type: str,
        confidence_at_time: float,
        user_modified: bool = False
    ):
        """Record a user approval."""
        trust = self.domains.get(domain, DomainTrust(domain=domain))
        
        # Update counters
        trust.total_actions += 1
        trust.approved_count += 1
        if user_modified:
            trust.modified_count += 1
        
        # Adjust trust
        adjustment = self.APPROVAL_BOOST
        if user_modified:
            adjustment -= self.MODIFY_PENALTY
        
        trust.level = min(self.MAX_TRUST, trust.level + adjustment)
        trust.last_update = datetime.now()
        
        # Record event
        event = TrustEvent(
            timestamp=datetime.now(),
            domain=domain,
            action_type=action_type,
            was_approved=True,
            confidence_at_time=confidence_at_time,
            user_modified=user_modified
        )
        self.event_history.append(event)
        
        self.domains[domain] = trust
        self._save_state()
        
        logger.info(f"Trust updated for {domain.value}: {trust.level:.2%} (+approval)")
    
    def record_rejection(
        self,
        domain: TrustDomain,
        action_type: str,
        confidence_at_time: float
    ):
        """Record a user rejection."""
        trust = self.domains.get(domain, DomainTrust(domain=domain))
        
        # Update counters
        trust.total_actions += 1
        trust.rejected_count += 1
        
        # Adjust trust
        trust.level = max(self.MIN_TRUST, trust.level - self.REJECTION_PENALTY)
        trust.last_update = datetime.now()
        
        # Record event
        event = TrustEvent(
            timestamp=datetime.now(),
            domain=domain,
            action_type=action_type,
            was_approved=False,
            confidence_at_time=confidence_at_time
        )
        self.event_history.append(event)
        
        self.domains[domain] = trust
        self._save_state()
        
        logger.info(f"Trust updated for {domain.value}: {trust.level:.2%} (-rejection)")
    
    def record_execution_result(
        self,
        domain: TrustDomain,
        success: bool
    ):
        """Record the result of an executed action."""
        trust = self.domains.get(domain)
        if not trust:
            return
        
        if success:
            trust.success_after_approval += 1
            trust.level = min(self.MAX_TRUST, trust.level + self.SUCCESS_BOOST)
        else:
            trust.failure_after_approval += 1
            trust.level = max(self.MIN_TRUST, trust.level - self.FAILURE_PENALTY)
        
        trust.last_update = datetime.now()
        self._save_state()
        
        logger.info(f"Trust updated for {domain.value}: {trust.level:.2%} ({'success' if success else 'failure'})")
    
    def _apply_decay(self, trust: DomainTrust):
        """Apply trust decay based on time since last interaction."""
        if not trust.last_update:
            return
        
        days_inactive = (datetime.now() - trust.last_update).days
        if days_inactive > 0:
            decay = self.DECAY_RATE * days_inactive
            trust.level = max(self.DECAY_FLOOR, trust.level - decay)
    
    def _save_state(self):
        """Persist trust state to disk."""
        try:
            state = {
                "domains": {
                    d.value: {
                        "level": self.domains[d].level,
                        "total_actions": self.domains[d].total_actions,
                        "approved_count": self.domains[d].approved_count,
                        "rejected_count": self.domains[d].rejected_count,
                        "modified_count": self.domains[d].modified_count,
                        "success_after_approval": self.domains[d].success_after_approval,
                        "failure_after_approval": self.domains[d].failure_after_approval,
                        "last_update": self.domains[d].last_update.isoformat()
                    }
                    for d in self.domains
                },
                "saved_at": datetime.now().isoformat()
            }
            
            with open(self.persistence_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save trust state: {e}")
    
    def _load_state(self):
        """Load trust state from disk."""
        try:
            if not Path(self.persistence_path).exists():
                return
            
            with open(self.persistence_path, 'r') as f:
                state = json.load(f)
            
            for domain_name, data in state.get("domains", {}).items():
                try:
                    domain = TrustDomain(domain_name)
                    self.domains[domain] = DomainTrust(
                        domain=domain,
                        level=data.get("level", self.DEFAULT_TRUST),
                        total_actions=data.get("total_actions", 0),
                        approved_count=data.get("approved_count", 0),
                        rejected_count=data.get("rejected_count", 0),
                        modified_count=data.get("modified_count", 0),
                        success_after_approval=data.get("success_after_approval", 0),
                        failure_after_approval=data.get("failure_after_approval", 0),
                        last_update=datetime.fromisoformat(data.get("last_update", datetime.now().isoformat()))
                    )
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to load domain {domain_name}: {e}")
            
            logger.info(f"Loaded trust state from {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to load trust state: {e}")
    
    def get_all_trust_levels(self) -> Dict[str, float]:
        """Get all trust levels."""
        return {d.value: self.get_trust(d) for d in TrustDomain}
    
    def get_domain_stats(self, domain: TrustDomain) -> Dict[str, Any]:
        """Get detailed stats for a domain."""
        trust = self.domains.get(domain)
        if not trust:
            return {"error": "Domain not found"}
        
        return {
            "domain": domain.value,
            "level": trust.level,
            "total_actions": trust.total_actions,
            "approval_rate": trust.approval_rate,
            "success_rate": trust.success_rate,
            "approved": trust.approved_count,
            "rejected": trust.rejected_count,
            "modified": trust.modified_count,
            "last_update": trust.last_update.isoformat()
        }


# Singleton instance
_trust_system: Optional[TrustSystem] = None

def get_trust_system() -> TrustSystem:
    """Get or create trust system instance."""
    global _trust_system
    if _trust_system is None:
        _trust_system = TrustSystem()
    return _trust_system

def get_trust_levels() -> Dict[str, Any]:
    """Get all trust levels (for API)."""
    system = get_trust_system()
    return {
        "levels": system.get_all_trust_levels(),
        "details": {
            domain.value: system.get_domain_stats(domain)
            for domain in TrustDomain
        }
    }

def get_trust_for_task(task_type: str) -> float:
    """Get trust level appropriate for a task type."""
    system = get_trust_system()
    
    # Map task types to domains
    type_to_domain = {
        "code_change": TrustDomain.CODE,
        "new_feature": TrustDomain.CODE,
        "bug_fix": TrustDomain.CODE,
        "refactor": TrustDomain.CODE,
        "deploy": TrustDomain.DEPLOY,
        "trade": TrustDomain.TRADE,
        "trading_signal": TrustDomain.TRADE,
        "server": TrustDomain.SERVER,
        "restart": TrustDomain.SERVER,
        "config": TrustDomain.CONFIG
    }
    
    domain = type_to_domain.get(task_type.lower(), TrustDomain.GENERAL)
    return system.get_trust(domain)


