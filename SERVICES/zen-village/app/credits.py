"""
Zen Credits — brand layer over the canonical UC ledger.

1 ZC = 1 UC = $1 USD. Internally we always use credit_type=uc on the
fp-credits-gateway. The "Zen Credits" wording is for guest-facing UI only.

Wallet identity: member:{sha1(lower(email))[:16]}
Compatible with the zend-wallet pattern (opaque stable string ids).
"""

from __future__ import annotations

import hashlib
import os
from typing import Optional

import httpx

CREDITS_GATEWAY = os.getenv("CREDITS_GATEWAY_URL", "http://127.0.0.1:8765")
CREDITS_API_KEY = os.getenv("CREDITS_GATEWAY_KEY", "")
CREDIT_TYPE = "uc"

ZC_LABEL_SINGULAR = "Zen Credit"
ZC_LABEL_PLURAL = "Zen Credits"
ZC_SHORT = "ZC"


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def wallet_id_for_email(email: str) -> str:
    """Stable opaque wallet account_id derived from email."""
    e = _norm_email(email)
    if not e:
        raise ValueError("email required")
    h = hashlib.sha1(e.encode("utf-8")).hexdigest()[:16]
    return f"member:{h}"


def format_zc(amount: float, *, with_label: bool = True, short: bool = False) -> str:
    """Render a UC amount as 'X Zen Credits' (or 'X ZC')."""
    n = float(amount or 0)
    s = f"{n:,.2f}".rstrip("0").rstrip(".") if n != int(n) else f"{int(n):,}"
    if not with_label:
        return s
    if short:
        return f"{s} {ZC_SHORT}"
    label = ZC_LABEL_SINGULAR if abs(n) == 1 else ZC_LABEL_PLURAL
    return f"{s} {label}"


def _gw_headers() -> dict:
    h = {"Content-Type": "application/json"}
    if CREDITS_API_KEY:
        h["X-API-Key"] = CREDITS_API_KEY
    return h


async def ensure_account(account_id: str, *, email: str = "", name: str = "") -> dict:
    """Create the account on the gateway if it doesn't exist. Idempotent."""
    async with httpx.AsyncClient(timeout=8) as c:
        try:
            r = await c.get(
                f"{CREDITS_GATEWAY}/api/accounts/{account_id}", headers=_gw_headers()
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        try:
            r = await c.post(
                f"{CREDITS_GATEWAY}/api/accounts",
                headers=_gw_headers(),
                json={
                    "account_id": account_id,
                    "name": name or account_id,
                    "email": email or "",
                    "account_type": "user",
                },
            )
            if r.status_code in (200, 201):
                return r.json()
        except Exception as e:
            print(f"[credits] ensure_account failed for {account_id}: {e}")
    return {"account_id": account_id}


async def gateway_balance_uc(account_id: str) -> float:
    """Return UC balance for the account, or 0.0 if not found."""
    async with httpx.AsyncClient(timeout=8) as c:
        try:
            r = await c.get(
                f"{CREDITS_GATEWAY}/api/balance/{account_id}", headers=_gw_headers()
            )
            if r.status_code != 200:
                return 0.0
            data = r.json() or {}
            balances = data.get("balances") or {}
            return float(balances.get(CREDIT_TYPE) or 0.0)
        except Exception as e:
            print(f"[credits] balance fetch failed for {account_id}: {e}")
            return 0.0


async def gateway_credit_uc(
    account_id: str,
    amount: float,
    reason: str,
    *,
    metadata: Optional[dict] = None,
) -> dict:
    """Credit UC to the account. Returns the gateway response or {ok:false,error}."""
    if amount <= 0:
        return {"ok": False, "error": "non-positive amount"}
    payload = {
        "account_id": account_id,
        "amount": float(amount),
        "credit_type": CREDIT_TYPE,
        "reason": (reason or "Zen Credits")[:500],
    }
    if metadata:
        payload["metadata"] = metadata
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.post(
                f"{CREDITS_GATEWAY}/api/credit", headers=_gw_headers(), json=payload
            )
            if r.status_code in (200, 201):
                return {"ok": True, **(r.json() or {})}
            return {"ok": False, "error": f"gateway {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


async def gateway_debit_uc(
    account_id: str,
    amount: float,
    reason: str,
    *,
    metadata: Optional[dict] = None,
) -> dict:
    if amount <= 0:
        return {"ok": False, "error": "non-positive amount"}
    payload = {
        "account_id": account_id,
        "amount": float(amount),
        "credit_type": CREDIT_TYPE,
        "reason": (reason or "Zen Credits debit")[:500],
    }
    if metadata:
        payload["metadata"] = metadata
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.post(
                f"{CREDITS_GATEWAY}/api/debit", headers=_gw_headers(), json=payload
            )
            if r.status_code in (200, 201):
                return {"ok": True, **(r.json() or {})}
            return {"ok": False, "error": f"gateway {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


async def gateway_recent_transactions(account_id: str, limit: int = 20) -> list[dict]:
    """Pull recent ledger entries for the account. Best-effort."""
    async with httpx.AsyncClient(timeout=8) as c:
        try:
            r = await c.get(
                f"{CREDITS_GATEWAY}/api/accounts/{account_id}/transactions",
                params={"limit": limit, "credit_type": CREDIT_TYPE},
                headers=_gw_headers(),
            )
            if r.status_code != 200:
                return []
            data = r.json() or {}
            return data.get("transactions") or data.get("list") or []
        except Exception:
            return []
