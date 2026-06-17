"""Advisory per-person Becoming Engine state for One Chat.

This is a SEE model, not a proactive nurture loop. It observes a person's
conversation, stores a reversible journey-state row, and renders a bounded
prompt block so the bot can speak to the next step without blocking answers.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("curator.becoming")

STAGES = ("spark", "awaken", "activate", "build", "contribute", "coach")
DEFAULT_STAGE = "spark"

_STAGE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("coach", ("coach", "mentor", "guide others", "clients", "teach", "facilitate")),
    ("contribute", ("contribute", "serve", "help others", "community", "team", "volunteer", "steward")),
    ("build", ("build", "building", "launch", "project", "offer", "business", "system", "ship", "create")),
    ("activate", ("start", "next step", "ready", "commit", "practice", "habit", "plan", "accountability")),
    ("awaken", ("stuck", "blocked", "change my life", "full potential", "purpose", "clarity", "meaning", "awakening")),
    ("spark", ("curious", "interested", "what is this", "learn more", "explore", "tell me more")),
)

_INTENT_PATTERNS = (
    re.compile(r"\b(?:i want to|i'd like to|i need to|i am trying to|i'm trying to)\s+(.+)", re.I | re.S),
    re.compile(r"\b(?:my goal is|the goal is|i intend to)\s+(.+)", re.I | re.S),
)
_BLOCKER_PATTERNS = (
    re.compile(r"\b(?:blocked by|stuck on|stuck with|can't because|cannot because|held back by)\s+(.+)", re.I | re.S),
    re.compile(r"\b(?:my blocker is|the blocker is)\s+(.+)", re.I | re.S),
)


@dataclass(frozen=True)
class BecomingState:
    person_id: str
    stage: str = DEFAULT_STAGE
    identity_contact: dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    stated_intent: str = ""
    proofs: dict[str, Any] = field(default_factory=dict)
    current_blocker: str = ""
    cora_balance: float | None = None
    last_touch: str | None = None
    next_nurture_action: str = ""
    updated_at: str | None = None


def infer_becoming_update(
    message: str,
    *,
    current: BecomingState | None = None,
    person_id: str = "",
    source: str = "telegram",
    identity_contact: dict[str, Any] | None = None,
) -> BecomingState:
    """Infer an advisory state update from one user message."""
    text = " ".join((message or "").split())
    base = current or BecomingState(person_id=person_id, source=source)
    if not text:
        return base

    inferred_stage = _infer_stage(text) or base.stage or DEFAULT_STAGE
    stage = _furthest_stage(base.stage, inferred_stage)
    stated_intent = _extract_first(_INTENT_PATTERNS, text) or base.stated_intent
    blocker = _extract_first(_BLOCKER_PATTERNS, text) or base.current_blocker
    proofs = _append_signal(base.proofs, text, stage)
    now = datetime.now(timezone.utc).isoformat()
    merged_identity = dict(base.identity_contact or {})
    if identity_contact:
        merged_identity.update({k: v for k, v in identity_contact.items() if v not in (None, "")})

    return replace(
        base,
        person_id=base.person_id or person_id,
        source=source or base.source,
        identity_contact=merged_identity,
        stage=stage,
        stated_intent=_clip(stated_intent, 500),
        proofs=proofs,
        current_blocker=_clip(blocker, 500),
        last_touch=now,
        next_nurture_action=next_nurture_action(stage, stated_intent=stated_intent, blocker=blocker),
        updated_at=now,
    )


def next_nurture_action(stage: str, *, stated_intent: str = "", blocker: str = "") -> str:
    if blocker:
        return f"Reflect the blocker and offer one small unblock step: {_clip(blocker, 120)}"
    if stage == "spark":
        return "Help them name what they are curious about and invite one honest intent."
    if stage == "awaken":
        return "Mirror the desired change and ask for the smallest real-life bottleneck."
    if stage == "activate":
        return "Convert intent into one concrete next action with proof."
    if stage == "build":
        return "Help shape the project or offer into a small shippable proof."
    if stage == "contribute":
        return "Route their energy toward one useful contribution with clear boundaries."
    if stage == "coach":
        return "Support them as a guide and look for coach-matching or CORA service signals."
    return "Ask what becoming looks like for them this week."


async def capture_becoming_exchange(
    *,
    person_id: str,
    user_message: str,
    source: str = "telegram",
    identity_contact: dict[str, Any] | None = None,
) -> BecomingState | None:
    """Best-effort DB capture. Failures are logged and never raised."""
    if not person_id or not user_message.strip():
        return None
    try:
        current = await fetch_becoming_state(person_id)
        updated = infer_becoming_update(
            user_message,
            current=current,
            person_id=person_id,
            source=source,
            identity_contact=identity_contact,
        )
        await write_becoming_state(updated)
        return updated
    except Exception as e:
        log.warning("becoming capture skipped person=%s: %s", person_id, e)
        return None


async def fetch_becoming_state(person_id: str) -> BecomingState | None:
    try:
        from .db import connect
    except ImportError:
        return None
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT person_id, identity_contact, source, stage, stated_intent,
                       proofs, current_blocker, cora_balance, last_touch::text,
                       next_nurture_action, updated_at::text
                  FROM brain_index.becoming
                 WHERE person_id = %s
                 LIMIT 1
                """,
                (str(person_id),),
            )
            row = await cur.fetchone()
    return _state_from_row(row) if row else None


async def write_becoming_state(state: BecomingState) -> None:
    try:
        from .db import connect
        from psycopg.types.json import Jsonb
    except ImportError:
        return
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO brain_index.becoming
                    (person_id, identity_contact, source, stage, stated_intent,
                     proofs, current_blocker, cora_balance, last_touch,
                     next_nurture_action, updated_at)
                VALUES (%s, %s::jsonb, %s, %s, %s, %s::jsonb, %s, %s, %s::timestamptz, %s, NOW())
                ON CONFLICT (person_id) DO UPDATE SET
                    identity_contact = brain_index.becoming.identity_contact || EXCLUDED.identity_contact,
                    source = EXCLUDED.source,
                    stage = EXCLUDED.stage,
                    stated_intent = COALESCE(NULLIF(EXCLUDED.stated_intent, ''), brain_index.becoming.stated_intent),
                    proofs = EXCLUDED.proofs,
                    current_blocker = COALESCE(NULLIF(EXCLUDED.current_blocker, ''), brain_index.becoming.current_blocker),
                    cora_balance = COALESCE(EXCLUDED.cora_balance, brain_index.becoming.cora_balance),
                    last_touch = EXCLUDED.last_touch,
                    next_nurture_action = EXCLUDED.next_nurture_action,
                    updated_at = NOW()
                """,
                (
                    state.person_id,
                    Jsonb(state.identity_contact),
                    state.source,
                    state.stage,
                    state.stated_intent,
                    Jsonb(state.proofs),
                    state.current_blocker,
                    state.cora_balance,
                    state.last_touch,
                    state.next_nurture_action,
                ),
            )


async def render_becoming_context(person_id: str, *, max_chars: int = 900) -> str:
    try:
        state = await fetch_becoming_state(person_id)
    except Exception as e:
        log.warning("becoming context lookup skipped person=%s: %s", person_id, e)
        return ""
    return render_becoming_state(state, max_chars=max_chars) if state else ""


def render_becoming_state(state: BecomingState, *, max_chars: int = 900) -> str:
    lines = [
        "--- BECOMING STATE (advisory, per-person) ---",
        "Use this to see the person and speak to their next step. Do not proactively message them, gate answers, make commitments, or treat this as a diagnosis.",
        f"Person: {state.person_id}",
        f"Stage: {state.stage}",
    ]
    if state.stated_intent:
        lines.append(f"Stated intent: {_clean_line(state.stated_intent)}")
    if state.current_blocker:
        lines.append(f"Current blocker: {_clean_line(state.current_blocker)}")
    if state.next_nurture_action:
        lines.append(f"Next nurture action: {_clean_line(state.next_nurture_action)}")
    if state.cora_balance is not None:
        lines.append(f"CORA balance: {state.cora_balance:g}")
    signals = (state.proofs or {}).get("signals") or []
    if signals:
        lines.append("Recent becoming signals:")
        for item in signals[-3:]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('stage', DEFAULT_STAGE)}: {_clean_line(str(item.get('text') or ''))}")
    rendered = "\n".join(lines)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[: max(0, max_chars - 20)].rsplit("\n", 1)[0] + "\n- ... bounded"


def _infer_stage(text: str) -> str:
    low = text.lower()
    for stage, keywords in _STAGE_KEYWORDS:
        if any(keyword in low for keyword in keywords):
            return stage
    return DEFAULT_STAGE


def _furthest_stage(current: str, inferred: str) -> str:
    try:
        return STAGES[max(STAGES.index(current), STAGES.index(inferred))]
    except ValueError:
        return inferred if inferred in STAGES else DEFAULT_STAGE


def _extract_first(patterns: tuple[re.Pattern[str], ...], text: str) -> str:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return _clip(match.group(1).split(".")[0].strip(" ,;:-"), 500)
    return ""


def _append_signal(proofs: dict[str, Any], text: str, stage: str) -> dict[str, Any]:
    merged = dict(proofs or {})
    signals = list(merged.get("signals") or [])
    signals.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "text": _clip(text, 240),
        }
    )
    merged["signals"] = signals[-12:]
    return merged


def _state_from_row(row: Any) -> BecomingState:
    return BecomingState(
        person_id=str(row[0]),
        identity_contact=dict(row[1] or {}),
        source=str(row[2] or "unknown"),
        stage=str(row[3] or DEFAULT_STAGE),
        stated_intent=str(row[4] or ""),
        proofs=dict(row[5] or {}),
        current_blocker=str(row[6] or ""),
        cora_balance=float(row[7]) if row[7] is not None else None,
        last_touch=str(row[8] or "") or None,
        next_nurture_action=str(row[9] or ""),
        updated_at=str(row[10] or "") or None,
    )


def _clip(value: str, limit: int) -> str:
    value = " ".join((value or "").split())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _clean_line(value: str) -> str:
    return _clip(value.replace("\n", " "), 240)
