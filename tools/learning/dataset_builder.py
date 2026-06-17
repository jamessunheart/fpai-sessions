#!/usr/bin/env python3
"""Build gated GLM-5.2 training JSONL from FPAI learning signals.

The builder is intentionally capture/export only. It can read fixture data or,
when explicitly requested, the live ``brain_index`` database. It refuses to
write a dataset until the minimum correction/example gates are satisfied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path(os.environ.get("LEARNING_DATASET_OUTPUT", "/opt/fpai-build/learning_datasets/glm52_training.jsonl"))
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
MIN_EXAMPLES = 50
MIN_CORRECTIONS = 50

SYSTEM_PROMPT = (
    "You are the Full Potential OS assistant. Follow James's corrections, preserve "
    "private boundaries, name concrete next moves, and prefer reversible defaults."
)
APPROVED_VERDICTS = {"approve", "approved", "pass", "passed", "done", "merged", "success", "successful"}
BLOCKED_VERDICTS = {"blocked", "reverted", "failed", "fail", "request_changes", "changes_requested"}
HIGH_QUALITY_THRESHOLD = 0.8
LOW_QUALITY_THRESHOLD = 0.3


class InsufficientExamples(ValueError):
    """Raised when dataset export would train on too little signal."""


@dataclass(frozen=True)
class ExportStats:
    corrections: int
    merge_outcomes: int
    probe_sessions: int
    examples: int

    def to_json(self) -> dict[str, int]:
        return {
            "corrections": self.corrections,
            "merge_outcomes": self.merge_outcomes,
            "probe_sessions": self.probe_sessions,
            "examples": self.examples,
        }


def build_examples(
    *,
    corrections: Iterable[dict[str, Any]] = (),
    merge_outcomes: Iterable[dict[str, Any]] = (),
    probe_sessions: Iterable[dict[str, Any]] = (),
) -> tuple[list[dict[str, Any]], ExportStats]:
    """Return HF chat-format examples and source counts."""
    correction_rows = list(corrections)
    merge_rows = list(merge_outcomes)
    probe_rows = list(probe_sessions)

    examples: list[dict[str, Any]] = []
    examples.extend(_examples_from_corrections(correction_rows))
    examples.extend(_examples_from_merge_outcomes(merge_rows))
    examples.extend(_examples_from_probe_sessions(probe_rows))

    unique: dict[str, dict[str, Any]] = {}
    for example in examples:
        unique.setdefault(str(example["id"]), example)
    ordered = [unique[key] for key in sorted(unique)]
    stats = ExportStats(
        corrections=len(correction_rows),
        merge_outcomes=len(merge_rows),
        probe_sessions=len(probe_rows),
        examples=len(ordered),
    )
    return ordered, stats


def export_jsonl(
    examples: list[dict[str, Any]],
    output: Path | str = DEFAULT_OUTPUT,
    *,
    stats: ExportStats | None = None,
    min_examples: int = MIN_EXAMPLES,
    min_corrections: int = MIN_CORRECTIONS,
) -> Path:
    """Write examples to JSONL after strict minimum-data gates."""
    correction_count = stats.corrections if stats else _count_source(examples, "brain_index.corrections")
    if correction_count < min_corrections:
        raise InsufficientExamples(f"need at least {min_corrections} corrections before export; found {correction_count}")
    if len(examples) < min_examples:
        raise InsufficientExamples(f"need at least {min_examples} examples before export; found {len(examples)}")
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for example in examples:
            validate_example(example)
            handle.write(json.dumps(example, sort_keys=True) + "\n")
    return path


def validate_example(example: dict[str, Any]) -> None:
    """Validate the chat/DPO shape used by this builder."""
    messages = example.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("example.messages must be a non-empty list")
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in {"system", "user", "assistant"} or not message.get("content"):
            raise ValueError("each message must have role and content")
    if example.get("format") == "dpo":
        for key in ("chosen", "rejected"):
            turns = example.get(key)
            if not isinstance(turns, list) or not turns:
                raise ValueError(f"DPO example missing {key} turns")
            if any(turn.get("role") != "assistant" or not turn.get("content") for turn in turns if isinstance(turn, dict)):
                raise ValueError(f"DPO {key} turns must be assistant messages")
    elif example.get("format") == "sft":
        if messages[-1].get("role") != "assistant":
            raise ValueError("SFT examples must end with an assistant turn")
    else:
        raise ValueError("example.format must be dpo or sft")


def load_fixture(path: Path | str) -> dict[str, list[dict[str, Any]]]:
    """Load fixture JSON with corrections, merge_outcomes, and probe_sessions arrays."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("fixture must be a JSON object")
    return {
        "corrections": _list_of_dicts(data.get("corrections", [])),
        "merge_outcomes": _list_of_dicts(data.get("merge_outcomes", [])),
        "probe_sessions": _list_of_dicts(data.get("probe_sessions", [])),
    }


def load_ops_ledger_merge_outcomes(path: Path | str = DEFAULT_OPS_LEDGER) -> list[dict[str, Any]]:
    """Read merge/build outcomes from an ops-ledger JSONL path."""
    ledger = Path(path)
    if not ledger.exists():
        return []
    rows: list[dict[str, Any]] = []
    with ledger.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            verdict = _verdict(row)
            if verdict in APPROVED_VERDICTS | BLOCKED_VERDICTS or row.get("event") in {"merge_outcome", "build_review", "auto_revert"}:
                rows.append(row)
    return rows


def load_live_brain_index(limit: int = 5000) -> dict[str, list[dict[str, Any]]]:
    """Opt-in live DB reader. Returns empty sources if DSN/dependency is unavailable."""
    dsn = os.environ.get("BRAIN_INDEX_DSN") or os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        return {"corrections": [], "probe_sessions": []}
    try:
        import psycopg  # type: ignore
    except ImportError:
        try:
            import psycopg2 as psycopg  # type: ignore
        except ImportError:
            return {"corrections": [], "probe_sessions": []}

    result: dict[str, list[dict[str, Any]]] = {"corrections": [], "probe_sessions": []}
    with psycopg.connect(dsn) as conn:  # type: ignore[attr-defined]
        with conn.cursor() as cur:
            if _table_exists(cur, "corrections"):
                has_messages = _table_exists(cur, "tg_messages")
                context_sql = (
                    """
                    (
                      SELECT prev_user.text
                      FROM brain_index.tg_messages bot_msg
                      JOIN LATERAL (
                        SELECT text
                        FROM brain_index.tg_messages user_msg
                        WHERE user_msg.chat_id = c.conversation_id
                          AND user_msg.role = 'user'
                          AND user_msg.at <= bot_msg.at
                        ORDER BY user_msg.at DESC
                        LIMIT 1
                      ) prev_user ON TRUE
                      WHERE bot_msg.id = c.bot_turn_id
                    ) AS context,
                    """
                    if has_messages
                    else "''::text AS context,"
                )
                cur.execute(
                    f"""
                    SELECT row_to_json(t)
                    FROM (
                      SELECT id::text, conversation_id, bot_turn_id::text, {context_sql} original_response,
                             james_correction, captured_at::text
                      FROM brain_index.corrections c
                      ORDER BY captured_at ASC
                      LIMIT %s
                    ) AS t
                    """,
                    (limit,),
                )
                result["corrections"] = [row[0] for row in cur.fetchall() if isinstance(row[0], dict)]
            if _table_exists(cur, "probe_sessions"):
                cur.execute(
                    """
                    SELECT row_to_json(t)
                    FROM (
                      SELECT probe_id, pool, initiated_at::text, last_message_at::text,
                             engaged, drop_off_message, completed_spark,
                             completed_onboarding, quality_score, corrections_triggered,
                             last_message, notes
                      FROM brain_index.probe_sessions
                      WHERE quality_score IS NOT NULL
                      ORDER BY initiated_at ASC
                      LIMIT %s
                    ) AS t
                    """,
                    (limit,),
                )
                result["probe_sessions"] = [row[0] for row in cur.fetchall() if isinstance(row[0], dict)]
    return result


def _examples_from_corrections(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        rejected = _clean(_first(row, "original_response", "rejected", "original"))
        chosen = _clean(_first(row, "corrected_response", "james_correction", "chosen", "preferred", "correction"))
        if not rejected or not chosen:
            continue
        context = _clean(_first(row, "context", "prompt", "user_message")) or "James corrected a prior assistant answer."
        source_id = _clean(_first(row, "id", "bot_turn_id", "captured_at")) or str(idx)
        examples.append(
            {
                "id": _stable_id("correction", source_id, context, chosen, rejected),
                "format": "dpo",
                "source": "brain_index.corrections",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context},
                ],
                "chosen": [{"role": "assistant", "content": chosen}],
                "rejected": [{"role": "assistant", "content": rejected}],
                "metadata": {
                    "captured_at": _clean(_first(row, "timestamp", "captured_at")),
                    "conversation_id": _clean(row.get("conversation_id")),
                    "training_signal": "james_correction",
                },
            }
        )
    return examples


def _examples_from_merge_outcomes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        verdict = _verdict(row)
        if verdict not in APPROVED_VERDICTS:
            continue
        spec = _clean(_first(row, "spec", "build", "branch", "id", "slug"))
        diff = _clean(_first(row, "code_diff", "diff", "files_changed", "files"))
        pattern = _clean(_first(row, "good_build_pattern", "summary", "notes", "proof", "result"))
        if not spec or not pattern:
            continue
        user = "\n".join(part for part in (f"Spec: {spec}", f"Context/diff: {diff}" if diff else "") if part)
        examples.append(
            {
                "id": _stable_id("merge", str(idx), spec, pattern),
                "format": "sft",
                "source": "ops_ledger.merge_outcomes",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": pattern},
                ],
                "metadata": {"verdict": verdict, "training_signal": "approved_build_pattern"},
            }
        )
    return examples


def _examples_from_probe_sessions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        score = _float_or_none(row.get("quality_score"))
        if score is None:
            continue
        prompt = _clean(_first(row, "context", "notes", "pool", "probe_id")) or "Probe conversation quality signal."
        answer = _clean(_first(row, "preferred_response", "last_message", "summary", "notes"))
        if score >= HIGH_QUALITY_THRESHOLD and answer:
            examples.append(
                {
                    "id": _stable_id("probe-high", str(idx), prompt, answer),
                    "format": "sft",
                    "source": "brain_index.probe_sessions",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": answer},
                    ],
                    "metadata": {"quality_score": score, "training_signal": "high_quality_probe_session"},
                }
            )
            continue
        rejected = _clean(_first(row, "rejected_response", "last_message", "summary"))
        chosen = _clean(_first(row, "corrected_response", "preferred_response"))
        if score <= LOW_QUALITY_THRESHOLD and chosen and rejected:
            examples.append(
                {
                    "id": _stable_id("probe-low", str(idx), prompt, chosen, rejected),
                    "format": "dpo",
                    "source": "brain_index.probe_sessions",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "chosen": [{"role": "assistant", "content": chosen}],
                    "rejected": [{"role": "assistant", "content": rejected}],
                    "metadata": {"quality_score": score, "training_signal": "low_quality_probe_session"},
                }
            )
    return examples


def _table_exists(cur: Any, table_name: str) -> bool:
    cur.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'brain_index' AND table_name = %s)",
        (table_name,),
    )
    return bool(cur.fetchone()[0])


def _verdict(row: dict[str, Any]) -> str:
    return _clean(_first(row, "verdict", "merge_outcome", "outcome", "result", "status")).lower().replace(" ", "_")


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _count_source(examples: list[dict[str, Any]], source: str) -> int:
    return sum(1 for example in examples if example.get("source") == source)


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("\n".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return f"learn-{digest[:16]}"


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return ""


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return " ".join(str(value).split())


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export gated GLM-5.2 learning JSONL.")
    parser.add_argument("--fixture", type=Path, help="JSON fixture with corrections/merge_outcomes/probe_sessions arrays")
    parser.add_argument("--from-live-db", action="store_true", help="Read brain_index.corrections and probe_sessions from configured DSN")
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-examples", type=int, default=MIN_EXAMPLES)
    parser.add_argument("--min-corrections", type=int, default=MIN_CORRECTIONS)
    parser.add_argument("--dry-run", action="store_true", help="Validate and print counts without writing JSONL")
    args = parser.parse_args(argv)

    sources = {"corrections": [], "merge_outcomes": [], "probe_sessions": []}
    if args.fixture:
        sources = load_fixture(args.fixture)
    if args.from_live_db:
        live = load_live_brain_index()
        sources["corrections"].extend(live.get("corrections", []))
        sources["probe_sessions"].extend(live.get("probe_sessions", []))
    sources["merge_outcomes"].extend(load_ops_ledger_merge_outcomes(args.ops_ledger))

    examples, stats = build_examples(**sources)
    result = {"stats": stats.to_json(), "output": str(args.output), "dry_run": args.dry_run}
    try:
        if not args.dry_run:
            export_jsonl(
                examples,
                args.output,
                stats=stats,
                min_examples=args.min_examples,
                min_corrections=args.min_corrections,
            )
        else:
            if stats.corrections < args.min_corrections or stats.examples < args.min_examples:
                raise InsufficientExamples(
                    f"dry-run gate blocked: corrections={stats.corrections}/{args.min_corrections}, "
                    f"examples={stats.examples}/{args.min_examples}"
                )
            for example in examples:
                validate_example(example)
    except InsufficientExamples as exc:
        print(json.dumps({**result, "ok": False, "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({**result, "ok": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
