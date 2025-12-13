"""
🧹 Memory Hygiene System
========================

Keeps the memory system clean and relevant through:
1. Retrieval tracking (which memories are useful)
2. Cleanup rules (remove unused memories after 90 days)
3. Weekly consolidation (merge similar memories)
4. Markdown sync-back (export high-value memories to git)

Run via cron job or scheduler:
    python -m memory_hygiene --action weekly
"""

import os
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx

logger = logging.getLogger("memory_hygiene")

# Configuration
MEM0_API_KEY = os.getenv("MEM0_API_KEY")
MEM0_BASE_URL = "https://api.mem0.ai/v1"
BASE_PATH = Path(__file__).parent.parent.parent.parent.parent  # Back to FPAI_Cockpit

# Memory entity types
ENTITY_IDS = [
    "fpai_insights",
    "fpai_patterns", 
    "fpai_learnings",
    "fpai_context",
    "fpai_decisions",
    "fpai_outcomes"
]

# Cleanup thresholds
CLEANUP_DAYS = 90  # Remove unused memories after 90 days
MIN_RETRIEVALS = 3  # Minimum retrievals to keep a memory
CONSOLIDATION_SIMILARITY = 0.8  # Similarity threshold for merging


class RetrievalTracker:
    """
    Tracks which memories are being retrieved.
    
    Used to identify valuable vs unused memories.
    """
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or str(BASE_PATH / "data" / "memory_retrievals.json")
        self.retrievals: Dict[str, Dict] = {}
        self._load()
    
    def _load(self):
        """Load retrieval stats from disk."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    self.retrievals = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load retrieval stats: {e}")
            self.retrievals = {}
    
    def _save(self):
        """Save retrieval stats to disk."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(self.retrievals, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save retrieval stats: {e}")
    
    def record_retrieval(self, memory_id: str, query: str, relevance_score: float = None):
        """Record that a memory was retrieved."""
        if memory_id not in self.retrievals:
            self.retrievals[memory_id] = {
                "count": 0,
                "first_retrieval": datetime.now(timezone.utc).isoformat(),
                "last_retrieval": None,
                "queries": [],
                "avg_relevance": 0
            }
        
        entry = self.retrievals[memory_id]
        entry["count"] += 1
        entry["last_retrieval"] = datetime.now(timezone.utc).isoformat()
        entry["queries"].append(query[:50])  # Keep last query (truncated)
        entry["queries"] = entry["queries"][-5:]  # Keep last 5 queries
        
        if relevance_score:
            # Running average
            n = entry["count"]
            entry["avg_relevance"] = (entry["avg_relevance"] * (n-1) + relevance_score) / n
        
        self._save()
    
    def get_unused_memories(self, days: int = 90, min_retrievals: int = 3) -> List[str]:
        """Get memory IDs that haven't been retrieved recently."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        unused = []
        
        for memory_id, stats in self.retrievals.items():
            last = stats.get("last_retrieval")
            count = stats.get("count", 0)
            
            if count < min_retrievals:
                unused.append(memory_id)
            elif last:
                last_dt = datetime.fromisoformat(last.replace('Z', '+00:00'))
                if last_dt < cutoff:
                    unused.append(memory_id)
        
        return unused
    
    def compute_quality_score(self, memory_id: str) -> float:
        """
        Compute a quality score for a memory based on multiple factors.
        
        Score components (0.0 - 1.0):
        - Retrieval frequency: How often is it retrieved? (40%)
        - Recency: When was it last used? (30%)
        - Relevance: Average search relevance score (30%)
        
        Returns: Quality score 0.0 - 1.0
        """
        if memory_id not in self.retrievals:
            return 0.0
        
        stats = self.retrievals[memory_id]
        
        # Retrieval frequency score (40%)
        count = stats.get("count", 0)
        freq_score = min(count / 20, 1.0)  # Max at 20 retrievals
        
        # Recency score (30%)
        last = stats.get("last_retrieval")
        recency_score = 0.0
        if last:
            try:
                last_dt = datetime.fromisoformat(last.replace('Z', '+00:00'))
                days_ago = (datetime.now(timezone.utc) - last_dt).days
                recency_score = max(0, 1.0 - (days_ago / 90))  # Decays over 90 days
            except:
                pass
        
        # Relevance score (30%)
        relevance_score = stats.get("avg_relevance", 0.5)  # Default 0.5 if unknown
        
        # Weighted combination
        quality = (freq_score * 0.4) + (recency_score * 0.3) + (relevance_score * 0.3)
        
        return round(quality, 3)
    
    def get_quality_scores(self, memory_ids: List[str] = None) -> Dict[str, float]:
        """Get quality scores for multiple memories."""
        if memory_ids is None:
            memory_ids = list(self.retrievals.keys())
        
        return {
            mid: self.compute_quality_score(mid)
            for mid in memory_ids
        }
    
    def get_top_memories(self, limit: int = 20) -> List[Dict]:
        """Get most frequently retrieved memories with quality scores."""
        sorted_memories = sorted(
            self.retrievals.items(),
            key=lambda x: x[1].get("count", 0),
            reverse=True
        )
        
        return [
            {
                "memory_id": mid, 
                "quality_score": self.compute_quality_score(mid),
                **stats
            }
            for mid, stats in sorted_memories[:limit]
        ]
    
    def get_stats(self) -> Dict:
        """Get overall retrieval statistics."""
        if not self.retrievals:
            return {
                "total_memories_tracked": 0,
                "total_retrievals": 0,
                "avg_retrievals_per_memory": 0
            }
        
        total_retrievals = sum(m.get("count", 0) for m in self.retrievals.values())
        
        return {
            "total_memories_tracked": len(self.retrievals),
            "total_retrievals": total_retrievals,
            "avg_retrievals_per_memory": total_retrievals / len(self.retrievals)
        }


class MemoryHygiene:
    """
    Memory cleanup and consolidation system.
    """
    
    def __init__(self):
        self.api_key = MEM0_API_KEY
        self.enabled = bool(self.api_key)
        self.tracker = RetrievalTracker()
        
        if self.enabled:
            self.headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json"
            }
        else:
            self.headers = {}
            logger.warning("MEM0_API_KEY not set - cleanup disabled")
    
    async def _get_all_memories(self, user_id: str) -> List[Dict]:
        """Get all memories for a user/entity."""
        if not self.enabled:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{MEM0_BASE_URL}/memories/",
                    headers=self.headers,
                    params={"user_id": user_id}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return data
                    return data.get("results", data.get("memories", []))
                return []
        except Exception as e:
            logger.error(f"Error fetching memories: {e}")
            return []
    
    async def _delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        if not self.enabled:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(
                    f"{MEM0_BASE_URL}/memories/{memory_id}/",
                    headers=self.headers
                )
                return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return False
    
    # =========================================================================
    # CLEANUP OPERATIONS
    # =========================================================================
    
    async def cleanup_unused_memories(
        self,
        days: int = CLEANUP_DAYS,
        min_retrievals: int = MIN_RETRIEVALS,
        dry_run: bool = True
    ) -> Dict:
        """
        Remove memories that haven't been retrieved in {days} days
        or have fewer than {min_retrievals} total retrievals.
        """
        results = {
            "checked": 0,
            "marked_for_deletion": 0,
            "deleted": 0,
            "dry_run": dry_run
        }
        
        unused_ids = self.tracker.get_unused_memories(days, min_retrievals)
        results["marked_for_deletion"] = len(unused_ids)
        
        if dry_run:
            logger.info(f"[DRY RUN] Would delete {len(unused_ids)} unused memories")
            return results
        
        for memory_id in unused_ids:
            if await self._delete_memory(memory_id):
                results["deleted"] += 1
                logger.info(f"🗑️ Deleted unused memory: {memory_id}")
        
        return results
    
    async def cleanup_by_age(
        self,
        user_id: str,
        max_age_days: int = 180,
        dry_run: bool = True
    ) -> Dict:
        """Remove memories older than max_age_days."""
        results = {
            "checked": 0,
            "marked_for_deletion": 0,
            "deleted": 0,
            "dry_run": dry_run
        }
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        memories = await self._get_all_memories(user_id)
        results["checked"] = len(memories)
        
        to_delete = []
        for memory in memories:
            created = memory.get("created_at") or memory.get("timestamp")
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    if created_dt < cutoff:
                        to_delete.append(memory.get("id"))
                except:
                    pass
        
        results["marked_for_deletion"] = len(to_delete)
        
        if dry_run:
            logger.info(f"[DRY RUN] Would delete {len(to_delete)} old memories from {user_id}")
            return results
        
        for memory_id in to_delete:
            if await self._delete_memory(memory_id):
                results["deleted"] += 1
        
        return results
    
    # =========================================================================
    # CONSOLIDATION OPERATIONS
    # =========================================================================
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Simple similarity score based on word overlap."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    async def find_similar_memories(
        self,
        user_id: str,
        similarity_threshold: float = CONSOLIDATION_SIMILARITY
    ) -> List[List[Dict]]:
        """Find groups of similar memories that could be consolidated."""
        memories = await self._get_all_memories(user_id)
        
        if len(memories) < 2:
            return []
        
        # Find similar pairs
        groups = []
        used = set()
        
        for i, mem1 in enumerate(memories):
            if i in used:
                continue
            
            group = [mem1]
            text1 = mem1.get("memory", "") or mem1.get("content", "")
            
            for j, mem2 in enumerate(memories[i+1:], i+1):
                if j in used:
                    continue
                
                text2 = mem2.get("memory", "") or mem2.get("content", "")
                similarity = self._compute_similarity(text1, text2)
                
                if similarity >= similarity_threshold:
                    group.append(mem2)
                    used.add(j)
            
            if len(group) > 1:
                groups.append(group)
                used.add(i)
        
        return groups
    
    async def consolidate_memories(
        self,
        user_id: str,
        dry_run: bool = True
    ) -> Dict:
        """
        Merge similar memories into single consolidated entries.
        
        Process:
        1. Find groups of similar memories
        2. Create a new merged memory combining the best content
        3. Delete the original memories
        4. Preserve metadata from highest-quality source
        """
        results = {
            "groups_found": 0,
            "memories_merged": 0,
            "new_memories_created": 0,
            "deleted": 0,
            "dry_run": dry_run,
            "consolidated_groups": []
        }
        
        groups = await self.find_similar_memories(user_id)
        results["groups_found"] = len(groups)
        
        if dry_run:
            for group in groups:
                texts = [m.get("memory", "")[:50] for m in group]
                logger.info(f"[DRY RUN] Would merge {len(group)} memories: {texts}")
                results["consolidated_groups"].append({
                    "size": len(group),
                    "preview": texts[0] if texts else ""
                })
            return results
        
        # Actually consolidate each group
        for group in groups:
            try:
                # Create merged content from group
                merged_content = self._create_merged_content(group, user_id)
                
                if merged_content:
                    # Store the new consolidated memory
                    stored = await self._store_consolidated_memory(
                        user_id=user_id,
                        content=merged_content["content"],
                        metadata=merged_content["metadata"]
                    )
                    
                    if stored:
                        results["new_memories_created"] += 1
                        
                        # Delete original memories
                        for mem in group:
                            memory_id = mem.get("id")
                            if memory_id:
                                if await self._delete_memory(memory_id):
                                    results["deleted"] += 1
                                    results["memories_merged"] += 1
                        
                        logger.info(f"✅ Consolidated {len(group)} memories into 1")
                        results["consolidated_groups"].append({
                            "size": len(group),
                            "merged_into": stored.get("id", "new")
                        })
            except Exception as e:
                logger.error(f"Error consolidating group: {e}")
        
        return results
    
    def _create_merged_content(self, group: List[Dict], user_id: str) -> Optional[Dict]:
        """
        Create merged content from a group of similar memories.
        
        Strategy:
        - Use the longest/most detailed memory as base
        - Add unique information from others
        - Preserve the most recent timestamp
        - Combine metadata
        """
        if not group:
            return None
        
        # Sort by content length (longest first - likely most detailed)
        sorted_group = sorted(
            group,
            key=lambda m: len(m.get("memory", "") or m.get("content", "")),
            reverse=True
        )
        
        # Base content from longest memory
        base = sorted_group[0]
        base_content = base.get("memory", "") or base.get("content", "")
        
        # Collect unique sentences from other memories
        base_sentences = set(s.strip() for s in base_content.split('.') if s.strip())
        additional_info = []
        
        for mem in sorted_group[1:]:
            content = mem.get("memory", "") or mem.get("content", "")
            for sentence in content.split('.'):
                sentence = sentence.strip()
                if sentence and sentence not in base_sentences:
                    # Check if this adds new information
                    if not any(self._compute_similarity(sentence, existing) > 0.7 
                              for existing in base_sentences):
                        additional_info.append(sentence)
                        base_sentences.add(sentence)
        
        # Combine into merged content
        merged_content = base_content
        if additional_info:
            merged_content += " Additional context: " + ". ".join(additional_info[:3])  # Limit additions
        
        # Get most recent timestamp
        timestamps = []
        for mem in group:
            ts = mem.get("created_at") or mem.get("timestamp")
            if ts:
                timestamps.append(ts)
        
        # Build merged metadata
        metadata = {
            "type": base.get("metadata", {}).get("type", "consolidated"),
            "consolidated_from": len(group),
            "original_ids": [m.get("id") for m in group if m.get("id")],
            "consolidated_at": datetime.now(timezone.utc).isoformat(),
            "source": "memory_hygiene_consolidation"
        }
        
        return {
            "content": merged_content,
            "metadata": metadata
        }
    
    async def _store_consolidated_memory(
        self,
        user_id: str,
        content: str,
        metadata: Dict
    ) -> Optional[Dict]:
        """Store a consolidated memory in Mem0."""
        if not self.enabled:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{MEM0_BASE_URL}/memories/",
                    headers=self.headers,
                    json={
                        "messages": [{"role": "user", "content": content}],
                        "user_id": user_id,
                        "metadata": metadata
                    }
                )
                
                if resp.status_code == 200:
                    return resp.json()
                else:
                    logger.error(f"Failed to store consolidated memory: {resp.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error storing consolidated memory: {e}")
            return None
    
    # =========================================================================
    # MARKDOWN SYNC-BACK
    # =========================================================================
    
    async def export_high_value_memories(
        self,
        user_id: str,
        min_retrievals: int = 5,
        output_path: str = None
    ) -> Dict:
        """
        Export high-value memories to markdown for git archival.
        """
        output_path = output_path or str(
            BASE_PATH / "core" / "INTELLIGENCE" / f"MEMORY_EXPORT_{user_id}.md"
        )
        
        memories = await self._get_all_memories(user_id)
        top_memories = self.tracker.get_top_memories(limit=50)
        top_ids = {m["memory_id"] for m in top_memories if m.get("count", 0) >= min_retrievals}
        
        # Filter to high-value memories
        high_value = [m for m in memories if m.get("id") in top_ids]
        
        if not high_value:
            return {"exported": 0, "path": None}
        
        # Generate markdown
        lines = [
            f"# Memory Export: {user_id}",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Total high-value memories: {len(high_value)}",
            "",
            "---",
            ""
        ]
        
        for memory in high_value:
            content = memory.get("memory", "") or memory.get("content", "")
            created = memory.get("created_at", "unknown")
            
            lines.extend([
                f"## Memory {memory.get('id', 'unknown')[:8]}",
                f"**Created:** {created}",
                "",
                content,
                "",
                "---",
                ""
            ])
        
        # Write file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
        
        return {
            "exported": len(high_value),
            "path": output_path
        }
    
    # =========================================================================
    # WEEKLY MAINTENANCE JOB
    # =========================================================================
    
    async def run_weekly_maintenance(self, dry_run: bool = True) -> Dict:
        """
        Run all weekly maintenance tasks:
        1. Cleanup unused memories
        2. Find consolidation candidates
        3. Export high-value memories
        """
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "cleanup": {},
            "consolidation": {},
            "export": {}
        }
        
        logger.info("🧹 Starting weekly memory maintenance...")
        
        # 1. Cleanup unused memories
        cleanup_result = await self.cleanup_unused_memories(dry_run=dry_run)
        results["cleanup"] = cleanup_result
        logger.info(f"Cleanup: {cleanup_result}")
        
        # 2. Find consolidation candidates for each entity
        for entity_id in ENTITY_IDS:
            groups = await self.find_similar_memories(entity_id)
            results["consolidation"][entity_id] = len(groups)
            if groups:
                logger.info(f"Consolidation candidates in {entity_id}: {len(groups)} groups")
        
        # 3. Export high-value learnings
        export_result = await self.export_high_value_memories("fpai_learnings")
        results["export"]["learnings"] = export_result
        
        # 4. Export high-value patterns
        export_result = await self.export_high_value_memories("fpai_patterns")
        results["export"]["patterns"] = export_result
        
        logger.info("✅ Weekly maintenance complete")
        
        return results


# Global instances
_tracker: Optional[RetrievalTracker] = None
_hygiene: Optional[MemoryHygiene] = None


def get_tracker() -> RetrievalTracker:
    """Get singleton retrieval tracker."""
    global _tracker
    if _tracker is None:
        _tracker = RetrievalTracker()
    return _tracker


def get_hygiene() -> MemoryHygiene:
    """Get singleton hygiene manager."""
    global _hygiene
    if _hygiene is None:
        _hygiene = MemoryHygiene()
    return _hygiene


# =========================================================================
# CLI INTERFACE
# =========================================================================

async def main():
    """CLI for memory hygiene operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Memory Hygiene System")
    parser.add_argument(
        "--action",
        choices=["weekly", "cleanup", "consolidate", "export", "stats"],
        default="stats",
        help="Action to perform"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually modify anything"
    )
    parser.add_argument(
        "--entity",
        default="fpai_learnings",
        help="Entity ID to operate on"
    )
    
    args = parser.parse_args()
    
    hygiene = get_hygiene()
    tracker = get_tracker()
    
    if args.action == "stats":
        print("📊 Retrieval Statistics:")
        stats = tracker.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n🏆 Top Memories:")
        for mem in tracker.get_top_memories(10):
            print(f"   {mem['memory_id']}: {mem['count']} retrievals")
    
    elif args.action == "weekly":
        results = await hygiene.run_weekly_maintenance(dry_run=args.dry_run)
        print(json.dumps(results, indent=2))
    
    elif args.action == "cleanup":
        results = await hygiene.cleanup_unused_memories(dry_run=args.dry_run)
        print(json.dumps(results, indent=2))
    
    elif args.action == "consolidate":
        groups = await hygiene.find_similar_memories(args.entity)
        print(f"Found {len(groups)} consolidation groups")
        for i, group in enumerate(groups[:5]):
            print(f"\nGroup {i+1}:")
            for mem in group:
                print(f"  - {mem.get('memory', '')[:80]}...")
    
    elif args.action == "export":
        results = await hygiene.export_high_value_memories(args.entity)
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

