"""
Zen Village Affiliate / Referral System
- Config-driven commission rates (editable at runtime via admin UI)
- ?ref=CODE auto-tracking via cookie
- Idempotent conversion (same source_id won't double-credit)
- Best-effort mirror to NocoDB (Partners + Commissions tables)
- Admin endpoints gated by ZV_AFFILIATES_ADMIN_TOKEN
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from pydantic import BaseModel, EmailStr

logger = logging.getLogger("affiliates")
router = APIRouter()

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
DATA_DIR = Path(os.environ.get("ZV_DATA_DIR", "/opt/fpai/apps/zen-village/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
PARTNERS_FILE = DATA_DIR / "partners.json"
REFERRALS_FILE = DATA_DIR / "referrals.json"
COMMISSIONS_FILE = DATA_DIR / "commissions.json"
CONFIG_FILE = DATA_DIR / "commission_config.json"
APPLICATIONS_FILE = DATA_DIR / "partner_applications.json"  # invite-only queue

DEFAULT_CONFIG = {
    "rates": {
        # ─── Role-based rates (stacked when one partner fills multiple roles) ──
        # sourcer: brought the lead via their own channel (?ref cookie)
        # closer:  had the conversation, got the yes (admin-assigned post-fact)
        # producer: admin-only super-rate; replaces stack when partner is flagged
        # repeat_bonus: paid to ORIGINAL sourcer when guest_email re-converts
        "sourcer": 0.10,
        "closer": 0.15,
        "producer": 0.35,
        "repeat_bonus": 0.05,
        # ─── Per-product rates (legacy / fallback) ────────────────────────────
        # Used as the sourcer slice when admin has explicitly tuned a product
        # away from the default 10%. Otherwise the sourcer rate above wins.
        "stay": 0.10,
        "retreat": 0.10,
        "day_pass": 0.10,
        "event": 0.10,
        "credits": 0.05,
        # Wallet top-ups: 5% on first top-up by a referral (the sign-up bonus
        # for the partner who set up that wallet), then 1% on every future
        # top-up by the same wallet. The system rewrites booking_type from
        # "credits_topup" → "credits_topup_first" when no prior top-up exists
        # for the same guest_email.
        "credits_topup_first": 0.05,
        "credits_topup": 0.01,
        "spend": 0.01,
        "coherent_inquiry": 0.10,
        "support_donation": 0.10,
        # Tier-2 sponsor share — MLM-style override. The partner who sponsored
        # a tier-1 partner (i.e. the partner whose ?ref the tier-1 used when
        # creating their own wallet) earns this share of every commission the
        # tier-1 partner earns. Default = 10% × tier-1.
        "tier2_share": 0.10,
        "default": 0.10,
    },
    "cookie_days": 90,
    "default_payout_method": "credits",
    "site_base_url": "https://zenvillagecr.com",
    "min_payout_amount": 0.0,
    "auto_create_partner_on_accept": True,
    "repeat_window_months": 12,
}

# ---------------------------------------------------------------------------
# Helpers — JSON file storage (atomic-ish writes)
# ---------------------------------------------------------------------------
def _load(p: Path) -> dict:
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            logger.exception("failed to load %s; resetting", p)
    return {}


def _save(p: Path, data: dict) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    os.replace(tmp, p)


def _config() -> dict:
    cfg = _load(CONFIG_FILE)
    if not cfg:
        cfg = DEFAULT_CONFIG.copy()
        _save(CONFIG_FILE, cfg)
        return cfg
    # Backfill any missing keys (so admin UI never sees holes), and persist
    # the merge so new defaults (e.g. role-based rate keys) land on disk.
    changed = False
    for k, v in DEFAULT_CONFIG.items():
        if k not in cfg:
            cfg[k] = v
            changed = True
    if "rates" in cfg:
        for k, v in DEFAULT_CONFIG["rates"].items():
            if k not in cfg["rates"]:
                cfg["rates"][k] = v
                changed = True
    if changed:
        try:
            _save(CONFIG_FILE, cfg)
        except Exception as e:
            logger.warning("could not persist backfilled config: %s", e)
    return cfg


def _calc_commission(booking_type: str, amount: float, cfg: dict | None = None) -> float:
    """Legacy single-rate calculator. Used as the sourcer slice when no closer
    is assigned. Honors per-product overrides (e.g. rates['credits']=0.05)."""
    cfg = cfg or _config()
    rates = cfg.get("rates", {})
    # Prefer per-product override if set, otherwise fall back to the role rate
    rate = rates.get(booking_type)
    if rate is None:
        rate = rates.get("sourcer", rates.get("default", 0.10))
    return round(float(amount) * float(rate), 2)


def _rate(role: str, cfg: dict) -> float:
    """Look up a role rate with sensible fallback defaults."""
    defaults = {"sourcer": 0.10, "closer": 0.15, "producer": 0.35, "repeat_bonus": 0.05}
    return float(cfg.get("rates", {}).get(role, defaults.get(role, 0.0)))


def _calc_stacked_commission(
    *,
    booking_type: str,
    amount: float,
    sourcer_code: str = "",
    closer_code: str = "",
    is_producer: bool = False,
    repeat_for_code: str = "",
    cfg: dict | None = None,
) -> dict:
    """Compute the per-role commission splits for a conversion.

    Returns:
      {
        "splits": [{"role", "partner_code", "rate", "amount"}, ...],
        "total":  float,
        "mode":   "producer" | "stacked"
      }

    Producer mode (admin-flagged partner) replaces the standard sourcer+closer
    stack with a single higher-rate payout. Repeat-bonus is independent: paid
    to the original sourcer whenever the same guest re-books, regardless of
    mode.
    """
    cfg = cfg or _config()
    splits: list[dict] = []

    if is_producer:
        primary = (sourcer_code or closer_code or "").upper().strip()
        if primary:
            rate = _rate("producer", cfg)
            splits.append({
                "role": "producer",
                "partner_code": primary,
                "rate": rate,
                "amount": round(float(amount) * rate, 2),
            })
        mode = "producer"
    else:
        # Sourcer slice — honors per-product override (e.g. credits=0.05) if set
        if sourcer_code:
            rates = cfg.get("rates", {})
            override = rates.get(booking_type)
            sourcer_rate = float(override) if override is not None else _rate("sourcer", cfg)
            splits.append({
                "role": "sourcer",
                "partner_code": sourcer_code.upper().strip(),
                "rate": sourcer_rate,
                "amount": round(float(amount) * sourcer_rate, 2),
            })
        if closer_code:
            closer_rate = _rate("closer", cfg)
            splits.append({
                "role": "closer",
                "partner_code": closer_code.upper().strip(),
                "rate": closer_rate,
                "amount": round(float(amount) * closer_rate, 2),
            })
        mode = "stacked"

    if repeat_for_code:
        repeat_rate = _rate("repeat_bonus", cfg)
        splits.append({
            "role": "repeat_bonus",
            "partner_code": repeat_for_code.upper().strip(),
            "rate": repeat_rate,
            "amount": round(float(amount) * repeat_rate, 2),
        })

    total = round(sum(s["amount"] for s in splits), 2)
    return {"splits": splits, "total": total, "mode": mode}


# ---------------------------------------------------------------------------
# Per-partner overrides — founding-cohort ramp-down + custom flat rates
# ---------------------------------------------------------------------------
# Partner record may carry these fields:
#   founding_rate            (float, e.g. 0.50)  — used while founding_sales_remaining > 0
#   founding_sales_remaining (int,   e.g. 2)    — decremented on each qualifying sale
#   standard_rate            (float, e.g. 0.15) — used once founding sales are spent
#
# When set, these REPLACE the standard sourcer/closer/producer stack with a
# single flat rate slice. Repeat-bonus is skipped under override (single-rate
# math by design). Override only fires for booking_type in FOUNDING_QUALIFY_TYPES.

FOUNDING_QUALIFY_TYPES = {"retreat", "stay", "5day_reset", "reset_retreat"}


def _per_partner_override_splits(
    *,
    partners: dict,
    sourcer_code: str,
    closer_code: str,
    booking_type: str,
    booking_amount: float,
) -> Optional[dict]:
    """If the primary partner (sourcer, or closer if sourcer is empty) has a
    per-partner rate override set (founding_rate or standard_rate), return a
    single-slice override dict and decrement founding_sales_remaining when
    applicable. Mutates `partners` in place; caller persists with _save().

    Returns None to fall through to the standard sourcer/closer/producer stack.
    """
    primary_code = (sourcer_code or closer_code or "").upper().strip()
    if not primary_code:
        return None
    p = partners.get(primary_code)
    if not p:
        return None
    if (p.get("status") or "active") != "active":
        return None

    founding_remaining = int(p.get("founding_sales_remaining", 0) or 0)
    founding_rate = float(p.get("founding_rate", 0) or 0)
    standard_rate = float(p.get("standard_rate", 0) or 0)

    qualifies = booking_type in FOUNDING_QUALIFY_TYPES

    if founding_remaining > 0 and founding_rate > 0 and qualifies:
        rate = founding_rate
        role = "founding"
        p["founding_sales_remaining"] = founding_remaining - 1
        if p["founding_sales_remaining"] == 0:
            p["founding_completed_at"] = datetime.utcnow().isoformat()
    elif standard_rate > 0:
        rate = standard_rate
        role = "standard_custom"
    else:
        return None

    amount = round(float(booking_amount) * rate, 2)
    return {
        "splits": [{
            "role": role,
            "partner_code": primary_code,
            "rate": rate,
            "amount": amount,
        }],
        "total": amount,
        "mode": role,
    }


def _is_first_topup(guest_email: str, exclude_source_id: str = "") -> bool:
    """True if this is the FIRST credits_topup conversion for guest_email.
    Used to swap booking_type from 'credits_topup' (1%) to 'credits_topup_first' (5%).
    """
    email_l = (guest_email or "").lower().strip()
    if not email_l:
        return False  # no email → can't tell, default to repeat-rate (safer)
    try:
        commissions = _load(COMMISSIONS_FILE)
        for c in commissions.values():
            if (c.get("guest_email") or "").lower().strip() != email_l:
                continue
            if c.get("source_id") == exclude_source_id:
                continue
            bt = c.get("booking_type") or ""
            if bt in ("credits_topup", "credits_topup_first"):
                return False
        return True
    except Exception:
        return False


def _credit_partner_wallet(
    partner_code: str,
    amount: float,
    reason: str,
    *,
    metadata: Optional[dict] = None,
) -> bool:
    """Best-effort: credit the partner's Zen Wallet (UC ledger) with `amount`.
    Returns True if the credit landed. Skips silently if partner has no email
    on file or the wallet account doesn't exist yet — those commissions stay
    'pending' and will be swept on wallet sign-up.
    """
    if amount <= 0 or not partner_code:
        return False
    try:
        partners = _load(PARTNERS_FILE)
        p = partners.get((partner_code or "").upper().strip())
        if not p:
            return False
        email = (p.get("email") or "").strip()
        if not email:
            return False  # no wallet to deposit into yet

        # Late import: avoid circular import at module load time.
        from app.credits import (
            wallet_id_for_email,
            ensure_account,
            gateway_credit_uc,
        )
        import asyncio as _aio

        wallet_id = wallet_id_for_email(email)

        async def _do():
            await ensure_account(wallet_id, email=email, name=p.get("name") or "")
            return await gateway_credit_uc(
                wallet_id, float(amount), reason,
                metadata=metadata or {"kind": "affiliate_commission"},
            )

        try:
            loop = _aio.get_event_loop()
            if loop.is_running():
                # Already inside an event loop (FastAPI handler context) — schedule
                # but don't block; caller continues.
                _aio.ensure_future(_do())
                return True
        except RuntimeError:
            pass

        result = _aio.run(_do())
        return bool(result and result.get("ok"))
    except Exception as e:
        logger.warning("credit_partner_wallet %s failed: %s", partner_code, e)
        return False


def sweep_pending_commissions_to_wallet(email: str) -> dict:
    """Called from wallet sign-up. For every active partner whose email matches
    the freshly-verified wallet email, mark all 'pending' commissions as 'paid'
    and credit the total to the wallet.
    Returns {"swept": int, "total_zc": float, "partners": [codes]}.
    """
    email_l = (email or "").strip().lower()
    if not email_l:
        return {"swept": 0, "total_zc": 0.0, "partners": []}

    partners = _load(PARTNERS_FILE)
    matched_codes = [
        code for code, p in partners.items()
        if (p.get("email") or "").strip().lower() == email_l
    ]
    if not matched_codes:
        return {"swept": 0, "total_zc": 0.0, "partners": []}

    commissions = _load(COMMISSIONS_FILE)
    now = datetime.utcnow().isoformat()
    total = 0.0
    swept_ids = []
    for cid, c in commissions.items():
        if c.get("partner_code") not in matched_codes:
            continue
        if c.get("status") != "pending":
            continue
        amt = float(c.get("commission_amount", 0))
        if amt <= 0:
            continue
        total += amt
        c["status"] = "paid"
        c["paid_at"] = now
        c["payout_method"] = "wallet_sweep"
        swept_ids.append(cid)

    if total > 0:
        # One consolidated wallet credit per sweep so the user sees a single
        # readable transaction in their wallet history.
        try:
            from app.credits import (
                wallet_id_for_email, ensure_account, gateway_credit_uc,
            )
            import asyncio as _aio

            wallet_id = wallet_id_for_email(email_l)

            async def _do():
                await ensure_account(wallet_id, email=email_l, name=partners[matched_codes[0]].get("name") or "")
                return await gateway_credit_uc(
                    wallet_id, round(total, 2),
                    f"Sweep affiliate commissions ({len(swept_ids)} pending)",
                    metadata={"kind": "affiliate_sweep", "partner_codes": matched_codes},
                )

            try:
                loop = _aio.get_event_loop()
                if loop.is_running():
                    _aio.ensure_future(_do())
                else:
                    _aio.run(_do())
            except RuntimeError:
                _aio.run(_do())
        except Exception as e:
            logger.warning("sweep wallet credit failed: %s", e)

        # Reset per-partner pending_payout
        for code in matched_codes:
            partners[code]["pending_payout"] = 0
        _save(PARTNERS_FILE, partners)
        _save(COMMISSIONS_FILE, commissions)

    return {
        "swept": len(swept_ids),
        "total_zc": round(total, 2),
        "partners": matched_codes,
    }


def link_partner_sponsor(partner_email: str, sponsor_code: str) -> Optional[str]:
    """Set partner.sponsor_code if not already set. Used when a wallet that
    came in via ?ref=SPONSOR later turns out to belong to a partner. Returns
    the partner code that got linked (or None)."""
    email_l = (partner_email or "").strip().lower()
    sp = (sponsor_code or "").upper().strip()
    if not (email_l and sp):
        return None
    partners = _load(PARTNERS_FILE)
    if sp not in partners:
        return None
    target = None
    for code, p in partners.items():
        if (p.get("email") or "").strip().lower() == email_l:
            if not p.get("sponsor_code"):
                p["sponsor_code"] = sp
                target = code
            break
    if target:
        _save(PARTNERS_FILE, partners)
        try:
            _sync_partner_to_nocodb(partners[target])
        except Exception:
            pass
    return target


def _find_original_sourcer(guest_email: str, exclude_source_id: str = "") -> Optional[str]:
    """Find the partner_code of the EARLIEST conversion for this guest_email
    (sourcer or producer role only) that falls within the repeat_window_months
    window from now. Used to credit a repeat-booking bonus to the partner who
    first brought the guest, but only while the relationship is still 'fresh'.
    """
    if not guest_email:
        return None
    email_l = guest_email.lower().strip()
    if not email_l:
        return None
    try:
        cfg = _config()
        window_months = int(cfg.get("repeat_window_months", 12) or 0)
        cutoff_iso = ""
        if window_months > 0:
            cutoff = datetime.utcnow() - timedelta(days=int(window_months * 30.5))
            cutoff_iso = cutoff.isoformat()

        commissions = _load(COMMISSIONS_FILE)
        candidates = []
        for c in commissions.values():
            if (c.get("guest_email") or "").lower().strip() != email_l:
                continue
            if c.get("source_id") == exclude_source_id:
                continue
            if c.get("role") not in (None, "", "sourcer", "producer"):
                continue
            ts = c.get("timestamp") or ""
            if cutoff_iso and ts and ts < cutoff_iso:
                continue
            candidates.append(c)
        if not candidates:
            return None
        candidates.sort(key=lambda c: c.get("timestamp", ""))
        return candidates[0].get("partner_code")
    except Exception:
        return None


def _gen_code(name: str) -> str:
    base = "".join(c for c in name.lower() if c.isalnum())[:6] or "zv"
    suffix = hashlib.md5(f"{name}{datetime.utcnow().isoformat()}{secrets.token_hex(4)}".encode()).hexdigest()[:4]
    return f"{base}{suffix}".upper()


# ---------------------------------------------------------------------------
# Admin auth — ZV_AFFILIATES_ADMIN_TOKEN env var (or first request bootstraps)
# ---------------------------------------------------------------------------
def _admin_token() -> str:
    return os.environ.get("ZV_AFFILIATES_ADMIN_TOKEN", "")


def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    expected = _admin_token()
    if not expected:
        raise HTTPException(503, "Admin token not configured (set ZV_AFFILIATES_ADMIN_TOKEN env var)")
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(401, "Invalid admin token")


# ---------------------------------------------------------------------------
# NocoDB best-effort mirror
# ---------------------------------------------------------------------------
_NOCODB_URL = os.environ.get("NOCODB_URL", "http://127.0.0.1:8080").rstrip("/")
_NOCODB_TOKEN = os.environ.get("NOCODB_API_TOKEN", "")
_NOCODB_PARTNERS_TABLE = os.environ.get("NOCODB_PARTNERS_TABLE_ID", "")
_NOCODB_COMMISSIONS_TABLE = os.environ.get("NOCODB_COMMISSIONS_TABLE_ID", "")


def _noco_upsert(table_id: str, where_field: str, where_value: str, payload: dict) -> None:
    if not (_NOCODB_TOKEN and table_id):
        return
    try:
        where = urllib.parse.quote(f"({where_field},eq,{where_value})")
        list_url = f"{_NOCODB_URL}/api/v2/tables/{table_id}/records?where={where}&limit=1&fields=Id,{where_field}"
        req = urllib.request.Request(list_url, headers={"xc-token": _NOCODB_TOKEN})
        existing = json.loads(urllib.request.urlopen(req, timeout=5).read()).get("list", [])
        if existing and existing[0].get("Id"):
            payload_with_id = dict(payload)
            payload_with_id["Id"] = existing[0]["Id"]
            req2 = urllib.request.Request(
                f"{_NOCODB_URL}/api/v2/tables/{table_id}/records",
                data=json.dumps([payload_with_id]).encode(),
                method="PATCH",
                headers={"xc-token": _NOCODB_TOKEN, "Content-Type": "application/json"},
            )
            urllib.request.urlopen(req2, timeout=5).read()
        else:
            req2 = urllib.request.Request(
                f"{_NOCODB_URL}/api/v2/tables/{table_id}/records",
                data=json.dumps(payload).encode(),
                method="POST",
                headers={"xc-token": _NOCODB_TOKEN, "Content-Type": "application/json"},
            )
            urllib.request.urlopen(req2, timeout=5).read()
    except Exception as e:
        logger.warning("nocodb upsert %s/%s failed: %s", table_id, where_value, e)


def _sync_partner_to_nocodb(p: dict) -> None:
    if not _NOCODB_PARTNERS_TABLE:
        return
    payload = {
        "Code": p.get("code", ""),
        "Name": (p.get("name") or "")[:255],
        "Email": (p.get("email") or "")[:255],
        "Phone": (p.get("phone") or "")[:64],
        "Status": (p.get("status") or "active"),
        "PayoutMethod": (p.get("payout_method") or "credits"),
        "TotalReferrals": int(p.get("total_referrals") or 0),
        "TotalEarned": float(p.get("total_earned") or 0),
        "PendingPayout": float(p.get("pending_payout") or 0),
        "CreatedAt": p.get("created_at") or datetime.utcnow().isoformat(),
        "Notes": (p.get("notes") or "")[:8000],
    }
    _noco_upsert(_NOCODB_PARTNERS_TABLE, "Code", p["code"], payload)


def _sync_commission_to_nocodb(c: dict) -> None:
    if not _NOCODB_COMMISSIONS_TABLE:
        return
    payload = {
        "CommissionId": c.get("id", ""),
        "PartnerCode": c.get("partner_code", ""),
        "BookingType": c.get("booking_type", ""),
        "BookingAmount": float(c.get("booking_amount") or 0),
        "CommissionAmount": float(c.get("commission_amount") or 0),
        "Status": c.get("status", "pending"),
        "GuestEmail": (c.get("guest_email") or "")[:255],
        "SourceId": (c.get("source_id") or "")[:128],
        "BookingDetails": (c.get("booking_details") or "")[:8000],
        "Timestamp": c.get("timestamp") or datetime.utcnow().isoformat(),
        "PaidAt": c.get("paid_at") or None,
    }
    _noco_upsert(_NOCODB_COMMISSIONS_TABLE, "CommissionId", c["id"], payload)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class TrackRequest(BaseModel):
    partner_code: str
    page: Optional[str] = "/"


class BookingConversion(BaseModel):
    partner_code: Optional[str] = ""           # sourcer (the ?ref cookie code)
    closer_partner_code: Optional[str] = ""    # closer (admin-assigned, optional)
    booking_type: str  # stay | retreat | day_pass | event | credits | other
    booking_amount: float
    guest_email: Optional[str] = ""
    booking_details: Optional[str] = None
    source_id: Optional[str] = None  # idempotency key (booking_id, pass_id, etc.)


class PartnerCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = ""
    payout_method: Optional[str] = None  # credits | cash | both
    notes: Optional[str] = ""


class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[str] = None  # active | paused | revoked
    payout_method: Optional[str] = None
    notes: Optional[str] = None
    # Per-partner rate overrides (see _per_partner_override_splits for semantics)
    founding_rate: Optional[float] = None             # e.g. 0.50 (50%)
    founding_sales_remaining: Optional[int] = None    # e.g. 2 — decrements per qualifying sale
    standard_rate: Optional[float] = None             # e.g. 0.15 (15%) — used after founding sales exhausted


class ConfigUpdate(BaseModel):
    rates: Optional[dict] = None
    cookie_days: Optional[int] = None
    default_payout_method: Optional[str] = None
    site_base_url: Optional[str] = None
    min_payout_amount: Optional[float] = None
    auto_create_partner_on_accept: Optional[bool] = None


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------
@router.post("/track")
async def track_referral(request: Request, response: Response, data: TrackRequest):
    """Record a visit + set the zv_ref cookie."""
    cfg = _config()
    referrals = _load(REFERRALS_FILE)
    code = data.partner_code.upper().strip()
    partners = _load(PARTNERS_FILE)
    if code not in partners:
        # Soft fail: we still set cookie so no race-conditions, but flag it
        logger.info("track called with unknown partner_code=%s", code)

    visitor_id = hashlib.md5(
        f"{request.client.host}{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()[:12]
    referral_id = f"ref_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{visitor_id[:6]}"
    referrals[referral_id] = {
        "id": referral_id,
        "partner_code": code,
        "visitor_id": visitor_id,
        "landing_page": data.page,
        "timestamp": datetime.utcnow().isoformat(),
        "converted": False,
        "ip_hash": hashlib.md5(request.client.host.encode()).hexdigest()[:8],
    }
    _save(REFERRALS_FILE, referrals)

    response.set_cookie(
        key="zv_ref",
        value=code,
        max_age=int(cfg.get("cookie_days", 90)) * 24 * 60 * 60,
        httponly=False,  # readable by JS so frontend can show "Referred by X"
        samesite="lax",
        path="/",
    )
    return {"status": "tracked", "referral_id": referral_id}


@router.get("/check")
async def check_referral(request: Request):
    code = (request.cookies.get("zv_ref") or "").upper().strip()
    if not code:
        return {"has_referral": False}
    partners = _load(PARTNERS_FILE)
    partner = partners.get(code)
    if not partner:
        return {"has_referral": False}
    return {
        "has_referral": True,
        "partner_code": code,
        "partner_name": partner.get("name", "Partner"),
    }


def _apply_conversion(
    *,
    booking_type: str,
    booking_amount: float,
    sourcer_code: str = "",
    closer_code: str = "",
    guest_email: str = "",
    booking_details: str = "",
    source_id: str = "",
    cfg: Optional[dict] = None,
) -> dict:
    """Core conversion writer. Builds one commission record per role-slice
    (sourcer / closer / producer / repeat_bonus) under a shared conversion
    group id. Idempotent on source_id.

    Returns:
      {"status": "converted"|"duplicate"|"skipped",
       "conversion_group_id": str, "commissions": [records...],
       "total": float, "mode": "stacked"|"producer", ...}
    """
    cfg = cfg or _config()
    partners = _load(PARTNERS_FILE)
    commissions = _load(COMMISSIONS_FILE)

    sourcer_code = (sourcer_code or "").upper().strip()
    closer_code = (closer_code or "").upper().strip()

    # Filter known/active partners
    def _ok(code: str) -> bool:
        return bool(code) and code in partners and (partners[code].get("status") or "active") == "active"

    if sourcer_code and not _ok(sourcer_code):
        sourcer_code = ""
    if closer_code and not _ok(closer_code):
        closer_code = ""

    if not (sourcer_code or closer_code):
        return {"status": "skipped", "reason": "no_active_partner"}

    # Idempotency
    if source_id:
        existing = [c for c in commissions.values() if c.get("source_id") == source_id]
        if existing:
            return {
                "status": "duplicate",
                "conversion_group_id": existing[0].get("conversion_group_id") or existing[0].get("id"),
                "commissions": existing,
                "total": round(sum(c.get("commission_amount", 0) for c in existing), 2),
            }

    # Wallet top-up: first-time gets the 5% sign-up bonus rate, every subsequent
    # top-up by the same wallet drops to 1% (transaction-fee tier).
    if booking_type == "credits_topup" and _is_first_topup(guest_email, exclude_source_id=source_id):
        booking_type = "credits_topup_first"

    # Producer mode is per-partner. If sourcer is producer-flagged, treat as
    # producer; else if closer is producer-flagged AND no sourcer, treat as
    # producer. Mixed sourcer/closer where one side is producer = stacked
    # (producer flag is owner-of-relationship, not a magic stacking trigger).
    is_producer = False
    primary = sourcer_code or closer_code
    if primary and partners.get(primary, {}).get("is_producer"):
        is_producer = True

    # Repeat-booking detection — paid to the ORIGINAL sourcer
    repeat_for_code = ""
    if guest_email:
        original = _find_original_sourcer(guest_email, exclude_source_id=source_id)
        if original and _ok(original):
            repeat_for_code = original

    # Per-partner override (founding-cohort ramp-down / custom flat rate).
    # If primary partner has founding_rate or standard_rate set, this REPLACES
    # the standard sourcer/closer/producer stack with a single-slice payout.
    # Mutates `partners` dict (decrements founding_sales_remaining); we persist
    # below via the existing _save(PARTNERS_FILE, partners) call.
    override = _per_partner_override_splits(
        partners=partners,
        sourcer_code=sourcer_code,
        closer_code=closer_code,
        booking_type=booking_type,
        booking_amount=float(booking_amount),
    )

    if override:
        splits = override
    else:
        splits = _calc_stacked_commission(
            booking_type=booking_type,
            amount=float(booking_amount),
            sourcer_code=sourcer_code,
            closer_code=closer_code,
            is_producer=is_producer,
            repeat_for_code=repeat_for_code,
            cfg=cfg,
        )

    if not splits["splits"]:
        return {"status": "skipped", "reason": "zero_splits"}

    group_id = f"conv_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(3)}"
    now = datetime.utcnow().isoformat()
    created: list[dict] = []

    for s in splits["splits"]:
        commission_id = f"com_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(3)}"
        record = {
            "id": commission_id,
            "conversion_group_id": group_id,
            "partner_code": s["partner_code"],
            "role": s["role"],
            "rate_applied": s["rate"],
            "booking_type": booking_type,
            "booking_amount": float(booking_amount),
            "commission_amount": s["amount"],
            "guest_email": guest_email or "",
            "booking_details": booking_details or "",
            "source_id": source_id or "",
            "timestamp": now,
            "status": "pending",
            "paid_at": None,
        }
        commissions[commission_id] = record
        created.append(record)

        p = partners[s["partner_code"]]
        # Only the sourcer slice counts as a NEW referral; closer / repeat /
        # producer are role payouts, not new visits.
        if s["role"] in ("sourcer", "producer"):
            p["total_referrals"] = int(p.get("total_referrals", 0)) + 1
        p["total_earned"] = round(float(p.get("total_earned", 0)) + s["amount"], 2)
        p["pending_payout"] = round(float(p.get("pending_payout", 0)) + s["amount"], 2)

    # ─── Tier-2 sponsor override (MLM 10%) ──────────────────────────────────
    # For each tier-1 split, if the earning partner has a sponsor_code and the
    # sponsor is an active partner, give the sponsor `tier2_share` × tier-1
    # amount. Skips repeat_bonus and tier2 splits themselves to avoid pyramid
    # cascading (single-level override only).
    # NOTE: per-partner overrides (founding / standard_custom) are flat single-rate
    # payouts by design — skip the tier-2 cascade in that mode so the override
    # rate stays the only commission paid.
    tier2_share = float(cfg.get("rates", {}).get("tier2_share", 0.10))
    if tier2_share > 0 and splits.get("mode") not in ("founding", "standard_custom"):
        tier2_records = []
        for s in list(splits["splits"]):
            if s["role"] in ("repeat_bonus", "tier2_sponsor"):
                continue
            tier1_partner = partners.get(s["partner_code"]) or {}
            sponsor_code = (tier1_partner.get("sponsor_code") or "").upper().strip()
            if not sponsor_code or sponsor_code == s["partner_code"] or not _ok(sponsor_code):
                continue
            tier2_amount = round(float(s["amount"]) * tier2_share, 2)
            if tier2_amount <= 0:
                continue
            commission_id = f"com_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(3)}"
            record = {
                "id": commission_id,
                "conversion_group_id": group_id,
                "partner_code": sponsor_code,
                "role": "tier2_sponsor",
                "rate_applied": tier2_share,
                "booking_type": booking_type,
                "booking_amount": float(booking_amount),
                "commission_amount": tier2_amount,
                "guest_email": guest_email or "",
                "booking_details": (booking_details or "") + f" [tier2 of {s['partner_code']}]",
                "source_id": source_id or "",
                "timestamp": now,
                "status": "pending",
                "paid_at": None,
                "tier1_partner_code": s["partner_code"],
            }
            commissions[commission_id] = record
            created.append(record)
            tier2_records.append(record)
            sp = partners[sponsor_code]
            sp["total_earned"] = round(float(sp.get("total_earned", 0)) + tier2_amount, 2)
            sp["pending_payout"] = round(float(sp.get("pending_payout", 0)) + tier2_amount, 2)
        if tier2_records:
            splits["total"] = round(splits["total"] + sum(r["commission_amount"] for r in tier2_records), 2)

    # ─── Auto-deposit each commission to the partner's Zen Wallet ────────────
    # Best-effort: if the partner has an email and a wallet account exists, the
    # ZC lands in their wallet immediately and the commission is marked paid.
    # Otherwise it stays 'pending' and will be swept when they sign up at /wallet.
    for record in created:
        try:
            ok = _credit_partner_wallet(
                record["partner_code"],
                record["commission_amount"],
                f"Affiliate commission: {record['booking_type']} ({record['role']})",
                metadata={
                    "kind": "affiliate_commission",
                    "conversion_group_id": group_id,
                    "commission_id": record["id"],
                    "role": record["role"],
                    "booking_type": record["booking_type"],
                },
            )
            if ok:
                record["status"] = "paid"
                record["paid_at"] = datetime.utcnow().isoformat()
                record["payout_method"] = "wallet_auto"
                pcode = record["partner_code"]
                p = partners.get(pcode)
                if p:
                    p["pending_payout"] = max(
                        0.0,
                        round(float(p.get("pending_payout", 0)) - record["commission_amount"], 2),
                    )
        except Exception as e:
            logger.warning("auto-deposit failed for %s: %s", record["id"], e)

    _save(COMMISSIONS_FILE, commissions)
    _save(PARTNERS_FILE, partners)

    for record in created:
        _sync_commission_to_nocodb(record)
    for code in {r["partner_code"] for r in created}:
        _sync_partner_to_nocodb(partners[code])

    logger.info(
        "conversion %s: type=%s amount=%s splits=%s total=%s mode=%s",
        group_id, booking_type, booking_amount,
        [(s["role"], s["partner_code"], s["amount"]) for s in splits["splits"]],
        splits["total"], splits["mode"],
    )
    return {
        "status": "converted",
        "conversion_group_id": group_id,
        "commissions": created,
        "total": splits["total"],
        "mode": splits["mode"],
    }


@router.post("/convert")
async def convert_referral(data: BookingConversion):
    """Idempotent conversion: same source_id will not double-credit.
    Stacks sourcer + closer commissions when both are provided."""
    if not (data.partner_code or data.closer_partner_code):
        raise HTTPException(400, "Either partner_code or closer_partner_code is required")
    return _apply_conversion(
        booking_type=data.booking_type,
        booking_amount=data.booking_amount,
        sourcer_code=data.partner_code or "",
        closer_code=data.closer_partner_code or "",
        guest_email=data.guest_email or "",
        booking_details=data.booking_details or "",
        source_id=data.source_id or "",
    )


@router.get("/partners/{code}/public")
async def partner_public(code: str):
    """Public partner page data (link, name, total_referrals only — no money figures)."""
    code = code.upper().strip()
    partners = _load(PARTNERS_FILE)
    if code not in partners:
        raise HTTPException(404, "Partner not found")
    p = partners[code]
    cfg = _config()
    base = cfg.get("site_base_url", "https://zenvillagecr.com").rstrip("/")
    return {
        "code": code,
        "name": p.get("name"),
        "status": p.get("status", "active"),
        "total_referrals": int(p.get("total_referrals", 0)),
        "referral_link": f"{base}/?ref={code}",
        "qr_url": f"{base}/api/affiliates/qr/{code}",
    }


@router.get("/qr/{code}")
async def partner_qr(code: str):
    """Generate a QR code PNG for the referral link."""
    try:
        import qrcode
        import io
        from fastapi.responses import StreamingResponse
    except ImportError:
        raise HTTPException(503, "qrcode library not installed")
    code = code.upper().strip()
    cfg = _config()
    base = cfg.get("site_base_url", "https://zenvillagecr.com").rstrip("/")
    img = qrcode.make(f"{base}/?ref={code}")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    from fastapi.responses import StreamingResponse
    return StreamingResponse(buf, media_type="image/png")


# ---------------------------------------------------------------------------
# Partner self-service dashboard (HMAC token, no admin auth)
# ---------------------------------------------------------------------------
import hmac as _hmac


def _dashboard_secret() -> str:
    """Secret for HMAC-signing partner dashboard tokens. Falls back to a stable
    hostname-derived value if ZV_PARTNER_DASHBOARD_SECRET isn't set so tokens
    remain valid across restarts on the same host."""
    s = (os.environ.get("ZV_PARTNER_DASHBOARD_SECRET") or "").strip()
    if not s:
        import socket
        s = "zv-partner-fallback-" + socket.gethostname()
    return s


def partner_dashboard_token(code: str) -> str:
    """Deterministic HMAC-SHA256 token for a partner code.

    Same code + same secret = same token, always. No persistence needed.
    Truncated to 24 hex chars (96 bits) — comfortable security margin for
    a low-volume affiliate dashboard.
    """
    code = (code or "").upper().strip()
    return _hmac.new(
        _dashboard_secret().encode(),
        code.encode(),
        hashlib.sha256,
    ).hexdigest()[:24]


@router.get("/me")
async def partner_me(code: str, token: str):
    """Per-partner self-service dashboard. HMAC-gated.

    Returns the partner's leads (filtered from inquiries.json by partner_code),
    pending + paid commissions, their commission rate, and shareable links.
    """
    code = (code or "").upper().strip()
    if not (code and token):
        raise HTTPException(400, "code and token required")
    expected = partner_dashboard_token(code)
    if not _hmac.compare_digest(token, expected):
        raise HTTPException(403, "invalid token")

    partners = _load(PARTNERS_FILE)
    p = partners.get(code)
    if not p:
        raise HTTPException(404, "partner not found")

    cfg = _config()
    base = cfg.get("site_base_url", "https://zenvillagecr.com").rstrip("/")

    # Their commissions
    commissions = _load(COMMISSIONS_FILE)
    if isinstance(commissions, dict):
        commission_records = list(commissions.values())
    else:
        commission_records = list(commissions or [])
    mine = [c for c in commission_records if (c.get("partner_code") or "").upper().strip() == code]
    pending = [c for c in mine if (c.get("status") or "pending") == "pending"]
    paid = [c for c in mine if (c.get("status") or "") == "paid"]

    def _sum(items):
        return round(sum(float(c.get("commission_amount", 0) or 0) for c in items), 2)

    # Their leads, filtered from inquiries.json
    leads = []
    try:
        inq_path = DATA_DIR / "inquiries.json"
        if inq_path.exists():
            raw = json.loads(inq_path.read_text())
            if isinstance(raw, list):
                for inq in raw:
                    if (inq.get("partner_code") or "").upper().strip() != code:
                        continue
                    pm = inq.get("payment_method") or ""
                    itype = inq.get("inquiry_type") or "Stay"
                    is_paid_intent = bool(pm) and (
                        "reset retreat" in itype.lower() or "jungle exhale" in itype.lower()
                    )
                    leads.append({
                        "id": inq.get("id"),
                        "timestamp": inq.get("timestamp"),
                        "name": inq.get("name"),
                        "email": inq.get("email"),
                        "dates": inq.get("dates"),
                        "accommodation": inq.get("accommodation"),
                        "type": itype,
                        "status": "paid_intent" if is_paid_intent else "inquired",
                        "payment_method": pm if is_paid_intent else None,
                    })
                leads.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    except Exception as e:
        logger.warning("failed loading inquiries for partner dashboard: %s", e)

    return {
        "code": code,
        "name": p.get("name", code),
        "status": p.get("status", "active"),
        "rates": {
            "founding_rate": p.get("founding_rate"),
            "founding_sales_remaining": p.get("founding_sales_remaining"),
            "standard_rate": p.get("standard_rate"),
            "default_sourcer_rate": (cfg.get("rates", {}) or {}).get("sourcer", 0.10),
        },
        "totals": {
            "leads": len(leads),
            "pending_commissions_count": len(pending),
            "pending_commissions_total": _sum(pending),
            "paid_commissions_count": len(paid),
            "paid_commissions_total": _sum(paid),
            "lifetime_earned": _sum(paid),
        },
        "leads": leads[:50],
        "share_link": f"{base}/reset?ref={code}",
        "dashboard_link": f"{base}/reset/me?code={code}&token={token}",
    }


# ---------------------------------------------------------------------------
# Public application + info (no admin auth)
# ---------------------------------------------------------------------------
class PartnerApplication(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = ""
    payout_method: Optional[str] = None  # credits | cash | both
    relationship: Optional[str] = ""     # how they know Zen Village
    how_share: Optional[str] = ""        # how they plan to share
    website: Optional[str] = ""          # honeypot — should stay empty
    referrer_code: Optional[str] = ""    # who referred this partner (zv_ref cookie)


# Tiny in-memory rate-limit (per-IP, per-process) — good enough first pass
_APPLY_BUCKET: dict = {}

def _apply_rate_ok(ip: str, max_per_hour: int = 5) -> bool:
    import time
    now = time.time()
    window = 3600
    bucket = _APPLY_BUCKET.setdefault(ip, [])
    bucket[:] = [t for t in bucket if now - t < window]
    if len(bucket) >= max_per_hour:
        return False
    bucket.append(now)
    return True


@router.post("/apply")
async def public_apply(request: Request, data: PartnerApplication):
    """Public partner signup. Auto-approves; admin can pause/revoke anytime."""
    # Honeypot — bots fill any visible field
    if (data.website or "").strip():
        return {"status": "ok", "code": "ZVPENDING"}  # silently swallow

    ip = (request.client.host if request.client else "unknown") or "unknown"
    if not _apply_rate_ok(ip):
        raise HTTPException(429, "Too many signups from this network. Please try again later.")

    cfg = _config()
    partners = _load(PARTNERS_FILE)

    # Reject duplicate email (silently return existing code so they don't double-create)
    email_lower = data.email.lower().strip()
    for code, p in partners.items():
        if (p.get("email") or "").lower().strip() == email_lower:
            base = cfg.get("site_base_url", "https://zenvillagecr.com").rstrip("/")
            return {
                "status": "existing",
                "code": code,
                "name": p.get("name"),
                "referral_link": f"{base}/?ref={code}",
                "qr_url": f"{base}/api/affiliates/qr/{code}",
            }

    code = _gen_code(data.name)
    while code in partners:
        code = _gen_code(data.name + secrets.token_hex(2))

    notes_parts = []
    if data.relationship: notes_parts.append(f"Relationship: {data.relationship}")
    if data.how_share: notes_parts.append(f"Plans to share: {data.how_share}")
    if data.referrer_code: notes_parts.append(f"Referred by: {data.referrer_code}")
    notes_parts.append(f"Signed up via /partner page from IP {ip}")

    partner = {
        "code": code,
        "name": data.name.strip(),
        "email": email_lower,
        "phone": (data.phone or "").strip(),
        "payout_method": data.payout_method or cfg.get("default_payout_method", "credits"),
        "notes": " | ".join(notes_parts),
        "created_at": datetime.utcnow().isoformat(),
        "status": "active",
        "total_referrals": 0,
        "total_earned": 0,
        "pending_payout": 0,
        "self_signup": True,
        "is_producer": False,  # Admin-only flag, never self-set
    }
    partners[code] = partner
    _save(PARTNERS_FILE, partners)
    _sync_partner_to_nocodb(partner)

    base = cfg.get("site_base_url", "https://zenvillagecr.com").rstrip("/")
    logger.info("public partner signup: code=%s email=%s ip=%s", code, email_lower, ip)
    return {
        "status": "created",
        "code": code,
        "name": partner["name"],
        "referral_link": f"{base}/?ref={code}",
        "qr_url": f"{base}/api/affiliates/qr/{code}",
        "dashboard_url": f"{base}/partner/{code}",
    }


@router.get("/public-info")
async def public_info():
    """Non-sensitive info for the public signup page — rates, cookie window,
    and the role-based stacking model so partners understand the math."""
    cfg = _config()
    rates = cfg.get("rates", {})
    def pct(v): return f"{round(v*100)}%"
    sourcer = float(rates.get("sourcer", 0.10))
    closer = float(rates.get("closer", 0.15))
    repeat = float(rates.get("repeat_bonus", 0.05))
    return {
        "site_base_url": cfg.get("site_base_url", "https://zenvillagecr.com").rstrip("/"),
        "cookie_days": cfg.get("cookie_days", 90),
        "default_payout_method": cfg.get("default_payout_method", "credits"),
        # ─── Role-based stacking model (the new headline) ─────────────────────
        "roles": [
            {
                "key": "sourcer",
                "label": "You source",
                "rate": pct(sourcer),
                "desc": "Your link, your channel, your audience. Guest converts via our funnel."
            },
            {
                "key": "closer",
                "label": "You close",
                "rate": pct(closer),
                "desc": "We send you a warm lead from our marketing. You have the call. You get the yes."
            },
            {
                "key": "stack",
                "label": "You source + close",
                "rate": pct(sourcer + closer),
                "desc": "Your lead, your conversation, your close. Top earnings.",
                "highlight": True,
            },
            {
                "key": "repeat_bonus",
                "label": "Repeat-booking bonus",
                "rate": "+" + pct(repeat),
                "desc": "Same guest comes back within 12 months — original sourcer earns again."
            },
        ],
        # ─── Per-product rates (mostly informational; sourcer rate applies)
        "tiers": [
            {"label": "Retreats & Stays", "rate": pct(rates.get("stay", 0.10)), "key": "stay"},
            {"label": "Event Passes", "rate": pct(rates.get("event", 0.10)), "key": "event"},
            {"label": "Day Passes", "rate": pct(rates.get("day_pass", 0.10)), "key": "day_pass"},
            {
                "label": "Wallet Top-up — first time",
                "rate": pct(rates.get("credits_topup_first", 0.05)),
                "key": "credits_topup_first",
                "desc": "5% sign-up bonus when your referral funds their wallet for the first time.",
            },
            {
                "label": "Wallet Top-up — repeat",
                "rate": pct(rates.get("credits_topup", 0.01)),
                "key": "credits_topup",
                "desc": "1% on every top-up after the first.",
            },
            {
                "label": "Zen Store / Menu Spend",
                "rate": pct(rates.get("spend", 0.01)),
                "key": "spend",
                "desc": "1% of every Zen Credit your referral spends with us.",
            },
            {"label": "Coherent Inquiries", "rate": pct(rates.get("coherent_inquiry", 0.10)), "key": "coherent_inquiry"},
            {"label": "Support / Donations", "rate": pct(rates.get("support_donation", 0.10)), "key": "support_donation"},
        ],
        # MLM tier-2 override: when someone you signed up later refers others,
        # you earn this slice of their commissions automatically.
        "tier2": {
            "share": pct(rates.get("tier2_share", 0.10)),
            "label": "Sponsor override",
            "desc": "When a partner you signed up earns a commission, you receive 10% of it on top.",
        },
    }


# ---------------------------------------------------------------------------
# Invite-only application queue
# ---------------------------------------------------------------------------
# Public posts an application → lands in pending_applications.json with
# status="pending". Admin reviews via GET /applications and approves with
# POST /applications/{id}/approve (which creates the partner record using the
# existing logic, optionally setting founding_rate / standard_rate).

class PartnerApplicationRequest(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = ""
    relationship: Optional[str] = ""     # how they know Zen Village
    how_share: Optional[str] = ""        # where + how they plan to share
    audience_size: Optional[str] = ""    # rough audience size / context
    payout_method: Optional[str] = None  # credits | cash | both
    website: Optional[str] = ""          # honeypot — should stay empty
    referrer_code: Optional[str] = ""    # zv_ref cookie of whoever sent them


class ApplicationApproval(BaseModel):
    notes: Optional[str] = ""
    founding_rate: Optional[float] = None
    founding_sales_remaining: Optional[int] = None
    standard_rate: Optional[float] = 0.15  # default 15% — overridable


def _notify_admin_new_application(app_data: dict) -> None:
    """Best-effort Telegram notification on new application. Never raises."""
    try:
        from app.telegram_send import send_to_admins
        text = (
            "🌿 <b>New affiliate application — Zen Village</b>\n"
            f"<b>{app_data.get('name', '?')}</b> · {app_data.get('email', '?')}\n"
            f"Phone: {app_data.get('phone') or '—'}\n"
            f"How they know us: {app_data.get('relationship') or '—'}\n"
            f"Plans to share: {app_data.get('how_share') or '—'}\n"
            f"Audience: {app_data.get('audience_size') or '—'}\n"
            f"Referred by: {app_data.get('referrer_code') or 'direct'}\n"
            f"\nReview + approve: /admin/affiliates"
        )
        send_to_admins(text, parse_mode="HTML")
    except Exception as e:
        logger.warning("admin notify on new application failed: %s", e)


@router.post("/apply-request")
async def public_apply_request(request: Request, data: PartnerApplicationRequest):
    """Invite-only application: lands in pending queue for admin review.
    Returns immediately so the partner sees "got it, we'll review" without
    receiving a referral code yet — that comes when admin approves."""
    # Honeypot — bots fill any visible field
    if (data.website or "").strip():
        return {"status": "received"}

    ip = (request.client.host if request.client else "unknown") or "unknown"
    if not _apply_rate_ok(ip):
        raise HTTPException(429, "Too many applications from this network. Please try again later.")

    apps = _load(APPLICATIONS_FILE)
    if not isinstance(apps, dict):
        apps = {}

    email_lower = data.email.lower().strip()

    # Reject duplicate pending application by email (silently — same status returned)
    for aid, a in apps.items():
        if (a.get("email") or "").lower().strip() == email_lower and a.get("status") == "pending":
            return {"status": "received", "application_id": aid}

    # Reject if already an active partner (silently swallow — they probably forgot)
    partners = _load(PARTNERS_FILE)
    for code, p in partners.items():
        if (p.get("email") or "").lower().strip() == email_lower:
            return {"status": "already_partner", "code": code}

    app_id = f"app_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(3)}"
    record = {
        "id": app_id,
        "name": data.name.strip(),
        "email": email_lower,
        "phone": (data.phone or "").strip(),
        "relationship": (data.relationship or "").strip(),
        "how_share": (data.how_share or "").strip(),
        "audience_size": (data.audience_size or "").strip(),
        "payout_method": data.payout_method or "credits",
        "referrer_code": (data.referrer_code or "").upper().strip(),
        "ip": ip,
        "status": "pending",
        "submitted_at": datetime.utcnow().isoformat(),
        "reviewed_at": None,
        "reviewed_by": None,
        "partner_code": None,  # filled in on approval
    }
    apps[app_id] = record
    _save(APPLICATIONS_FILE, apps)

    _notify_admin_new_application(record)

    logger.info("affiliate application: id=%s email=%s ip=%s", app_id, email_lower, ip)
    return {"status": "received", "application_id": app_id}


@router.get("/applications", dependencies=[Depends(require_admin)])
async def list_applications(status: Optional[str] = "pending"):
    """List applications, default to pending only. status=all returns everything."""
    apps = _load(APPLICATIONS_FILE)
    if not isinstance(apps, dict):
        return {"applications": []}
    rows = list(apps.values())
    if status and status != "all":
        rows = [r for r in rows if (r.get("status") or "") == status]
    rows.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)
    return {"applications": rows, "count": len(rows)}


@router.post("/applications/{application_id}/approve", dependencies=[Depends(require_admin)])
async def approve_application(application_id: str, data: ApplicationApproval):
    """Approve a pending application: creates the partner record with the
    standard rate (default 15%) and optional founding-cohort rate boost.
    Idempotent: if application already approved, returns existing partner."""
    apps = _load(APPLICATIONS_FILE)
    if application_id not in apps:
        raise HTTPException(404, "Application not found")
    app_record = apps[application_id]
    if app_record.get("status") == "approved" and app_record.get("partner_code"):
        partners = _load(PARTNERS_FILE)
        existing_code = app_record["partner_code"]
        if existing_code in partners:
            return {"status": "already_approved", "partner_code": existing_code, "partner": partners[existing_code]}
    if app_record.get("status") == "declined":
        raise HTTPException(409, "Application was declined")

    cfg = _config()
    partners = _load(PARTNERS_FILE)

    # Build partner code
    code = _gen_code(app_record["name"])
    while code in partners:
        code = _gen_code(app_record["name"] + secrets.token_hex(2))

    notes_parts = []
    if app_record.get("relationship"): notes_parts.append(f"Relationship: {app_record['relationship']}")
    if app_record.get("how_share"): notes_parts.append(f"Plans to share: {app_record['how_share']}")
    if app_record.get("audience_size"): notes_parts.append(f"Audience: {app_record['audience_size']}")
    if app_record.get("referrer_code"): notes_parts.append(f"Referred by: {app_record['referrer_code']}")
    if data.notes: notes_parts.append(f"Admin: {data.notes}")
    notes_parts.append(f"Approved from application {application_id}")

    partner = {
        "code": code,
        "name": app_record["name"],
        "email": app_record["email"],
        "phone": app_record.get("phone", ""),
        "payout_method": app_record.get("payout_method") or cfg.get("default_payout_method", "credits"),
        "notes": " | ".join(notes_parts),
        "created_at": datetime.utcnow().isoformat(),
        "status": "active",
        "total_referrals": 0,
        "total_earned": 0,
        "pending_payout": 0,
        "is_producer": False,
        "approved_from_application": application_id,
    }
    # Per-partner rate overrides (founding ramp-down + standard rate)
    if data.founding_rate is not None:
        partner["founding_rate"] = float(data.founding_rate)
    if data.founding_sales_remaining is not None:
        partner["founding_sales_remaining"] = int(data.founding_sales_remaining)
    if data.standard_rate is not None:
        partner["standard_rate"] = float(data.standard_rate)
    partners[code] = partner
    _save(PARTNERS_FILE, partners)
    _sync_partner_to_nocodb(partner)

    # Mark application as approved
    app_record["status"] = "approved"
    app_record["reviewed_at"] = datetime.utcnow().isoformat()
    app_record["partner_code"] = code
    apps[application_id] = app_record
    _save(APPLICATIONS_FILE, apps)

    base = cfg.get("site_base_url", "https://zenvillagecr.com").rstrip("/")
    logger.info("application approved: app=%s → partner=%s email=%s", application_id, code, app_record["email"])
    return {
        "status": "approved",
        "partner_code": code,
        "partner": partner,
        "referral_link": f"{base}/reset?ref={code}",
        "qr_url": f"{base}/api/affiliates/qr/{code}",
    }


@router.post("/applications/{application_id}/decline", dependencies=[Depends(require_admin)])
async def decline_application(application_id: str, reason: Optional[str] = ""):
    apps = _load(APPLICATIONS_FILE)
    if application_id not in apps:
        raise HTTPException(404, "Application not found")
    app_record = apps[application_id]
    if app_record.get("status") in ("approved", "declined"):
        return {"status": f"already_{app_record['status']}", "application_id": application_id}
    app_record["status"] = "declined"
    app_record["reviewed_at"] = datetime.utcnow().isoformat()
    app_record["decline_reason"] = reason or ""
    apps[application_id] = app_record
    _save(APPLICATIONS_FILE, apps)
    return {"status": "declined", "application_id": application_id}


# ---------------------------------------------------------------------------
# Admin endpoints (token-gated)
# ---------------------------------------------------------------------------
@router.get("/config", dependencies=[Depends(require_admin)])
async def get_config():
    return _config()


@router.put("/config", dependencies=[Depends(require_admin)])
async def update_config(data: ConfigUpdate):
    cfg = _config()
    payload = data.model_dump(exclude_none=True)
    if "rates" in payload:
        # Merge instead of replace so admin can update one rate at a time
        cfg["rates"] = {**cfg.get("rates", {}), **payload.pop("rates")}
    cfg.update(payload)
    _save(CONFIG_FILE, cfg)
    return {"status": "ok", "config": cfg}


@router.get("/partners", dependencies=[Depends(require_admin)])
async def list_partners():
    partners = _load(PARTNERS_FILE)
    return {"partners": list(partners.values())}


@router.post("/partners", dependencies=[Depends(require_admin)])
async def create_partner(data: PartnerCreate):
    cfg = _config()
    partners = _load(PARTNERS_FILE)
    code = _gen_code(data.name)
    while code in partners:
        code = _gen_code(data.name + secrets.token_hex(2))
    partner = {
        "code": code,
        "name": data.name,
        "email": data.email,
        "phone": data.phone or "",
        "payout_method": data.payout_method or cfg.get("default_payout_method", "credits"),
        "notes": data.notes or "",
        "created_at": datetime.utcnow().isoformat(),
        "status": "active",
        "total_referrals": 0,
        "total_earned": 0,
        "pending_payout": 0,
        "is_producer": False,  # Admin-only flag, toggled via /partners/{code}/producer-mode
    }
    partners[code] = partner
    _save(PARTNERS_FILE, partners)
    _sync_partner_to_nocodb(partner)
    base = cfg.get("site_base_url", "https://zenvillagecr.com").rstrip("/")
    return {
        "status": "created",
        "partner": partner,
        "referral_link": f"{base}/?ref={code}",
    }


@router.patch("/partners/{code}", dependencies=[Depends(require_admin)])
async def update_partner(code: str, data: PartnerUpdate):
    code = code.upper().strip()
    partners = _load(PARTNERS_FILE)
    if code not in partners:
        raise HTTPException(404, "Partner not found")
    payload = data.model_dump(exclude_none=True)
    partners[code].update(payload)
    _save(PARTNERS_FILE, partners)
    _sync_partner_to_nocodb(partners[code])
    return {"status": "updated", "partner": partners[code]}


@router.get("/partners/{code}", dependencies=[Depends(require_admin)])
async def get_partner_admin(code: str):
    code = code.upper().strip()
    partners = _load(PARTNERS_FILE)
    commissions = _load(COMMISSIONS_FILE)
    if code not in partners:
        raise HTTPException(404, "Partner not found")
    partner_commissions = sorted(
        [c for c in commissions.values() if c.get("partner_code") == code],
        key=lambda x: x.get("timestamp", ""),
        reverse=True,
    )
    cfg = _config()
    base = cfg.get("site_base_url", "https://zenvillagecr.com").rstrip("/")
    return {
        "partner": partners[code],
        "recent_commissions": partner_commissions[:50],
        "referral_link": f"{base}/?ref={code}",
    }


@router.get("/commissions", dependencies=[Depends(require_admin)])
async def list_commissions(status: Optional[str] = None, partner_code: Optional[str] = None, limit: int = 200):
    commissions = _load(COMMISSIONS_FILE)
    rows = list(commissions.values())
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if partner_code:
        partner_code = partner_code.upper()
        rows = [r for r in rows if r.get("partner_code") == partner_code]
    rows.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"commissions": rows[:limit], "count": len(rows)}


@router.get("/stats", dependencies=[Depends(require_admin)])
async def get_stats():
    partners = _load(PARTNERS_FILE)
    commissions = _load(COMMISSIONS_FILE)
    referrals = _load(REFERRALS_FILE)
    paid = [c for c in commissions.values() if c.get("status") == "paid"]
    pending = [c for c in commissions.values() if c.get("status") == "pending"]
    return {
        "total_partners": len(partners),
        "active_partners": len([p for p in partners.values() if p.get("status") == "active"]),
        "total_visits": len(referrals),
        "total_conversions": len(commissions),
        "total_commission_paid": round(sum(c.get("commission_amount", 0) for c in paid), 2),
        "pending_payouts": round(sum(c.get("commission_amount", 0) for c in pending), 2),
        "total_booking_volume": round(sum(c.get("booking_amount", 0) for c in commissions.values()), 2),
    }


@router.post("/payout/{commission_id}", dependencies=[Depends(require_admin)])
async def mark_paid(commission_id: str):
    commissions = _load(COMMISSIONS_FILE)
    partners = _load(PARTNERS_FILE)
    if commission_id not in commissions:
        raise HTTPException(404, "Commission not found")
    c = commissions[commission_id]
    if c.get("status") == "paid":
        return {"status": "already_paid", "commission_id": commission_id}
    if c.get("status") == "reversed":
        raise HTTPException(409, "Cannot pay a reversed commission")
    c["status"] = "paid"
    c["paid_at"] = datetime.utcnow().isoformat()
    _save(COMMISSIONS_FILE, commissions)
    code = c.get("partner_code")
    if code in partners:
        partners[code]["pending_payout"] = max(
            0, round(float(partners[code].get("pending_payout", 0)) - float(c.get("commission_amount", 0)), 2)
        )
        _save(PARTNERS_FILE, partners)
        _sync_partner_to_nocodb(partners[code])
    _sync_commission_to_nocodb(c)
    return {"status": "paid", "commission_id": commission_id}


@router.post("/partners/{code}/producer-mode", dependencies=[Depends(require_admin)])
async def set_producer_mode(code: str, enabled: bool):
    """Admin-only toggle for producer status. Producer-flagged partners earn
    a higher single-rate commission (35% default) instead of the standard
    sourcer+closer stack. Cannot be self-set; requires explicit admin action.
    """
    code = code.upper().strip()
    partners = _load(PARTNERS_FILE)
    if code not in partners:
        raise HTTPException(404, "Partner not found")
    partners[code]["is_producer"] = bool(enabled)
    partners[code]["producer_set_at"] = datetime.utcnow().isoformat()
    _save(PARTNERS_FILE, partners)
    _sync_partner_to_nocodb(partners[code])
    logger.info("admin set producer_mode=%s on partner=%s", enabled, code)
    return {"status": "updated", "partner_code": code, "is_producer": bool(enabled)}


class CloserAssignment(BaseModel):
    closer_partner_code: str
    note: Optional[str] = ""


@router.post("/conversions/{conversion_group_id}/assign-closer", dependencies=[Depends(require_admin)])
async def assign_closer(conversion_group_id: str, data: CloserAssignment):
    """Retroactively attach a closer slice to an existing conversion group.
    Use after a sales call: 'this paid booking was actually closed by John'
    -> creates a new closer commission record under the same group_id.
    Idempotent: re-running with the same closer is a no-op.
    """
    cfg = _config()
    partners = _load(PARTNERS_FILE)
    commissions = _load(COMMISSIONS_FILE)

    closer_code = (data.closer_partner_code or "").upper().strip()
    if not closer_code:
        raise HTTPException(400, "closer_partner_code required")
    if closer_code not in partners:
        raise HTTPException(404, f"Closer partner not found: {closer_code}")
    if (partners[closer_code].get("status") or "active") != "active":
        raise HTTPException(409, f"Closer partner not active: {closer_code}")

    group = [c for c in commissions.values() if c.get("conversion_group_id") == conversion_group_id]
    if not group:
        # Fall back to id-match (for very old records before grouping existed)
        group = [c for c in commissions.values() if c.get("id") == conversion_group_id]
        if not group:
            raise HTTPException(404, "Conversion group not found")

    # Idempotency: don't double-create a closer slice for the same partner
    for existing in group:
        if existing.get("role") == "closer" and existing.get("partner_code") == closer_code:
            return {
                "status": "duplicate",
                "commission_id": existing.get("id"),
                "commission_amount": existing.get("commission_amount"),
            }

    seed = group[0]
    booking_amount = float(seed.get("booking_amount", 0))
    booking_type = seed.get("booking_type", "default")
    closer_rate = _rate("closer", cfg)
    amount = round(booking_amount * closer_rate, 2)

    commission_id = f"com_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(3)}"
    record = {
        "id": commission_id,
        "conversion_group_id": seed.get("conversion_group_id") or conversion_group_id,
        "partner_code": closer_code,
        "role": "closer",
        "rate_applied": closer_rate,
        "booking_type": booking_type,
        "booking_amount": booking_amount,
        "commission_amount": amount,
        "guest_email": seed.get("guest_email", ""),
        "booking_details": (seed.get("booking_details", "") or "") + (
            f" | closer assigned by admin: {data.note}" if data.note else " | closer assigned by admin"
        ),
        "source_id": seed.get("source_id", ""),
        "timestamp": datetime.utcnow().isoformat(),
        "status": "pending",
        "paid_at": None,
        "assigned_by_admin": True,
    }
    commissions[commission_id] = record
    _save(COMMISSIONS_FILE, commissions)

    p = partners[closer_code]
    p["total_earned"] = round(float(p.get("total_earned", 0)) + amount, 2)
    p["pending_payout"] = round(float(p.get("pending_payout", 0)) + amount, 2)
    _save(PARTNERS_FILE, partners)
    _sync_commission_to_nocodb(record)
    _sync_partner_to_nocodb(p)

    logger.info("closer assigned: group=%s closer=%s amount=%s",
                conversion_group_id, closer_code, amount)
    return {"status": "assigned", "commission_id": commission_id,
            "commission_amount": amount, "rate_applied": closer_rate}


@router.delete("/commissions/{commission_id}", dependencies=[Depends(require_admin)])
async def reverse_commission(commission_id: str, reason: str = ""):
    """Reverse a commission record (e.g. mis-assigned closer). Marks it
    'reversed' rather than deleting, so the audit trail survives. Updates
    partner totals."""
    commissions = _load(COMMISSIONS_FILE)
    partners = _load(PARTNERS_FILE)
    if commission_id not in commissions:
        raise HTTPException(404, "Commission not found")
    c = commissions[commission_id]
    if c.get("status") == "reversed":
        return {"status": "already_reversed", "commission_id": commission_id}
    if c.get("status") == "paid":
        raise HTTPException(409, "Cannot reverse a commission that has already been paid out")

    c["status"] = "reversed"
    c["reversed_at"] = datetime.utcnow().isoformat()
    c["reversal_reason"] = reason or ""
    _save(COMMISSIONS_FILE, commissions)

    code = c.get("partner_code")
    if code in partners:
        amt = float(c.get("commission_amount", 0))
        partners[code]["total_earned"] = max(0, round(float(partners[code].get("total_earned", 0)) - amt, 2))
        partners[code]["pending_payout"] = max(0, round(float(partners[code].get("pending_payout", 0)) - amt, 2))
        if c.get("role") in ("sourcer", "producer"):
            partners[code]["total_referrals"] = max(0, int(partners[code].get("total_referrals", 0)) - 1)
        _save(PARTNERS_FILE, partners)
        _sync_partner_to_nocodb(partners[code])
    _sync_commission_to_nocodb(c)
    return {"status": "reversed", "commission_id": commission_id}


@router.post("/payout/bulk", dependencies=[Depends(require_admin)])
async def bulk_payout(partner_code: str):
    """Mark all pending commissions for a partner as paid."""
    partner_code = partner_code.upper().strip()
    commissions = _load(COMMISSIONS_FILE)
    partners = _load(PARTNERS_FILE)
    if partner_code not in partners:
        raise HTTPException(404, "Partner not found")
    paid_ids = []
    total = 0.0
    for cid, c in commissions.items():
        if c.get("partner_code") == partner_code and c.get("status") == "pending":
            c["status"] = "paid"
            c["paid_at"] = datetime.utcnow().isoformat()
            paid_ids.append(cid)
            total += float(c.get("commission_amount", 0))
            _sync_commission_to_nocodb(c)
    _save(COMMISSIONS_FILE, commissions)
    partners[partner_code]["pending_payout"] = 0
    _save(PARTNERS_FILE, partners)
    _sync_partner_to_nocodb(partners[partner_code])
    return {"status": "ok", "paid_count": len(paid_ids), "total_paid": round(total, 2)}


# ---------------------------------------------------------------------------
# Internal helpers exposed for hooks in main_lite / zen_pass
# ---------------------------------------------------------------------------
def try_convert(
    partner_code: Optional[str],
    booking_type: str,
    booking_amount: float,
    guest_email: str = "",
    source_id: str = "",
    booking_details: str = "",
    closer_partner_code: Optional[str] = "",
) -> Optional[dict]:
    """Best-effort conversion fired from external hooks (booking webhook,
    Stripe completed, pass payment, etc.). Safe to call from any handler —
    never raises.

    `partner_code` is the SOURCER (typically from the ?ref cookie / pass
    record). `closer_partner_code` is optional and usually filled later by
    admin via the closer-assignment endpoint.
    """
    sourcer = (partner_code or "").upper().strip()
    closer = (closer_partner_code or "").upper().strip()
    if sourcer in {"", "DIRECT", "NONE", "NULL"}:
        sourcer = ""
    if closer in {"", "DIRECT", "NONE", "NULL"}:
        closer = ""
    if not (sourcer or closer):
        return None
    try:
        result = _apply_conversion(
            booking_type=booking_type,
            booking_amount=float(booking_amount),
            sourcer_code=sourcer,
            closer_code=closer,
            guest_email=guest_email or "",
            booking_details=booking_details or "",
            source_id=source_id or "",
        )
        return result if result.get("status") in ("converted", "duplicate") else None
    except Exception as e:
        logger.warning("affiliates try_convert failed: %s", e)
        return None
