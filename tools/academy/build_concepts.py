#!/usr/bin/env python3
"""Build the concept layer — turn the flat curated brain into a structured mind.

The brain audit (2026-07-03) found `brain_index.note_chunks` was a flat pile: 0 of
5,080 chunks linked to a concept, `brain_index.concepts` empty. After cold-tiering
the stale dump, ~301 curated chunks remain. This clusters them by meaning into
concepts (populating `concepts` + each chunk's `concept_id`), so the brain has
TOPICS — retrieval can reason by subject, near-duplicates collapse into one concept,
and knowledge stops being an undifferentiated bag.

Method: greedy cosine clustering over the 768-dim embeddings (numpy; no sklearn).
A chunk joins the nearest concept whose centroid similarity ≥ threshold, else starts
a new concept. Each concept is named from its centroid-nearest chunk's heading.

SAFE / reversible: only touches the curated tier (sensitivity public|personal),
rebuilds cleanly each run (clears prior concept_ids + concepts it owns first). No
chunk content is changed. Reverse: `UPDATE note_chunks SET concept_id=NULL;
DELETE FROM concepts;`

Run:  build_concepts.py            # dry-run: show the concepts it would form
      build_concepts.py --execute  # write concepts + concept_id
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter

import numpy as np

DB_ENV = "BRAIN_INDEX_DB_URL"
SEARCH_SENSITIVITIES = ("public", "personal")
DEFAULT_THRESHOLD = float(os.environ.get("CONCEPT_SIM_THRESHOLD", "0.72"))


def _name_from_content(content: str) -> str:
    """Derive a concept name from a chunk's heading / tagged first line."""
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        # strip markdown/heading + our [tag] prefix
        line = re.sub(r"^#+\s*", "", line)
        m = re.match(r"^\[([a-z_]+)\]\s*(.+)", line)
        if m:
            line = f"{m.group(2)}"
        line = line.strip("*_# ").strip()
        if len(line) >= 4:
            return line[:80]
    return content.strip()[:60] or "concept"


def load_chunks(cur) -> list[dict]:
    cur.execute(
        """
        SELECT id::text, content, source, created_at, embedding::text
          FROM brain_index.note_chunks
         WHERE sensitivity = ANY(%s) AND embedding IS NOT NULL
         ORDER BY created_at
        """,
        (list(SEARCH_SENSITIVITIES),),
    )
    rows = []
    for cid, content, source, created, emb_text in cur.fetchall():
        try:
            vec = np.asarray(json.loads(emb_text), dtype=np.float32)
        except Exception:
            continue
        n = np.linalg.norm(vec)
        if n == 0:
            continue
        rows.append({"id": cid, "content": content or "", "source": source or "",
                     "created": created, "vec": vec / n})
    return rows


def greedy_cluster(chunks: list[dict], threshold: float) -> list[list[int]]:
    """Return clusters as lists of chunk indices. Centroid = running mean (renormalized)."""
    centroids: list[np.ndarray] = []
    clusters: list[list[int]] = []
    for i, ch in enumerate(chunks):
        v = ch["vec"]
        best, best_sim = -1, -1.0
        for c, cen in enumerate(centroids):
            sim = float(np.dot(v, cen))
            if sim > best_sim:
                best, best_sim = c, sim
        if best >= 0 and best_sim >= threshold:
            clusters[best].append(i)
            m = np.mean([chunks[j]["vec"] for j in clusters[best]], axis=0)
            centroids[best] = m / (np.linalg.norm(m) or 1.0)
        else:
            clusters.append([i])
            centroids.append(v.copy())
    return clusters


def build(cur, chunks: list[dict], clusters: list[list[int]], *, execute: bool) -> list[dict]:
    summaries = []
    if execute:
        cur.execute("UPDATE brain_index.note_chunks SET concept_id=NULL WHERE sensitivity = ANY(%s)",
                    (list(SEARCH_SENSITIVITIES),))
        cur.execute("DELETE FROM brain_index.concepts")
    for members in sorted(clusters, key=len, reverse=True):
        idxs = members
        centroid = np.mean([chunks[j]["vec"] for j in idxs], axis=0)
        centroid = centroid / (np.linalg.norm(centroid) or 1.0)
        # name from the chunk nearest the centroid
        central = max(idxs, key=lambda j: float(np.dot(chunks[j]["vec"], centroid)))
        name = _name_from_content(chunks[central]["content"])
        domains = sorted({chunks[j]["source"] for j in idxs if chunks[j]["source"]})
        salience = "high" if len(idxs) >= 8 else "med" if len(idxs) >= 3 else "low"
        summaries.append({"name": name, "size": len(idxs), "domains": domains,
                          "sample": chunks[central]["content"].strip().replace("\n", " ")[:60]})
        if execute:
            cur.execute(
                """
                INSERT INTO brain_index.concepts
                    (name, description, centroid, note_count, domain, salience, first_seen, last_reinforced)
                VALUES (%s, %s, %s::vector, %s, %s, %s, now(), now())
                RETURNING id
                """,
                (name, f"Auto-clustered concept · {len(idxs)} chunks · sources: {','.join(domains)}",
                 "[" + ",".join(f"{x:.6f}" for x in centroid.tolist()) + "]",
                 len(idxs), domains, salience),
            )
            concept_id = cur.fetchone()[0]
            ids = [chunks[j]["id"] for j in idxs]
            cur.execute("UPDATE brain_index.note_chunks SET concept_id=%s WHERE id::text = ANY(%s)",
                        (concept_id, ids))
    return summaries


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args(argv)

    db = os.environ.get(DB_ENV, "")
    if not db:
        print(f"{DB_ENV} not set"); return 1
    import psycopg
    with psycopg.connect(db) as conn, conn.cursor() as cur:
        chunks = load_chunks(cur)
        clusters = greedy_cluster(chunks, args.threshold)
        summaries = build(cur, chunks, clusters, execute=args.execute)
        if args.execute:
            conn.commit()
    sizes = Counter(len(c) for c in clusters)
    print(f"{len(chunks)} curated chunks → {len(clusters)} concepts (threshold {args.threshold})")
    print(f"singletons: {sizes.get(1,0)} · largest: {max((len(c) for c in clusters), default=0)}")
    print("\nconcepts (largest first):")
    for s in summaries[:30]:
        print(f"  [{s['size']:2}] {s['name'][:52]:54} {','.join(s['domains'])[:22]}")
    print("\nDRY-RUN — re-run with --execute to write." if not args.execute
          else "\nWROTE concepts + concept_id. Reverse: UPDATE note_chunks SET concept_id=NULL; DELETE FROM concepts;")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
