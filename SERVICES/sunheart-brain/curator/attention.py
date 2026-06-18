"""Relevance-triggered attention surfacing for Sunheart Brain.

This module turns existing pgvector search hits into bounded attention context.
It deliberately does not schedule checks or send messages; a candidate is
surfaced only when the current query is similar enough to an indexed chunk.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


DEFAULT_MIN_SCORE = float(os.environ.get("SH_ATTENTION_MIN_SCORE", "0.72"))
DEFAULT_MAX_ITEMS = int(os.environ.get("SH_ATTENTION_MAX_ITEMS", "3"))
DEFAULT_MAX_CHARS = int(os.environ.get("SH_ATTENTION_MAX_CHARS", "1200"))
RELEVANCE_TAGS = {
    "attention",
    "current",
    "decision",
    "goal",
    "hot",
    "intent",
    "next",
    "proof",
    "relevant",
    "surface",
}


@dataclass(frozen=True)
class AttentionCandidate:
    note_row_id: str
    chunk_idx: int
    source: str
    sensitivity: str
    score: float
    tags: tuple[str, ...]
    content: str
    reason: str

    def as_event_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tags"] = list(self.tags)
        data["content"] = self.content[:500]
        return data


def candidates_from_hits(
    hits: list[dict[str, Any]],
    *,
    min_score: float = DEFAULT_MIN_SCORE,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> list[AttentionCandidate]:
    """Return relevance-triggered candidates from pgvector hits.

    The caller is expected to supply hits from pgvector search. We filter by
    similarity threshold, exclude private rows defensively, dedupe chunks, and
    lightly prefer tags that are explicitly attention/current-state oriented.
    """
    if os.environ.get("SH_ATTENTION_SURFACING_DISABLE", "").strip() == "1":
        return []
    candidates: list[AttentionCandidate] = []
    seen: set[tuple[str, int]] = set()
    for hit in hits:
        try:
            score = float(hit.get("score") or 0.0)
        except (TypeError, ValueError):
            continue
        if score < min_score:
            continue
        sensitivity = str(hit.get("sensitivity") or "public")
        if sensitivity == "private":
            continue
        note_row_id = str(hit.get("note_row_id") or hit.get("source_id") or "")
        chunk_idx = int(hit.get("chunk_idx") or 0)
        key = (note_row_id, chunk_idx)
        if key in seen:
            continue
        seen.add(key)
        tags = tuple(str(tag).lower() for tag in (hit.get("tags") or []) if str(tag).strip())
        tag_bonus = 0.03 if RELEVANCE_TAGS.intersection(tags) else 0.0
        content = " ".join(str(hit.get("content") or "").split())[:700]
        if not content:
            continue
        reason = f"pgvector cosine {score:.2f}"
        if tag_bonus:
            reason += " + attention tag"
        candidates.append(
            AttentionCandidate(
                note_row_id=note_row_id,
                chunk_idx=chunk_idx,
                source=str(hit.get("source") or ""),
                sensitivity=sensitivity,
                score=min(1.0, score + tag_bonus),
                tags=tags,
                content=content,
                reason=reason,
            )
        )
    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[:max(0, max_items)]


def render_attention_context(
    candidates: list[AttentionCandidate],
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    if not candidates:
        return ""
    lines = [
        "--- RELEVANCE-TRIGGERED ATTENTION CONTEXT ---",
        "These surfaced because the current query matched pgvector memory above threshold. Use only when directly relevant; do not treat this as a scheduled reminder or approval.",
    ]
    for idx, candidate in enumerate(candidates, 1):
        tag_text = ",".join(candidate.tags[:4])
        lines.append(
            f"[A{idx}] {candidate.reason} source={candidate.source}/{candidate.sensitivity} tags={tag_text}"
        )
        lines.append(candidate.content)
    rendered = "\n".join(lines)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[: max(0, max_chars - 20)].rsplit("\n", 1)[0] + "\n- ... bounded"


async def attention_context_from_hits(
    query: str,
    hits: list[dict[str, Any]],
    *,
    conversation_id: str | None = None,
    min_score: float = DEFAULT_MIN_SCORE,
    max_items: int = DEFAULT_MAX_ITEMS,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    candidates = candidates_from_hits(hits, min_score=min_score, max_items=max_items)
    await log_attention_surface_event(
        query=query,
        candidates=candidates,
        conversation_id=conversation_id,
        threshold=min_score,
    )
    return render_attention_context(candidates, max_chars=max_chars)


async def log_attention_surface_event(
    *,
    query: str,
    candidates: list[AttentionCandidate],
    conversation_id: str | None,
    threshold: float,
) -> None:
    """Best-effort audit write. Missing DB/table must never block chat."""
    if os.environ.get("SH_ATTENTION_LOG_DISABLE", "").strip() == "1":
        return
    try:
        try:
            from .db import connect
        except ImportError:
            from db import connect
    except ImportError:
        return
    payload = [candidate.as_event_dict() for candidate in candidates]
    try:
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO brain_index.attention_surface_events
                        (conversation_id, query, threshold, surfaced_count, candidates, surfaced_at)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        conversation_id,
                        query[:1000],
                        threshold,
                        len(candidates),
                        json.dumps(payload, ensure_ascii=True),
                        datetime.now(timezone.utc),
                    ),
                )
    except Exception:
        return
