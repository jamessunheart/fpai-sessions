#!/usr/bin/env python3
"""Bridge live/repo learning signals into the d010 preference dataset.

This closes the L2 gate (James greenlit 2026-06-15): curator/corrections.py captures James's
corrections into Postgres on the live bot; this bridge converts each row into the SAME preference-pair
shape tools/learn/capture_corrections.py already produces, and appends (deduped) to the training JSONL
that the reward-LoRA will consume. It also harvests repo-local independent review verdicts into
``brain_index.review_signals`` and appends those labels to the same preference dataset.

CAPTURE/PREP ONLY: reads + writes a local JSONL. Does not train, deploy, route, or grant authority.
Run under a venv that has psycopg (e.g. the bot venv) with BRAIN_INDEX_DB_URL in env:
    set -a; . /etc/sh-brain/curator.env; set +a
    /opt/sh-brain-src/.venv/bin/python tools/learn/sync_corrections_to_dataset.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# import the already-tested pair builder from the sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_corrections import make_correction_pair, append_pair, DEFAULT_DATASET  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REVIEWS_DIR = REPO_ROOT / "core" / "BUILD" / "reviews"
POSITIVE_REVIEW_VERDICTS = {"approve", "pass", "ready", "ready_for_review", "council_ready"}
NEGATIVE_REVIEW_VERDICTS = {"request_changes", "blocked", "reverted", "reversal", "fail", "failed"}


@dataclass(frozen=True)
class ReviewSignal:
    spec_id: str
    verdict: str
    reasons: str
    code_ref: str
    source_path: str

    def to_json(self) -> dict[str, str]:
        return {
            "spec_id": self.spec_id,
            "verdict": self.verdict,
            "reasons": self.reasons,
            "code_ref": self.code_ref,
            "source_path": self.source_path,
        }


def _dsn() -> str | None:
    for k in ("BRAIN_INDEX_DB_URL", "DATABASE_URL", "DB_URL"):
        v = os.environ.get(k)
        if v:
            return v
    return None


def fetch_corrections(limit: int = 5000) -> list[dict]:
    """Read correction rows from the live table. Returns [] if psycopg/DSN unavailable (safe degrade)."""
    dsn = _dsn()
    if not dsn:
        print("no DSN in env (BRAIN_INDEX_DB_URL) — nothing to sync", file=sys.stderr)
        return []
    try:
        import psycopg
    except ImportError:
        print("psycopg not available in this interpreter — run under the bot venv", file=sys.stderr)
        return []
    rows: list[dict] = []
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT conversation_id, bot_turn_id, original_response, james_correction, "
                "captured_at::text FROM brain_index.corrections ORDER BY captured_at ASC LIMIT %s",
                (limit,),
            )
            for cid, bot_turn_id, original, correction, captured_at in cur.fetchall():
                rows.append({
                    "conversation_id": cid,
                    "bot_turn_id": bot_turn_id,
                    "original_response": original or "",
                    "james_correction": correction or "",
                    "captured_at": captured_at,
                })
    return rows


def harvest_review_signals(reviews_dir: Path | str = DEFAULT_REVIEWS_DIR) -> list[ReviewSignal]:
    """Parse repo-local build/council/reversal review markdown into labeled signals."""
    root = Path(reviews_dir)
    if not root.exists():
        return []
    signals: list[ReviewSignal] = []
    for path in sorted(root.glob("*.md")):
        signal = parse_review_file(path)
        if signal:
            signals.append(signal)
    return signals


def parse_review_file(path: Path | str) -> ReviewSignal | None:
    """Return one review signal from a markdown review file, or None if unlabeled."""
    review_path = Path(path)
    text = review_path.read_text(encoding="utf-8", errors="replace")
    verdict = _extract_review_verdict(text)
    if not verdict:
        return None
    spec_id = _extract_spec_id(review_path, text)
    reasons = _extract_reasons(text)
    if not spec_id or not reasons:
        return None
    rel = _repo_relative(review_path)
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
    return ReviewSignal(
        spec_id=spec_id,
        verdict=verdict,
        reasons=reasons,
        code_ref=f"{rel}#sha256={digest}",
        source_path=rel,
    )


def insert_review_signals(signals: list[ReviewSignal]) -> dict[str, int | str | bool]:
    """Append new review signals to brain_index.review_signals when a DSN is configured."""
    dsn = _dsn()
    if not dsn:
        return {"db_available": False, "inserted": 0, "skipped_dupes": 0, "reason": "no DSN"}
    if not signals:
        return {"db_available": True, "inserted": 0, "skipped_dupes": 0}
    try:
        import psycopg  # type: ignore
        psycopg2_mode = False
    except ImportError:
        try:
            import psycopg2 as psycopg  # type: ignore
            psycopg2_mode = True
        except ImportError:
            return {"db_available": False, "inserted": 0, "skipped_dupes": 0, "reason": "psycopg unavailable"}

    inserted = 0
    skipped = 0
    with psycopg.connect(dsn) as conn:  # type: ignore[attr-defined]
        if psycopg2_mode:
            conn.autocommit = True
        with conn.cursor() as cur:
            _ensure_review_signals_table(cur)
            for signal in signals:
                cur.execute(
                    """
                    INSERT INTO brain_index.review_signals (spec_id, verdict, reasons, code_ref)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (code_ref) DO NOTHING
                    """,
                    (signal.spec_id, signal.verdict, signal.reasons, signal.code_ref),
                )
                rowcount = int(getattr(cur, "rowcount", 0) or 0)
                if rowcount:
                    inserted += 1
                else:
                    skipped += 1
        if not psycopg2_mode:
            conn.commit()
    return {"db_available": True, "inserted": inserted, "skipped_dupes": skipped}


def _ensure_review_signals_table(cur: Any) -> None:
    cur.execute("CREATE SCHEMA IF NOT EXISTS brain_index")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS brain_index.review_signals (
            id SERIAL PRIMARY KEY,
            spec_id TEXT NOT NULL,
            verdict TEXT NOT NULL,
            reasons TEXT NOT NULL,
            code_ref TEXT NOT NULL UNIQUE,
            captured_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )


def _review_signal_pair(signal: ReviewSignal) -> dict[str, Any] | None:
    prompt = f"Spec: {signal.spec_id}\nReview evidence: {signal.code_ref}"
    if signal.verdict in POSITIVE_REVIEW_VERDICTS:
        preferred = f"Treat this build pattern as reusable only with the reviewer evidence: {signal.reasons}"
        rejected = "Block or discard this build pattern without reviewer evidence."
        verdict = "review_approved"
    elif signal.verdict in NEGATIVE_REVIEW_VERDICTS:
        preferred = f"Hold or repair this build before reuse because the review found: {signal.reasons}"
        rejected = "Merge or reuse this build pattern despite unresolved review findings."
        verdict = "review_rejected"
    else:
        return None
    return make_correction_pair(
        rejected=rejected,
        preferred=preferred,
        prompt=prompt,
        source="brain_index.review_signals",
        metadata={
            "spec_id": signal.spec_id,
            "review_verdict": signal.verdict,
            "code_ref": signal.code_ref,
            "source_path": signal.source_path,
            "training_signal": verdict,
        },
        captured_at=None,
    )


def _extract_review_verdict(text: str) -> str:
    head = text[:4000]
    blocked_head = head.lower()
    if "blocked" in blocked_head and "protected audit/improve layer" in blocked_head:
        return "blocked"
    patterns = [
        r"\*\*Verdict:\*\*\s*([^`\n\r*]+)",
        r"\*\*Verdict:\s*([^`\n\r*]+)\*\*",
        r"^Verdict:\s*([^`\n\r*]+)",
        r"\*\*Council verdict:\*\*\s*([^.\n\r]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, head, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return _normalize_review_verdict(match.group(1))
    if re.search(r"\b(reverted|auto-revert|reversal)\b", head, flags=re.IGNORECASE):
        return "reversal"
    return ""


def _normalize_review_verdict(raw: str) -> str:
    text = raw.strip().lower()
    text = text.split("·", 1)[0].split("-", 1)[0].strip()
    text = re.sub(r"[✅🔴🟢🟡🔶:]", " ", text)
    text = re.sub(r"[^a-z0-9_ ]+", " ", text)
    text = "_".join(text.split())
    if "request_changes" in text or "changes_requested" in text:
        return "request_changes"
    if "approve" in text or text == "approved":
        return "approve"
    if text.startswith("pass") or "mergeable" in text:
        return "pass"
    if "blocked" in text:
        return "blocked"
    if "revert" in text or "reversal" in text:
        return "reversal"
    if text.startswith("ready") or "ready_for_independent" in text:
        return "council_ready"
    if "fail" in text:
        return "failed"
    return text


def _extract_spec_id(path: Path, text: str) -> str:
    name = path.name
    for pattern in (
        r"build-(SPEC_[A-Za-z0-9_.-]+)\.md$",
        r"^(SPEC_[A-Za-z0-9_.-]+)\.(?:review|council)\.md$",
        r"^(SPEC_[A-Za-z0-9_.-]+)\.md$",
        r"^([0-9]{3}-[A-Za-z0-9_.-]+)\.review\.md$",
    ):
        match = re.search(pattern, name)
        if match:
            return match.group(1)
    match = re.search(r"Branch\s+`build/([^`]+)`", text)
    if match:
        return match.group(1)
    match = re.search(r"#(?: AI Review -| Review —| )\s*([A-Za-z0-9_.:/-]+)", text)
    if match:
        return match.group(1).replace("build/", "")
    return path.stem


def _extract_reasons(text: str, *, max_chars: int = 1800) -> str:
    parts: list[str] = []
    summary = re.search(r"\*\*Summary:\*\*\s*(.+)", text, flags=re.IGNORECASE)
    if summary:
        parts.append(summary.group(1).strip())
    if "## Findings" in text:
        findings = text.split("## Findings", 1)[1]
        findings = re.split(r"\n##\s+", findings, maxsplit=1)[0]
        bullets = [line.strip("-* \t") for line in findings.splitlines() if line.strip().startswith("-")]
        parts.extend(bullets[:6])
    elif "## Council Lenses" in text:
        lenses = text.split("## Council Lenses", 1)[1]
        lenses = re.split(r"\n## Verdict", lenses, maxsplit=1)[0]
        sentences = re.split(r"(?<=[.!?])\s+", " ".join(lenses.split()))
        parts.extend(sentence for sentence in sentences[:6] if sentence)
    else:
        lead_lines = [
            line.strip("# \t")
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("-")
        ]
        parts.extend(lead_lines[:3])
        bullets = [line.strip("-* \t") for line in text.splitlines() if line.strip().startswith("-")]
        parts.extend(bullets[:6])
    if not parts:
        body = "\n".join(line.strip() for line in text.splitlines()[1:12] if line.strip())
        parts.append(body)
    return " ".join(" ".join(parts).split())[:max_chars]


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sync(
    *,
    dataset: Path | str = DEFAULT_DATASET,
    dry_run: bool = False,
    include_corrections: bool = True,
    include_reviews: bool = True,
    reviews_dir: Path | str = DEFAULT_REVIEWS_DIR,
) -> dict:
    rows = fetch_corrections() if include_corrections else []
    added = skipped = 0
    for r in rows:
        if not r["original_response"].strip() or not r["james_correction"].strip():
            continue
        pair = make_correction_pair(
            rejected=r["original_response"],
            preferred=r["james_correction"],
            prompt="",
            source="brain_index.corrections",
            metadata={"conversation_id": r["conversation_id"], "bot_turn_id": r["bot_turn_id"]},
            captured_at=r["captured_at"],
        )
        if dry_run:
            added += 1
            continue
        if append_pair(pair, dataset, dedupe=True):
            added += 1
        else:
            skipped += 1

    review_signals = harvest_review_signals(reviews_dir) if include_reviews else []
    review_db = insert_review_signals(review_signals) if include_reviews and not dry_run else {
        "db_available": False,
        "inserted": 0,
        "skipped_dupes": 0,
        "reason": "dry-run" if dry_run else "disabled",
    }
    review_added = review_skipped = 0
    for signal in review_signals:
        pair = _review_signal_pair(signal)
        if not pair:
            continue
        if dry_run:
            review_added += 1
            continue
        if append_pair(pair, dataset, dedupe=True):
            review_added += 1
        else:
            review_skipped += 1
    return {
        "corrections_read": len(rows),
        "corrections_added": added,
        "corrections_skipped_dupes": skipped,
        "review_signals_read": len(review_signals),
        "review_signals_db": review_db,
        "review_pairs_added": review_added,
        "review_pairs_skipped_dupes": review_skipped,
        "dataset": str(dataset),
        "dry_run": dry_run,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Sync live corrections and repo review verdicts -> preference dataset.")
    p.add_argument("--dry-run", action="store_true", help="Count without writing")
    p.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    p.add_argument("--reviews-dir", type=Path, default=DEFAULT_REVIEWS_DIR)
    p.add_argument("--skip-corrections", action="store_true", help="Do not read brain_index.corrections")
    p.add_argument("--skip-reviews", action="store_true", help="Do not parse/insert review signals")
    args = p.parse_args(argv)
    print(json.dumps(
        sync(
            dataset=args.dataset,
            dry_run=args.dry_run,
            include_corrections=not args.skip_corrections,
            include_reviews=not args.skip_reviews,
            reviews_dir=args.reviews_dir,
        ),
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
