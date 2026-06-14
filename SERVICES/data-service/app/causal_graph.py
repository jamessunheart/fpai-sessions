"""
Causal Graph - "Why Map"
========================
Stores causal nodes/edges and can explain likely causes.
"""

from typing import Dict, List
from pydantic import BaseModel
from datetime import datetime, timezone
import json


class CausalNode(BaseModel):
    id: str
    type: str  # "event" | "pattern" | "prediction" | "outcome"
    label: str
    timestamp: str
    metadata: Dict = {}


class CausalEdge(BaseModel):
    source_id: str
    target_id: str
    relation: str  # "causes" | "contributes_to" | "correlates_with" | "contradicts"
    weight: float  # 0-1
    confidence: float  # 0-1
    created_at: str


class CausalGraph:
    def __init__(self):
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: List[CausalEdge] = []

    def add_node(self, node: CausalNode):
        self.nodes[node.id] = node

    def add_edge(self, edge: CausalEdge):
        self.edges.append(edge)

    def get_explanation(self, target_id: str, max_edges: int = 3) -> str:
        relevant = [e for e in self.edges if e.target_id == target_id]
        relevant = sorted(relevant, key=lambda e: e.weight * e.confidence, reverse=True)[:max_edges]
        parts = []
        for e in relevant:
            src = self.nodes.get(e.source_id)
            if src:
                parts.append(f"{src.label} ({e.relation}, w={e.weight:.2f}, c={e.confidence:.2f})")
        if not parts:
            return "No strong causal links recorded."
        return " ; ".join(parts)

    def to_json(self) -> str:
        return json.dumps({
            "nodes": [n.dict() for n in self.nodes.values()],
            "edges": [e.dict() for e in self.edges]
        })


# Singleton
causal_graph = CausalGraph()












