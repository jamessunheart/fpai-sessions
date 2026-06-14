"""app/db.py — sqlite layer for apprentice-gateway.

Schema documented in SPEC.md §"Data store". Idempotent migrations on startup.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

DB_PATH = Path(os.environ.get("DB_PATH", "/var/lib/apprentice-gateway/apprentice.db"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def migrate() -> None:
    """Idempotent schema bootstrap. Safe to call on every startup."""
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS apprentices (
              email TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              stripe_customer_id TEXT NOT NULL,
              stripe_subscription_id TEXT,
              tier TEXT NOT NULL DEFAULT 'apprentice',
              founding INTEGER NOT NULL DEFAULT 0,
              founding_number INTEGER,
              active INTEGER NOT NULL DEFAULT 1,
              inviter TEXT,
              champion_number INTEGER,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              provision_state TEXT NOT NULL DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS provision_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT NOT NULL,
              step TEXT NOT NULL,
              status TEXT NOT NULL,
              detail TEXT,
              ts TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stripe_events (
              event_id TEXT PRIMARY KEY,
              event_type TEXT NOT NULL,
              email TEXT,
              ts TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS character_applications (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT NOT NULL,
              name TEXT NOT NULL,
              work TEXT NOT NULL,
              link TEXT,
              why TEXT NOT NULL,
              inviter TEXT,
              agreed_terms INTEGER NOT NULL DEFAULT 0,
              agreed_privacy INTEGER NOT NULL DEFAULT 0,
              agreed_at TEXT,
              status TEXT NOT NULL DEFAULT 'pending',
              decision_note TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS characters (
              email TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              stripe_customer_id TEXT NOT NULL,
              stripe_subscription_id TEXT,
              tier TEXT NOT NULL DEFAULT 'character',
              founding INTEGER NOT NULL DEFAULT 0,
              founding_number INTEGER,
              co_design_fee_paid INTEGER NOT NULL DEFAULT 0,
              active INTEGER NOT NULL DEFAULT 1,
              inviter TEXT,
              work TEXT,
              vision_link TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              provision_state TEXT NOT NULL DEFAULT 'pending'
            );

            CREATE INDEX IF NOT EXISTS idx_apprentices_active ON apprentices(active);
            CREATE INDEX IF NOT EXISTS idx_apprentices_founding ON apprentices(founding);
            CREATE INDEX IF NOT EXISTS idx_provision_log_email ON provision_log(email);
            CREATE INDEX IF NOT EXISTS idx_character_apps_status ON character_applications(status);
            CREATE INDEX IF NOT EXISTS idx_characters_active ON characters(active);
            CREATE INDEX IF NOT EXISTS idx_characters_founding ON characters(founding);
            """
        )


def get_apprentice(email: str) -> Optional[dict]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM apprentices WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
        return dict(row) if row else None


def upsert_apprentice(
    *,
    email: str,
    name: str,
    stripe_customer_id: str,
    stripe_subscription_id: Optional[str] = None,
    founding: bool = False,
    inviter: Optional[str] = None,
) -> dict:
    email = email.lower().strip()
    now = _now()
    with db() as conn:
        existing = conn.execute("SELECT * FROM apprentices WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.execute(
                """UPDATE apprentices SET
                       name = ?,
                       stripe_customer_id = ?,
                       stripe_subscription_id = COALESCE(?, stripe_subscription_id),
                       founding = founding | ?,
                       active = 1,
                       updated_at = ?
                   WHERE email = ?""",
                (
                    name,
                    stripe_customer_id,
                    stripe_subscription_id,
                    1 if founding else 0,
                    now,
                    email,
                ),
            )
        else:
            # Assign founding number if applicable
            founding_number = None
            if founding:
                row = conn.execute(
                    "SELECT COALESCE(MAX(founding_number), 0) AS m FROM apprentices WHERE founding = 1"
                ).fetchone()
                founding_number = (row["m"] or 0) + 1
            conn.execute(
                """INSERT INTO apprentices
                   (email, name, stripe_customer_id, stripe_subscription_id,
                    founding, founding_number, inviter, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    email,
                    name,
                    stripe_customer_id,
                    stripe_subscription_id,
                    1 if founding else 0,
                    founding_number,
                    inviter,
                    now,
                    now,
                ),
            )
    return get_apprentice(email) or {}


def mark_subscription(email: str, *, subscription_id: str, active: bool) -> None:
    email = email.lower().strip()
    now = _now()
    with db() as conn:
        conn.execute(
            """UPDATE apprentices SET
                   stripe_subscription_id = ?,
                   active = ?,
                   updated_at = ?
               WHERE email = ?""",
            (subscription_id, 1 if active else 0, now, email),
        )


def set_provision_state(email: str, state: str) -> None:
    """state ∈ {'pending', 'partial', 'complete', 'failed'}"""
    email = email.lower().strip()
    with db() as conn:
        conn.execute(
            "UPDATE apprentices SET provision_state = ?, updated_at = ? WHERE email = ?",
            (state, _now(), email),
        )


def log_provision_step(email: str, step: str, status: str, detail: Optional[str] = None) -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO provision_log (email, step, status, detail, ts)
               VALUES (?, ?, ?, ?, ?)""",
            (email.lower().strip(), step, status, detail, _now()),
        )


def already_processed(event_id: str) -> bool:
    with db() as conn:
        row = conn.execute(
            "SELECT 1 FROM stripe_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return row is not None


def record_event(event_id: str, event_type: str, email: Optional[str]) -> None:
    with db() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO stripe_events (event_id, event_type, email, ts)
               VALUES (?, ?, ?, ?)""",
            (event_id, event_type, email, _now()),
        )


def count_founding() -> int:
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM apprentices WHERE founding = 1 AND active = 1"
        ).fetchone()
        return int(row["n"] or 0)


def count_active() -> int:
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM apprentices WHERE active = 1"
        ).fetchone()
        return int(row["n"] or 0)


def list_apprentices() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM apprentices ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# ── Character tier helpers ──────────────────────────────────────────────────


def create_character_application(
    *,
    email: str,
    name: str,
    work: str,
    why: str,
    link: Optional[str] = None,
    inviter: Optional[str] = None,
    agreed_terms: bool = False,
    agreed_privacy: bool = False,
    agreed_at: Optional[str] = None,
) -> dict:
    email = email.lower().strip()
    now = _now()
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO character_applications
               (email, name, work, link, why, inviter,
                agreed_terms, agreed_privacy, agreed_at,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                email,
                name,
                work,
                link,
                why,
                inviter,
                1 if agreed_terms else 0,
                1 if agreed_privacy else 0,
                agreed_at,
                now,
                now,
            ),
        )
        app_id = cur.lastrowid
        row = conn.execute(
            "SELECT * FROM character_applications WHERE id = ?", (app_id,)
        ).fetchone()
        return dict(row) if row else {}


def list_character_applications(status: Optional[str] = None) -> list[dict]:
    with db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM character_applications WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM character_applications ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def update_character_application_status(
    app_id: int, status: str, decision_note: Optional[str] = None
) -> None:
    """status ∈ {'pending', 'accepted', 'declined', 'paid'}"""
    with db() as conn:
        conn.execute(
            """UPDATE character_applications
               SET status = ?, decision_note = ?, updated_at = ?
               WHERE id = ?""",
            (status, decision_note, _now(), app_id),
        )


def get_character(email: str) -> Optional[dict]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM characters WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
        return dict(row) if row else None


def upsert_character(
    *,
    email: str,
    name: str,
    stripe_customer_id: str,
    stripe_subscription_id: Optional[str] = None,
    founding: bool = False,
    co_design_fee_paid: bool = False,
    inviter: Optional[str] = None,
    work: Optional[str] = None,
    vision_link: Optional[str] = None,
) -> dict:
    email = email.lower().strip()
    now = _now()
    with db() as conn:
        existing = conn.execute(
            "SELECT * FROM characters WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE characters SET
                       name = ?,
                       stripe_customer_id = ?,
                       stripe_subscription_id = COALESCE(?, stripe_subscription_id),
                       founding = founding | ?,
                       co_design_fee_paid = co_design_fee_paid | ?,
                       active = 1,
                       updated_at = ?
                   WHERE email = ?""",
                (
                    name,
                    stripe_customer_id,
                    stripe_subscription_id,
                    1 if founding else 0,
                    1 if co_design_fee_paid else 0,
                    now,
                    email,
                ),
            )
        else:
            founding_number = None
            if founding:
                row = conn.execute(
                    "SELECT COALESCE(MAX(founding_number), 0) AS m FROM characters WHERE founding = 1"
                ).fetchone()
                founding_number = (row["m"] or 0) + 1
            conn.execute(
                """INSERT INTO characters
                   (email, name, stripe_customer_id, stripe_subscription_id,
                    founding, founding_number, co_design_fee_paid, inviter,
                    work, vision_link, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    email,
                    name,
                    stripe_customer_id,
                    stripe_subscription_id,
                    1 if founding else 0,
                    founding_number,
                    1 if co_design_fee_paid else 0,
                    inviter,
                    work,
                    vision_link,
                    now,
                    now,
                ),
            )
    return get_character(email) or {}


def mark_character_subscription(email: str, *, subscription_id: str, active: bool) -> None:
    email = email.lower().strip()
    with db() as conn:
        conn.execute(
            """UPDATE characters SET
                   stripe_subscription_id = ?,
                   active = ?,
                   updated_at = ?
               WHERE email = ?""",
            (subscription_id, 1 if active else 0, _now(), email),
        )


def set_character_provision_state(email: str, state: str) -> None:
    """state ∈ {'pending', 'partial', 'complete', 'failed'}"""
    with db() as conn:
        conn.execute(
            "UPDATE characters SET provision_state = ?, updated_at = ? WHERE email = ?",
            (state, _now(), email.lower().strip()),
        )


def count_founding_characters() -> int:
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM characters WHERE founding = 1 AND active = 1"
        ).fetchone()
        return int(row["n"] or 0)


def count_active_characters() -> int:
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM characters WHERE active = 1"
        ).fetchone()
        return int(row["n"] or 0)


def list_characters() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM characters ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
