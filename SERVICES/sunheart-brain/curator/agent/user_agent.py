"""Per-user agent model and storage backends."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Protocol


TIER_ORDER = {"free": 0, "basic": 1, "pro": 2}
DAILY_MESSAGE_LIMITS = {"free": 10, "basic": 100, "pro": None}


class UserNotOnboarded(Exception):
    """Raised when no user_agents row exists for the requested user."""


class RateLimitExceeded(Exception):
    """Raised when a tenant has exhausted their daily tier allowance."""


class AgentStore(Protocol):
    async def load(self, user_id: str) -> dict[str, Any] | None: ...
    async def create(self, row: dict[str, Any]) -> dict[str, Any]: ...
    async def update(self, user_id: str, updates: dict[str, Any]) -> None: ...
    async def recent_context(self, user_id: str, last_n: int) -> list[dict[str, Any]]: ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _same_utc_day(value: Any, today: date | None = None) -> bool:
    if value is None:
        return False
    today = today or _utc_now().date()
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date() == today
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date() == today
    except ValueError:
        return False


def _memory_namespace(user_id: str, channel: str) -> str:
    safe_user = re.sub(r"[^A-Za-z0-9_]+", "_", str(user_id or "user"))[:32].strip("_")
    safe_channel = re.sub(r"[^A-Za-z0-9_]+", "_", str(channel or "unknown"))[:24].strip("_")
    return f"u_{safe_user[:8] or 'user'}_{safe_channel or 'unknown'}"


@dataclass
class UserAgent:
    user_id: str
    namespace: str
    tier: str = "free"
    capabilities: dict[str, bool] = field(default_factory=dict)
    consent_log: list[dict[str, Any]] = field(default_factory=list)
    cora_balance: int = 0
    proof_count: int = 0
    session_count: int = 0
    last_seen: Any = None
    deletion_requested_at: Any = None
    display_name: str | None = None
    store: AgentStore | None = field(default=None, repr=False, compare=False)

    @classmethod
    async def load(cls, user_id: str, store: AgentStore | None = None) -> "UserAgent":
        store = store or PostgresAgentStore()
        row = await store.load(user_id)
        if not row:
            raise UserNotOnboarded(user_id)
        return cls.from_row(row, store=store)

    @classmethod
    async def create(
        cls,
        user_id: str,
        channel: str,
        beacon_id: str,
        store: AgentStore | None = None,
        display_name: str | None = None,
    ) -> "UserAgent":
        store = store or PostgresAgentStore()
        row = {
            "user_id": user_id,
            "display_name": display_name,
            "tier": "free",
            "system_prompt_override": None,
            "memory_namespace": _memory_namespace(user_id, channel),
            "capability_grants": {},
            "consent_log": [],
            "stripe_customer_id": None,
            "subscription_status": "none",
            "cora_balance": 0,
            "proof_count": 0,
            "session_count": 0,
            "last_seen": None,
            "data_region": "eu",
            "beacon_id": beacon_id,
        }
        return cls.from_row(await store.create(row), store=store)

    @classmethod
    def from_row(cls, row: dict[str, Any], store: AgentStore | None = None) -> "UserAgent":
        capabilities = row.get("capability_grants") or {}
        if isinstance(capabilities, str):
            capabilities = json.loads(capabilities)
        consent_log = row.get("consent_log") or []
        if isinstance(consent_log, str):
            consent_log = json.loads(consent_log)
        return cls(
            user_id=str(row["user_id"]),
            namespace=str(row["memory_namespace"]),
            tier=str(row.get("tier") or "free"),
            capabilities=dict(capabilities),
            consent_log=list(consent_log),
            cora_balance=int(row.get("cora_balance") or 0),
            proof_count=int(row.get("proof_count") or 0),
            session_count=int(row.get("session_count") or 0),
            last_seen=row.get("last_seen"),
            deletion_requested_at=row.get("deletion_requested_at"),
            display_name=row.get("display_name"),
            store=store,
        )

    async def get_context(self, last_n: int = 20) -> list[dict[str, Any]]:
        if not self.store:
            raise RuntimeError("UserAgent has no store")
        return await self.store.recent_context(self.user_id, last_n)

    def can(self, capability: str) -> bool:
        from .capability_registry import CAPABILITY_REGISTRY

        spec = CAPABILITY_REGISTRY.get(capability)
        if not spec:
            return False
        if TIER_ORDER.get(self.tier, 0) < TIER_ORDER[str(spec["tier"])]:
            return False
        if spec["consent_required"]:
            return bool(self.capabilities.get(capability, False))
        return True

    async def grant(self, capability: str, consented_at: str) -> None:
        self.capabilities[capability] = True
        self.consent_log.append({"capability": capability, "granted_at": consented_at, "revoked_at": None})
        await self._persist({"capability_grants": self.capabilities, "consent_log": self.consent_log})

    async def revoke(self, capability: str) -> None:
        self.capabilities.pop(capability, None)
        revoked_at = _utc_now().isoformat()
        for entry in reversed(self.consent_log):
            if entry.get("capability") == capability and not entry.get("revoked_at"):
                entry["revoked_at"] = revoked_at
                break
        else:
            self.consent_log.append({"capability": capability, "granted_at": None, "revoked_at": revoked_at})
        await self._persist({"capability_grants": self.capabilities, "consent_log": self.consent_log})

    async def request_deletion(self) -> None:
        self.deletion_requested_at = _utc_now().isoformat()
        await self._persist({"deletion_requested_at": self.deletion_requested_at})

    async def record_message_or_raise(self) -> None:
        limit = DAILY_MESSAGE_LIMITS.get(self.tier, DAILY_MESSAGE_LIMITS["free"])
        if limit is None:
            self.session_count += 1
            self.last_seen = _utc_now()
            await self._persist({"session_count": self.session_count, "last_seen": self.last_seen})
            return
        if not _same_utc_day(self.last_seen):
            self.session_count = 0
        if self.session_count >= limit:
            raise RateLimitExceeded(self.user_id)
        self.session_count += 1
        self.last_seen = _utc_now()
        await self._persist({"session_count": self.session_count, "last_seen": self.last_seen})

    async def _persist(self, updates: dict[str, Any]) -> None:
        if not self.store:
            raise RuntimeError("UserAgent has no store")
        await self.store.update(self.user_id, updates)


class InMemoryAgentStore:
    """Tiny async store for unit tests and dry local wiring checks."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self.thread: list[dict[str, Any]] = []

    async def load(self, user_id: str) -> dict[str, Any] | None:
        row = self.rows.get(user_id)
        return copy.deepcopy(row) if row else None

    async def create(self, row: dict[str, Any]) -> dict[str, Any]:
        base_ns = str(row["memory_namespace"])
        namespace = base_ns
        suffix = 2
        existing = {r["memory_namespace"] for r in self.rows.values()}
        while namespace in existing:
            namespace = f"{base_ns}_{suffix}"
            suffix += 1
        stored = copy.deepcopy(row)
        stored["memory_namespace"] = namespace
        stored.setdefault("created_at", _utc_now())
        self.rows[stored["user_id"]] = stored
        return copy.deepcopy(stored)

    async def update(self, user_id: str, updates: dict[str, Any]) -> None:
        self.rows[user_id].update(copy.deepcopy(updates))

    async def recent_context(self, user_id: str, last_n: int) -> list[dict[str, Any]]:
        rows = [copy.deepcopy(r) for r in self.thread if r.get("user_id") == user_id]
        rows = sorted(rows, key=lambda r: r.get("at") or "")[-last_n:]
        return rows


class PostgresAgentStore:
    async def load(self, user_id: str) -> dict[str, Any] | None:
        from ..db import connect

        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM brain_index.user_agents WHERE user_id = %s",
                    (user_id,),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                cols = [d.name for d in cur.description]
                return dict(zip(cols, row))

    async def create(self, row: dict[str, Any]) -> dict[str, Any]:
        from ..db import connect

        base_namespace = str(row["memory_namespace"])
        for suffix in range(1, 100):
            attempt = dict(row)
            attempt["memory_namespace"] = base_namespace if suffix == 1 else f"{base_namespace}_{suffix}"
            async with connect() as conn:
                async with conn.cursor() as cur:
                    try:
                        await cur.execute(
                            """
                            INSERT INTO brain_index.user_agents
                                (user_id, display_name, tier, system_prompt_override,
                                 memory_namespace, capability_grants, consent_log,
                                 stripe_customer_id, subscription_status, cora_balance,
                                 proof_count, session_count, last_seen, data_region)
                            VALUES
                                (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s,
                                 %s, %s, %s, %s, %s)
                            ON CONFLICT (user_id) DO NOTHING
                            RETURNING *
                            """,
                            (
                                attempt["user_id"],
                                attempt.get("display_name"),
                                attempt.get("tier", "free"),
                                attempt.get("system_prompt_override"),
                                attempt["memory_namespace"],
                                json.dumps(attempt.get("capability_grants") or {}),
                                json.dumps(attempt.get("consent_log") or []),
                                attempt.get("stripe_customer_id"),
                                attempt.get("subscription_status", "none"),
                                attempt.get("cora_balance", 0),
                                attempt.get("proof_count", 0),
                                attempt.get("session_count", 0),
                                attempt.get("last_seen"),
                                attempt.get("data_region", "eu"),
                            ),
                        )
                        inserted = await cur.fetchone()
                        if inserted:
                            cols = [d.name for d in cur.description]
                            return dict(zip(cols, inserted))
                        break
                    except Exception as exc:
                        await conn.rollback()
                        if "memory_namespace" not in str(exc):
                            raise
                        continue
        loaded = await self.load(row["user_id"])
        if not loaded:
            raise UserNotOnboarded(row["user_id"])
        return loaded

    async def update(self, user_id: str, updates: dict[str, Any]) -> None:
        from ..db import connect

        allowed = {
            "capability_grants",
            "consent_log",
            "deletion_requested_at",
            "session_count",
            "last_seen",
        }
        updates = {k: v for k, v in updates.items() if k in allowed}
        if not updates:
            return
        assignments: list[str] = []
        params: list[Any] = []
        for key, value in updates.items():
            if key in {"capability_grants", "consent_log"}:
                assignments.append(f"{key} = %s::jsonb")
                params.append(json.dumps(value))
            else:
                assignments.append(f"{key} = %s")
                params.append(value)
        params.append(user_id)
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"UPDATE brain_index.user_agents SET {', '.join(assignments)} WHERE user_id = %s",
                    tuple(params),
                )

    async def recent_context(self, user_id: str, last_n: int) -> list[dict[str, Any]]:
        from ..db import connect

        async with connect() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        """
                        SELECT at, surface, role, text
                          FROM brain_index.thread
                         WHERE user_id = %s
                         ORDER BY at DESC
                         LIMIT %s
                        """,
                        (user_id, last_n),
                    )
                    rows = list(reversed(await cur.fetchall()))
                    return [
                        {"at": at, "surface": surface, "role": role, "text": text, "user_id": user_id}
                        for at, surface, role, text in rows
                    ]
                except Exception:
                    await conn.rollback()
                    await cur.execute(
                        """
                        SELECT at, 'telegram' AS surface, role, text
                          FROM brain_index.tg_messages
                         WHERE chat_id = %s AND private_flag IS NOT TRUE
                         ORDER BY at DESC
                         LIMIT %s
                        """,
                        (user_id, last_n),
                    )
                    rows = list(reversed(await cur.fetchall()))
                    return [
                        {"at": at, "surface": surface, "role": role, "text": text, "user_id": user_id}
                        for at, surface, role, text in rows
                    ]
