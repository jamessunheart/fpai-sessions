"""SQLite layer for ZV Wallet.

v0.1 — single-currency (CORA only). Currently in production.

v0.2 — dual-ledger (Work Credits + CORA Credits). Pending migration drafted at
       SERVICES/zv-wallet/app/_pending_v0.2_migration.sql. NOT YET APPLIED.
       Adds:
         * work_credits_balances (mirrors cora_balances)
         * work_credits_ledger   (mirrors cora_ledger)
         * cora_ledger.currency_type column (with CHECK ('WC', 'CORA'))
         * currency_conversions audit table
         * weekly_seals.wc_* columns
         * users.approved_volunteer flag (gate for CORA -> WC conversion)

       Mechanics module (mechanics.py) already exposes dual-ledger formulas
       and conversion helpers (compute_work_credits, compute_cora_bonus,
       convert_wc_to_cora, convert_cora_to_wc). Service keeps running v0.1
       until the migration is rehearsed against a snapshot and approved.
"""
from __future__ import annotations
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.environ.get("ZV_WALLET_DB", "/var/lib/zv-wallet/zv-wallet.db")
MEDIA_DIR = os.environ.get("ZV_WALLET_MEDIA", "/var/lib/zv-wallet/media")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(MEDIA_DIR).mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  phone TEXT PRIMARY KEY,
  display_name TEXT,
  role TEXT NOT NULL,
  tier TEXT,
  week_number INTEGER DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1,
  onboarded_at TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS witness_pairings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  participant_phone TEXT NOT NULL,
  witness_phone TEXT NOT NULL,
  paired_at TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS invoices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  participant_phone TEXT NOT NULL,
  week_start TEXT NOT NULL,
  tier TEXT NOT NULL,
  value_stack_cents INTEGER NOT NULL,
  floor_cents INTEGER NOT NULL,
  trust_curve_pct INTEGER NOT NULL,
  p1 TEXT NOT NULL,
  p2 TEXT NOT NULL,
  p3 TEXT NOT NULL,
  issued_at TEXT NOT NULL,
  sealed INTEGER NOT NULL DEFAULT 0,
  final_due_cents INTEGER,
  final_cora_earned INTEGER,
  final_honor_entry INTEGER
);

CREATE TABLE IF NOT EXISTS proofs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  invoice_id INTEGER NOT NULL,
  participant_phone TEXT NOT NULL,
  priority TEXT,
  content_text TEXT,
  media_path TEXT,
  media_type TEXT,
  classification TEXT DEFAULT 'PRIVATE',
  submitted_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  witness_decision_at TEXT,
  witness_phone TEXT,
  witness_note TEXT,
  cora_awarded INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cora_balances (
  phone TEXT PRIMARY KEY,
  balance INTEGER NOT NULL DEFAULT 0,
  lifetime_earned INTEGER NOT NULL DEFAULT 0,
  lifetime_spent INTEGER NOT NULL DEFAULT 0,
  honor_entries INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cora_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phone TEXT NOT NULL,
  delta INTEGER NOT NULL,
  reason TEXT NOT NULL,
  ref_id INTEGER,
  balance_after INTEGER NOT NULL,
  ts TEXT NOT NULL,
  classification TEXT DEFAULT 'PRIVATE'
);

CREATE TABLE IF NOT EXISTS redemptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  participant_phone TEXT NOT NULL,
  item TEXT NOT NULL,
  cora_cost INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'requested',
  requested_at TEXT NOT NULL,
  fulfilled_at TEXT,
  fulfilled_by TEXT
);

CREATE TABLE IF NOT EXISTS weekly_seals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  invoice_id INTEGER NOT NULL UNIQUE,
  participant_phone TEXT NOT NULL,
  hours_logged INTEGER DEFAULT 0,
  p1_status TEXT,
  p2_status TEXT,
  p3_status TEXT,
  proof_count INTEGER DEFAULT 0,
  hourly_offset_cents INTEGER DEFAULT 0,
  invoice_reduction_cents INTEGER DEFAULT 0,
  final_due_cents INTEGER NOT NULL,
  cora_earned_raw INTEGER DEFAULT 0,
  cora_capped INTEGER DEFAULT 0,
  honor_entries INTEGER DEFAULT 0,
  sealed_at TEXT NOT NULL,
  witness_phone TEXT NOT NULL,
  narrative TEXT
);

CREATE TABLE IF NOT EXISTS wa_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  wa_message_id TEXT UNIQUE,
  from_phone TEXT NOT NULL,
  to_phone TEXT,
  direction TEXT NOT NULL,
  message_type TEXT NOT NULL,
  body TEXT,
  media_path TEXT,
  raw_payload TEXT,
  ts TEXT NOT NULL,
  processed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  target TEXT,
  detail TEXT,
  ts TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_proofs_invoice ON proofs(invoice_id);
CREATE INDEX IF NOT EXISTS idx_proofs_status ON proofs(status, witness_phone);
CREATE INDEX IF NOT EXISTS idx_wa_messages_from ON wa_messages(from_phone, ts);
CREATE INDEX IF NOT EXISTS idx_cora_ledger_phone ON cora_ledger(phone, ts);
CREATE INDEX IF NOT EXISTS idx_invoices_participant ON invoices(participant_phone, week_start);

-- ZV Work Credit Group Observer v0.1 — additive only (no existing schema changes)

CREATE TABLE IF NOT EXISTS group_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  group_jid TEXT NOT NULL,
  sender_jid TEXT NOT NULL,
  sender_display_name TEXT,
  message_id TEXT UNIQUE,
  message_text TEXT,
  media_url TEXT,
  media_type TEXT,
  timestamp INTEGER NOT NULL,
  raw_event_json TEXT,
  classification TEXT DEFAULT 'COUNCIL-RESTRICTED',
  parsed INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_group_messages_group_ts
  ON group_messages(group_jid, timestamp);
CREATE INDEX IF NOT EXISTS idx_group_messages_parsed
  ON group_messages(parsed, created_at);

CREATE TABLE IF NOT EXISTS work_credit_pending (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_message_id TEXT,
  group_jid TEXT,
  actor_jid TEXT NOT NULL,
  actor_display_name TEXT,
  activity TEXT,
  hours_claimed REAL,
  wc_amount INTEGER,
  evidence_type TEXT,
  parser_confidence REAL,
  parser_extracted_json TEXT,
  status TEXT NOT NULL DEFAULT 'pending', -- pending | approved | rejected
  witness_jid TEXT,
  witness_display_name TEXT,
  witness_reason TEXT,
  approved_at INTEGER,
  rejected_at INTEGER,
  bot_reply_message_id TEXT,
  created_at INTEGER DEFAULT (strftime('%s', 'now')),
  FOREIGN KEY (source_message_id) REFERENCES group_messages(message_id)
);

CREATE INDEX IF NOT EXISTS idx_wcp_status_created
  ON work_credit_pending(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_wcp_actor
  ON work_credit_pending(actor_jid, approved_at DESC);
CREATE INDEX IF NOT EXISTS idx_wcp_reply_mid
  ON work_credit_pending(bot_reply_message_id);

CREATE TABLE IF NOT EXISTS member_roles (
  jid TEXT PRIMARY KEY,
  display_name TEXT,
  role TEXT NOT NULL,   -- volunteer | member | steward | witness
  approved_at INTEGER DEFAULT (strftime('%s', 'now')),
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_member_roles_role ON member_roles(role);
"""


def init_db() -> None:
    with conn() as c:
        c.executescript(SCHEMA)
        # Pre-seed James as witness if his WhatsApp JID is provided via env.
        # If not yet known, first-DM auto-detect (in main.py group bootstrap)
        # can promote him later.
        james_jid = os.environ.get("ZV_JAMES_JID", "").strip()
        if james_jid:
            c.execute(
                """INSERT OR IGNORE INTO member_roles
                   (jid, display_name, role, notes)
                   VALUES (?, ?, 'witness', 'seeded from ZV_JAMES_JID env')""",
                (james_jid, "James"),
            )


def audit_log(actor: str, action: str, target: str | None = None, detail: str | None = None) -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO audit (actor, action, target, detail, ts) VALUES (?, ?, ?, ?, ?)",
            (actor, action, target, detail, now_iso()),
        )
