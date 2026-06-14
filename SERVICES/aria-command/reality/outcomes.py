"""
Outcome Tracking - Measures real-world impact of code changes.

Tracks metrics before and after changes to learn what works.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger("aria.reality.outcomes")


@dataclass
class MetricSnapshot:
    """A snapshot of metrics at a point in time."""
    timestamp: datetime
    
    # Performance metrics
    response_time_ms: Optional[float] = None
    error_rate: Optional[float] = None
    throughput: Optional[float] = None
    
    # Resource metrics
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    
    # Business metrics
    active_users: Optional[int] = None
    revenue: Optional[float] = None
    
    # Custom metrics
    custom: Dict[str, float] = field(default_factory=dict)


@dataclass
class ChangeOutcome:
    """Outcome of a code change."""
    change_id: str
    change_type: str
    description: str
    files_modified: List[str]
    
    # Timing
    deployed_at: datetime
    measured_at: Optional[datetime] = None
    
    # Metrics
    before: Optional[MetricSnapshot] = None
    after: Optional[MetricSnapshot] = None
    
    # Analysis
    impact_score: float = 0.0  # -1 to 1 (negative = worse, positive = better)
    confidence: float = 0.0  # How confident we are in the measurement
    
    # Insights
    insights: List[str] = field(default_factory=list)
    
    @property
    def is_positive(self) -> bool:
        """Check if the change had a positive impact."""
        return self.impact_score > 0
    
    @property
    def is_significant(self) -> bool:
        """Check if the impact is statistically significant."""
        return abs(self.impact_score) > 0.1 and self.confidence > 0.7


class OutcomeTracker:
    """
    Tracks outcomes of code changes to learn what works.
    
    Flow:
    1. Before change: snapshot metrics
    2. Apply change
    3. Wait stabilization period
    4. After change: snapshot metrics
    5. Analyze impact
    6. Learn from outcome
    """
    
    STABILIZATION_MINUTES = 15  # Wait time before measuring "after"
    
    def __init__(self, persistence_path: str = None):
        self.outcomes: Dict[str, ChangeOutcome] = {}
        self.pending_measurements: Dict[str, datetime] = {}  # change_id -> when to measure
        self.persistence_path = persistence_path or "/tmp/aria_outcomes.json"
        
        self._load_state()
    
    async def record_before(self, change_id: str, description: str, files: List[str]) -> MetricSnapshot:
        """
        Record metrics before a change.
        
        Call this before deploying a change.
        """
        snapshot = await self._take_snapshot()
        
        outcome = ChangeOutcome(
            change_id=change_id,
            change_type=self._infer_type(description),
            description=description,
            files_modified=files,
            deployed_at=datetime.now(),
            before=snapshot
        )
        
        self.outcomes[change_id] = outcome
        self._save_state()
        
        logger.info(f"Recorded before metrics for change {change_id}")
        return snapshot
    
    async def schedule_after_measurement(self, change_id: str):
        """
        Schedule the "after" measurement.
        
        Call this after deploying a change.
        """
        measure_at = datetime.now() + timedelta(minutes=self.STABILIZATION_MINUTES)
        self.pending_measurements[change_id] = measure_at
        
        logger.info(f"Scheduled after measurement for {change_id} at {measure_at}")
    
    async def record_after(self, change_id: str) -> Optional[ChangeOutcome]:
        """
        Record metrics after a change and analyze impact.
        
        Can be called manually or automatically after stabilization.
        """
        if change_id not in self.outcomes:
            logger.warning(f"No before metrics for change {change_id}")
            return None
        
        outcome = self.outcomes[change_id]
        outcome.after = await self._take_snapshot()
        outcome.measured_at = datetime.now()
        
        # Analyze impact
        self._analyze_impact(outcome)
        
        # Remove from pending
        if change_id in self.pending_measurements:
            del self.pending_measurements[change_id]
        
        self._save_state()
        
        logger.info(f"Recorded outcome for {change_id}: impact={outcome.impact_score:.2f}")
        return outcome
    
    async def check_pending_measurements(self):
        """
        Check and process any pending measurements.
        
        Call this periodically from a background task.
        """
        now = datetime.now()
        completed = []
        
        for change_id, measure_at in self.pending_measurements.items():
            if now >= measure_at:
                await self.record_after(change_id)
                completed.append(change_id)
        
        for change_id in completed:
            if change_id in self.pending_measurements:
                del self.pending_measurements[change_id]
    
    async def _take_snapshot(self) -> MetricSnapshot:
        """Take a snapshot of current metrics."""
        snapshot = MetricSnapshot(timestamp=datetime.now())
        
        # Performance metrics
        try:
            import httpx
            import time
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                start = time.time()
                response = await client.get("http://localhost:8750/health")
                snapshot.response_time_ms = (time.time() - start) * 1000
        except:
            pass
        
        # Resource metrics
        try:
            import psutil
            snapshot.cpu_percent = psutil.cpu_percent(interval=0.1)
            snapshot.memory_percent = psutil.virtual_memory().percent
        except:
            pass
        
        return snapshot
    
    def _analyze_impact(self, outcome: ChangeOutcome):
        """Analyze the impact of a change."""
        if not outcome.before or not outcome.after:
            outcome.confidence = 0.0
            return
        
        impacts = []
        weights = []
        insights = []
        
        # Response time impact
        if outcome.before.response_time_ms and outcome.after.response_time_ms:
            before_rt = outcome.before.response_time_ms
            after_rt = outcome.after.response_time_ms
            
            if before_rt > 0:
                change = (before_rt - after_rt) / before_rt  # Positive = improvement
                impacts.append(change)
                weights.append(0.3)
                
                if change > 0.1:
                    insights.append(f"Response time improved by {change:.1%}")
                elif change < -0.1:
                    insights.append(f"Response time degraded by {abs(change):.1%}")
        
        # Memory impact
        if outcome.before.memory_percent and outcome.after.memory_percent:
            before_mem = outcome.before.memory_percent
            after_mem = outcome.after.memory_percent
            
            change = (before_mem - after_mem) / 100  # Positive = less memory
            impacts.append(change)
            weights.append(0.2)
            
            if abs(after_mem - before_mem) > 5:
                if change > 0:
                    insights.append(f"Memory usage decreased by {before_mem - after_mem:.1f}%")
                else:
                    insights.append(f"Memory usage increased by {after_mem - before_mem:.1f}%")
        
        # CPU impact
        if outcome.before.cpu_percent and outcome.after.cpu_percent:
            before_cpu = outcome.before.cpu_percent
            after_cpu = outcome.after.cpu_percent
            
            change = (before_cpu - after_cpu) / 100  # Positive = less CPU
            impacts.append(change)
            weights.append(0.2)
        
        # Calculate weighted impact
        if impacts and weights:
            total_weight = sum(weights)
            outcome.impact_score = sum(i * w for i, w in zip(impacts, weights)) / total_weight
            outcome.confidence = min(1.0, total_weight / 0.7)  # Confidence based on available metrics
        else:
            outcome.impact_score = 0.0
            outcome.confidence = 0.0
        
        outcome.insights = insights
    
    def _infer_type(self, description: str) -> str:
        """Infer change type from description."""
        desc_lower = description.lower()
        
        if "fix" in desc_lower or "bug" in desc_lower:
            return "bug_fix"
        if "optimize" in desc_lower or "performance" in desc_lower:
            return "optimization"
        if "feature" in desc_lower or "add" in desc_lower:
            return "feature"
        if "refactor" in desc_lower:
            return "refactor"
        if "security" in desc_lower:
            return "security"
        
        return "change"
    
    def get_success_rate_by_type(self) -> Dict[str, float]:
        """Get success rate grouped by change type."""
        by_type: Dict[str, List[ChangeOutcome]] = {}
        
        for outcome in self.outcomes.values():
            if outcome.is_significant:
                if outcome.change_type not in by_type:
                    by_type[outcome.change_type] = []
                by_type[outcome.change_type].append(outcome)
        
        rates = {}
        for change_type, outcomes in by_type.items():
            if outcomes:
                positive = sum(1 for o in outcomes if o.is_positive)
                rates[change_type] = positive / len(outcomes)
        
        return rates
    
    def get_recent_outcomes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent outcomes."""
        sorted_outcomes = sorted(
            self.outcomes.values(),
            key=lambda o: o.deployed_at,
            reverse=True
        )
        
        return [
            {
                "change_id": o.change_id,
                "type": o.change_type,
                "description": o.description[:100],
                "impact_score": o.impact_score,
                "confidence": o.confidence,
                "is_positive": o.is_positive,
                "insights": o.insights,
                "deployed_at": o.deployed_at.isoformat()
            }
            for o in sorted_outcomes[:limit]
        ]
    
    def _save_state(self):
        """Persist outcome state."""
        try:
            state = {
                "outcomes": {
                    change_id: {
                        "change_id": o.change_id,
                        "change_type": o.change_type,
                        "description": o.description,
                        "files_modified": o.files_modified,
                        "deployed_at": o.deployed_at.isoformat(),
                        "impact_score": o.impact_score,
                        "confidence": o.confidence,
                        "insights": o.insights
                    }
                    for change_id, o in self.outcomes.items()
                },
                "saved_at": datetime.now().isoformat()
            }
            
            with open(self.persistence_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save outcome state: {e}")
    
    def _load_state(self):
        """Load outcome state."""
        try:
            if not Path(self.persistence_path).exists():
                return
            
            with open(self.persistence_path, 'r') as f:
                state = json.load(f)
            
            for change_id, data in state.get("outcomes", {}).items():
                self.outcomes[change_id] = ChangeOutcome(
                    change_id=data["change_id"],
                    change_type=data["change_type"],
                    description=data["description"],
                    files_modified=data["files_modified"],
                    deployed_at=datetime.fromisoformat(data["deployed_at"]),
                    impact_score=data.get("impact_score", 0.0),
                    confidence=data.get("confidence", 0.0),
                    insights=data.get("insights", [])
                )
            
            logger.info(f"Loaded {len(self.outcomes)} outcomes")
        except Exception as e:
            logger.error(f"Failed to load outcome state: {e}")


# Singleton instance
_tracker: Optional[OutcomeTracker] = None

def get_outcome_tracker() -> OutcomeTracker:
    """Get or create outcome tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = OutcomeTracker()
    return _tracker


