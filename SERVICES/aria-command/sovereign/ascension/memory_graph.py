#!/usr/bin/env python3
"""
ARIA ASCENSION - SEMANTIC MEMORY GRAPH
======================================

Neo4j-style graph in SQLite:
- Nodes: Concepts, People, Actions, Outcomes
- Edges: "leads_to", "prefers", "frustrated_by"
- Query: "What does James usually want after asking about SOL?"

Target: < 50ms query time
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.ascension.memory")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("ASCENSION_DB", "/opt/fpai/aria-command/state/ascension.db")


class NodeType(str, Enum):
    """Types of nodes in the memory graph."""
    CONCEPT = "concept"       # Abstract ideas (trading, server health)
    ACTION = "action"         # Things Aria does (check signal, restart service)
    OUTCOME = "outcome"       # Results (success, failure, satisfaction)
    PERSON = "person"         # People (James, etc.)
    TIME = "time"             # Time contexts (morning, weekend)
    TOPIC = "topic"           # Specific topics (SOL, BTC, server memory)


class EdgeType(str, Enum):
    """Types of relationships between nodes."""
    LEADS_TO = "leads_to"           # A often followed by B
    PREFERS = "prefers"             # User prefers A over B
    FRUSTRATED_BY = "frustrated_by"  # User frustrated when A
    SATISFIED_BY = "satisfied_by"    # User satisfied when A
    RELATED_TO = "related_to"        # A is related to B
    FOLLOWED_BY = "followed_by"      # A was followed by B
    CONTEXT_OF = "context_of"        # A is context for B


@dataclass
class Node:
    """A node in the memory graph."""
    id: str
    type: NodeType
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "access_count": self.access_count
        }


@dataclass
class Edge:
    """An edge in the memory graph."""
    source_id: str
    target_id: str
    type: EdgeType
    weight: float = 1.0  # Strength of relationship
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type.value,
            "weight": self.weight,
            "properties": self.properties
        }


GRAPH_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    properties TEXT,
    created_at TEXT NOT NULL,
    access_count INTEGER DEFAULT 0,
    last_accessed TEXT
);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    type TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    properties TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(source_id, target_id, type)
);

CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT NOT NULL,
    description TEXT,
    node_sequence TEXT,
    confidence REAL DEFAULT 0.5,
    occurrence_count INTEGER DEFAULT 1,
    last_seen TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
"""


# ============================================================================
# MEMORY GRAPH
# ============================================================================

class MemoryGraph:
    """
    Semantic memory graph for learning patterns.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        self._ensure_core_nodes()
    
    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_db(self):
        """Initialize database."""
        from pathlib import Path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with self._cursor() as cursor:
            cursor.executescript(GRAPH_SCHEMA)
        
        logger.info(f"Memory graph initialized: {self.db_path}")
    
    def _ensure_core_nodes(self):
        """Ensure core concept nodes exist."""
        core_nodes = [
            ("person:james", NodeType.PERSON, "James"),
            ("concept:trading", NodeType.CONCEPT, "Trading"),
            ("concept:system_health", NodeType.CONCEPT, "System Health"),
            ("concept:building", NodeType.CONCEPT, "Building"),
            ("topic:sol", NodeType.TOPIC, "SOL"),
            ("topic:btc", NodeType.TOPIC, "BTC"),
            ("topic:eth", NodeType.TOPIC, "ETH"),
            ("time:morning", NodeType.TIME, "Morning"),
            ("time:afternoon", NodeType.TIME, "Afternoon"),
            ("time:evening", NodeType.TIME, "Evening"),
            ("time:night", NodeType.TIME, "Night"),
            ("time:weekend", NodeType.TIME, "Weekend"),
            ("outcome:success", NodeType.OUTCOME, "Success"),
            ("outcome:failure", NodeType.OUTCOME, "Failure"),
            ("outcome:satisfaction", NodeType.OUTCOME, "User Satisfied"),
            ("outcome:frustration", NodeType.OUTCOME, "User Frustrated"),
        ]
        
        for node_id, node_type, name in core_nodes:
            self.add_node(node_id, node_type, name)
    
    # ========================================================================
    # NODE OPERATIONS
    # ========================================================================
    
    def add_node(
        self,
        node_id: str,
        node_type: NodeType,
        name: str,
        properties: Dict = None
    ) -> Node:
        """Add or update a node."""
        now = datetime.now()
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO nodes (id, type, name, properties, created_at, access_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(id) DO UPDATE SET
                    access_count = access_count + 1,
                    last_accessed = ?
            """, (
                node_id, node_type.value, name,
                json.dumps(properties or {}),
                now.isoformat(), now.isoformat(), now.isoformat()
            ))
        
        return Node(
            id=node_id, type=node_type, name=name,
            properties=properties or {}, created_at=now
        )
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID."""
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return Node(
                id=row["id"],
                type=NodeType(row["type"]),
                name=row["name"],
                properties=json.loads(row["properties"] or "{}"),
                created_at=datetime.fromisoformat(row["created_at"]),
                access_count=row["access_count"]
            )
    
    def find_nodes(
        self,
        node_type: NodeType = None,
        name_contains: str = None,
        limit: int = 20
    ) -> List[Node]:
        """Find nodes by criteria."""
        query = "SELECT * FROM nodes WHERE 1=1"
        params = []
        
        if node_type:
            query += " AND type = ?"
            params.append(node_type.value)
        
        if name_contains:
            query += " AND name LIKE ?"
            params.append(f"%{name_contains}%")
        
        query += " ORDER BY access_count DESC LIMIT ?"
        params.append(limit)
        
        with self._cursor() as cursor:
            cursor.execute(query, params)
            
            return [
                Node(
                    id=row["id"],
                    type=NodeType(row["type"]),
                    name=row["name"],
                    properties=json.loads(row["properties"] or "{}"),
                    access_count=row["access_count"]
                )
                for row in cursor.fetchall()
            ]
    
    # ========================================================================
    # EDGE OPERATIONS
    # ========================================================================
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        weight: float = 1.0,
        properties: Dict = None
    ) -> Edge:
        """Add or strengthen an edge."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO edges (source_id, target_id, type, weight, properties, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, type) DO UPDATE SET
                    weight = weight + 0.1
            """, (
                source_id, target_id, edge_type.value,
                weight, json.dumps(properties or {}),
                datetime.now().isoformat()
            ))
        
        return Edge(
            source_id=source_id, target_id=target_id,
            type=edge_type, weight=weight, properties=properties or {}
        )
    
    def get_edges_from(self, source_id: str, edge_type: EdgeType = None) -> List[Edge]:
        """Get all edges from a node."""
        query = "SELECT * FROM edges WHERE source_id = ?"
        params = [source_id]
        
        if edge_type:
            query += " AND type = ?"
            params.append(edge_type.value)
        
        query += " ORDER BY weight DESC"
        
        with self._cursor() as cursor:
            cursor.execute(query, params)
            
            return [
                Edge(
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    type=EdgeType(row["type"]),
                    weight=row["weight"],
                    properties=json.loads(row["properties"] or "{}")
                )
                for row in cursor.fetchall()
            ]
    
    def get_edges_to(self, target_id: str, edge_type: EdgeType = None) -> List[Edge]:
        """Get all edges to a node."""
        query = "SELECT * FROM edges WHERE target_id = ?"
        params = [target_id]
        
        if edge_type:
            query += " AND type = ?"
            params.append(edge_type.value)
        
        query += " ORDER BY weight DESC"
        
        with self._cursor() as cursor:
            cursor.execute(query, params)
            
            return [
                Edge(
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    type=EdgeType(row["type"]),
                    weight=row["weight"]
                )
                for row in cursor.fetchall()
            ]
    
    # ========================================================================
    # PATTERN QUERIES
    # ========================================================================
    
    def what_usually_follows(self, node_id: str, min_weight: float = 0.5) -> List[Tuple[str, float]]:
        """
        Query: What usually follows this node?
        Returns list of (target_id, weight) tuples.
        """
        edges = self.get_edges_from(node_id, EdgeType.LEADS_TO)
        
        return [
            (e.target_id, e.weight)
            for e in edges
            if e.weight >= min_weight
        ]
    
    def what_user_prefers(self, context_node_id: str = None) -> List[Tuple[str, float]]:
        """
        Query: What does the user prefer?
        Optionally filtered by context.
        """
        query = """
            SELECT target_id, SUM(weight) as total_weight
            FROM edges
            WHERE type = ?
        """
        params = [EdgeType.PREFERS.value]
        
        if context_node_id:
            query += " AND source_id = ?"
            params.append(context_node_id)
        
        query += " GROUP BY target_id ORDER BY total_weight DESC LIMIT 10"
        
        with self._cursor() as cursor:
            cursor.execute(query, params)
            return [(row["target_id"], row["total_weight"]) for row in cursor.fetchall()]
    
    def what_frustrates_user(self) -> List[Tuple[str, float]]:
        """Query: What frustrates the user?"""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT target_id, SUM(weight) as total_weight
                FROM edges
                WHERE type = ?
                GROUP BY target_id
                ORDER BY total_weight DESC
                LIMIT 10
            """, (EdgeType.FRUSTRATED_BY.value,))
            
            return [(row["target_id"], row["total_weight"]) for row in cursor.fetchall()]
    
    def predict_next_action(
        self,
        current_topic: str,
        time_of_day: str = None
    ) -> List[Tuple[str, float]]:
        """
        Predict what the user likely wants next.
        
        Uses: current topic + time context → likely next action
        """
        topic_node = f"topic:{current_topic.lower()}"
        time_node = f"time:{time_of_day}" if time_of_day else None
        
        predictions = {}
        
        # What follows this topic?
        topic_follows = self.what_usually_follows(topic_node)
        for target, weight in topic_follows:
            predictions[target] = predictions.get(target, 0) + weight
        
        # What follows this time of day?
        if time_node:
            time_follows = self.what_usually_follows(time_node)
            for target, weight in time_follows:
                predictions[target] = predictions.get(target, 0) + weight * 0.5
        
        # Sort by combined weight
        sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_predictions[:5]
    
    # ========================================================================
    # LEARNING
    # ========================================================================
    
    def learn_sequence(self, sequence: List[str]):
        """
        Learn from a sequence of nodes.
        Creates LEADS_TO edges between consecutive nodes.
        """
        for i in range(len(sequence) - 1):
            self.add_edge(sequence[i], sequence[i + 1], EdgeType.LEADS_TO)
    
    def learn_preference(self, context: str, preferred: str):
        """Learn that user prefers something in a context."""
        self.add_edge(context, preferred, EdgeType.PREFERS)
    
    def learn_frustration(self, trigger: str):
        """Learn that something frustrates the user."""
        self.add_edge("person:james", trigger, EdgeType.FRUSTRATED_BY)
    
    def learn_satisfaction(self, trigger: str):
        """Learn that something satisfies the user."""
        self.add_edge("person:james", trigger, EdgeType.SATISFIED_BY)
    
    def record_pattern(
        self,
        pattern_type: str,
        description: str,
        node_sequence: List[str],
        confidence: float = 0.5
    ):
        """Record a discovered pattern."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO patterns (pattern_type, description, node_sequence, confidence, last_seen, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT DO UPDATE SET
                    occurrence_count = occurrence_count + 1,
                    confidence = MIN(confidence + 0.05, 1.0),
                    last_seen = ?
            """, (
                pattern_type, description,
                json.dumps(node_sequence), confidence,
                datetime.now().isoformat(), datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
    
    # ========================================================================
    # STATS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        with self._cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM nodes")
            node_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM edges")
            edge_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM patterns")
            pattern_count = cursor.fetchone()["count"]
            
            cursor.execute("""
                SELECT type, COUNT(*) as count FROM nodes GROUP BY type
            """)
            node_types = {row["type"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("""
                SELECT type, COUNT(*) as count FROM edges GROUP BY type
            """)
            edge_types = {row["type"]: row["count"] for row in cursor.fetchall()}
        
        return {
            "total_nodes": node_count,
            "total_edges": edge_count,
            "total_patterns": pattern_count,
            "node_types": node_types,
            "edge_types": edge_types
        }


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_graph: Optional[MemoryGraph] = None


def get_memory_graph() -> MemoryGraph:
    """Get global memory graph."""
    global _graph
    if _graph is None:
        _graph = MemoryGraph()
    return _graph


def learn_from_interaction(
    topic: str,
    action: str,
    outcome: str,
    time_of_day: str = None
):
    """Learn from a single interaction."""
    graph = get_memory_graph()
    
    # Create nodes
    topic_node = f"topic:{topic.lower()}"
    action_node = f"action:{action.lower()}"
    outcome_node = f"outcome:{outcome.lower()}"
    
    graph.add_node(topic_node, NodeType.TOPIC, topic)
    graph.add_node(action_node, NodeType.ACTION, action)
    
    # Learn sequence
    sequence = [topic_node, action_node, outcome_node]
    if time_of_day:
        sequence.insert(0, f"time:{time_of_day}")
    
    graph.learn_sequence(sequence)


def predict_user_need(topic: str, time_of_day: str = None) -> List[Tuple[str, float]]:
    """Predict what user needs."""
    return get_memory_graph().predict_next_action(topic, time_of_day)


