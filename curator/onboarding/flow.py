"""User onboarding flow from beacon touch to Agent Passport memory.

The live Hermes gateway calls ``start_onboarding`` for a new user. Database
writes are disabled unless ``HERMES_DISABLE=0`` so importing or smoke-running
this module cannot mutate production by accident.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
import sqlite3
from typing import Any, Protocol


ONBOARDING_CORA_AWARD = 25
VALID_PATHS = {
    "clarity_reflection",
    "action_plan",
    "camp_zen_invite",
    "community_call",
    "fi_art_idea",
    "service_match",
    "human_guide",
    "video_link",
}


@dataclass(frozen=True)
class HermesMessage:
    user_id: str
    text: str
    channel: str = "one_chat"
    beacon_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HermesResponse:
    user_id: str
    text: str
    onboarding_path: str | None = None
    cora_awarded: int = 0
    onboarding_complete: bool = False


@dataclass(frozen=True)
class BeaconContext:
    beacon_id: str
    source: str
    campaign: str
    expected_intent: str
    opening_tone: str


@dataclass(frozen=True)
class PassportFields:
    situation: str
    goals: str
    energy: str


class OnboardingStore(Protocol):
    def load_beacon(self, beacon_id: str | None) -> BeaconContext | None:
        ...

    def save_passport(
        self,
        *,
        user_id: str,
        fields: PassportFields,
        beacon_id: str | None,
        channel: str,
        onboarding_path: str,
        cora_balance: int,
    ) -> None:
        ...

    def flag_onboarded(self, *, user_id: str, channel: str) -> None:
        ...

    def write_thread(self, *, user_id: str, channel: str, role: str, text: str) -> None:
        ...

    def increment_beacon_conversion(self, beacon_id: str | None) -> None:
        ...


class DisabledStore:
    """No-op store used unless Hermes explicitly enables live writes."""

    def load_beacon(self, beacon_id: str | None) -> BeaconContext | None:
        return None

    def save_passport(
        self,
        *,
        user_id: str,
        fields: PassportFields,
        beacon_id: str | None,
        channel: str,
        onboarding_path: str,
        cora_balance: int,
    ) -> None:
        return None

    def flag_onboarded(self, *, user_id: str, channel: str) -> None:
        return None

    def write_thread(self, *, user_id: str, channel: str, role: str, text: str) -> None:
        return None

    def increment_beacon_conversion(self, beacon_id: str | None) -> None:
        return None


class SQLiteOnboardingStore:
    """Small local/test store with the same logical tables as brain_index."""

    def __init__(self, path: str):
        self.path = path
        self.migrate()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def migrate(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS beacons (
                    beacon_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    campaign TEXT NOT NULL,
                    expected_intent TEXT NOT NULL,
                    opening_tone TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    click_count INTEGER NOT NULL DEFAULT 0,
                    converted_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS agent_passports (
                    user_id TEXT PRIMARY KEY,
                    goals TEXT NOT NULL,
                    situation TEXT NOT NULL,
                    energy TEXT NOT NULL,
                    beacon_id TEXT,
                    channel TEXT NOT NULL,
                    onboarding_path TEXT NOT NULL,
                    cora_balance INTEGER NOT NULL DEFAULT 0,
                    proof_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS user_channels (
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    onboarded INTEGER NOT NULL DEFAULT 0,
                    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, channel)
                );

                CREATE TABLE IF NOT EXISTS thread (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    surface TEXT NOT NULL,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL
                );
                """
            )
            for beacon in seed_beacons():
                conn.execute(
                    """
                    INSERT OR IGNORE INTO beacons
                        (beacon_id, source, campaign, expected_intent, opening_tone)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        beacon.beacon_id,
                        beacon.source,
                        beacon.campaign,
                        beacon.expected_intent,
                        beacon.opening_tone,
                    ),
                )

    def load_beacon(self, beacon_id: str | None) -> BeaconContext | None:
        if not beacon_id:
            return None
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT beacon_id, source, campaign, expected_intent, opening_tone
                  FROM beacons
                 WHERE beacon_id = ?
                """,
                (beacon_id,),
            ).fetchone()
        if not row:
            return None
        return BeaconContext(**dict(row))

    def save_passport(
        self,
        *,
        user_id: str,
        fields: PassportFields,
        beacon_id: str | None,
        channel: str,
        onboarding_path: str,
        cora_balance: int,
    ) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_passports
                    (user_id, goals, situation, energy, beacon_id, channel,
                     onboarding_path, cora_balance, proof_count, created_at, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    goals = excluded.goals,
                    situation = excluded.situation,
                    energy = excluded.energy,
                    beacon_id = excluded.beacon_id,
                    channel = excluded.channel,
                    onboarding_path = excluded.onboarding_path,
                    cora_balance = excluded.cora_balance,
                    last_seen = excluded.last_seen
                """,
                (
                    user_id,
                    fields.goals,
                    fields.situation,
                    fields.energy,
                    beacon_id,
                    channel,
                    onboarding_path,
                    cora_balance,
                    now,
                    now,
                ),
            )

    def flag_onboarded(self, *, user_id: str, channel: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO user_channels (user_id, channel, onboarded, last_seen)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(user_id, channel) DO UPDATE SET
                    onboarded = 1,
                    last_seen = excluded.last_seen
                """,
                (user_id, channel, utc_now()),
            )

    def write_thread(self, *, user_id: str, channel: str, role: str, text: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO thread (user_id, surface, role, text) VALUES (?, ?, ?, ?)",
                (user_id, channel, role, text),
            )

    def increment_beacon_conversion(self, beacon_id: str | None) -> None:
        if not beacon_id:
            return
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE beacons
                   SET converted_count = converted_count + 1
                 WHERE beacon_id = ?
                """,
                (beacon_id,),
            )


class PsycopgOnboardingStore:
    """Live brain_index store. Constructed only when Hermes writes are enabled."""

    def __init__(self, db_url: str):
        self.db_url = db_url

    def connect(self):
        import psycopg

        return psycopg.connect(self.db_url, autocommit=True)

    def load_beacon(self, beacon_id: str | None) -> BeaconContext | None:
        if not beacon_id:
            return None
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT beacon_id, source, campaign, expected_intent, opening_tone
                  FROM brain_index.beacons
                 WHERE beacon_id = %s
                """,
                (beacon_id,),
            ).fetchone()
        if not row:
            return None
        return BeaconContext(
            beacon_id=row[0],
            source=row[1],
            campaign=row[2],
            expected_intent=row[3],
            opening_tone=row[4],
        )

    def save_passport(
        self,
        *,
        user_id: str,
        fields: PassportFields,
        beacon_id: str | None,
        channel: str,
        onboarding_path: str,
        cora_balance: int,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO brain_index.agent_passports
                    (user_id, goals, situation, energy, beacon_id, channel,
                     onboarding_path, cora_balance, proof_count, created_at, last_seen)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, NOW(), NOW())
                ON CONFLICT(user_id) DO UPDATE SET
                    goals = excluded.goals,
                    situation = excluded.situation,
                    energy = excluded.energy,
                    beacon_id = excluded.beacon_id,
                    channel = excluded.channel,
                    onboarding_path = excluded.onboarding_path,
                    cora_balance = excluded.cora_balance,
                    last_seen = NOW()
                """,
                (
                    user_id,
                    fields.goals,
                    fields.situation,
                    fields.energy,
                    beacon_id,
                    channel,
                    onboarding_path,
                    cora_balance,
                ),
            )

    def flag_onboarded(self, *, user_id: str, channel: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO brain_index.user_channels (user_id, channel, onboarded, last_seen)
                VALUES (%s, %s, TRUE, NOW())
                ON CONFLICT(user_id, channel) DO UPDATE SET
                    onboarded = TRUE,
                    last_seen = NOW()
                """,
                (user_id, channel),
            )

    def write_thread(self, *, user_id: str, channel: str, role: str, text: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO brain_index.thread (user_id, surface, role, text)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, channel, role, text),
            )

    def increment_beacon_conversion(self, beacon_id: str | None) -> None:
        if not beacon_id:
            return
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE brain_index.beacons
                   SET converted_count = converted_count + 1
                 WHERE beacon_id = %s
                """,
                (beacon_id,),
            )


def start_onboarding(hermes_msg: HermesMessage) -> HermesResponse:
    """Start or complete the onboarding capture for a new Hermes user."""

    store = default_store()
    beacon = store.load_beacon(getattr(hermes_msg, "beacon_id", None))
    answers = _answers_from_message(hermes_msg)
    if len(answers) < 3:
        text = opening_message(beacon)
        store.write_thread(
            user_id=hermes_msg.user_id,
            channel=hermes_msg.channel,
            role="bot",
            text=text,
        )
        return HermesResponse(user_id=hermes_msg.user_id, text=text)

    return complete_onboarding(hermes_msg, answers, store=store, beacon=beacon)


def complete_onboarding(
    hermes_msg: HermesMessage,
    answers: list[str],
    *,
    store: OnboardingStore | None = None,
    beacon: BeaconContext | None = None,
) -> HermesResponse:
    store = store or default_store()
    if beacon is None:
        beacon = store.load_beacon(hermes_msg.beacon_id)

    fields = extract_passport_fields(answers)
    onboarding_path = route_next_step(fields, beacon)
    cora_awarded = ONBOARDING_CORA_AWARD if os.environ.get("CORA_POLICY_LIVE") == "1" else 0
    response_text = routed_response(onboarding_path, fields, cora_awarded=cora_awarded)

    store.save_passport(
        user_id=hermes_msg.user_id,
        fields=fields,
        beacon_id=hermes_msg.beacon_id if beacon else None,
        channel=hermes_msg.channel,
        onboarding_path=onboarding_path,
        cora_balance=cora_awarded,
    )
    store.flag_onboarded(user_id=hermes_msg.user_id, channel=hermes_msg.channel)
    store.write_thread(
        user_id=hermes_msg.user_id,
        channel=hermes_msg.channel,
        role="user",
        text=json.dumps(
            {"event": "onboarding_capture", "answers": answers, "passport": fields.__dict__},
            sort_keys=True,
        ),
    )
    store.write_thread(
        user_id=hermes_msg.user_id,
        channel=hermes_msg.channel,
        role="bot",
        text=response_text,
    )
    store.increment_beacon_conversion(hermes_msg.beacon_id if beacon else None)
    return HermesResponse(
        user_id=hermes_msg.user_id,
        text=response_text,
        onboarding_path=onboarding_path,
        cora_awarded=cora_awarded,
        onboarding_complete=True,
    )


def default_store() -> OnboardingStore:
    if os.environ.get("HERMES_DISABLE", "1") != "0":
        return DisabledStore()
    sqlite_path = os.environ.get("ONBOARDING_SQLITE_PATH")
    if sqlite_path:
        return SQLiteOnboardingStore(sqlite_path)
    db_url = os.environ.get("BRAIN_INDEX_DB_URL")
    if db_url:
        return PsycopgOnboardingStore(db_url)
    raise RuntimeError("BRAIN_INDEX_DB_URL is required when HERMES_DISABLE=0")


def opening_message(beacon: BeaconContext | None) -> str:
    if beacon and beacon.beacon_id == "camp_zen":
        opener = "Welcome in. If Camp Zen caught your attention, let's find the next grounded step."
    elif beacon and beacon.beacon_id == "business_builder":
        opener = "Welcome. Let's turn the business signal that brought you here into one clear next move."
    elif beacon and beacon.opening_tone:
        opener = f"Welcome. {beacon.opening_tone.strip()}"
    else:
        opener = "Welcome. Let's find the most useful next step for you."
    questions = [
        "What brought you here today?",
        "What would feel like a win for you in the next 30 days?",
        "How are you showing up right now - full energy, or running on fumes?",
    ]
    return opener + "\n\n" + "\n".join(questions)


def extract_passport_fields(answers: list[str]) -> PassportFields:
    padded = [a.strip() for a in answers[:3]]
    while len(padded) < 3:
        padded.append("")
    return PassportFields(
        situation=padded[0],
        goals=padded[1],
        energy=_extract_energy(padded[2]),
    )


def route_next_step(fields: PassportFields, beacon: BeaconContext | None) -> str:
    text = " ".join([fields.situation, fields.goals, fields.energy]).lower()
    beacon_id = beacon.beacon_id if beacon else ""
    expected = (beacon.expected_intent if beacon else "").lower()

    if beacon_id == "camp_zen" or "camp zen" in text or "retreat" in text:
        return "camp_zen_invite"
    if "community" in text or beacon_id == "community":
        return "community_call"
    if "art" in text or "creative" in text or "fi-art" in text or "fi art" in text:
        return "fi_art_idea"
    if any(word in text for word in ["client", "business", "offer", "revenue", "service"]):
        return "service_match" if "service" in text else "action_plan"
    if any(word in text for word in ["stuck", "confused", "unclear", "clarity", "fumes"]):
        return "clarity_reflection"
    if "video" in text or "watch" in expected:
        return "video_link"
    if any(word in text for word in ["human", "coach", "guide", "person"]):
        return "human_guide"
    return "action_plan"


def routed_response(onboarding_path: str, fields: PassportFields, *, cora_awarded: int) -> str:
    messages = {
        "clarity_reflection": "Start here: write the one sentence version of what feels tangled, then name the smallest next choice.",
        "action_plan": "Start here: make a 3-step plan for the next 7 days, with the first step small enough to do today.",
        "camp_zen_invite": "Start here: look at the next Camp Zen opening and see whether your 30-day win belongs in that container.",
        "community_call": "Start here: join the next community call and bring the question you named today.",
        "fi_art_idea": "Start here: turn this into one Fi-Art sketch - the current state, the desired state, and the bridge.",
        "service_match": "Start here: match this need to one concrete Full Potential service path and test fit with one sentence.",
        "human_guide": "Start here: ask for a human guide review, with your situation and 30-day win already captured.",
        "video_link": "Start here: watch the shortest relevant intro video, then come back with what clicked or did not.",
    }
    if onboarding_path not in VALID_PATHS:
        raise ValueError(f"invalid onboarding path: {onboarding_path}")
    text = messages[onboarding_path]
    if cora_awarded:
        text += f"\n\nYou earned {cora_awarded} CORA for completing onboarding."
    return text


def seed_beacons() -> list[BeaconContext]:
    return [
        BeaconContext("camp_zen", "field", "Camp Zen", "retreat coherence", "Let's keep this grounded and human."),
        BeaconContext("general", "direct", "General", "open exploration", "We can start from what is alive now."),
        BeaconContext("business_builder", "offer", "Business Builder", "business growth", "We'll look for the clearest business next step."),
        BeaconContext("community", "community", "Community", "community participation", "We'll route you toward the right shared room."),
    ]


def upgrade_gate_message(*, sessions: int, proof_count: int) -> str | None:
    if sessions > 3 and (proof_count > 0 or sessions > 3):
        return (
            "You've been building something here. Want your AI guide to remember "
            "your full path? That's what the next level unlocks."
        )
    return None


def _answers_from_message(hermes_msg: HermesMessage) -> list[str]:
    raw = hermes_msg.metadata.get("onboarding_answers") or hermes_msg.metadata.get("answers")
    if isinstance(raw, list):
        return [str(item) for item in raw]
    return []


def _extract_energy(answer: str) -> str:
    lowered = answer.lower()
    if any(word in lowered for word in ["fumes", "tired", "exhausted", "low", "depleted"]):
        return "running on fumes"
    if any(word in lowered for word in ["full", "energized", "ready", "strong", "clear"]):
        return "full energy"
    return answer.strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
