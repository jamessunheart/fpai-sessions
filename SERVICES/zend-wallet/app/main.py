"""
ZEND Wallet (UC Credits) v2.0 - Regenerative Integration
=========================================================

Service: zend-wallet
Port: 8580

Implements:
- Wallet balance view (UC)
- AI-assisted (best-effort) draft of "Zend It" sends
- UC transfers via fp-credits-gateway
- Invite + claim flow (escrowed UC)
- Trust Index integration (adaptive ease)
- Contribution logging (Proof of Contribution)
- Experience layer (Zend to Ascend)

Source of truth:
- docs/protocols/ZEND_REGENERATIVE_SPEC.md (v2.0) — PRIMARY
- SERVICES/zend-wallet/SPEC.md
- docs/protocols/ZEND_UC_CREDITS_SPEC.md
"""

from __future__ import annotations

import json
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Settings(BaseModel):
    service_name: str = "zend-wallet"
    service_version: str = "1.0.0"
    service_port: int = int(os.getenv("ZEND_SERVICE_PORT", "8580"))

    credits_gateway_url: str = os.getenv("ZEND_CREDITS_GATEWAY_URL", "http://localhost:8765").rstrip("/")
    credits_api_key: Optional[str] = os.getenv("ZEND_CREDITS_API_KEY")

    escrow_account: str = os.getenv("ZEND_ESCROW_ACCOUNT", "system:zend_escrow")
    fees_account: str = os.getenv("ZEND_FEES_ACCOUNT", "system:zend_fees")

    zend_admin_key: Optional[str] = os.getenv("ZEND_ZEND_ADMIN_KEY")

    # MVP guardrails
    max_send_uc: float = float(os.getenv("ZEND_MAX_SEND_UC", "1000"))
    large_amount_threshold_uc: float = float(os.getenv("ZEND_LARGE_AMOUNT_THRESHOLD_UC", "100"))
    repeated_sends_threshold: int = int(os.getenv("ZEND_REPEATED_SENDS_THRESHOLD", "5"))
    repeated_sends_window_minutes: int = int(os.getenv("ZEND_REPEATED_SENDS_WINDOW_MINUTES", "60"))

    # Drafting
    draft_use_ai: bool = os.getenv("ZEND_DRAFT_USE_AI", "true").lower() in {"1", "true", "yes", "on"}
    draft_ai_model: str = os.getenv("ZEND_DRAFT_AI_MODEL", "claude")
    draft_ai_max_tokens: int = int(os.getenv("ZEND_DRAFT_AI_MAX_TOKENS", "500"))

    # Persistence
    data_dir: Path = Path(os.getenv("ZEND_DATA_DIR", str(Path(__file__).resolve().parents[1] / "data")))
    db_path: Optional[Path] = None

    def model_post_init(self, __context: Any) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        env_db_path = os.getenv("ZEND_DB_PATH")
        if env_db_path:
            self.db_path = Path(env_db_path)
        if self.db_path is None:
            self.db_path = self.data_dir / "zend_wallet.db"


settings = Settings()


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------


class DraftSendRequest(BaseModel):
    member_id: str = Field(..., min_length=1, max_length=120)
    prompt: str = Field(..., min_length=1, max_length=2000)


class DraftSendResponse(BaseModel):
    recipient: Optional[str] = None  # member_id or invite_contact
    recipient_type: str = "unknown"  # member|invite|unknown
    amount_uc: float = 0.0
    note: str = ""
    risk_flags: List[str] = []
    confirm_level: str = "high"  # low|medium|high
    requires_confirm: bool = True
    ai_used: bool = False
    ai_error: Optional[str] = None


class SendRequest(BaseModel):
    from_member_id: str = Field(..., min_length=1, max_length=120)
    to_member_id: Optional[str] = Field(default=None, max_length=120)
    invite_contact: Optional[str] = Field(default=None, max_length=200)
    amount_uc: float = Field(..., gt=0)
    note: Optional[str] = Field(default="", max_length=2000)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Safety confirmation (required for non-trivial risk cases)
    confirm: bool = Field(default=False)


class SendResponse(BaseModel):
    success: bool
    kind: str  # direct|invite
    amount_uc: float
    from_member_id: str
    to_member_id: Optional[str] = None
    invite_contact: Optional[str] = None
    invite_code: Optional[str] = None
    escrow_account: Optional[str] = None
    gateway_result: Optional[Dict[str, Any]] = None
    risk_flags: List[str] = []
    confirm_level: str = "low"
    message: str = ""


class ClaimInviteRequest(BaseModel):
    invite_code: str = Field(..., min_length=6, max_length=64)
    claimer_member_id: str = Field(..., min_length=1, max_length=120)
    confirm: bool = Field(default=True)


class ClaimInviteResponse(BaseModel):
    success: bool
    invite_code: str
    amount_uc: float
    claimer_member_id: str
    gateway_result: Optional[Dict[str, Any]] = None
    message: str = ""


class WalletResponse(BaseModel):
    member_id: str
    uc_balance: float
    balances: Dict[str, float]
    pending: Dict[str, float]
    total_value_usd: float
    unlocked: List[str]
    notes: List[str]
    timestamp: str


# -----------------------------------------------------------------------------
# Entity Models
# -----------------------------------------------------------------------------


class EntityType(str):
    INDIVIDUAL = "individual"
    TRUST = "trust"
    LLC = "llc"
    CORPORATION = "corporation"
    CHURCH = "church"
    NONPROFIT = "nonprofit"
    DAO = "dao"
    FAMILY_OFFICE = "family_office"


ENTITY_LIMITS = {
    "individual": {"daily_buy": 1000, "daily_distribute": 1000, "can_provide_liquidity": False},
    "trust": {"daily_buy": 50000, "daily_distribute": 25000, "can_provide_liquidity": True},
    "llc": {"daily_buy": 25000, "daily_distribute": 10000, "can_provide_liquidity": True},
    "corporation": {"daily_buy": 25000, "daily_distribute": 10000, "can_provide_liquidity": True},
    "church": {"daily_buy": 100000, "daily_distribute": 50000, "can_provide_liquidity": True},
    "nonprofit": {"daily_buy": 50000, "daily_distribute": 25000, "can_provide_liquidity": True},
    "dao": {"daily_buy": 25000, "daily_distribute": 10000, "can_provide_liquidity": True},
    "family_office": {"daily_buy": 500000, "daily_distribute": 250000, "can_provide_liquidity": True},
}


class CreateEntityRequest(BaseModel):
    entity_type: str = Field(..., description="Type: trust, llc, church, etc.")
    legal_name: str = Field(..., min_length=2, max_length=200)
    ein_or_tin: Optional[str] = Field(default=None, max_length=20)
    admin_member_id: str = Field(..., min_length=1, max_length=120)
    ton_wallet_address: Optional[str] = None


class EntityResponse(BaseModel):
    entity_id: str
    entity_type: str
    legal_name: str
    ein_or_tin: Optional[str] = None
    uc_account_id: str
    ton_wallet_address: Optional[str] = None
    daily_buy_limit_uc: float
    daily_distribute_limit_uc: float
    is_liquidity_provider: bool = False
    admins: List[str] = []
    beneficiaries: List[str] = []
    uc_balance: float = 0.0
    created_at: str
    updated_at: str


class AddMemberRequest(BaseModel):
    member_id: str = Field(..., min_length=1, max_length=120)
    role: str = Field(default="beneficiary", description="admin or beneficiary")


class DistributeRequest(BaseModel):
    distributions: List[Dict[str, Any]] = Field(..., description="List of {member_id, amount_uc, note}")
    total_amount_uc: Optional[float] = None
    note: str = ""


class DistributeResponse(BaseModel):
    entity_id: str
    success: bool
    distributed_count: int
    total_uc: float
    results: List[Dict[str, Any]]
    treasury_after: float
    message: str


class ScheduledDistributionRequest(BaseModel):
    frequency: str = Field(..., description="monthly, weekly, quarterly")
    day_of_period: int = Field(default=1, ge=1, le=31)
    beneficiaries: List[Dict[str, Any]] = Field(..., description="List of {member_id, amount_uc}")
    total_amount_uc: float
    note: str = ""
    enabled: bool = True


class UnifiedWalletResponse(BaseModel):
    member_id: str
    uc_balance: float
    entity_contexts: List[Dict[str, Any]] = []
    ton_connected: bool = False
    ton_address: Optional[str] = None
    ton_balances: Dict[str, float] = Field(default_factory=dict)
    total_value_usd: float = 0.0
    unlocked: List[str] = []
    timestamp: str


# -----------------------------------------------------------------------------
# Auth helpers (optional MVP protection)
# -----------------------------------------------------------------------------


def require_admin_key(x_zend_admin_key: Optional[str] = Header(None)) -> None:
    if not settings.zend_admin_key:
        return
    if not x_zend_admin_key or x_zend_admin_key != settings.zend_admin_key:
        raise HTTPException(status_code=401, detail="Zend admin key required (X-Zend-Admin-Key)")


# -----------------------------------------------------------------------------
# Credits Gateway client
# -----------------------------------------------------------------------------


class CreditsGatewayClient:
    def __init__(self, base_url: str, api_key: Optional[str]):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def health(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self.base_url}/health")
                if r.status_code == 200:
                    return True, r.json()
        except Exception:
            pass
        return False, None

    async def get_balance(self, account_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{self.base_url}/api/balance/{account_id}",
                headers=self._headers(),
            )
            if r.status_code == 200:
                return r.json()
            raise HTTPException(status_code=502, detail=f"Credits Gateway balance error: {r.text}")

    async def transfer_uc(
        self,
        from_account: str,
        to_account: str,
        amount_uc: float,
        reason: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = {
            "from_account": from_account,
            "to_account": to_account,
            "amount": round(float(amount_uc), 8),
            "credit_type": "uc",
            "reason": reason,
            "metadata": metadata or {},
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{self.base_url}/api/transfer",
                headers=self._headers(),
                json=payload,
            )
            if r.status_code == 200:
                return r.json()
            raise HTTPException(status_code=502, detail=f"Credits Gateway transfer error: {r.text}")

    async def ai_query(self, account_id: str, prompt: str, model: str, max_tokens: int) -> Dict[str, Any]:
        payload = {
            "account_id": account_id,
            "prompt": prompt,
            "model": model,
            "max_tokens": max_tokens,
            "metadata": {"source": "zend-wallet", "purpose": "draft-send"},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{self.base_url}/api/ai/query",
                headers=self._headers(),
                json=payload,
            )
            if r.status_code == 200:
                return r.json()
            raise HTTPException(status_code=502, detail=f"Credits Gateway AI query error: {r.text}")


credits = CreditsGatewayClient(settings.credits_gateway_url, settings.credits_api_key)


# -----------------------------------------------------------------------------
# Trust Index Client (Adaptive Ease)
# -----------------------------------------------------------------------------


class TrustIndexPolicy(BaseModel):
    """Trust Index policy snapshot for adaptive confirmation levels."""
    trust_index: Optional[float] = None
    posture: str = "balanced"  # emergency|conservative|balanced|generous
    parameters: Dict[str, Any] = {}
    source: str = "fallback"


class TrustIndexClient:
    """Client for Trust Index service - enables adaptive ease based on Commons health."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._cached_policy: Optional[TrustIndexPolicy] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 60  # Refresh every minute

    async def get_policy(self, force_refresh: bool = False) -> TrustIndexPolicy:
        """Get current Trust Index policy (cached for performance)."""
        now = datetime.now(timezone.utc)

        # Return cached if still fresh
        if (
            not force_refresh
            and self._cached_policy
            and self._cache_time
            and (now - self._cache_time).total_seconds() < self._cache_ttl_seconds
        ):
            return self._cached_policy

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/trust-index/policy")
                if r.status_code == 200:
                    data = r.json()
                    self._cached_policy = TrustIndexPolicy(
                        trust_index=data.get("trust_index"),
                        posture=data.get("posture") or data.get("policy_posture") or "balanced",
                        parameters=data.get("parameters", {}),
                        source="trust-index"
                    )
                    self._cache_time = now
                    return self._cached_policy
        except Exception:
            pass

        # Fallback: balanced posture (safe default)
        return TrustIndexPolicy(posture="balanced", source="fallback")

    def confirmation_level_for_posture(self, posture: str, amount_uc: float, risk_flags: List[str]) -> str:
        """
        Determine confirmation level based on Trust Index posture.
        Per ZEND_REGENERATIVE_SPEC.md Part 4.1
        """
        p = (posture or "").lower().strip()

        # Emergency: always full confirm + human review
        if p == "emergency":
            return "human_review"

        # Conservative: full confirm for > $100, human review for > $500
        if p == "conservative":
            if amount_uc > 500 or "human_escalation" in risk_flags:
                return "human_review"
            if amount_uc > 100 or risk_flags:
                return "full"
            return "medium"

        # Balanced: light confirm for < $500, full for larger
        if p == "balanced":
            if amount_uc > settings.large_amount_threshold_uc * 5:  # > $500
                return "full"
            if risk_flags:
                return "medium"
            return "light"

        # Generous: light confirm for < $2000, "Send for Me" enabled
        if p == "generous":
            if amount_uc > 2000 or "human_escalation" in risk_flags:
                return "full"
            return "light"

        return "medium"

    def sponsored_sends_for_posture(self, posture: str) -> int:
        """Returns weekly sponsored sends based on posture."""
        p = (posture or "").lower().strip()
        if p == "generous":
            return 3
        if p == "balanced":
            return 1
        return 0  # conservative/emergency


trust_index = TrustIndexClient(os.getenv("ZEND_TRUST_INDEX_URL", "http://localhost:8560"))


# -----------------------------------------------------------------------------
# Contribution Tracker Client (Proof of Contribution)
# -----------------------------------------------------------------------------


class ContributionTrackerClient:
    """Client for logging Zend sends as contributions (earns TRUST)."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def log_send_contribution(
        self,
        member_id: str,
        amount_uc: float,
        recipient_id: Optional[str],
        is_first_send_to_recipient: bool,
        is_invite: bool,
        transfer_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Log a completed Zend send as a contribution.
        Per ZEND_REGENERATIVE_SPEC.md Part 5.1:
        - Successful send: +5
        - First-time send to new recipient: +10
        - Recipient claims invite: +50 (handled separately in claim_invite)
        """
        # Calculate contribution score
        if is_invite:
            # Invite sends will be credited when claimed
            description = f"Zend invite ({amount_uc} UC)"
            contribution_type = "referral"  # Will be credited on claim
        else:
            description = f"Zend send ({amount_uc} UC)"
            contribution_type = "service"

        payload = {
            "member_id": member_id,
            "type": contribution_type,
            "description": description,
            "reference_id": transfer_id,
            "amount": amount_uc,
            "recipient_id": recipient_id,
            "metadata": {
                "source": "zend-wallet",
                "is_first_send": is_first_send_to_recipient,
                "is_invite": is_invite,
                "amount_uc": amount_uc,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(
                    f"{self.base_url}/api/contributions/log",
                    json=payload,
                )
                if r.status_code == 200:
                    return r.json()
        except Exception:
            pass
        return None

    async def log_claim_contribution(
        self,
        sender_member_id: str,
        claimer_member_id: str,
        amount_uc: float,
        invite_code: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Log an invite claim - credits referral bonus to sender.
        Per ZEND_REGENERATIVE_SPEC.md Part 5.1:
        - Recipient claims invite: +50 (referral bonus)
        """
        payload = {
            "member_id": sender_member_id,
            "type": "referral",
            "description": f"Zend referral claimed by {claimer_member_id} ({amount_uc} UC)",
            "reference_id": invite_code,
            "recipient_id": claimer_member_id,
            "metadata": {
                "source": "zend-wallet",
                "claim_event": True,
                "claimer_member_id": claimer_member_id,
                "amount_uc": amount_uc,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(
                    f"{self.base_url}/api/contributions/log",
                    json=payload,
                )
                if r.status_code == 200:
                    return r.json()
        except Exception:
            pass
        return None


contribution_tracker = ContributionTrackerClient(os.getenv("ZEND_CONTRIBUTION_TRACKER_URL", "http://localhost:8570"))


# -----------------------------------------------------------------------------
# Persistence (SQLite via aiosqlite)
# -----------------------------------------------------------------------------


async def init_db():
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS transfers (
              id TEXT PRIMARY KEY,
              created_at TEXT NOT NULL,
              from_member_id TEXT NOT NULL,
              to_member_id TEXT,
              invite_contact TEXT,
              invite_code TEXT,
              amount_uc REAL NOT NULL,
              note TEXT,
              credit_type TEXT NOT NULL,
              gateway_result_json TEXT
            );

            CREATE TABLE IF NOT EXISTS invites (
              invite_code TEXT PRIMARY KEY,
              created_at TEXT NOT NULL,
              from_member_id TEXT NOT NULL,
              invite_contact TEXT NOT NULL,
              amount_uc REAL NOT NULL,
              note TEXT,
              status TEXT NOT NULL,
              escrow_gateway_result_json TEXT,
              claimed_at TEXT,
              claimed_by TEXT,
              claim_gateway_result_json TEXT
            );

            -- Entity accounts (trusts, churches, LLCs, etc.)
            CREATE TABLE IF NOT EXISTS entities (
              entity_id TEXT PRIMARY KEY,
              entity_type TEXT NOT NULL,
              legal_name TEXT NOT NULL,
              ein_or_tin TEXT,
              uc_account_id TEXT NOT NULL,
              ton_wallet_address TEXT,
              daily_buy_limit_uc REAL DEFAULT 10000,
              daily_distribute_limit_uc REAL DEFAULT 5000,
              is_liquidity_provider BOOLEAN DEFAULT FALSE,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            -- Entity membership (admins and beneficiaries)
            CREATE TABLE IF NOT EXISTS entity_members (
              entity_id TEXT NOT NULL,
              member_id TEXT NOT NULL,
              role TEXT NOT NULL,
              added_at TEXT NOT NULL,
              PRIMARY KEY (entity_id, member_id)
            );

            -- Scheduled distributions
            CREATE TABLE IF NOT EXISTS scheduled_distributions (
              schedule_id TEXT PRIMARY KEY,
              entity_id TEXT NOT NULL,
              frequency TEXT NOT NULL,
              day_of_period INTEGER NOT NULL,
              beneficiaries_json TEXT NOT NULL,
              total_amount_uc REAL NOT NULL,
              next_run TEXT NOT NULL,
              last_run TEXT,
              enabled BOOLEAN DEFAULT TRUE
            );
            """
        )
        await conn.commit()


async def record_transfer(
    *,
    transfer_id: str,
    created_at: str,
    from_member_id: str,
    to_member_id: Optional[str],
    invite_contact: Optional[str],
    invite_code: Optional[str],
    amount_uc: float,
    note: str,
    credit_type: str,
    gateway_result: Dict[str, Any],
):
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        await conn.execute(
            """
            INSERT INTO transfers (id, created_at, from_member_id, to_member_id, invite_contact, invite_code, amount_uc, note, credit_type, gateway_result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transfer_id,
                created_at,
                from_member_id,
                to_member_id,
                invite_contact,
                invite_code,
                float(amount_uc),
                note,
                credit_type,
                json.dumps(gateway_result or {}),
            ),
        )
        await conn.commit()


async def get_recent_send_count(from_member_id: str, window_minutes: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM transfers
            WHERE from_member_id = ?
              AND created_at >= ?
            """,
            (from_member_id, cutoff.isoformat()),
        )
        row = await cur.fetchone()
        return int(row["c"] or 0) if row else 0


async def has_sent_to_recipient(from_member_id: str, to_member_id: str) -> bool:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        cur = await conn.execute(
            """
            SELECT 1
            FROM transfers
            WHERE from_member_id = ?
              AND to_member_id = ?
            LIMIT 1
            """,
            (from_member_id, to_member_id),
        )
        row = await cur.fetchone()
        return row is not None


async def create_invite_record(invite_code: str, from_member_id: str, invite_contact: str, amount_uc: float, note: str, escrow_gateway_result: Dict[str, Any]):
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        await conn.execute(
            """
            INSERT INTO invites (invite_code, created_at, from_member_id, invite_contact, amount_uc, note, status, escrow_gateway_result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invite_code,
                _utc_now_iso(),
                from_member_id,
                invite_contact,
                float(amount_uc),
                note,
                "pending",
                json.dumps(escrow_gateway_result or {}),
            ),
        )
        await conn.commit()


async def get_invite(invite_code: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM invites WHERE invite_code = ?", (invite_code,))
        row = await cur.fetchone()
        if not row:
            return None
        return dict(row)


async def mark_invite_claimed(invite_code: str, claimer_member_id: str, claim_gateway_result: Dict[str, Any]):
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        await conn.execute(
            """
            UPDATE invites
               SET status = ?,
                   claimed_at = ?,
                   claimed_by = ?,
                   claim_gateway_result_json = ?
             WHERE invite_code = ?
            """,
            ("claimed", _utc_now_iso(), claimer_member_id, json.dumps(claim_gateway_result or {}), invite_code),
        )
        await conn.commit()


# -----------------------------------------------------------------------------
# Entity Database Functions
# -----------------------------------------------------------------------------


async def create_entity(
    entity_id: str,
    entity_type: str,
    legal_name: str,
    ein_or_tin: Optional[str],
    uc_account_id: str,
    ton_wallet_address: Optional[str],
    daily_buy_limit_uc: float,
    daily_distribute_limit_uc: float,
) -> None:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        await conn.execute(
            """
            INSERT INTO entities (entity_id, entity_type, legal_name, ein_or_tin, uc_account_id, ton_wallet_address, daily_buy_limit_uc, daily_distribute_limit_uc, is_liquidity_provider, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (entity_id, entity_type, legal_name, ein_or_tin, uc_account_id, ton_wallet_address, daily_buy_limit_uc, daily_distribute_limit_uc, False, _utc_now_iso(), _utc_now_iso()),
        )
        await conn.commit()


async def get_entity(entity_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_entity_members(entity_id: str) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM entity_members WHERE entity_id = ? ORDER BY role, member_id",
            (entity_id,)
        )
        rows = await cur.fetchall()
        return [dict(row) for row in rows]


async def add_entity_member(entity_id: str, member_id: str, role: str) -> None:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        await conn.execute(
            """
            INSERT INTO entity_members (entity_id, member_id, role, added_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(entity_id, member_id) DO UPDATE SET role = excluded.role
            """,
            (entity_id, member_id, role, _utc_now_iso()),
        )
        await conn.commit()


async def remove_entity_member(entity_id: str, member_id: str) -> None:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        await conn.execute(
            "DELETE FROM entity_members WHERE entity_id = ? AND member_id = ?",
            (entity_id, member_id),
        )
        await conn.commit()


async def get_member_entities(member_id: str) -> List[Dict[str, Any]]:
    """Get all entities a member is part of (as admin or beneficiary)."""
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """
            SELECT e.*, em.role
            FROM entities e
            JOIN entity_members em ON e.entity_id = em.entity_id
            WHERE em.member_id = ?
            ORDER BY e.entity_type, e.legal_name
            """,
            (member_id,)
        )
        rows = await cur.fetchall()
        return [dict(row) for row in rows]


async def is_entity_admin(entity_id: str, member_id: str) -> bool:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        cur = await conn.execute(
            "SELECT 1 FROM entity_members WHERE entity_id = ? AND member_id = ? AND role = 'admin'",
            (entity_id, member_id),
        )
        row = await cur.fetchone()
        return row is not None


async def update_entity(entity_id: str, **updates) -> None:
    if not updates:
        return
    updates["updated_at"] = _utc_now_iso()
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [entity_id]
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        await conn.execute(
            f"UPDATE entities SET {set_clause} WHERE entity_id = ?",
            values,
        )
        await conn.commit()


async def create_scheduled_distribution(
    schedule_id: str,
    entity_id: str,
    frequency: str,
    day_of_period: int,
    beneficiaries: List[Dict[str, Any]],
    total_amount_uc: float,
    next_run: str,
) -> None:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        await conn.execute(
            """
            INSERT INTO scheduled_distributions (schedule_id, entity_id, frequency, day_of_period, beneficiaries_json, total_amount_uc, next_run, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (schedule_id, entity_id, frequency, day_of_period, json.dumps(beneficiaries), total_amount_uc, next_run, True),
        )
        await conn.commit()


async def get_entity_schedules(entity_id: str) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM scheduled_distributions WHERE entity_id = ? ORDER BY next_run",
            (entity_id,)
        )
        rows = await cur.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["beneficiaries"] = json.loads(d.get("beneficiaries_json", "[]"))
            result.append(d)
        return result


async def delete_schedule(schedule_id: str) -> None:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        await conn.execute("DELETE FROM scheduled_distributions WHERE schedule_id = ?", (schedule_id,))
        await conn.commit()


# -----------------------------------------------------------------------------
# Draft parsing + risk
# -----------------------------------------------------------------------------


_AMOUNT_RE = re.compile(r"(?P<amt>\d+(?:\.\d{1,2})?)\s*(?:uc|credits|credit|usd|\\$)?", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[^\\s@]+@[^\\s@]+\\.[^\\s@]+")
_PHONE_RE = re.compile(r"\\+?\\d[\\d\\s\\-\\(\\)]{7,}")


def _extract_amount_uc(prompt: str) -> Optional[float]:
    # Prefer explicit "UC" mentions if present
    matches = list(_AMOUNT_RE.finditer(prompt))
    if not matches:
        return None
    # Heuristic: take the first amount that is not part of a year/date-like pattern
    for m in matches:
        try:
            amt = float(m.group("amt"))
        except Exception:
            continue
        if amt <= 0:
            continue
        if amt > 1_000_000:
            continue
        return amt
    return None


def _extract_recipient(prompt: str) -> Tuple[Optional[str], str]:
    # Email first
    em = _EMAIL_RE.search(prompt or "")
    if em:
        return em.group(0), "invite"
    ph = _PHONE_RE.search(prompt or "")
    if ph:
        return ph.group(0).strip(), "invite"
    # Member-like handle: @alice or member:alice
    handle = re.search(r"@([a-zA-Z0-9_\\-]{3,})", prompt or "")
    if handle:
        return handle.group(1), "member"
    member = re.search(r"member:([a-zA-Z0-9_\\-]{3,})", prompt or "")
    if member:
        return member.group(1), "member"
    return None, "unknown"


def _clean_note(prompt: str) -> str:
    # Remove obvious amount and recipient tokens, keep remainder as note
    text = (prompt or "").strip()
    text = _EMAIL_RE.sub("", text)
    text = _PHONE_RE.sub("", text)
    text = re.sub(r"@([a-zA-Z0-9_\\-]{3,})", "", text)
    text = re.sub(r"member:([a-zA-Z0-9_\\-]{3,})", "", text)
    text = _AMOUNT_RE.sub("", text, count=1)
    text = re.sub(r"\\s+", " ", text).strip()
    return text[:400]


async def assess_risk(from_member_id: str, amount_uc: float, to_member_id: Optional[str], invite_contact: Optional[str]) -> Tuple[List[str], str, TrustIndexPolicy]:
    """
    Assess risk and determine confirmation level using Trust Index adaptive ease.
    Per ZEND_REGENERATIVE_SPEC.md Part 4.1
    """
    flags: List[str] = []

    # Basic risk flags
    if amount_uc >= settings.large_amount_threshold_uc:
        flags.append("large_amount")

    if to_member_id:
        if not await has_sent_to_recipient(from_member_id, to_member_id):
            flags.append("new_recipient")
    if invite_contact:
        flags.append("invite_recipient")

    recent_sends = await get_recent_send_count(from_member_id, settings.repeated_sends_window_minutes)
    if recent_sends >= settings.repeated_sends_threshold:
        flags.append("repeated_sends")

    # Hard guardrails per spec Part 9
    if amount_uc > settings.max_send_uc:
        flags.append("exceeds_max_send")
    if amount_uc >= 5000:  # Human escalation threshold
        flags.append("human_escalation")

    # Fetch Trust Index policy for adaptive confirmation level
    policy = await trust_index.get_policy()

    # Emergency freeze check
    if policy.trust_index is not None and policy.trust_index < 0.2:
        flags.append("emergency_freeze")
        return flags, "human_review", policy

    # Determine confirmation level based on posture
    level = trust_index.confirmation_level_for_posture(policy.posture, amount_uc, flags)

    return flags, level, policy


async def ai_draft_best_effort(member_id: str, prompt: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Use credits-gateway /api/ai/query if configured. Best-effort only.
    """
    if not settings.draft_use_ai:
        return None, "ai_draft_disabled"
    if not settings.credits_api_key:
        return None, "missing_credits_api_key"

    # Ask the AI for strict JSON output matching our draft response shape.
    ai_prompt = f"""
You are an assistant drafting a ZEND UC transfer.
Output JSON only (no markdown).

User prompt:
{prompt}

Extract:
- recipient (member handle or invite contact like email/phone)
- recipient_type: member|invite|unknown
- amount_uc (number, UC units)
- note (short)

Return:
{{"recipient":"...", "recipient_type":"member|invite|unknown", "amount_uc": 0, "note": "..."}}
"""
    try:
        res = await credits.ai_query(
            account_id=member_id,
            prompt=ai_prompt,
            model=settings.draft_ai_model,
            max_tokens=settings.draft_ai_max_tokens,
        )
        if not res.get("success"):
            return None, res.get("error") or "ai_query_failed"
        raw = str(res.get("response") or "")
        if "{" in raw:
            parsed = json.loads(raw[raw.find("{") : raw.rfind("}") + 1])
            if isinstance(parsed, dict):
                return parsed, None
        return None, "ai_response_unparseable"
    except Exception as e:
        return None, str(e)


# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="ZEND Wallet", version=settings.service_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    ok, gateway_health = await credits.health()
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
        "credits_gateway": {
            "configured": bool(settings.credits_api_key),
            "url": settings.credits_gateway_url,
            "reachable": ok,
            "health": gateway_health,
        },
        "db_path": str(settings.db_path),
        "timestamp": _utc_now_iso(),
    }


@app.get("/api/zend/wallet/{member_id}", response_model=WalletResponse)
async def get_wallet(member_id: str):
    """
    Return UC balance + a calm 'unlocks' list.
    Per ZEND_REGENERATIVE_SPEC.md Part 6: Experience Layer
    """
    bal = await credits.get_balance(member_id)
    balances = bal.get("balances", {}) or {}
    pending = bal.get("pending", {}) or {}
    total_value = float(bal.get("total_value_usd") or 0.0)

    uc = float(balances.get("uc") or 0.0)

    # Experience unlocks based on lifetime UC balance
    # Per ZEND_REGENERATIVE_SPEC.md Part 6.1
    unlocked: List[str] = []
    if uc >= 100:  # EXPERIENCE_THRESHOLD_MEDITATION
        unlocked.append("meditation_invite")
    if uc >= 250:  # EXPERIENCE_THRESHOLD_ZEN_RAFFLE
        unlocked.append("zen_village_raffle")
    if uc >= 500:  # EXPERIENCE_THRESHOLD_SEND_FOR_ME
        unlocked.append("send_for_me")
    if uc >= 1000:  # EXPERIENCE_THRESHOLD_CONCIERGE
        unlocked.append("concierge_priority")
    if uc >= 2500:  # EXPERIENCE_THRESHOLD_FOUNDER
        unlocked.append("founding_member")

    # Friendly unlock descriptions
    unlock_descriptions = {
        "meditation_invite": "Meditation Partner Invite (1/month)",
        "zen_village_raffle": "Zen Village Raffle Entry",
        "send_for_me": "Send for Me (AI delegation)",
        "concierge_priority": "Concierge Human Review (priority queue)",
        "founding_member": "Founding Member Badge + Governance Voice",
    }

    unlocked_display = [unlock_descriptions.get(u, u) for u in unlocked]

    # Get Trust Index posture for sponsored sends info
    policy = await trust_index.get_policy()
    sponsored_sends = trust_index.sponsored_sends_for_posture(policy.posture)
    if sponsored_sends > 0:
        unlocked_display.append(f"{sponsored_sends} Sponsored Sends/week")

    notes = [
        "UC Credits are prepaid service credits (not money).",
        "No charts. No volatility. No stress.",
        "Money moves outside. Ease lives inside.",
        "Zend to Ascend.",
    ]

    return WalletResponse(
        member_id=member_id,
        uc_balance=round(uc, 8),
        balances={k: float(v) for k, v in balances.items()},
        pending={k: float(v) for k, v in pending.items()},
        total_value_usd=round(total_value, 4),
        unlocked=unlocked_display,
        notes=notes,
        timestamp=_utc_now_iso(),
    )


@app.post("/api/zend/draft-send", response_model=DraftSendResponse, dependencies=[Depends(require_admin_key)])
async def draft_send(req: DraftSendRequest):
    """
    Draft a UC send from natural language.
    Best-effort AI parsing + safe fallback parser.
    """
    ai_used = False
    ai_error: Optional[str] = None
    recipient: Optional[str] = None
    recipient_type: str = "unknown"
    amount_uc: float = 0.0
    note: str = ""

    ai_parsed, err = await ai_draft_best_effort(req.member_id, req.prompt)
    if ai_parsed:
        ai_used = True
        try:
            recipient = (ai_parsed.get("recipient") or "").strip() or None
            recipient_type = str(ai_parsed.get("recipient_type") or "unknown")
            amount_uc = float(ai_parsed.get("amount_uc") or 0.0)
            note = str(ai_parsed.get("note") or "")
        except Exception:
            ai_error = "ai_parsed_invalid"
            ai_used = False
    else:
        ai_error = err

    # Fallback parse
    if not recipient:
        recipient, recipient_type = _extract_recipient(req.prompt)
    if amount_uc <= 0:
        amt = _extract_amount_uc(req.prompt)
        amount_uc = float(amt or 0.0)
    if not note:
        note = _clean_note(req.prompt)

    # Clamp + guardrails for draft
    if amount_uc > settings.max_send_uc:
        amount_uc = settings.max_send_uc

    to_member_id = recipient if recipient_type == "member" else None
    invite_contact = recipient if recipient_type == "invite" else None
    risk_flags, confirm_level, policy = await assess_risk(req.member_id, amount_uc, to_member_id, invite_contact)

    return DraftSendResponse(
        recipient=recipient,
        recipient_type=recipient_type,
        amount_uc=round(float(amount_uc or 0.0), 2),
        note=note,
        risk_flags=risk_flags,
        confirm_level=confirm_level,
        requires_confirm=confirm_level not in ("low", "light") or bool(risk_flags),
        ai_used=ai_used,
        ai_error=ai_error,
    )


@app.post("/api/zend/send", response_model=SendResponse, dependencies=[Depends(require_admin_key)])
async def send_uc(req: SendRequest, background_tasks: BackgroundTasks):
    """
    Execute a UC transfer. If invite_contact is provided, escrow to system account and create invite_code.
    Logs contributions to contribution-tracker for Proof of Contribution (earns TRUST).
    """
    if req.amount_uc > settings.max_send_uc:
        raise HTTPException(status_code=400, detail=f"Amount exceeds cap ({settings.max_send_uc} UC)")

    if bool(req.to_member_id) == bool(req.invite_contact):
        raise HTTPException(status_code=400, detail="Provide exactly one of to_member_id OR invite_contact")

    # Risk assess with Trust Index integration
    risk_flags, confirm_level, policy = await assess_risk(req.from_member_id, req.amount_uc, req.to_member_id, req.invite_contact)

    # Emergency freeze check
    if "emergency_freeze" in risk_flags:
        raise HTTPException(status_code=503, detail="System is in emergency freeze mode. Sends are temporarily disabled.")

    # Confirmation required for non-light levels
    requires_confirm = confirm_level not in ("low", "light")
    if requires_confirm and not req.confirm:
        return SendResponse(
            success=False,
            kind="direct" if req.to_member_id else "invite",
            amount_uc=float(req.amount_uc),
            from_member_id=req.from_member_id,
            to_member_id=req.to_member_id,
            invite_contact=req.invite_contact,
            risk_flags=risk_flags,
            confirm_level=confirm_level,
            message=f"Confirmation required (posture: {policy.posture}). Use confirm=true to execute.",
        )

    now = _utc_now_iso()

    if req.invite_contact:
        invite_code = f"zend_{secrets.token_urlsafe(6)}"
        reason = f"zend_invite:{invite_code}"
        metadata = {
            **(req.metadata or {}),
            "invite_code": invite_code,
            "invite_contact": req.invite_contact,
            "note": req.note or "",
            "source": "zend-wallet",
        }

        gateway_result = await credits.transfer_uc(
            from_account=req.from_member_id,
            to_account=settings.escrow_account,
            amount_uc=req.amount_uc,
            reason=reason,
            metadata=metadata,
        )

        transfer_id = secrets.token_hex(8)

        # Persist invite + transfer record + log contribution (async)
        async def _persist():
            await create_invite_record(invite_code, req.from_member_id, req.invite_contact or "", req.amount_uc, req.note or "", gateway_result)
            await record_transfer(
                transfer_id=transfer_id,
                created_at=now,
                from_member_id=req.from_member_id,
                to_member_id=None,
                invite_contact=req.invite_contact,
                invite_code=invite_code,
                amount_uc=req.amount_uc,
                note=req.note or "",
                credit_type="uc",
                gateway_result=gateway_result,
            )
            # Log contribution for Proof of Contribution (referral will be credited on claim)
            await contribution_tracker.log_send_contribution(
                member_id=req.from_member_id,
                amount_uc=req.amount_uc,
                recipient_id=None,
                is_first_send_to_recipient=True,
                is_invite=True,
                transfer_id=transfer_id,
            )

        background_tasks.add_task(_persist)

        return SendResponse(
            success=True,
            kind="invite",
            amount_uc=float(req.amount_uc),
            from_member_id=req.from_member_id,
            invite_contact=req.invite_contact,
            invite_code=invite_code,
            escrow_account=settings.escrow_account,
            gateway_result=gateway_result,
            risk_flags=risk_flags,
            confirm_level=confirm_level,
            message="Escrowed to invite. Recipient must claim with invite_code.",
        )

    # Direct member-to-member
    reason = "zend_send"
    metadata = {
        **(req.metadata or {}),
        "note": req.note or "",
        "source": "zend-wallet",
    }

    gateway_result = await credits.transfer_uc(
        from_account=req.from_member_id,
        to_account=req.to_member_id or "",
        amount_uc=req.amount_uc,
        reason=reason,
        metadata=metadata,
    )

    transfer_id = secrets.token_hex(8)
    is_first_send = "new_recipient" in risk_flags

    async def _persist_direct():
        await record_transfer(
            transfer_id=transfer_id,
            created_at=now,
            from_member_id=req.from_member_id,
            to_member_id=req.to_member_id,
            invite_contact=None,
            invite_code=None,
            amount_uc=req.amount_uc,
            note=req.note or "",
            credit_type="uc",
            gateway_result=gateway_result,
        )
        # Log contribution for Proof of Contribution
        await contribution_tracker.log_send_contribution(
            member_id=req.from_member_id,
            amount_uc=req.amount_uc,
            recipient_id=req.to_member_id,
            is_first_send_to_recipient=is_first_send,
            is_invite=False,
            transfer_id=transfer_id,
        )

    background_tasks.add_task(_persist_direct)

    return SendResponse(
        success=True,
        kind="direct",
        amount_uc=float(req.amount_uc),
        from_member_id=req.from_member_id,
        to_member_id=req.to_member_id,
        gateway_result=gateway_result,
        risk_flags=risk_flags,
        confirm_level=confirm_level,
        message="Transfer executed.",
    )


@app.post("/api/zend/invites/claim", response_model=ClaimInviteResponse, dependencies=[Depends(require_admin_key)])
async def claim_invite(req: ClaimInviteRequest, background_tasks: BackgroundTasks):
    invite = await get_invite(req.invite_code)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Invite not claimable (status={invite.get('status')})")
    if not req.confirm:
        raise HTTPException(status_code=400, detail="confirm=true required to claim invite")

    amount_uc = float(invite.get("amount_uc") or 0.0)
    if amount_uc <= 0:
        raise HTTPException(status_code=400, detail="Invite amount invalid")

    reason = f"zend_claim:{req.invite_code}"
    metadata = {
        "invite_code": req.invite_code,
        "claimer_member_id": req.claimer_member_id,
        "invite_contact": invite.get("invite_contact"),
        "source": "zend-wallet",
    }

    gateway_result = await credits.transfer_uc(
        from_account=settings.escrow_account,
        to_account=req.claimer_member_id,
        amount_uc=amount_uc,
        reason=reason,
        metadata=metadata,
    )

    sender_member_id = invite.get("from_member_id") or ""

    async def _persist_claim():
        await mark_invite_claimed(req.invite_code, req.claimer_member_id, gateway_result)
        await record_transfer(
            transfer_id=secrets.token_hex(8),
            created_at=_utc_now_iso(),
            from_member_id=settings.escrow_account,
            to_member_id=req.claimer_member_id,
            invite_contact=invite.get("invite_contact"),
            invite_code=req.invite_code,
            amount_uc=amount_uc,
            note=f"claim:{req.invite_code}",
            credit_type="uc",
            gateway_result=gateway_result,
        )
        # Log referral contribution for sender (+50 per ZEND_REGENERATIVE_SPEC.md Part 5.1)
        if sender_member_id:
            await contribution_tracker.log_claim_contribution(
                sender_member_id=sender_member_id,
                claimer_member_id=req.claimer_member_id,
                amount_uc=amount_uc,
                invite_code=req.invite_code,
            )

    background_tasks.add_task(_persist_claim)

    return ClaimInviteResponse(
        success=True,
        invite_code=req.invite_code,
        amount_uc=amount_uc,
        claimer_member_id=req.claimer_member_id,
        gateway_result=gateway_result,
        message="Invite claimed and credited.",
    )


@app.get("/api/zend/policy")
async def get_policy():
    """
    Get current Trust Index policy affecting Zend confirmation levels.
    Per ZEND_REGENERATIVE_SPEC.md Part 11: AI Stewardship
    """
    policy = await trust_index.get_policy()
    sponsored_sends = trust_index.sponsored_sends_for_posture(policy.posture)

    return {
        "trust_index": policy.trust_index,
        "posture": policy.posture,
        "parameters": policy.parameters,
        "source": policy.source,
        "sponsored_sends_per_week": sponsored_sends,
        "confirmation_matrix": {
            "conservative": "Full confirm > $100, human review > $500",
            "balanced": "Light confirm < $500, full for larger",
            "generous": "Light confirm < $2000, Send for Me enabled",
            "emergency": "All sends require human review",
        },
        "timestamp": _utc_now_iso(),
    }


@app.post("/api/zend/explain")
async def explain_draft(req: DraftSendRequest):
    """
    Explain AI reasoning for a potential send.
    Per ZEND_REGENERATIVE_SPEC.md Part 11.2: Explain Endpoint

    Returns risk assessment and reasoning in transparent format.
    """
    # Parse the draft
    ai_parsed, ai_error = await ai_draft_best_effort(req.member_id, req.prompt)

    recipient: Optional[str] = None
    recipient_type: str = "unknown"
    amount_uc: float = 0.0

    if ai_parsed:
        recipient = (ai_parsed.get("recipient") or "").strip() or None
        recipient_type = str(ai_parsed.get("recipient_type") or "unknown")
        amount_uc = float(ai_parsed.get("amount_uc") or 0.0)

    if not recipient:
        recipient, recipient_type = _extract_recipient(req.prompt)
    if amount_uc <= 0:
        amt = _extract_amount_uc(req.prompt)
        amount_uc = float(amt or 0.0)

    to_member_id = recipient if recipient_type == "member" else None
    invite_contact = recipient if recipient_type == "invite" else None
    risk_flags, confirm_level, policy = await assess_risk(req.member_id, amount_uc, to_member_id, invite_contact)

    # Generate reasoning
    reasoning: List[str] = []

    # Amount reasoning
    if amount_uc <= 0:
        reasoning.append("Could not parse amount from prompt")
    elif amount_uc < 100:
        reasoning.append(f"Amount (${amount_uc:.2f}) is within normal range")
    elif amount_uc < 500:
        reasoning.append(f"Amount (${amount_uc:.2f}) is moderate")
    elif amount_uc < 5000:
        reasoning.append(f"Amount (${amount_uc:.2f}) is large, extra confirmation required")
    else:
        reasoning.append(f"Amount (${amount_uc:.2f}) exceeds human escalation threshold")

    # Recipient reasoning
    if "new_recipient" in risk_flags:
        reasoning.append("Recipient is new (no previous sends)")
    elif to_member_id:
        reasoning.append(f"Recipient ({to_member_id}) is a known contact")
    if "invite_recipient" in risk_flags:
        reasoning.append("Send to invite contact (requires escrow)")

    # Trust Index reasoning
    reasoning.append(f"Trust Index is {policy.trust_index or 'unknown'} ({policy.posture} posture)")

    # Risk flags reasoning
    if "repeated_sends" in risk_flags:
        reasoning.append("High-frequency sending detected")
    if "emergency_freeze" in risk_flags:
        reasoning.append("ALERT: System is in emergency freeze mode")

    return {
        "member_id": req.member_id,
        "parsed": {
            "recipient": recipient,
            "recipient_type": recipient_type,
            "amount_uc": amount_uc,
        },
        "risk_score": len(risk_flags) * 0.2,  # Simple risk score
        "risk_flags": risk_flags,
        "confirm_level": confirm_level,
        "policy": {
            "trust_index": policy.trust_index,
            "posture": policy.posture,
        },
        "reasoning": reasoning,
        "ai_used": bool(ai_parsed),
        "timestamp": _utc_now_iso(),
    }


# -----------------------------------------------------------------------------
# Entity Endpoints
# -----------------------------------------------------------------------------


@app.post("/api/zend/entities", response_model=EntityResponse, dependencies=[Depends(require_admin_key)])
async def register_entity(req: CreateEntityRequest, background_tasks: BackgroundTasks):
    """
    Register a new entity (trust, church, LLC, etc.).
    The requesting admin becomes the first admin of the entity.
    """
    entity_type = req.entity_type.lower()
    if entity_type not in ENTITY_LIMITS:
        raise HTTPException(status_code=400, detail=f"Invalid entity type: {entity_type}")

    limits = ENTITY_LIMITS[entity_type]
    entity_id = f"entity:{entity_type}:{secrets.token_urlsafe(8)}"
    uc_account_id = entity_id  # Use entity_id as Credits Gateway account

    # Create entity record
    await create_entity(
        entity_id=entity_id,
        entity_type=entity_type,
        legal_name=req.legal_name,
        ein_or_tin=req.ein_or_tin,
        uc_account_id=uc_account_id,
        ton_wallet_address=req.ton_wallet_address,
        daily_buy_limit_uc=limits["daily_buy"],
        daily_distribute_limit_uc=limits["daily_distribute"],
    )

    # Add the creator as admin
    await add_entity_member(entity_id, req.admin_member_id, "admin")

    return EntityResponse(
        entity_id=entity_id,
        entity_type=entity_type,
        legal_name=req.legal_name,
        ein_or_tin=req.ein_or_tin,
        uc_account_id=uc_account_id,
        ton_wallet_address=req.ton_wallet_address,
        daily_buy_limit_uc=limits["daily_buy"],
        daily_distribute_limit_uc=limits["daily_distribute"],
        is_liquidity_provider=False,
        admins=[req.admin_member_id],
        beneficiaries=[],
        uc_balance=0.0,
        created_at=_utc_now_iso(),
        updated_at=_utc_now_iso(),
    )


@app.get("/api/zend/entities/{entity_id}", response_model=EntityResponse)
async def get_entity_details(entity_id: str):
    """Get entity details including members and balance."""
    entity = await get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    members = await get_entity_members(entity_id)
    admins = [m["member_id"] for m in members if m["role"] == "admin"]
    beneficiaries = [m["member_id"] for m in members if m["role"] == "beneficiary"]

    # Get UC balance from Credits Gateway
    try:
        bal = await credits.get_balance(entity["uc_account_id"])
        uc_balance = float(bal.get("balances", {}).get("uc", 0.0))
    except Exception:
        uc_balance = 0.0

    return EntityResponse(
        entity_id=entity_id,
        entity_type=entity["entity_type"],
        legal_name=entity["legal_name"],
        ein_or_tin=entity.get("ein_or_tin"),
        uc_account_id=entity["uc_account_id"],
        ton_wallet_address=entity.get("ton_wallet_address"),
        daily_buy_limit_uc=entity["daily_buy_limit_uc"],
        daily_distribute_limit_uc=entity["daily_distribute_limit_uc"],
        is_liquidity_provider=bool(entity.get("is_liquidity_provider")),
        admins=admins,
        beneficiaries=beneficiaries,
        uc_balance=uc_balance,
        created_at=entity["created_at"],
        updated_at=entity["updated_at"],
    )


@app.put("/api/zend/entities/{entity_id}", dependencies=[Depends(require_admin_key)])
async def update_entity_details(entity_id: str, ton_wallet_address: Optional[str] = None, is_liquidity_provider: Optional[bool] = None):
    """Update entity details (admin only)."""
    entity = await get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    updates = {}
    if ton_wallet_address is not None:
        updates["ton_wallet_address"] = ton_wallet_address
    if is_liquidity_provider is not None:
        updates["is_liquidity_provider"] = is_liquidity_provider

    if updates:
        await update_entity(entity_id, **updates)

    return {"success": True, "entity_id": entity_id, "updated": list(updates.keys())}


@app.post("/api/zend/entities/{entity_id}/members", dependencies=[Depends(require_admin_key)])
async def add_member_to_entity(entity_id: str, req: AddMemberRequest):
    """Add a member (admin or beneficiary) to an entity."""
    entity = await get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    if req.role not in ("admin", "beneficiary"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'beneficiary'")

    await add_entity_member(entity_id, req.member_id, req.role)

    return {
        "success": True,
        "entity_id": entity_id,
        "member_id": req.member_id,
        "role": req.role,
        "message": f"Added {req.member_id} as {req.role}",
    }


@app.delete("/api/zend/entities/{entity_id}/members/{member_id}", dependencies=[Depends(require_admin_key)])
async def remove_member_from_entity(entity_id: str, member_id: str):
    """Remove a member from an entity."""
    entity = await get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    await remove_entity_member(entity_id, member_id)

    return {"success": True, "entity_id": entity_id, "member_id": member_id, "message": "Member removed"}


@app.post("/api/zend/entities/{entity_id}/distribute", response_model=DistributeResponse, dependencies=[Depends(require_admin_key)])
async def distribute_from_entity(entity_id: str, req: DistributeRequest, background_tasks: BackgroundTasks):
    """
    Distribute UC from entity treasury to multiple recipients.
    Only admins can execute distributions.
    """
    entity = await get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Validate distributions
    if not req.distributions:
        raise HTTPException(status_code=400, detail="No distributions provided")

    total_uc = sum(d.get("amount_uc", 0) for d in req.distributions)
    if req.total_amount_uc and abs(total_uc - req.total_amount_uc) > 0.01:
        raise HTTPException(status_code=400, detail=f"Distribution total ({total_uc}) doesn't match specified total ({req.total_amount_uc})")

    # Check entity has sufficient balance
    try:
        bal = await credits.get_balance(entity["uc_account_id"])
        entity_balance = float(bal.get("balances", {}).get("uc", 0.0))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to check entity balance: {e}")

    if entity_balance < total_uc:
        raise HTTPException(status_code=400, detail=f"Insufficient balance. Entity has {entity_balance} UC, need {total_uc} UC")

    # Check against daily limit
    if total_uc > entity["daily_distribute_limit_uc"]:
        raise HTTPException(status_code=400, detail=f"Distribution exceeds daily limit of {entity['daily_distribute_limit_uc']} UC")

    # Execute distributions
    results = []
    success_count = 0
    for dist in req.distributions:
        member_id = dist.get("member_id")
        amount = dist.get("amount_uc", 0)
        note = dist.get("note", req.note or f"Distribution from {entity['legal_name']}")

        if not member_id or amount <= 0:
            results.append({"member_id": member_id, "success": False, "error": "Invalid member_id or amount"})
            continue

        try:
            gateway_result = await credits.transfer_uc(
                from_account=entity["uc_account_id"],
                to_account=member_id,
                amount_uc=amount,
                reason=f"entity_distribution:{entity_id}",
                metadata={"entity_id": entity_id, "note": note, "source": "zend-wallet"},
            )
            results.append({"member_id": member_id, "success": True, "amount_uc": amount, "gateway_result": gateway_result})
            success_count += 1
        except Exception as e:
            results.append({"member_id": member_id, "success": False, "error": str(e)})

    # Get updated balance
    try:
        bal = await credits.get_balance(entity["uc_account_id"])
        treasury_after = float(bal.get("balances", {}).get("uc", 0.0))
    except Exception:
        treasury_after = entity_balance - total_uc

    return DistributeResponse(
        entity_id=entity_id,
        success=success_count == len(req.distributions),
        distributed_count=success_count,
        total_uc=total_uc,
        results=results,
        treasury_after=treasury_after,
        message=f"Distributed {total_uc} UC to {success_count}/{len(req.distributions)} recipients",
    )


@app.post("/api/zend/entities/{entity_id}/schedules", dependencies=[Depends(require_admin_key)])
async def create_distribution_schedule(entity_id: str, req: ScheduledDistributionRequest):
    """Create a scheduled distribution for an entity."""
    entity = await get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    if req.frequency not in ("weekly", "monthly", "quarterly"):
        raise HTTPException(status_code=400, detail="Frequency must be weekly, monthly, or quarterly")

    schedule_id = f"sched_{secrets.token_urlsafe(8)}"

    # Calculate next run
    now = datetime.now(timezone.utc)
    if req.frequency == "monthly":
        next_run = now.replace(day=min(req.day_of_period, 28), hour=9, minute=0, second=0, microsecond=0)
        if next_run <= now:
            if now.month == 12:
                next_run = next_run.replace(year=now.year + 1, month=1)
            else:
                next_run = next_run.replace(month=now.month + 1)
    elif req.frequency == "weekly":
        days_ahead = req.day_of_period - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_run = (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
    else:  # quarterly
        next_run = now.replace(day=min(req.day_of_period, 28), hour=9, minute=0, second=0, microsecond=0)
        month = ((now.month - 1) // 3 + 1) * 3 + 1
        if month > 12:
            month = 1
            next_run = next_run.replace(year=now.year + 1)
        next_run = next_run.replace(month=month)

    await create_scheduled_distribution(
        schedule_id=schedule_id,
        entity_id=entity_id,
        frequency=req.frequency,
        day_of_period=req.day_of_period,
        beneficiaries=req.beneficiaries,
        total_amount_uc=req.total_amount_uc,
        next_run=next_run.isoformat(),
    )

    return {
        "success": True,
        "schedule_id": schedule_id,
        "entity_id": entity_id,
        "frequency": req.frequency,
        "next_run": next_run.isoformat(),
    }


@app.get("/api/zend/entities/{entity_id}/schedules")
async def list_entity_schedules(entity_id: str):
    """List all scheduled distributions for an entity."""
    entity = await get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    schedules = await get_entity_schedules(entity_id)
    return {"entity_id": entity_id, "schedules": schedules, "count": len(schedules)}


@app.delete("/api/zend/entities/{entity_id}/schedules/{schedule_id}", dependencies=[Depends(require_admin_key)])
async def remove_distribution_schedule(entity_id: str, schedule_id: str):
    """Delete a scheduled distribution."""
    await delete_schedule(schedule_id)
    return {"success": True, "schedule_id": schedule_id, "message": "Schedule deleted"}


@app.get("/api/zend/wallet/{member_id}/unified", response_model=UnifiedWalletResponse)
async def get_unified_wallet(member_id: str):
    """
    Get unified wallet view including:
    - Personal UC balance
    - Entity contexts (trusts, churches, LLCs they admin/belong to)
    - TON wallet balances (if connected)
    """
    # Get personal UC balance
    try:
        bal = await credits.get_balance(member_id)
        uc_balance = float(bal.get("balances", {}).get("uc", 0.0))
    except Exception:
        uc_balance = 0.0

    # Get entities
    entities = await get_member_entities(member_id)
    entity_contexts = []
    for e in entities:
        try:
            ebal = await credits.get_balance(e["uc_account_id"])
            e_uc_balance = float(ebal.get("balances", {}).get("uc", 0.0))
        except Exception:
            e_uc_balance = 0.0

        entity_contexts.append({
            "entity_id": e["entity_id"],
            "entity_type": e["entity_type"],
            "name": e["legal_name"],
            "role": e["role"],
            "uc_balance": e_uc_balance,
            "ton_balance_usdt": None,  # TODO: Fetch from zend-ton
        })

    # Calculate total value
    total_entities_uc = sum(ec["uc_balance"] for ec in entity_contexts if ec["role"] == "admin")
    total_value = uc_balance + total_entities_uc  # 1 UC = $1

    # Get experience unlocks
    unlocked = []
    if uc_balance >= 100:
        unlocked.append("meditation_invite")
    if uc_balance >= 250:
        unlocked.append("zen_village_raffle")
    if uc_balance >= 500:
        unlocked.append("send_for_me")
    if uc_balance >= 1000:
        unlocked.append("concierge_priority")
    if uc_balance >= 2500:
        unlocked.append("founding_member")

    return UnifiedWalletResponse(
        member_id=member_id,
        uc_balance=uc_balance,
        entity_contexts=entity_contexts,
        ton_connected=False,  # TODO: Check zend-ton
        ton_address=None,
        ton_balances={},
        total_value_usd=total_value,
        unlocked=unlocked,
        timestamp=_utc_now_iso(),
    )


@app.get("/api/zend/member/{member_id}/entities")
async def list_member_entities(member_id: str):
    """List all entities a member belongs to."""
    entities = await get_member_entities(member_id)
    return {
        "member_id": member_id,
        "entities": entities,
        "count": len(entities),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
