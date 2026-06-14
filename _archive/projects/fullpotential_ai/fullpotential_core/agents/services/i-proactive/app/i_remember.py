"""
I REMEMBER - Unified memory interface for the system.

This module wraps the existing MemoryManager and provides a higher‑level,
consciousness‑oriented API:

- remember()   → store decisions, episodes, and insights in a unified way
- recall()     → retrieve relevant memories across all types
- summarize()  → get compressed views of what's stored

Initial implementation keeps storage simple (JSON via MemoryManager) while
making it easy to later swap in SQLite / vector DB backends without changing
call sites.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence
import sys
import uuid

from .memory_manager import MemoryManager

try:
    from core.memory import vector_store as semantic_vector_store  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - path juggling for dev mode
    repo_root = Path(__file__).resolve()
    for _ in range(6):
        repo_root = repo_root.parent
    if str(repo_root) not in sys.path:
        sys.path.append(str(repo_root))
    try:
        from core.memory import vector_store as semantic_vector_store  # type: ignore
    except Exception:  # pragma: no cover
        semantic_vector_store = None  # type: ignore
except Exception:  # pragma: no cover
    semantic_vector_store = None  # type: ignore


class MemoryKind(str, Enum):
    """High‑level categories for I REMEMBER entries."""

    DECISION = "decision"
    EPISODE = "episode"
    INSIGHT = "insight"


@dataclass
class MemoryQuery:
    """Query parameters for recall()."""

    text: str
    kinds: Optional[Sequence[MemoryKind]] = None
    limit: int = 10


class IRemember:
    """
    Unified, higher‑level memory facade over MemoryManager.

    This is intentionally thin: it relies on MemoryManager for persistence
    while adding:
    - a shared schema for episodes and insights
    - cross‑cutting recall across decisions / episodes / insights
    - simple summarization helpers
    """

    def __init__(self, manager: Optional[MemoryManager] = None):
        self.manager = manager or MemoryManager()

    # === Remember APIs ===

    def remember_decision(
        self,
        decision: Any,
        outcome: str,
        success: bool,
        revenue_impact: Optional[float] = None,
        tags: Optional[Sequence[str]] = None,
    ) -> None:
        """
        Store a decision event and attach optional semantic tags.

        Delegates core storage to MemoryManager, then backfills tags into the
        latest decision record for unified recall.
        """
        before_count = len(self.manager.memory_store.get("decisions", []))

        self.manager.remember_decision(
            decision=decision,
            outcome=outcome,
            success=success,
            revenue_impact=revenue_impact,
        )

        if tags:
            decisions = self.manager.memory_store.get("decisions", [])
            if len(decisions) > before_count:
                # Attach tags to the newly added decision
                decisions[-1]["tags"] = list(tags)
                self.manager._save_memory()

    def remember_episode(
        self,
        title: str,
        summary: str,
        episode_type: Literal["session", "build", "deployment", "campaign", "generic"] = "generic",
        data: Optional[Dict[str, Any]] = None,
        tags: Optional[Sequence[str]] = None,
        open_loops: Optional[Sequence[str]] = None,
    ) -> str:
        """
        Remember a higher‑level episode (e.g., a session, build, or campaign).

        This is the primary way to store "what happened this block of time and why
        it matters" so future agents can quickly load continuity.

        Returns the generated `episode_id` so callers can correlate follow-on logs.

        Side effect: also stores a semantic embedding in the vector store so
        future recall can be based on meaning, not just keywords.
        """
        episodes = self.manager.memory_store.setdefault("episodes", [])

        episode_id = f"ep-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()

        episode = {
            "episode_id": episode_id,
            "title": title,
            "summary": summary,
            "episode_type": episode_type,
            "data": data or {},
            "tags": list(tags) if tags else [],
            # Open loops are simple text descriptions of unresolved items
            "open_loops": list(open_loops) if open_loops else [],
            "timestamp": timestamp,
        }

        episodes.append(episode)
        self.manager._save_memory()

        # Store semantic embedding (best-effort, never crash caller)
        if semantic_vector_store is not None:
            try:
                project = None
                for t in episode["tags"]:
                    normalized = str(t).lower()
                    if normalized.startswith("i ") or "match" in normalized or "treasury" in normalized:
                        project = str(t)
                        break

                text_repr = " | ".join(
                    [
                        title,
                        summary,
                        json.dumps(episode["data"], sort_keys=True),
                        "open_loops:" + " ".join(episode["open_loops"]),
                        "tags:" + " ".join(episode["tags"]),
                    ]
                )

                semantic_vector_store.add_episode(
                    text=text_repr,
                    metadata={
                        "episode_id": episode_id,
                        "episode_type": episode_type,
                        "project": project or "",
                        "timestamp": timestamp,
                        "tags": episode["tags"],
                    },
                )
            except Exception:
                # Embedding/vector failures should not break memory writes
                pass

        return episode_id

    def remember_insight(
        self,
        insight_type: str,
        description: str,
        data: Dict[str, Any],
        tags: Optional[Sequence[str]] = None,
    ) -> None:
        """
        Store a strategic insight and attach semantic tags.
        """
        before_count = len(self.manager.memory_store.get("strategic_insights", []))

        self.manager.remember_insight(
            insight_type=insight_type,
            description=description,
            data=data,
        )

        if tags:
            insights = self.manager.memory_store.get("strategic_insights", [])
            if len(insights) > before_count:
                insights[-1]["tags"] = list(tags)
                self.manager._save_memory()

    # === Recall APIs ===

    def recall(self, query: MemoryQuery) -> Dict[str, List[Dict[str, Any]]]:
        """
        Recall relevant memories across decisions, episodes, and insights.

        Uses simple keyword overlap as a first implementation. This can later be
        upgraded to embeddings / vector search without changing callers.
        """
        text = query.text.lower()
        keywords = set(text.split())
        kinds = set(query.kinds) if query.kinds else {k for k in MemoryKind}
        limit = max(1, query.limit)

        results: Dict[str, List[Dict[str, Any]]] = {
            "decisions": [],
            "episodes": [],
            "insights": [],
        }

        # Decisions
        if MemoryKind.DECISION in kinds:
            for d in self.manager.memory_store.get("decisions", []):
                haystack = " ".join(
                    [
                        str(d.get("title", "")),
                        str(d.get("outcome", "")),
                        " ".join(d.get("tags", [])),
                    ]
                ).lower()
                score = self._keyword_score(keywords, haystack)
                if score > 0:
                    d_copy = dict(d)
                    d_copy["score"] = score
                    results["decisions"].append(d_copy)

            results["decisions"].sort(key=lambda x: x["score"], reverse=True)
            results["decisions"] = results["decisions"][:limit]

        # Episodes
        if MemoryKind.EPISODE in kinds:
            for e in self.manager.memory_store.get("episodes", []):
                haystack = " ".join(
                    [
                        str(e.get("title", "")),
                        str(e.get("summary", "")),
                        " ".join(e.get("tags", [])),
                    ]
                ).lower()
                score = self._keyword_score(keywords, haystack)
                if score > 0:
                    e_copy = dict(e)
                    e_copy["score"] = score
                    results["episodes"].append(e_copy)

            results["episodes"].sort(key=lambda x: x["score"], reverse=True)
            results["episodes"] = results["episodes"][:limit]

        # Insights
        if MemoryKind.INSIGHT in kinds:
            for i in self.manager.memory_store.get("strategic_insights", []):
                haystack = " ".join(
                    [
                        str(i.get("type", "")),
                        str(i.get("description", "")),
                        " ".join(i.get("tags", [])),
                    ]
                ).lower()
                score = self._keyword_score(keywords, haystack)
                if score > 0:
                    i_copy = dict(i)
                    i_copy["score"] = score
                    results["insights"].append(i_copy)

            results["insights"].sort(key=lambda x: x["score"], reverse=True)
            results["insights"] = results["insights"][:limit]

        return results

    def semantic_recall(
        self,
        query_text: str,
        project: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Semantic recall of episodes using the vector store.

        Returns episodes ordered by cosine similarity along with a score field.
        Falls back gracefully to keyword-based recall if the vector store
        is empty.
        """
        if semantic_vector_store is None:
            return self.recall(
                MemoryQuery(text=query_text, kinds=[MemoryKind.EPISODE], limit=limit)
            )["episodes"]

        filters = {"project": project} if project else None
        matches = semantic_vector_store.recall(
            query=query_text,
            limit=limit,
            filters=filters,
        )

        if not matches:
            return self.recall(
                MemoryQuery(text=query_text, kinds=[MemoryKind.EPISODE], limit=limit)
            )["episodes"]

        # Index episodes by id for quick lookup
        episodes = self.manager.memory_store.get("episodes", [])
        by_id = {e.get("episode_id"): e for e in episodes}

        results: List[Dict[str, Any]] = []
        for entry in matches:
            ep = by_id.get(entry.episode_id)
            if not ep:
                continue
            ep_copy = dict(ep)
            ep_copy["score"] = entry.score
            results.append(ep_copy)

        return results

    # === Summaries ===

    def summarize_memory(self) -> Dict[str, Any]:
        """
        High‑level summary of stored memory for consciousness‑style reporting.
        """
        base_summary = self.manager.get_memory_summary()
        episodes = self.manager.memory_store.get("episodes", [])

        base_summary["episodes_count"] = len(episodes)
        base_summary["latest_episode"] = episodes[-1] if episodes else None

        return base_summary

    # === Reflection ===

    def reflect_recent(
        self,
        max_episodes: int = 20,
    ) -> Dict[str, Any]:
        """
        Generate a simple reflection insight from recent episodes and open loops.

        This is intentionally heuristic (no LLM call) and focuses on:
        - What projects have been active recently
        - How many open loops exist and a sample of them
        """
        episodes = list(self.manager.memory_store.get("episodes", []))[-max_episodes:]

        projects: Dict[str, int] = {}
        total_open_loops = 0
        sample_loops: List[str] = []

        for ep in episodes:
            tags = ep.get("tags", []) or []
            project_tag = None
            for t in tags:
                if t.lower().startswith("i ") or "match" in t.lower() or "treasury" in t.lower():
                    project_tag = t
                    break
            if project_tag:
                projects[project_tag] = projects.get(project_tag, 0) + 1

            loops = ep.get("open_loops", []) or []
            total_open_loops += len(loops)
            for l in loops:
                if l not in sample_loops and len(sample_loops) < 10:
                    sample_loops.append(l)

        reflection = {
            "generated_at": datetime.now().isoformat(),
            "episodes_considered": len(episodes),
            "active_projects": projects,
            "total_open_loops": total_open_loops,
            "sample_open_loops": sample_loops,
        }

        # Store as an insight so it becomes part of the evolving memory
        self.remember_insight(
            insight_type="reflection",
            description="Automated reflection over recent episodes and open loops.",
            data=reflection,
            tags=["reflection", "self_state"],
        )

        return reflection

    def get_open_loops(
        self,
        project: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate open loops across episodes into a unified list.

        Open loops are treated as simple text descriptions associated
        with the episode and (optionally) a project tag.
        """
        # Use description as a deduplication key so the latest occurrence wins
        seen: Dict[str, Dict[str, Any]] = {}

        episodes = list(self.manager.memory_store.get("episodes", []))
        episodes.reverse()  # newest first

        for ep in episodes:
            ep_tags = ep.get("tags", []) or []
            ep_project = None
            for t in ep_tags:
                # Heuristic: treat tags that look like project names as project
                if t.lower().startswith("i ") or "match" in t.lower() or "treasury" in t.lower():
                    ep_project = t
                    break

            if project and ep_project and ep_project.lower() != project.lower():
                continue

            for loop_desc in ep.get("open_loops", []):
                key = loop_desc.strip()
                if not key or key in seen:
                    continue

                seen[key] = {
                    "description": loop_desc,
                    "project": ep_project,
                    "source_title": ep.get("title"),
                    "source_summary": ep.get("summary"),
                    "timestamp": ep.get("timestamp"),
                }

                if len(seen) >= limit:
                    break

            if len(seen) >= limit:
                break

        # Return newest-first list
        items = list(seen.values())
        items.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        return items

    # === Internal helpers ===

    @staticmethod
    def _keyword_score(keywords: set, haystack: str) -> float:
        if not keywords:
            return 0.0
        words = set(haystack.split())
        if not words:
            return 0.0
        return len(keywords & words) / len(keywords)


