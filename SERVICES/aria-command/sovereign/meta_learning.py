"""
Meta-Learning System - Aria improves her own processes.

Tracks which agent combinations work best, learns confidence thresholds,
optimizes prompts based on outcomes, and evolves decision-making.
"""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("aria.sovereign.meta_learning")


@dataclass
class LearningEvent:
    """A learning event from a task execution."""
    timestamp: datetime
    task_type: str
    
    # What happened
    agents_used: List[str]
    confidence_at_decision: float
    tier_assigned: int
    
    # Outcome
    was_approved: bool
    execution_success: bool
    
    # Feedback
    user_modified: bool = False
    user_feedback: Optional[str] = None


@dataclass
class AgentPerformance:
    """Performance metrics for an agent."""
    agent_name: str
    total_evaluations: int = 0
    total_executions: int = 0
    
    successful_evaluations: int = 0
    successful_executions: int = 0
    
    avg_confidence: float = 0.0
    avg_execution_time_ms: float = 0.0
    
    @property
    def evaluation_accuracy(self) -> float:
        """How often the agent's recommendations were followed."""
        if self.total_evaluations == 0:
            return 0.5
        return self.successful_evaluations / self.total_evaluations
    
    @property
    def execution_success_rate(self) -> float:
        """Success rate of executions."""
        if self.total_executions == 0:
            return 1.0
        return self.successful_executions / self.total_executions


@dataclass
class ThresholdLearning:
    """Learning about confidence thresholds."""
    task_type: str
    
    # Threshold performance
    threshold_outcomes: Dict[float, List[bool]] = field(default_factory=dict)
    
    # Optimal threshold
    optimal_threshold: float = 0.7
    threshold_confidence: float = 0.5
    
    def record_outcome(self, confidence: float, success: bool):
        """Record an outcome at a given confidence level."""
        # Round to nearest 0.05
        bucket = round(confidence * 20) / 20
        
        if bucket not in self.threshold_outcomes:
            self.threshold_outcomes[bucket] = []
        
        self.threshold_outcomes[bucket].append(success)
        
        # Recalculate optimal threshold
        self._calculate_optimal()
    
    def _calculate_optimal(self):
        """Calculate the optimal threshold based on outcomes."""
        best_threshold = 0.7
        best_score = 0.0
        
        for threshold in sorted(self.threshold_outcomes.keys(), reverse=True):
            outcomes = self.threshold_outcomes[threshold]
            if len(outcomes) < 3:
                continue
            
            success_rate = sum(outcomes) / len(outcomes)
            
            # Score combines success rate and threshold height
            # Higher threshold = more selective = better
            score = success_rate * 0.7 + (threshold / 1.0) * 0.3
            
            if score > best_score:
                best_score = score
                best_threshold = threshold
        
        self.optimal_threshold = best_threshold
        self.threshold_confidence = min(1.0, sum(len(v) for v in self.threshold_outcomes.values()) / 20)


class MetaLearningSystem:
    """
    Learns from Aria's own performance to improve over time.
    
    Tracks:
    - Agent performance and accuracy
    - Optimal confidence thresholds
    - Task type patterns
    - User preferences
    """
    
    def __init__(self, persistence_path: str = None):
        self.events: List[LearningEvent] = []
        self.agent_performance: Dict[str, AgentPerformance] = {}
        self.threshold_learning: Dict[str, ThresholdLearning] = {}
        
        # Pattern learning
        self.task_patterns: Dict[str, Dict[str, Any]] = {}
        
        # Prompt optimization (stored learnings)
        self.prompt_learnings: List[str] = []
        
        self.persistence_path = persistence_path or "/tmp/aria_meta_learning.json"
        self._load_state()
    
    def record_event(
        self,
        task_type: str,
        agents_used: List[str],
        confidence: float,
        tier: int,
        was_approved: bool,
        success: bool,
        user_modified: bool = False,
        feedback: str = None
    ):
        """Record a learning event."""
        event = LearningEvent(
            timestamp=datetime.now(),
            task_type=task_type,
            agents_used=agents_used,
            confidence_at_decision=confidence,
            tier_assigned=tier,
            was_approved=was_approved,
            execution_success=success,
            user_modified=user_modified,
            user_feedback=feedback
        )
        
        self.events.append(event)
        
        # Update agent performance
        self._update_agent_performance(event)
        
        # Update threshold learning
        self._update_threshold_learning(event)
        
        # Update task patterns
        self._update_task_patterns(event)
        
        self._save_state()
    
    def _update_agent_performance(self, event: LearningEvent):
        """Update agent performance metrics."""
        for agent_name in event.agents_used:
            if agent_name not in self.agent_performance:
                self.agent_performance[agent_name] = AgentPerformance(agent_name=agent_name)
            
            perf = self.agent_performance[agent_name]
            perf.total_evaluations += 1
            
            if event.was_approved:
                perf.successful_evaluations += 1
            
            if event.execution_success:
                perf.total_executions += 1
                perf.successful_executions += 1
            elif event.was_approved:  # Approved but failed
                perf.total_executions += 1
            
            # Update running average confidence
            n = perf.total_evaluations
            perf.avg_confidence = (perf.avg_confidence * (n - 1) + event.confidence_at_decision) / n
    
    def _update_threshold_learning(self, event: LearningEvent):
        """Update threshold learning."""
        task_type = event.task_type
        
        if task_type not in self.threshold_learning:
            self.threshold_learning[task_type] = ThresholdLearning(task_type=task_type)
        
        # Record outcome
        success = event.was_approved and event.execution_success
        self.threshold_learning[task_type].record_outcome(
            event.confidence_at_decision,
            success
        )
    
    def _update_task_patterns(self, event: LearningEvent):
        """Learn patterns about task types."""
        task_type = event.task_type
        
        if task_type not in self.task_patterns:
            self.task_patterns[task_type] = {
                "count": 0,
                "avg_confidence": 0.0,
                "success_rate": 0.0,
                "common_agents": defaultdict(int),
                "best_agent_combo": []
            }
        
        pattern = self.task_patterns[task_type]
        pattern["count"] += 1
        
        # Update success rate
        n = pattern["count"]
        old_success = pattern["success_rate"]
        new_success = 1.0 if event.execution_success else 0.0
        pattern["success_rate"] = (old_success * (n - 1) + new_success) / n
        
        # Update confidence
        old_conf = pattern["avg_confidence"]
        pattern["avg_confidence"] = (old_conf * (n - 1) + event.confidence_at_decision) / n
        
        # Track agent combinations
        for agent in event.agents_used:
            pattern["common_agents"][agent] += 1
        
        # Update best combo if this was successful
        if event.execution_success:
            pattern["best_agent_combo"] = event.agents_used
    
    def get_optimal_threshold(self, task_type: str) -> float:
        """Get the optimal confidence threshold for a task type."""
        if task_type in self.threshold_learning:
            return self.threshold_learning[task_type].optimal_threshold
        return 0.7  # Default
    
    def get_recommended_agents(self, task_type: str) -> List[str]:
        """Get recommended agents for a task type."""
        if task_type in self.task_patterns:
            pattern = self.task_patterns[task_type]
            if pattern["best_agent_combo"]:
                return pattern["best_agent_combo"]
        
        return ["builder", "reviewer"]  # Default
    
    def get_agent_ranking(self) -> List[Dict[str, Any]]:
        """Get agents ranked by performance."""
        agents = list(self.agent_performance.values())
        
        # Score by success rate and accuracy
        def score(a: AgentPerformance) -> float:
            return a.execution_success_rate * 0.6 + a.evaluation_accuracy * 0.4
        
        agents.sort(key=score, reverse=True)
        
        return [
            {
                "name": a.agent_name,
                "score": score(a),
                "success_rate": a.execution_success_rate,
                "accuracy": a.evaluation_accuracy,
                "total_evaluations": a.total_evaluations
            }
            for a in agents
        ]
    
    def generate_insights(self) -> List[str]:
        """Generate insights from learning."""
        insights = []
        
        # Agent insights
        ranking = self.get_agent_ranking()
        if ranking:
            best = ranking[0]
            if best["total_evaluations"] >= 10:
                insights.append(f"Best performing agent: {best['name']} ({best['success_rate']:.0%} success)")
        
        # Threshold insights
        for task_type, learning in self.threshold_learning.items():
            if learning.threshold_confidence > 0.7:
                insights.append(
                    f"Optimal threshold for {task_type}: {learning.optimal_threshold:.0%} "
                    f"(confidence: {learning.threshold_confidence:.0%})"
                )
        
        # Pattern insights
        for task_type, pattern in self.task_patterns.items():
            if pattern["count"] >= 10:
                insights.append(
                    f"{task_type}: {pattern['success_rate']:.0%} success rate "
                    f"over {pattern['count']} tasks"
                )
        
        return insights
    
    def get_status(self) -> Dict[str, Any]:
        """Get meta-learning status."""
        return {
            "total_events": len(self.events),
            "agents_tracked": len(self.agent_performance),
            "task_types_learned": len(self.task_patterns),
            "insights": self.generate_insights(),
            "agent_ranking": self.get_agent_ranking()[:5]
        }
    
    def _save_state(self):
        """Persist learning state."""
        try:
            state = {
                "agent_performance": {
                    name: {
                        "agent_name": perf.agent_name,
                        "total_evaluations": perf.total_evaluations,
                        "total_executions": perf.total_executions,
                        "successful_evaluations": perf.successful_evaluations,
                        "successful_executions": perf.successful_executions,
                        "avg_confidence": perf.avg_confidence
                    }
                    for name, perf in self.agent_performance.items()
                },
                "task_patterns": {
                    k: {
                        "count": v["count"],
                        "avg_confidence": v["avg_confidence"],
                        "success_rate": v["success_rate"],
                        "best_agent_combo": v["best_agent_combo"]
                    }
                    for k, v in self.task_patterns.items()
                },
                "prompt_learnings": self.prompt_learnings,
                "saved_at": datetime.now().isoformat()
            }
            
            with open(self.persistence_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save meta-learning state: {e}")
    
    def _load_state(self):
        """Load learning state."""
        try:
            if not Path(self.persistence_path).exists():
                return
            
            with open(self.persistence_path, 'r') as f:
                state = json.load(f)
            
            for name, data in state.get("agent_performance", {}).items():
                self.agent_performance[name] = AgentPerformance(
                    agent_name=data["agent_name"],
                    total_evaluations=data["total_evaluations"],
                    total_executions=data["total_executions"],
                    successful_evaluations=data["successful_evaluations"],
                    successful_executions=data["successful_executions"],
                    avg_confidence=data.get("avg_confidence", 0.0)
                )
            
            for k, v in state.get("task_patterns", {}).items():
                self.task_patterns[k] = {
                    "count": v["count"],
                    "avg_confidence": v["avg_confidence"],
                    "success_rate": v["success_rate"],
                    "common_agents": defaultdict(int),
                    "best_agent_combo": v.get("best_agent_combo", [])
                }
            
            self.prompt_learnings = state.get("prompt_learnings", [])
            
            logger.info("Loaded meta-learning state")
        except Exception as e:
            logger.error(f"Failed to load meta-learning state: {e}")


# Singleton instance
_system: Optional[MetaLearningSystem] = None

def get_meta_learning() -> MetaLearningSystem:
    """Get or create meta-learning system instance."""
    global _system
    if _system is None:
        _system = MetaLearningSystem()
    return _system


