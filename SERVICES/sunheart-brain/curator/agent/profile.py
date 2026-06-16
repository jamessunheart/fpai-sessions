"""User profile seed and compact context injection helpers."""
from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

log = logging.getLogger("curator.agent.profile")

ENERGY_LEVELS = {"full", "medium", "low"}
TONES = {"direct", "reflective", "story", "analytical"}
LIFE_AREAS = ("work", "relationships", "health", "finances", "creativity", "purpose")
PROFILE_COLUMNS = (
    "user_id",
    "situation",
    "goals",
    "energy_level",
    "life_areas",
    "routing_history",
    "dominant_path",
    "strengths",
    "preferred_tone",
    "avg_message_length",
    "response_speed",
    "best_session_day",
    "best_session_hour",
    "streak_days",
    "longest_streak",
    "connected_services",
    "match_tags",
    "match_open",
    "last_updated",
)


@dataclass
class UserProfile:
    user_id: str
    situation: str | None = None
    goals: list[dict[str, Any]] = field(default_factory=list)
    energy_level: str | None = None
    life_areas: dict[str, int] = field(default_factory=dict)
    routing_history: list[dict[str, Any]] = field(default_factory=list)
    dominant_path: str | None = None
    strengths: list[str] = field(default_factory=list)
    preferred_tone: str | None = None
    avg_message_length: int | None = None
    response_speed: str | None = None
    best_session_day: str | None = None
    best_session_hour: int | None = None
    streak_days: int = 0
    longest_streak: int = 0
    connected_services: dict[str, Any] = field(default_factory=dict)
    match_tags: list[Any] = field(default_factory=list)
    match_open: bool = False
    last_updated: datetime | None = None


def seed_profile(user_id: str, onboarding_answers: dict) -> UserProfile:
    extracted = _extract_onboarding(onboarding_answers)
    profile = UserProfile(
        user_id=str(user_id),
        situation=_clean_text(extracted.get("situation")),
        goals=_normalize_goals(extracted.get("goals")),
        energy_level=_normalize_choice(extracted.get("energy_level"), ENERGY_LEVELS),
        life_areas=_normalize_life_areas(extracted.get("life_areas")),
        preferred_tone=_normalize_choice(extracted.get("preferred_tone"), TONES),
        match_tags=_derive_match_tags(
            _normalize_goals(extracted.get("goals")),
            [],
            _normalize_life_areas(extracted.get("life_areas")),
        ),
        last_updated=_utcnow(),
    )
    _upsert_profile(profile)
    return profile


def update_profile_from_session(user_id: str, session_messages: list) -> None:
    user_id = str(user_id)
    existing = _get_profile(user_id) or UserProfile(user_id=user_id)
    now = _latest_message_time(session_messages) or _utcnow()
    user_texts = _message_texts(session_messages, role="user")
    all_text = "\n".join(_message_texts(session_messages)).lower()

    avg_len = _average_message_length(user_texts)
    if avg_len is not None:
        existing.avg_message_length = avg_len
    existing.response_speed = _detect_response_speed(session_messages)

    energy, confidence = _detect_energy(all_text)
    if energy and (not existing.energy_level or confidence > 0.8):
        existing.energy_level = energy

    goals, confidence = _detect_goal_updates(all_text)
    if goals and (not existing.goals or confidence > 0.8):
        existing.goals = _merge_goals(existing.goals, goals)

    routes = _extract_routes(session_messages)
    if routes:
        existing.routing_history = (existing.routing_history + routes)[-50:]
        existing.dominant_path = _dominant_path(existing.routing_history)

    existing.best_session_day = now.strftime("%A")
    existing.best_session_hour = now.hour
    existing.streak_days, existing.longest_streak = _next_streak(
        existing.last_updated,
        now,
        existing.streak_days,
        existing.longest_streak,
    )
    existing.match_tags = _derive_match_tags(existing.goals, existing.strengths, existing.life_areas)
    existing.last_updated = now.replace(tzinfo=None)
    _upsert_profile(existing)


def get_agent_context(user_id: str) -> str:
    profile = _get_profile(str(user_id))
    if not profile:
        return ""

    parts: list[str] = []
    goals = [str(g.get("goal") or "").strip() for g in profile.goals if isinstance(g, dict)]
    goals = [g for g in goals if g]
    if goals:
        parts.append("Goals: " + "; ".join(goals[:3]))
    if profile.situation:
        parts.append("Situation: " + profile.situation)
    if profile.strengths:
        parts.append("Proven strengths: " + ", ".join(profile.strengths[:4]))
    if profile.dominant_path:
        parts.append(f"Usually responds to: {profile.dominant_path} paths")
    if profile.energy_level:
        parts.append(f"Energy today: {profile.energy_level}")
    if profile.preferred_tone:
        parts.append(f"Tone: {profile.preferred_tone}")

    if not parts:
        return ""
    return _limit_tokens("[User context] " + " | ".join(parts), 200)


def profile_exists(user_id: str) -> bool:
    return _get_profile(str(user_id)) is not None


def extract_strength_from_proof(user_id: str, proof_text: str) -> None:
    strength = _extract_strength(proof_text)
    if not strength:
        return
    profile = _get_profile(str(user_id)) or UserProfile(user_id=str(user_id))
    if strength.lower() not in {item.lower() for item in profile.strengths}:
        profile.strengths.append(strength)
    profile.match_tags = _derive_match_tags(profile.goals, profile.strengths, profile.life_areas)
    profile.last_updated = _utcnow()
    _upsert_profile(profile)


def _extract_onboarding(onboarding_answers: dict) -> dict[str, Any]:
    prompt = (
        "From these onboarding answers, extract: situation, goals (with timeframes), "
        "energy_level, life_areas scores, preferred_tone. JSON only.\n\n"
        + json.dumps(onboarding_answers, ensure_ascii=False, sort_keys=True)
    )
    data = _claude_json(prompt)
    if data:
        return data
    return _heuristic_onboarding(onboarding_answers)


def _extract_strength(proof_text: str) -> str | None:
    prompt = (
        "From this proof, extract the single strongest demonstrated strength. "
        "Return JSON only: {\"strength\":\"...\"}.\n\n"
        + proof_text[:4000]
    )
    data = _claude_json(prompt)
    strength = _clean_text(data.get("strength")) if isinstance(data, dict) else None
    if strength:
        return strength
    lowered = proof_text.lower()
    if any(word in lowered for word in ("finished", "shipped", "completed", "delivered")):
        return "follow-through"
    if any(word in lowered for word in ("helped", "supported", "listened", "coached")):
        return "careful support"
    return _clean_text(proof_text).split(".")[0][:80] if _clean_text(proof_text) else None


def _claude_json(prompt: str) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception as e:
        log.info("claude extraction unavailable: %s", e)
        return {}
    if proc.returncode != 0:
        log.warning("claude extraction failed: %s", proc.stderr[:200])
        return {}
    return _parse_json_object(proc.stdout)


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return {}
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}


def _heuristic_onboarding(answers: dict) -> dict[str, Any]:
    blob = " ".join(str(v) for v in answers.values())
    lowered = blob.lower()
    situation = (
        answers.get("situation")
        or answers.get("what_brought_you_here")
        or answers.get("why")
        or blob[:240]
    )
    goals = []
    for key, value in answers.items():
        if "goal" in str(key).lower() or "want" in str(key).lower():
            goals.append({"goal": str(value), "timeframe": "", "status": "active"})
    if not goals and blob:
        goals.append({"goal": blob[:120], "timeframe": "", "status": "active"})
    tone = "analytical" if any(w in lowered for w in ("system", "plan", "strategy")) else "direct"
    energy = "low" if any(w in lowered for w in ("tired", "low", "overwhelmed")) else "medium"
    life_areas = {area: 5 for area in LIFE_AREAS}
    return {
        "situation": situation,
        "goals": goals,
        "energy_level": energy,
        "life_areas": life_areas,
        "preferred_tone": tone,
    }


def _upsert_profile(profile: UserProfile) -> None:
    row = _profile_to_row(profile)
    placeholders = ", ".join(["%s"] * len(PROFILE_COLUMNS))
    columns = ", ".join(PROFILE_COLUMNS)
    updates = ", ".join(f"{col} = EXCLUDED.{col}" for col in PROFILE_COLUMNS if col != "user_id")
    import psycopg
    from psycopg.types.json import Jsonb
    from ..db import DB_URL

    values = []
    for col in PROFILE_COLUMNS:
        value = row[col]
        if col in {"goals", "life_areas", "routing_history", "strengths", "connected_services", "match_tags"}:
            value = Jsonb(value)
        values.append(value)
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO brain_index.user_profiles ({columns})
                VALUES ({placeholders})
                ON CONFLICT (user_id) DO UPDATE SET {updates}
                """,
                values,
            )


def _get_profile(user_id: str) -> UserProfile | None:
    try:
        import psycopg
        from ..db import DB_URL

        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {', '.join(PROFILE_COLUMNS)} FROM brain_index.user_profiles WHERE user_id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
    except Exception as e:
        log.warning("user profile lookup failed for %s: %s", user_id, e)
        return None
    return _row_to_profile(row) if row else None


def _profile_to_row(profile: UserProfile) -> dict[str, Any]:
    data = profile.__dict__.copy()
    data["last_updated"] = _as_naive_datetime(profile.last_updated or _utcnow())
    return data


def _row_to_profile(row: tuple) -> UserProfile:
    data = dict(zip(PROFILE_COLUMNS, row))
    data["goals"] = data.get("goals") or []
    data["life_areas"] = data.get("life_areas") or {}
    data["routing_history"] = data.get("routing_history") or []
    data["strengths"] = data.get("strengths") or []
    data["connected_services"] = data.get("connected_services") or {}
    data["match_tags"] = data.get("match_tags") or []
    data["streak_days"] = data.get("streak_days") or 0
    data["longest_streak"] = data.get("longest_streak") or 0
    data["match_open"] = bool(data.get("match_open"))
    return UserProfile(**data)


def _normalize_goals(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    goals = []
    for item in value:
        if isinstance(item, str):
            goal = item.strip()
            if goal:
                goals.append({"goal": goal, "timeframe": "", "status": "active"})
        elif isinstance(item, dict):
            goal = _clean_text(item.get("goal"))
            if goal:
                goals.append(
                    {
                        "goal": goal,
                        "timeframe": _clean_text(item.get("timeframe")) or "",
                        "status": item.get("status") if item.get("status") in {"active", "achieved", "dropped"} else "active",
                    }
                )
    return goals


def _normalize_life_areas(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    scores = {}
    for area in LIFE_AREAS:
        try:
            score = int(value.get(area))
        except (TypeError, ValueError):
            continue
        scores[area] = max(1, min(score, 10))
    return scores


def _normalize_choice(value: Any, allowed: set[str]) -> str | None:
    text = str(value or "").strip().lower()
    return text if text in allowed else None


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _message_texts(messages: list, *, role: str | None = None) -> list[str]:
    texts = []
    for message in messages or []:
        if isinstance(message, dict):
            if role and message.get("role") != role:
                continue
            text = message.get("text") or message.get("content") or ""
        else:
            text = str(message)
        if text:
            texts.append(str(text))
    return texts


def _average_message_length(texts: list[str]) -> int | None:
    if not texts:
        return None
    return round(sum(len(text.split()) for text in texts) / len(texts))


def _detect_response_speed(messages: list) -> str | None:
    times = [_parse_message_time(m) for m in messages or [] if isinstance(m, dict)]
    times = [t for t in times if t]
    if len(times) < 2:
        return None
    times.sort()
    gaps = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
    if any(gap > 3600 for gap in gaps) and any(gap < 180 for gap in gaps):
        return "burst"
    avg = sum(gaps) / len(gaps)
    if avg < 300:
        return "fast"
    return "slow"


def _detect_energy(text: str) -> tuple[str | None, float]:
    if re.search(r"\b(full energy|energized|rested|clear|strong)\b", text):
        return "full", 0.9
    if re.search(r"\b(tired|depleted|exhausted|low energy|overwhelmed)\b", text):
        return "low", 0.9
    if re.search(r"\b(okay|medium energy|some energy|steady)\b", text):
        return "medium", 0.85
    return None, 0.0


def _detect_goal_updates(text: str) -> tuple[list[dict[str, str]], float]:
    goals = []
    for match in re.finditer(r"\b(?:my goal is|i want to|i need to)\s+([^.;\n]+)", text):
        goals.append({"goal": match.group(1).strip(), "timeframe": "", "status": "active"})
    return goals[:5], 0.85 if goals else 0.0


def _merge_goals(existing: list[dict[str, Any]], updates: list[dict[str, str]]) -> list[dict[str, Any]]:
    seen = {str(goal.get("goal", "")).lower() for goal in existing if isinstance(goal, dict)}
    merged = list(existing)
    for goal in updates:
        key = goal["goal"].lower()
        if key not in seen:
            merged.append(goal)
            seen.add(key)
    return merged[-20:]


def _extract_routes(messages: list) -> list[dict[str, Any]]:
    routes = []
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        path = message.get("path") or message.get("route_path")
        if not path:
            text = str(message.get("text") or message.get("content") or "")
            match = re.search(r"\bpath[:=]\s*([a-z0-9_-]+)", text, re.I)
            path = match.group(1) if match else None
        if path:
            routes.append(
                {
                    "path": str(path),
                    "offered_at": _iso_time(_parse_message_time(message) or _utcnow()),
                    "acted": bool(message.get("acted")),
                    "proof_id": message.get("proof_id"),
                }
            )
    return routes


def _dominant_path(routes: list[dict[str, Any]]) -> str | None:
    scores: dict[str, int] = {}
    for route in routes:
        path = str(route.get("path") or "")
        if not path:
            continue
        scores[path] = scores.get(path, 0) + (2 if route.get("acted") else 1)
    return max(scores, key=scores.get) if scores else None


def _latest_message_time(messages: list) -> datetime | None:
    times = [_parse_message_time(m) for m in messages or [] if isinstance(m, dict)]
    times = [t for t in times if t]
    return max(times) if times else None


def _parse_message_time(message: dict) -> datetime | None:
    raw = message.get("at") or message.get("timestamp") or message.get("created_at")
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _next_streak(last_updated: datetime | None, now: datetime, current: int, longest: int) -> tuple[int, int]:
    now_date = _date_utc(now)
    last_date = _date_utc(last_updated) if last_updated else None
    if last_date == now_date:
        streak = max(1, current)
    elif last_date == now_date - timedelta(days=1):
        streak = max(0, current) + 1
    else:
        streak = 1
    return streak, max(longest, streak)


def _derive_match_tags(goals: list[dict[str, Any]], strengths: list[str], life_areas: dict[str, int]) -> list[dict[str, list[str]]]:
    offer = [s for s in strengths[:5] if s]
    need = []
    for area, score in life_areas.items():
        if score <= 4:
            need.append(area)
    for goal in goals[:5]:
        text = str(goal.get("goal") or "").lower()
        for keyword in ("accountability", "design", "coaching", "tech", "health", "creative"):
            if keyword in text and keyword not in need:
                need.append(keyword)
    return [{"offer": offer, "need": need}]


def _limit_tokens(text: str, max_tokens: int) -> str:
    words = text.split()
    return " ".join(words[:max_tokens])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_naive_datetime(value: datetime) -> datetime:
    if value.tzinfo:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _date_utc(value: datetime | None):
    if value is None:
        return None
    if value.tzinfo:
        return value.astimezone(timezone.utc).date()
    return value.date()


def _iso_time(value: datetime) -> str:
    if value.tzinfo:
        return value.astimezone(timezone.utc).isoformat()
    return value.replace(tzinfo=timezone.utc).isoformat()
