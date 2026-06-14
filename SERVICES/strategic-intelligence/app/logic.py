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
        seen_names = set()
        
        # 1. Identify Gaps from Service Health
        services = world_model.get("services", {})
        for name, status in services.items():
            if status == "down":
                item = {
                    "name": f"Fix Service: {name}",
                    "type": "fix",
                    "target": name,
                    "impact": 10,  # Critical infrastructure
                    "alignment": 10, # Must be up
                    "unblocked": 1,
                    "reason": f"Service {name} is DOWN"
                }
                if item["name"] not in seen_names:
                    candidates.append(item)
                    seen_names.add(item["name"])

        # 2. External signals (from Data Service + Nerve Center digests)
        signals = world_model.get("signals", []) or []
        for s in signals[:50]:
            title = str(s.get("title") or "").strip()
            if not title:
                continue

            category = str(s.get("category") or "general")
            relevance = float(s.get("relevance") or 0.5)
            kind = str(s.get("kind") or "signal")

            # Base impact by category
            impact = 6
            if category in {"markets", "trading"}:
                impact = 9
            elif category in {"leadgen", "sales", "revenue"}:
                impact = 8
            elif category in {"system", "ops"}:
                impact = 7

            # Scale impact mildly by relevance (0.5..1.0 multiplier)
            impact = max(1, int(round(impact * (0.5 + (relevance / 2)))))

            item = {
                "name": f"Signal ({category}): {title[:80]}",
                "type": "signal",
                "target": category,
                "impact": impact,
                "alignment": 10,  # Revenue-first and system integrity by default
                "unblocked": 1,
                "reason": f"External {kind} received (relevance={relevance:.2f})",
                "meta": {
                    "signal_id": s.get("id"),
                    "kind": kind,
                    "source": s.get("source"),
                    "received_at": s.get("received_at"),
                },
            }
            if item["name"] not in seen_names:
                candidates.append(item)
                seen_names.add(item["name"])

        # 2. Identify Revenue Opportunities (Placeholder logic)
        # If revenue < target, prioritize revenue-generating features
        
        # 3. Identify Staging Review
        # If files in STAGING/incoming, verify them
        
        # 4. Standing Order: System Optimization (Docs & Specs)
        # Always available as a fallback/maintenance task
        item = {
            "name": "Optimize System Documentation",
            "type": "optimization",
            "target": "documentation",
            "impact": 5,      # Important but not critical
            "alignment": 10,  # Pure alignment with Constitutuion
            "unblocked": 1,
            "reason": "Periodic optimization of specs and documentation to ensure clarity."
        }
        if item["name"] not in seen_names:
            candidates.append(item)
            seen_names.add(item["name"])
        
        # 5. Score Candidates
        ranked = self._score_and_rank(candidates)
        
        return ranked

    def _score_and_rank(self, candidates: List[Dict]) -> List[Dict]:
        for item in candidates:
            score = item["impact"] * item["alignment"] * item["unblocked"]
            item["score"] = score
            
        return sorted(candidates, key=lambda x: x["score"], reverse=True)

