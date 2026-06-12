"""Cluster-tag job — cluster recently-added notes by embedding and propose
canonical tags for each cluster. Proposals land as 'add-tag' rows; new tags
also propose a row in '05 · Tags' with Status = 🟡 Proposed.
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Any

import numpy as np

from ..appflowy import AppFlowy
from ..db import connect
from ..llm import complete
from ..proposals import Proposal, ProposalWriter

log = logging.getLogger("curator.cluster_tag")

LOOKBACK_HOURS = int(os.environ.get("CURATOR_CLUSTER_LOOKBACK_H", "24"))
MIN_CLUSTER = int(os.environ.get("CURATOR_CLUSTER_MIN_SIZE", "3"))

SYSTEM = (
    "You name clusters of notes. Given 5-15 short excerpts, produce ONE short "
    "canonical tag (lowercase, hyphenated, <30 chars) that fits all of them, "
    "and a 1-sentence description."
)


def _kmeans(embeddings: np.ndarray, k: int, iters: int = 20) -> np.ndarray:
    rng = np.random.default_rng(42)
    centers = embeddings[rng.choice(len(embeddings), size=k, replace=False)]
    labels = np.zeros(len(embeddings), dtype=int)
    for _ in range(iters):
        d = ((embeddings[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
        labels = d.argmin(axis=1)
        for i in range(k):
            members = embeddings[labels == i]
            if len(members):
                centers[i] = members.mean(axis=0)
    return labels


async def run(run_id: str) -> dict[str, Any]:
    stats = {"notes": 0, "clusters": 0, "proposals": 0, "errors": 0}

    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                SELECT note_row_id, content, embedding
                  FROM brain_index.note_chunks
                 WHERE sensitivity = 'public'
                   AND created_at > NOW() - INTERVAL '{LOOKBACK_HOURS} hours'
                 ORDER BY created_at DESC
                 LIMIT 400
                """
            )
            rows = await cur.fetchall()

    if len(rows) < MIN_CLUSTER * 2:
        log.info("only %d recent notes; skipping cluster pass", len(rows))
        return stats

    embeddings = np.array([np.array(r[2], dtype=np.float32) for r in rows])
    stats["notes"] = len(embeddings)

    k = max(2, min(10, len(embeddings) // 5))
    labels = _kmeans(embeddings, k)

    clusters: dict[int, list[tuple[str, str]]] = defaultdict(list)
    for (note_id, content, _), lab in zip(rows, labels):
        clusters[int(lab)].append((note_id, content))

    async with AppFlowy() as af:
        writer = ProposalWriter(af)
        for cid, members in clusters.items():
            if len(members) < MIN_CLUSTER:
                continue
            excerpts = [c[:400] for (_, c) in members[:12]]
            user = "EXCERPTS:\n" + "\n---\n".join(excerpts)
            hint = 'Return JSON: {"tag":"…","description":"…","confidence":0.0-1.0}'
            try:
                res = await complete(SYSTEM, user + "\n\n" + hint, max_tokens=200)
                d = res.parse_json()
            except Exception as e:
                log.warning("cluster %d llm failed: %s", cid, e)
                stats["errors"] += 1
                continue

            tag = (d.get("tag") or "").strip().lower().replace(" ", "-")
            if not tag:
                continue
            proposal = Proposal(
                proposal=f"Tag '{tag}' ({len(members)} notes)",
                type="add-tag",
                confidence_score=float(d.get("confidence", 0.7)),
                proposed_by="cluster-tag",
                reasoning=d.get("description", ""),
                diff={
                    "tag": tag,
                    "description": d.get("description", ""),
                    "note_count": len(members),
                    "note_ids": [m[0] for m in members],
                },
                target_note_ids=[m[0] for m in members],
                run_id=run_id,
                model=res.model,
                prompt_sha1=res.prompt_sha1,
            )
            await writer.write(proposal, auto_apply=False)  # tag additions need human confirm
            stats["proposals"] += 1
            stats["clusters"] += 1

        await writer.notify("cluster-tag", run_id=run_id)

    return stats
