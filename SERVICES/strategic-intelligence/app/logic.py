import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger("IntelligenceEngine")

class IntelligenceEngine:
    """
    The Logic Core.
    Decides what matters based on the World Model.
    Formula: Priority = Impact * Alignment * Unblocked
    """
    
    def __init__(self):
        pass

    def analyze(self, world_model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze world model and return ranked priorities."""
        candidates = []
        
        # 1. Identify Gaps from Service Health
        services = world_model.get("services", {})
        for name, status in services.items():
            if status == "down":
                candidates.append({
                    "name": f"Fix Service: {name}",
                    "type": "fix",
                    "target": name,
                    "impact": 10,  # Critical infrastructure
                    "alignment": 10, # Must be up
                    "unblocked": 1,
                    "reason": f"Service {name} is DOWN"
                })

        # 2. Identify Revenue Opportunities (Placeholder logic)
        # If revenue < target, prioritize revenue-generating features
        
        # 3. Identify Staging Review
        # If files in STAGING/incoming, verify them
        
        # 4. Standing Order: System Optimization (Docs & Specs)
        # Always available as a fallback/maintenance task
        candidates.append({
            "name": "Optimize System Documentation",
            "type": "optimization",
            "target": "documentation",
            "impact": 5,      # Important but not critical
            "alignment": 10,  # Pure alignment with Constitutuion
            "unblocked": 1,
            "reason": "Periodic optimization of specs and documentation to ensure clarity."
        })
        
        # 5. Score Candidates
        ranked = self._score_and_rank(candidates)
        
        return ranked

    def _score_and_rank(self, candidates: List[Dict]) -> List[Dict]:
        for item in candidates:
            score = item["impact"] * item["alignment"] * item["unblocked"]
            item["score"] = score
            
        return sorted(candidates, key=lambda x: x["score"], reverse=True)

