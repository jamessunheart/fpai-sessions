"""
ARIA KNOWLEDGE GRAPH
=====================

Connects memories through relationships.

Human memory is associative:
- "Trading" links to "SOL", "signals", "WhaleTrack"
- "James" links to "steward", "preferences", "priorities"
- "Errors" link to "fixes", "learnings"

This enables:
- "What do I know about X?" → follows all connections
- "How is X related to Y?" → finds paths
- "What else is relevant?" → proactive surfacing
- Pattern detection across linked memories
"""

import os
import sqlite3
import logging
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from contextlib import contextmanager
from enum import Enum
import re

logger = logging.getLogger("aria.memory.graph")

# Configuration
GRAPH_DB_PATH = Path(os.getenv("ARIA_GRAPH_DB", "/opt/fpai/aria-command/state/knowledge_graph.db"))


class RelationType(str, Enum):
    """Types of relationships between concepts."""
    IS_A = "is_a"           # "SOL is_a cryptocurrency"
    PART_OF = "part_of"     # "Claude is part_of thinking"
    RELATED_TO = "related_to"  # General association
    CAUSES = "causes"       # "timeout causes error"
    FIXES = "fixes"         # "restart fixes hang"
    PREFERS = "prefers"     # "James prefers concise"
    LEARNED_FROM = "learned_from"  # "pattern learned_from episode"
    SIMILAR_TO = "similar_to"  # Conceptual similarity


@dataclass
class Concept:
    """A concept/entity in the knowledge graph."""
    id: str
    name: str
    concept_type: str  # person, service, topic, pattern, etc.
    importance: float
    first_seen: datetime
    last_referenced: datetime
    reference_count: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.concept_type,
            "importance": self.importance,
            "first_seen": self.first_seen.isoformat(),
            "last_referenced": self.last_referenced.isoformat(),
            "reference_count": self.reference_count,
            "metadata": self.metadata
        }


@dataclass
class Relationship:
    """A relationship between two concepts."""
    from_concept: str
    to_concept: str
    relation_type: RelationType
    strength: float  # 0-1
    evidence: List[str]  # Memory IDs that support this
    created_at: datetime
    
    def to_dict(self) -> Dict:
        return {
            "from": self.from_concept,
            "to": self.to_concept,
            "type": self.relation_type.value,
            "strength": self.strength,
            "evidence_count": len(self.evidence),
            "created_at": self.created_at.isoformat()
        }


class KnowledgeGraph:
    """
    Aria's knowledge graph - connects concepts through relationships.
    
    Features:
    - Auto-extract concepts from memories
    - Build relationships from patterns
    - Traverse for related knowledge
    - Strengthen connections through reinforcement
    """
    
    # Common concepts to seed the graph
    SEED_CONCEPTS = {
        # People
        "James": ("person", 1.0, {"role": "steward", "alias": "Sunheart"}),
        "Aria": ("person", 1.0, {"role": "ai_partner"}),
        
        # Services
        "aria-command": ("service", 0.9, {"type": "core"}),
        "whaletrack": ("service", 0.8, {"type": "trading"}),
        "consciousness": ("service", 0.9, {"type": "core"}),
        
        # Topics
        "trading": ("topic", 0.8, {}),
        "memory": ("topic", 0.9, {}),
        "consciousness": ("topic", 0.9, {}),
        "building": ("topic", 0.8, {}),
        
        # Crypto
        "SOL": ("crypto", 0.7, {"name": "Solana"}),
        "BTC": ("crypto", 0.7, {"name": "Bitcoin"}),
        "ETH": ("crypto", 0.7, {"name": "Ethereum"}),
    }
    
    def __init__(self):
        self._ensure_db()
        self._seed_concepts()
        logger.info("🕸️ Knowledge graph initialized")
    
    def _ensure_db(self):
        """Create database and tables."""
        GRAPH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS concepts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    concept_type TEXT NOT NULL,
                    importance REAL DEFAULT 0.5,
                    first_seen TEXT NOT NULL,
                    last_referenced TEXT NOT NULL,
                    reference_count INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                );
                
                CREATE TABLE IF NOT EXISTS relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_concept TEXT NOT NULL,
                    to_concept TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    strength REAL DEFAULT 0.5,
                    evidence TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (from_concept) REFERENCES concepts(id),
                    FOREIGN KEY (to_concept) REFERENCES concepts(id),
                    UNIQUE(from_concept, to_concept, relation_type)
                );
                
                CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(name);
                CREATE INDEX IF NOT EXISTS idx_concepts_type ON concepts(concept_type);
                CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_concept);
                CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_concept);
            """)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(str(GRAPH_DB_PATH), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _seed_concepts(self):
        """Seed the graph with core concepts."""
        now = datetime.now(timezone.utc).isoformat()
        
        with self._get_connection() as conn:
            for name, (ctype, importance, metadata) in self.SEED_CONCEPTS.items():
                concept_id = name.lower().replace(" ", "_")
                
                conn.execute("""
                    INSERT OR IGNORE INTO concepts 
                    (id, name, concept_type, importance, first_seen, last_referenced, reference_count, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                """, (concept_id, name, ctype, importance, now, now, json.dumps(metadata)))
    
    def add_concept(
        self,
        name: str,
        concept_type: str = "topic",
        importance: float = 0.5,
        metadata: Dict = None
    ) -> Concept:
        """Add a new concept to the graph."""
        concept_id = name.lower().replace(" ", "_").replace("-", "_")
        now = datetime.now(timezone.utc)
        
        with self._get_connection() as conn:
            # Check if exists
            existing = conn.execute(
                "SELECT * FROM concepts WHERE id = ?", (concept_id,)
            ).fetchone()
            
            if existing:
                # Update reference
                conn.execute("""
                    UPDATE concepts 
                    SET last_referenced = ?, reference_count = reference_count + 1
                    WHERE id = ?
                """, (now.isoformat(), concept_id))
                
                return self._row_to_concept(existing)
            
            # Create new
            conn.execute("""
                INSERT INTO concepts 
                (id, name, concept_type, importance, first_seen, last_referenced, reference_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (concept_id, name, concept_type, importance, now.isoformat(), now.isoformat(), json.dumps(metadata or {})))
            
            return Concept(
                id=concept_id,
                name=name,
                concept_type=concept_type,
                importance=importance,
                first_seen=now,
                last_referenced=now,
                reference_count=1,
                metadata=metadata or {}
            )
    
    def add_relationship(
        self,
        from_concept: str,
        to_concept: str,
        relation_type: RelationType,
        strength: float = 0.5,
        evidence_id: str = None
    ):
        """Add or strengthen a relationship."""
        from_id = from_concept.lower().replace(" ", "_")
        to_id = to_concept.lower().replace(" ", "_")
        now = datetime.now(timezone.utc).isoformat()
        
        # Ensure concepts exist
        self.add_concept(from_concept)
        self.add_concept(to_concept)
        
        with self._get_connection() as conn:
            # Check if relationship exists
            existing = conn.execute("""
                SELECT * FROM relationships 
                WHERE from_concept = ? AND to_concept = ? AND relation_type = ?
            """, (from_id, to_id, relation_type.value)).fetchone()
            
            if existing:
                # Strengthen existing relationship
                evidence = json.loads(existing["evidence"])
                if evidence_id and evidence_id not in evidence:
                    evidence.append(evidence_id)
                
                new_strength = min(1.0, existing["strength"] + 0.1)
                
                conn.execute("""
                    UPDATE relationships 
                    SET strength = ?, evidence = ?
                    WHERE from_concept = ? AND to_concept = ? AND relation_type = ?
                """, (new_strength, json.dumps(evidence), from_id, to_id, relation_type.value))
            else:
                # Create new relationship
                evidence = [evidence_id] if evidence_id else []
                
                conn.execute("""
                    INSERT INTO relationships 
                    (from_concept, to_concept, relation_type, strength, evidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (from_id, to_id, relation_type.value, strength, json.dumps(evidence), now))
    
    def extract_concepts_from_text(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract concepts from text.
        
        Returns list of (concept_name, concept_type) tuples.
        """
        concepts = []
        text_lower = text.lower()
        
        # Check for known concepts
        with self._get_connection() as conn:
            known = conn.execute("SELECT name, concept_type FROM concepts").fetchall()
            
            for row in known:
                if row["name"].lower() in text_lower:
                    concepts.append((row["name"], row["concept_type"]))
        
        # Extract potential new concepts (capitalized words, technical terms)
        # Simple heuristic: capitalized words that aren't at sentence start
        words = text.split()
        for i, word in enumerate(words):
            if i > 0 and word[0].isupper() and len(word) > 2:
                clean_word = re.sub(r'[^\w]', '', word)
                if clean_word and clean_word not in [c[0] for c in concepts]:
                    concepts.append((clean_word, "topic"))
        
        return concepts[:10]  # Limit to prevent noise
    
    def learn_from_memory(self, memory_id: str, content: str, memory_type: str = "learning"):
        """
        Learn concepts and relationships from a memory.
        
        Auto-extracts entities and infers relationships.
        """
        concepts = self.extract_concepts_from_text(content)
        
        if len(concepts) < 2:
            return
        
        # Add all concepts
        for name, ctype in concepts:
            self.add_concept(name, ctype)
        
        # Infer relationships between concepts mentioned together
        for i, (c1_name, _) in enumerate(concepts):
            for c2_name, _ in concepts[i+1:]:
                self.add_relationship(
                    c1_name, c2_name,
                    RelationType.RELATED_TO,
                    strength=0.3,
                    evidence_id=memory_id
                )
        
        # Check for specific relationship patterns in text
        content_lower = content.lower()
        
        if "prefer" in content_lower or "likes" in content_lower:
            # Find what James prefers
            for name, _ in concepts:
                if name.lower() != "james":
                    self.add_relationship("James", name, RelationType.PREFERS, 0.6, memory_id)
        
        if "fixed" in content_lower or "solved" in content_lower:
            # Find fix relationships
            for i, (c1_name, _) in enumerate(concepts):
                for c2_name, _ in concepts[i+1:]:
                    self.add_relationship(c1_name, c2_name, RelationType.FIXES, 0.5, memory_id)
        
        if "learned" in content_lower or "realized" in content_lower:
            for name, _ in concepts:
                self.add_relationship(name, "learning", RelationType.LEARNED_FROM, 0.5, memory_id)
    
    def get_related(
        self,
        concept: str,
        depth: int = 2,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get concepts related to the given concept.
        
        Uses BFS to find connected concepts up to given depth.
        """
        concept_id = concept.lower().replace(" ", "_")
        visited: Set[str] = set()
        results = []
        
        with self._get_connection() as conn:
            queue = [(concept_id, 0)]
            
            while queue and len(results) < limit:
                current_id, current_depth = queue.pop(0)
                
                if current_id in visited or current_depth > depth:
                    continue
                
                visited.add(current_id)
                
                # Get concept info
                concept_row = conn.execute(
                    "SELECT * FROM concepts WHERE id = ?", (current_id,)
                ).fetchone()
                
                if concept_row and current_id != concept_id:
                    results.append({
                        "concept": self._row_to_concept(concept_row).to_dict(),
                        "depth": current_depth
                    })
                
                # Get relationships
                rels = conn.execute("""
                    SELECT to_concept, relation_type, strength FROM relationships
                    WHERE from_concept = ?
                    UNION
                    SELECT from_concept, relation_type, strength FROM relationships
                    WHERE to_concept = ?
                """, (current_id, current_id)).fetchall()
                
                for rel in rels:
                    neighbor = rel[0]
                    if neighbor not in visited:
                        queue.append((neighbor, current_depth + 1))
        
        # Sort by depth then importance
        results.sort(key=lambda x: (x["depth"], -x["concept"]["importance"]))
        return results
    
    def get_relationships(self, concept: str) -> List[Relationship]:
        """Get all relationships for a concept."""
        concept_id = concept.lower().replace(" ", "_")
        
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM relationships
                WHERE from_concept = ? OR to_concept = ?
                ORDER BY strength DESC
            """, (concept_id, concept_id)).fetchall()
            
            return [self._row_to_relationship(row) for row in rows]
    
    def find_path(self, from_concept: str, to_concept: str, max_depth: int = 4) -> Optional[List[str]]:
        """
        Find a path between two concepts.
        
        Returns list of concept IDs forming the path, or None if not found.
        """
        from_id = from_concept.lower().replace(" ", "_")
        to_id = to_concept.lower().replace(" ", "_")
        
        with self._get_connection() as conn:
            visited = set()
            queue = [(from_id, [from_id])]
            
            while queue:
                current, path = queue.pop(0)
                
                if len(path) > max_depth:
                    continue
                
                if current == to_id:
                    return path
                
                if current in visited:
                    continue
                
                visited.add(current)
                
                # Get neighbors
                rels = conn.execute("""
                    SELECT to_concept FROM relationships WHERE from_concept = ?
                    UNION
                    SELECT from_concept FROM relationships WHERE to_concept = ?
                """, (current, current)).fetchall()
                
                for rel in rels:
                    neighbor = rel[0]
                    if neighbor not in visited:
                        queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def get_context_prompt(self, topic: str) -> str:
        """
        Get knowledge graph context for prompt injection.
        
        Returns related concepts and relationships for a topic.
        """
        related = self.get_related(topic, depth=2, limit=5)
        relationships = self.get_relationships(topic)
        
        if not related and not relationships:
            return ""
        
        lines = [f"\n## 🕸️ Knowledge Graph: {topic}\n"]
        
        if related:
            lines.append("**Related Concepts:**")
            for r in related[:5]:
                c = r["concept"]
                lines.append(f"- {c['name']} ({c['type']}, depth: {r['depth']})")
        
        if relationships:
            lines.append("\n**Relationships:**")
            for rel in relationships[:5]:
                if rel.from_concept.lower() == topic.lower():
                    lines.append(f"- {topic} {rel.relation_type.value} {rel.to_concept}")
                else:
                    lines.append(f"- {rel.from_concept} {rel.relation_type.value} {topic}")
        
        lines.append("\n---\n")
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        with self._get_connection() as conn:
            concepts = conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
            relationships = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
            by_type = dict(conn.execute(
                "SELECT concept_type, COUNT(*) FROM concepts GROUP BY concept_type"
            ).fetchall())
            by_rel = dict(conn.execute(
                "SELECT relation_type, COUNT(*) FROM relationships GROUP BY relation_type"
            ).fetchall())
            
            return {
                "total_concepts": concepts,
                "total_relationships": relationships,
                "concepts_by_type": by_type,
                "relationships_by_type": by_rel,
                "db_path": str(GRAPH_DB_PATH)
            }
    
    def _row_to_concept(self, row: sqlite3.Row) -> Concept:
        """Convert row to Concept."""
        return Concept(
            id=row["id"],
            name=row["name"],
            concept_type=row["concept_type"],
            importance=row["importance"],
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_referenced=datetime.fromisoformat(row["last_referenced"]),
            reference_count=row["reference_count"],
            metadata=json.loads(row["metadata"])
        )
    
    def _row_to_relationship(self, row: sqlite3.Row) -> Relationship:
        """Convert row to Relationship."""
        return Relationship(
            from_concept=row["from_concept"],
            to_concept=row["to_concept"],
            relation_type=RelationType(row["relation_type"]),
            strength=row["strength"],
            evidence=json.loads(row["evidence"]),
            created_at=datetime.fromisoformat(row["created_at"])
        )


# ============================================================================
# SINGLETON
# ============================================================================

_graph: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    """Get or create knowledge graph instance."""
    global _graph
    if _graph is None:
        _graph = KnowledgeGraph()
    return _graph









