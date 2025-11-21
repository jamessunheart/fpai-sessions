"""Persistent memory management using Mem0.ai"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os

from .config import settings
from .models import Task, Decision


class MemoryManager:
    """
    Manages persistent memory across sessions using Mem0.ai.

    Stores:
    - Past decisions and their outcomes
    - Task execution patterns
    - Strategic insights
    - Learning from successes and failures
    """

    def __init__(self):
        """Initialize memory store"""
        self.memory_store: Dict[str, Any] = {
            "decisions": [],
            "task_patterns": [],
            "strategic_insights": [],
            "revenue_history": [],
            "service_builds": []
        }

        # Try to load existing memory
        self._load_memory()

    def _load_memory(self):
        """Load memory from persistent storage"""
        if os.path.exists(settings.mem0_config_path):
            try:
                with open(settings.mem0_config_path, 'r') as f:
                    self.memory_store = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load memory: {e}")

    def _save_memory(self):
        """Save memory to persistent storage"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(settings.mem0_config_path), exist_ok=True)

            with open(settings.mem0_config_path, 'w') as f:
                json.dump(self.memory_store, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not save memory: {e}")

    # === Decision Memory ===

    def remember_decision(
        self,
        decision: Decision,
        outcome: str,
        success: bool,
        revenue_impact: Optional[float] = None
    ):
        """Remember a decision and its outcome for future reference"""
        memory_entry = {
            "decision_id": decision.decision_id,
            "title": decision.title,
            "chosen_option": decision.recommended_option,
            "outcome": outcome,
            "success": success,
            "revenue_impact_usd": revenue_impact,
            "timestamp": datetime.now().isoformat(),
            "criteria": decision.criteria.dict() if hasattr(decision, 'criteria') else {}
        }

        self.memory_store["decisions"].append(memory_entry)
        self._save_memory()

    def recall_similar_decisions(
        self,
        decision_title: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Recall similar past decisions to inform current decision"""
        # Simple keyword matching (could be improved with embeddings)
        keywords = set(decision_title.lower().split())

        similar_decisions = []
        for decision in self.memory_store["decisions"]:
            decision_keywords = set(decision["title"].lower().split())
            similarity = len(keywords & decision_keywords) / max(len(keywords), 1)

            if similarity > 0.3:  # 30% keyword overlap threshold
                decision["similarity_score"] = similarity
                similar_decisions.append(decision)

        # Sort by similarity and return top N
        similar_decisions.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar_decisions[:limit]

    # === Task Pattern Memory ===

    def remember_task_pattern(
        self,
        task: Task,
        execution_time_seconds: float,
        success: bool,
        model_used: str,
        agent_used: str
    ):
        """Remember how a task was executed for future optimization"""
        pattern = {
            "task_type": self._classify_task(task),
            "description_keywords": task.description.lower().split()[:10],
            "execution_time_seconds": execution_time_seconds,
            "success": success,
            "model_used": model_used,
            "agent_used": agent_used,
            "priority": task.priority,
            "timestamp": datetime.now().isoformat()
        }

        self.memory_store["task_patterns"].append(pattern)
        self._save_memory()

    def suggest_optimal_execution(self, task: Task) -> Dict[str, Any]:
        """Suggest optimal model and agent based on past patterns"""
        task_type = self._classify_task(task)

        # Find successful executions of similar task types
        relevant_patterns = [
            p for p in self.memory_store["task_patterns"]
            if p["task_type"] == task_type and p["success"]
        ]

        if not relevant_patterns:
            return {
                "suggested_model": "auto",
                "suggested_agent": "builder",
                "confidence": 0.0,
                "based_on_samples": 0
            }

        # Find most common successful model/agent combination
        combinations = {}
        for pattern in relevant_patterns:
            key = (pattern["model_used"], pattern["agent_used"])
            if key not in combinations:
                combinations[key] = {
                    "count": 0,
                    "avg_time": 0,
                    "times": []
                }
            combinations[key]["count"] += 1
            combinations[key]["times"].append(pattern["execution_time_seconds"])

        # Calculate averages
        for combo in combinations.values():
            combo["avg_time"] = sum(combo["times"]) / len(combo["times"])

        # Find best combination (most successful + fastest)
        best_combo = max(
            combinations.items(),
            key=lambda x: (x[1]["count"], -x[1]["avg_time"])
        )

        model, agent = best_combo[0]
        stats = best_combo[1]

        return {
            "suggested_model": model,
            "suggested_agent": agent,
            "confidence": min(stats["count"] / 10, 1.0),  # Max confidence at 10+ samples
            "based_on_samples": stats["count"],
            "expected_time_seconds": stats["avg_time"]
        }

    # === Strategic Insights ===

    def remember_insight(
        self,
        insight_type: str,
        description: str,
        data: Dict[str, Any]
    ):
        """Remember a strategic insight"""
        insight = {
            "type": insight_type,
            "description": description,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

        self.memory_store["strategic_insights"].append(insight)
        self._save_memory()

    def get_insights(
        self,
        insight_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve strategic insights"""
        insights = self.memory_store["strategic_insights"]

        if insight_type:
            insights = [i for i in insights if i["type"] == insight_type]

        # Return most recent
        insights.sort(key=lambda x: x["timestamp"], reverse=True)
        return insights[:limit]

    # === Revenue Tracking ===

    def record_revenue(
        self,
        service_name: str,
        amount_usd: float,
        source: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Record revenue generated"""
        revenue = {
            "service_name": service_name,
            "amount_usd": amount_usd,
            "source": source,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }

        self.memory_store["revenue_history"].append(revenue)
        self._save_memory()

    def get_revenue_stats(self) -> Dict[str, Any]:
        """Get revenue statistics"""
        if not self.memory_store["revenue_history"]:
            return {
                "total_revenue_usd": 0,
                "by_service": {},
                "by_source": {},
                "count": 0
            }

        total = sum(r["amount_usd"] for r in self.memory_store["revenue_history"])

        by_service = {}
        by_source = {}

        for revenue in self.memory_store["revenue_history"]:
            service = revenue["service_name"]
            source = revenue["source"]
            amount = revenue["amount_usd"]

            by_service[service] = by_service.get(service, 0) + amount
            by_source[source] = by_source.get(source, 0) + amount

        return {
            "total_revenue_usd": total,
            "by_service": by_service,
            "by_source": by_source,
            "count": len(self.memory_store["revenue_history"])
        }

    # === Service Build Tracking ===

    def record_build(
        self,
        service_name: str,
        build_time_hours: float,
        success: bool,
        architect_time_hours: Optional[float] = None
    ):
        """Record a service build"""
        build = {
            "service_name": service_name,
            "build_time_hours": build_time_hours,
            "architect_time_hours": architect_time_hours,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }

        self.memory_store["service_builds"].append(build)
        self._save_memory()

    def get_build_stats(self) -> Dict[str, Any]:
        """Get build statistics"""
        if not self.memory_store["service_builds"]:
            return {
                "total_builds": 0,
                "success_rate": 0,
                "avg_build_time_hours": 0,
                "avg_architect_time_hours": 0,
                "time_saved_hours": 0
            }

        builds = self.memory_store["service_builds"]
        successful = [b for b in builds if b["success"]]

        total_build_time = sum(b["build_time_hours"] for b in builds)
        total_architect_time = sum(b.get("architect_time_hours", 0) for b in builds if b.get("architect_time_hours"))

        # Assume manual coding would take full build time
        time_saved = total_build_time - total_architect_time

        return {
            "total_builds": len(builds),
            "successful_builds": len(successful),
            "success_rate": len(successful) / len(builds) if builds else 0,
            "avg_build_time_hours": total_build_time / len(builds) if builds else 0,
            "avg_architect_time_hours": total_architect_time / len(builds) if builds else 0,
            "time_saved_hours": time_saved,
            "productivity_multiplier": total_build_time / total_architect_time if total_architect_time > 0 else 0
        }

    # === Helper Methods ===

    def _classify_task(self, task: Task) -> str:
        """Classify task into a category"""
        description_lower = task.description.lower()

        if any(word in description_lower for word in ["code", "implement", "build"]):
            return "code_generation"
        elif any(word in description_lower for word in ["analyze", "review", "evaluate"]):
            return "analysis"
        elif any(word in description_lower for word in ["decide", "strategy", "plan"]):
            return "strategic"
        elif any(word in description_lower for word in ["deploy", "configure"]):
            return "deployment"
        else:
            return "general"

    def get_memory_summary(self) -> Dict[str, int]:
        """Get summary of what's stored in memory"""
        return {
            "decisions_count": len(self.memory_store["decisions"]),
            "task_patterns_count": len(self.memory_store["task_patterns"]),
            "strategic_insights_count": len(self.memory_store["strategic_insights"]),
            "revenue_records_count": len(self.memory_store["revenue_history"]),
            "service_builds_count": len(self.memory_store["service_builds"])
        }
