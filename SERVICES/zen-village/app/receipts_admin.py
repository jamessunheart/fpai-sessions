"""
Zen Village — Admin Receipts Browser

Reads the accounting JSONL files written by the Telegram bot at
/opt/zen-village/accounting-intake/<YYYY-MM>/intake.jsonl and serves the
photos/docs from the same directory. Used by the password-gated
accounting.zenvillagecr.com subdomain so admins can verify what the bot
captured without SSH'ing into the box.

Auth model
----------
API endpoints require X-Admin-Token (env var ZV_ADMIN_TOKEN, falls back to
ZV_AFFILIATES_ADMIN_TOKEN for repos where that's already configured). In
production these routes sit behind nginx basic-auth on the accounting
subdomain, and nginx injects the token after the basic-auth handshake —
single password for the user, double-gate for the API.

Boundary preserved
------------------
Raw receipts stay in /opt/zen-village/accounting-intake (root-only on disk).
This module never copies them anywhere. AppFlowy / NocoDB still see only
sanitized summaries the user chooses to promote.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import mimetypes
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

from fastapi import APIRouter, Body, Header, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

logger = logging.getLogger("zen_village.receipts_admin")

ACCOUNTING_ROOT = Path(
    os.environ.get("ZV_ACCOUNTING_ROOT", "/opt/zen-village/accounting-intake")
)


# ─── auth ───────────────────────────────────────────────────────────────────
# Admin role names (case-insensitive). Anyone whose nginx basic-auth username
# is in this set sees ALL receipts; anyone else sees only their own.
ADMIN_USERS = {
    u.strip().lower() for u in
    os.environ.get("ZV_ADMIN_USERS", "admin,sunheart").split(",")
    if u.strip()
}


def _admin_token() -> str:
    return (
        os.environ.get("ZV_ADMIN_TOKEN")
        or os.environ.get("ZV_AFFILIATES_ADMIN_TOKEN")
        or ""
    )


def _require_admin(x_admin_token: Optional[str]) -> None:
    expected = _admin_token()
    if not expected:
        raise HTTPException(503, "Admin token not configured (set ZV_ADMIN_TOKEN)")
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(401, "Invalid admin token")


def _resolve_user(x_forwarded_user: Optional[str]) -> tuple[str, bool]:
    """Return (username, is_admin) based on the nginx-injected header.

    No header → treated as an admin context (direct internal call). In
    production nginx ALWAYS sets this header, so absence means a trusted
    invocation (e.g. localhost smoke test, internal script).
    """
    raw = (x_forwarded_user or "").strip()
    if not raw:
        return ("admin", True)
    return (raw, raw.lower() in ADMIN_USERS)


def _enforce_user_scope(row: dict, user: str, is_admin: bool) -> None:
    """Raise 403 if a non-admin tries to act on someone else's receipt."""
    if is_admin:
        return
    owner = (row.get("username") or row.get("user_name") or "").strip().lower()
    if owner != user.strip().lower():
        raise HTTPException(403, "You can only access your own receipts")


# ─── jsonl iteration ────────────────────────────────────────────────────────
def _month_dirs() -> list[Path]:
    if not ACCOUNTING_ROOT.exists():
        return []
    return sorted(
        (p for p in ACCOUNTING_ROOT.glob("20??-??") if p.is_dir()),
        reverse=True,
    )


def _load_jsonl_by_id(path: Path) -> dict[str, dict]:
    """Load a JSONL sidecar keyed by `id`. Returns empty if file absent."""
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            rid = d.get("id")
            if rid:
                out[str(rid)] = d
    except Exception as e:
        logger.warning("could not read %s: %s", path, e)
    return out


def _load_parsed_sidecar(month_dir: Path) -> dict[str, dict]:
    """parsed.jsonl: machine extraction (caption / OCR / LLM) keyed by id."""
    return _load_jsonl_by_id(month_dir / "parsed.jsonl")


def _load_edits_sidecar(month_dir: Path) -> dict[str, dict]:
    """edits.jsonl: human overrides keyed by id. Latest line per id wins."""
    p = month_dir / "edits.jsonl"
    if not p.exists():
        return {}
    out: dict[str, dict] = {}
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            rid = d.get("id")
            if rid:
                # Keep merging — later lines override earlier ones.
                prev = out.get(rid, {})
                merged = {**prev, **d}
                if "fields" in d:
                    merged["fields"] = {**prev.get("fields", {}), **d["fields"]}
                out[rid] = merged
    except Exception as e:
        logger.warning("could not read %s: %s", p, e)
    return out


def _append_edit(month_dir: Path, edit_record: dict) -> None:
    """Append a single edit row to edits.jsonl atomically."""
    p = month_dir / "edits.jsonl"
    line = json.dumps(edit_record, ensure_ascii=False) + "\n"
    with p.open("a", encoding="utf-8") as fp:
        fp.write(line)
    try:
        os.chmod(p, 0o600)
    except Exception:
        pass


def _iter_entries(months: Optional[set[str]] = None) -> Iterable[dict]:
    """Yield receipt rows newest-first across all (or a subset of) months.

    Sidecar parsed.jsonl values are merged into each row under
    `_parsed` so downstream code can prefer LLM-extracted data.
    """
    for md in _month_dirs():
        if months and md.name not in months:
            continue
        f = md / "intake.jsonl"
        if not f.exists():
            continue
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            logger.warning("could not read %s: %s", f, e)
            continue
        parsed = _load_parsed_sidecar(md)
        edits = _load_edits_sidecar(md)
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            # Match against the same id the normaliser will compute below.
            from hashlib import sha1
            rid = row.get("id")
            if not rid:
                seed = f"{row.get('ts') or row.get('timestamp') or ''}|{row.get('filename') or row.get('file_name') or ''}|{row.get('telegram_user_id') or row.get('user_id') or ''}"
                rid = "rcpt_" + sha1(seed.encode("utf-8")).hexdigest()[:16]
            row["_parsed"] = parsed.get(str(rid), {})
            row["_edit"] = edits.get(str(rid), {})
            row["_month_dir"] = str(md)
            yield row


def _to_date(v: str) -> Optional[date]:
    s = (v or "").strip()
    if len(s) >= 10:
        s = s[:10]
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


# ─── schema normalisation ───────────────────────────────────────────────────
# The deployed Zen Village bot writes JSONL with these fields:
#   ts, username, telegram_user_id, intake_kind, kind, caption,
#   filename, stored_file, extracted_text, paperless_task_id, paperless_error
# An older / alternate variant uses:
#   timestamp, user_name, user_id, note, file_name, file_path, id
# We normalise to a single shape so the rest of the code (and the UI) doesn't
# have to know which writer produced the row.

_PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".bmp"}


def _normalise(raw: dict) -> dict:
    ts = raw.get("ts") or raw.get("timestamp") or ""
    username = raw.get("username") or raw.get("user_name") or ""
    user_name_disp = raw.get("user_name") or raw.get("username") or ""
    user_id = str(raw.get("telegram_user_id") or raw.get("user_id") or "")
    note = raw.get("caption") or raw.get("note") or ""
    extracted = raw.get("extracted_text") or ""
    file_name = raw.get("filename") or raw.get("file_name") or ""
    file_path = raw.get("stored_file") or raw.get("file_path") or ""
    intake_kind = (raw.get("intake_kind") or "").lower()
    raw_kind = (raw.get("kind") or "").lower()

    # Derive a stable id we can use to address one receipt:
    rid = raw.get("id")
    if not rid:
        # Use ts + filename hash-ish fallback. Keep it URL-safe.
        from hashlib import sha1
        seed = f"{ts}|{file_name}|{user_id}"
        rid = "rcpt_" + sha1(seed.encode("utf-8")).hexdigest()[:16]

    # Display kind: "photo", "document", or "text"
    if file_path:
        ext = ""
        try:
            ext = Path(file_path).suffix.lower()
        except Exception:
            pass
        if ext in _PHOTO_EXT or raw_kind == "photo":
            disp_kind = "photo"
        else:
            disp_kind = "document"
    else:
        disp_kind = "text"

    return {
        "id": str(rid),
        "timestamp": ts,
        "username": username,
        "user_name": user_name_disp or username or "",
        "user_id": user_id,
        "note": note,
        "extracted_text": extracted,
        "intake_kind": intake_kind,
        "kind": disp_kind,
        "file_name": file_name,
        "file_path": file_path,
        "paperless_task_id": raw.get("paperless_task_id") or "",
        "paperless_error": raw.get("paperless_error") or "",
    }


# ─── parsing helpers (mirror bot.py) ────────────────────────────────────────
def _parse_number_token(t: str) -> Optional[float]:
    t = (t or "").strip().replace(" ", "")
    if not t:
        return None
    sign = -1 if t.startswith("-") else 1
    t = t.lstrip("+-")
    if not t:
        return None
    if "," in t and "." in t:
        if t.rfind(".") > t.rfind(","):
            t = t.replace(",", "")
        else:
            t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        parts = t.split(",")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            t = "".join(parts)
        else:
            t = t.replace(",", ".")
    try:
        return sign * float(t)
    except Exception:
        return None


def _extract_amount(text: str) -> Optional[float]:
    s = text or ""
    m = re.search(r"(?:\$|₡|usd|crc|colones?)\s*(-?\d[\d.,]*)", s, re.I)
    if m:
        v = _parse_number_token(m.group(1))
        if v is not None:
            return abs(v)
    m = re.search(r"(-?\d[\d.,]*)", s)
    if m:
        v = _parse_number_token(m.group(1))
        if v is not None:
            return abs(v)
    return None


def _detect_currency(text: str) -> str:
    s = (text or "").lower()
    if "₡" in s or "crc" in s or "colon" in s:
        return "CRC"
    if "$" in s or "usd" in s or "dollar" in s:
        return "USD"
    return "UNK"


def _detect_flow(text: str) -> str:
    s = (text or "").lower()
    out_words = ("paid", "spent", "expense", "cost", "purchase", "bought",
                 "vendor", "reimburse", "withdraw", "outflow", "bill", "invoice")
    in_words = ("received", "income", "sale", "sold", "deposit", "payment from",
                "wire in", "credit", "refund", "inflow")
    out_hit = any(w in s for w in out_words)
    in_hit = any(w in s for w in in_words)
    if out_hit and not in_hit:
        return "out"
    if in_hit and not out_hit:
        return "in"
    return "unknown"


# ─── enrichment ─────────────────────────────────────────────────────────────
def _enrich(raw: dict) -> dict:
    row = _normalise(raw)
    parsed = raw.get("_parsed") or {}
    edit = raw.get("_edit") or {}
    edit_fields = edit.get("fields") or {}

    # Layer 1: machine extraction (parsed.jsonl)
    text_for_amount = row["note"] or row["extracted_text"] or ""
    if parsed.get("amount") is not None:
        amount = parsed["amount"]
        currency = parsed.get("currency") or "UNK"
        method = parsed.get("method") or "sidecar"
        confidence = parsed.get("confidence", 0.0)
        vendor = parsed.get("vendor")
        parsed_date = parsed.get("date")
    else:
        amount = _extract_amount(text_for_amount)
        currency = _detect_currency(text_for_amount) if amount is not None else None
        method = "regex_fallback" if amount is not None else "none"
        confidence = 0.4 if amount is not None else 0.0
        vendor = None
        parsed_date = None

    # Layer 2: human edits (edits.jsonl) — always win.
    edited_amount = edit_fields.get("amount")
    if edited_amount is not None:
        try:
            amount = float(edited_amount)
            method = "human"
            confidence = 1.0
        except (TypeError, ValueError):
            pass
    if "currency" in edit_fields and edit_fields["currency"]:
        currency = edit_fields["currency"]
    if "vendor" in edit_fields:
        vendor = edit_fields["vendor"] or vendor
    if "note" in edit_fields:
        row["note"] = edit_fields["note"] or row["note"]
    if "intake_kind" in edit_fields and edit_fields["intake_kind"]:
        row["intake_kind"] = edit_fields["intake_kind"]
    if "date" in edit_fields:
        parsed_date = edit_fields["date"] or parsed_date
    is_hidden = bool(edit_fields.get("hidden")) or bool(edit.get("hidden"))

    return {
        **row,
        "amount": amount,
        "currency": currency,
        "flow": _detect_flow(text_for_amount),
        "has_file": bool(row.get("file_path")),
        "vendor": vendor,
        "parsed_date": parsed_date,
        "parse_method": method,
        "parse_confidence": confidence,
        "is_hidden": is_hidden,
        "edited_by": edit.get("edited_by"),
        "edited_at": edit.get("edited_at"),
    }


# ─── filtering ──────────────────────────────────────────────────────────────
def _matches(
    row: dict,
    *,
    start: Optional[date],
    end: Optional[date],
    who: str,
    q: str,
    has_photo: Optional[bool],
    has_amount: Optional[bool],
) -> bool:
    d = _to_date(str(row.get("timestamp") or ""))
    if start and (not d or d < start):
        return False
    if end and (not d or d > end):
        return False
    if who:
        hay = " ".join([
            str(row.get("user_name") or ""),
            str(row.get("username") or ""),
            str(row.get("user_id") or ""),
        ]).lower()
        if who.lower() not in hay:
            return False
    if q:
        hay = " ".join([
            str(row.get("id") or ""),
            str(row.get("user_name") or ""),
            str(row.get("username") or ""),
            str(row.get("note") or ""),
            str(row.get("extracted_text") or ""),
            str(row.get("file_name") or ""),
            str(row.get("intake_kind") or ""),
        ]).lower()
        if q.lower() not in hay:
            return False
    if has_photo is True and (row.get("kind") != "photo"):
        return False
    if has_photo is False and (row.get("kind") == "photo"):
        return False
    if has_amount is True and row.get("amount") is None:
        return False
    if has_amount is False and row.get("amount") is not None:
        return False
    return True


# ─── totals ─────────────────────────────────────────────────────────────────
def _totals(rows: list[dict]) -> dict:
    by_cur: dict[str, dict[str, float]] = {
        "USD": {"in": 0.0, "out": 0.0, "unknown": 0.0},
        "CRC": {"in": 0.0, "out": 0.0, "unknown": 0.0},
        "UNK": {"in": 0.0, "out": 0.0, "unknown": 0.0},
    }
    parsed = 0
    photo_count = 0
    for r in rows:
        if r.get("kind") == "photo":
            photo_count += 1
        amt = r.get("amount")
        if amt is None:
            continue
        parsed += 1
        cur = r.get("currency") or "UNK"
        flow = r.get("flow") or "unknown"
        if cur not in by_cur:
            by_cur[cur] = {"in": 0.0, "out": 0.0, "unknown": 0.0}
        by_cur[cur][flow] = round(by_cur[cur][flow] + float(amt), 2)
    return {
        "count": len(rows),
        "parsed_count": parsed,
        "photo_count": photo_count,
        "by_currency": {k: v for k, v in by_cur.items() if any(v.values())},
    }


# ─── router ─────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/admin/receipts")


def _months_param(months: Optional[str]) -> Optional[set[str]]:
    if not months:
        return None
    out = set()
    for tok in months.split(","):
        tok = tok.strip()
        if re.match(r"^\d{4}-\d{2}$", tok):
            out.add(tok)
    return out or None


def _gather(
    *,
    months: Optional[str],
    start_iso: Optional[str],
    end_iso: Optional[str],
    who: str,
    q: str,
    has_photo: Optional[bool],
    has_amount: Optional[bool],
    limit: int,
    include_hidden: bool = False,
) -> list[dict]:
    start = date.fromisoformat(start_iso) if start_iso else None
    end = date.fromisoformat(end_iso) if end_iso else None
    month_set = _months_param(months)
    out: list[dict] = []
    for raw in _iter_entries(month_set):
        row = _enrich(raw)
        if row.get("is_hidden") and not include_hidden:
            continue
        if not _matches(
            row, start=start, end=end, who=who, q=q,
            has_photo=has_photo, has_amount=has_amount,
        ):
            continue
        out.append(row)
        if len(out) >= max(1, min(limit, 5000)):
            break
    return out


@router.get("")
@router.get("/")
async def list_receipts(
    months: Optional[str] = Query(None, description="comma-separated YYYY-MM list"),
    start: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    who: str = Query("", description="filter by user name / username / id"),
    q: str = Query("", description="free-text match across note/id/file"),
    has_photo: Optional[bool] = Query(None),
    has_amount: Optional[bool] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    show_hidden: bool = Query(False),
    x_admin_token: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
):
    _require_admin(x_admin_token)
    user, is_admin = _resolve_user(x_forwarded_user)
    # Non-admins only ever see their own receipts; ignore any client-side `who`.
    if not is_admin:
        who = user
    rows = _gather(
        months=months, start_iso=start, end_iso=end, who=who, q=q,
        has_photo=has_photo, has_amount=has_amount, limit=limit,
        include_hidden=is_admin and show_hidden,
    )
    return {
        "rows": rows,
        "totals": _totals(rows),
        "available_months": [p.name for p in _month_dirs()],
        "accounting_root_exists": ACCOUNTING_ROOT.exists(),
        "fetched_at": datetime.utcnow().isoformat(),
        "viewer": {"user": user, "is_admin": is_admin},
    }


@router.get("/file/{rid}")
async def get_receipt_file(
    rid: str,
    x_admin_token: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
):
    _require_admin(x_admin_token)
    user, is_admin = _resolve_user(x_forwarded_user)
    if not re.match(r"^(acct|rcpt)_[A-Za-z0-9_]+$", rid):
        raise HTTPException(400, "Invalid receipt id")
    for raw in _iter_entries():
        norm = _normalise(raw)
        if norm["id"] != rid:
            continue
        _enforce_user_scope(norm, user, is_admin)
        path_str = norm["file_path"]
        if not path_str:
            raise HTTPException(404, "Receipt has no attached file")
        p = Path(path_str).resolve()
        try:
            p.relative_to(ACCOUNTING_ROOT.resolve())
        except ValueError:
            raise HTTPException(403, "File outside accounting vault")
        if not p.exists():
            raise HTTPException(404, "File missing on disk")
        media_type = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        return FileResponse(
            str(p),
            media_type=media_type,
            filename=p.name,
            headers={"Content-Disposition": f'inline; filename="{p.name}"'},
        )
    raise HTTPException(404, "Receipt id not found")


@router.get("/csv")
async def export_csv(
    months: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    who: str = Query(""),
    q: str = Query(""),
    has_photo: Optional[bool] = Query(None),
    has_amount: Optional[bool] = Query(None),
    limit: int = Query(5000, ge=1, le=5000),
    x_admin_token: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
):
    _require_admin(x_admin_token)
    user, is_admin = _resolve_user(x_forwarded_user)
    if not is_admin:
        who = user
    rows = _gather(
        months=months, start_iso=start, end_iso=end, who=who, q=q,
        has_photo=has_photo, has_amount=has_amount, limit=limit,
    )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "id", "timestamp", "user_name", "username", "user_id",
        "intake_kind", "kind", "note", "amount", "currency", "flow",
        "file_name", "file_path", "extracted_text",
    ])
    for r in rows:
        w.writerow([
            r.get("id", ""),
            r.get("timestamp", ""),
            r.get("user_name", ""),
            r.get("username", ""),
            r.get("user_id", ""),
            r.get("intake_kind", ""),
            r.get("kind", ""),
            (r.get("note") or "").replace("\n", " ").strip(),
            r.get("amount") if r.get("amount") is not None else "",
            r.get("currency") or "",
            r.get("flow") or "",
            r.get("file_name", ""),
            r.get("file_path", ""),
            (r.get("extracted_text") or "").replace("\n", " ").strip(),
        ])
    buf.seek(0)
    fname = f"zen-village-receipts-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/_meta")
async def meta(x_admin_token: Optional[str] = Header(default=None)):
    """Lightweight probe — useful for the page to verify auth before loading."""
    _require_admin(x_admin_token)
    return {
        "ok": True,
        "accounting_root": str(ACCOUNTING_ROOT),
        "accounting_root_exists": ACCOUNTING_ROOT.exists(),
        "available_months": [p.name for p in _month_dirs()],
    }


@router.post("/reparse/{rid}")
async def reparse_one(
    rid: str,
    x_admin_token: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
):
    """Re-run the receipt parser (caption → OCR keyword → LLM) on a single
    receipt and persist the new result to that month's parsed.jsonl.
    """
    _require_admin(x_admin_token)
    user, is_admin = _resolve_user(x_forwarded_user)
    if not re.match(r"^(acct|rcpt)_[A-Za-z0-9_]+$", rid):
        raise HTTPException(400, "Invalid receipt id")

    # Find the row + which month dir owns it.
    found_row: Optional[dict] = None
    found_month: Optional[Path] = None
    for md in _month_dirs():
        f = md / "intake.jsonl"
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            norm = _normalise(row)
            if norm["id"] == rid:
                _enforce_user_scope(norm, user, is_admin)
                found_row = row
                found_month = md
                break
        if found_row:
            break

    if not found_row or not found_month:
        raise HTTPException(404, "Receipt not found")

    # Lazy import so the API doesn't fail to start if Ollama isn't reachable.
    try:
        from parse_receipt_amount import parse_one as _parse_one
    except ImportError:
        try:
            from app.parse_receipt_amount import parse_one as _parse_one
        except ImportError as e:
            raise HTTPException(503, f"Parser module unavailable: {e}")

    caption = str(found_row.get("caption") or found_row.get("note") or "")
    ocr = str(found_row.get("extracted_text") or "")
    result = _parse_one(caption=caption, ocr_text=ocr, use_llm=True)

    d = result.to_dict()
    d["id"] = rid
    d["parsed_at"] = datetime.utcnow().isoformat() + "Z"
    if d.get("method") != "llm":
        d.pop("raw_response", None)

    # Merge into parsed.jsonl atomically.
    parsed_path = found_month / "parsed.jsonl"
    existing: dict[str, dict] = {}
    if parsed_path.exists():
        for line in parsed_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if e.get("id"):
                    existing[e["id"]] = e
            except Exception:
                continue
    existing[rid] = d

    tmp = parsed_path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as fp:
        for k in sorted(existing.keys()):
            fp.write(json.dumps(existing[k], ensure_ascii=False) + "\n")
    tmp.replace(parsed_path)
    try:
        os.chmod(parsed_path, 0o600)
    except Exception:
        pass

    return {"ok": True, "id": rid, "parsed": d}


# ─── Manual edits — Halley's correction loop ────────────────────────────────
_EDITABLE_FIELDS = {
    "amount", "currency", "vendor", "note", "intake_kind", "date", "hidden",
}
_VALID_CURRENCIES = {"USD", "CRC", "UNK"}
_VALID_INTAKE_KINDS = {"receipt", "proforma", "note", "expense", "income"}


@router.post("/edit/{rid}")
async def edit_receipt(
    rid: str,
    payload: dict = Body(...),
    x_admin_token: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
):
    """Append a human override to edits.jsonl for the given receipt id.

    Body shape:
      {
        "amount": <number|null>,
        "currency": "USD"|"CRC"|"UNK",
        "vendor": "string",
        "note": "string",
        "intake_kind": "receipt"|"proforma"|"note"|"expense"|"income",
        "date": "YYYY-MM-DD",
        "hidden": true|false,        # soft-delete (admin only)
        "comment": "free-text reason for the edit"
      }
    Only fields the caller wants to change need to be present. Empty strings
    clear a field. Hidden=true is admin-only.
    """
    _require_admin(x_admin_token)
    user, is_admin = _resolve_user(x_forwarded_user)
    if not re.match(r"^(acct|rcpt)_[A-Za-z0-9_]+$", rid):
        raise HTTPException(400, "Invalid receipt id")

    if not isinstance(payload, dict):
        raise HTTPException(400, "Body must be a JSON object")

    # Locate the row's owning month + verify ownership for non-admins.
    found_row: Optional[dict] = None
    found_month: Optional[Path] = None
    for md in _month_dirs():
        f = md / "intake.jsonl"
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            norm = _normalise(row)
            if norm["id"] == rid:
                _enforce_user_scope(norm, user, is_admin)
                found_row = row
                found_month = md
                break
        if found_row:
            break
    if not found_row or not found_month:
        raise HTTPException(404, "Receipt not found")

    # Validate + sanitize incoming fields
    fields: dict = {}
    for k in _EDITABLE_FIELDS:
        if k not in payload:
            continue
        v = payload[k]
        if k == "amount":
            if v in (None, "", "null"):
                fields["amount"] = None
            else:
                try:
                    fields["amount"] = float(v)
                except (TypeError, ValueError):
                    raise HTTPException(400, f"amount must be a number, got {v!r}")
        elif k == "currency":
            cur = (str(v or "")).upper().strip() or None
            if cur and cur not in _VALID_CURRENCIES:
                raise HTTPException(400, f"currency must be one of {sorted(_VALID_CURRENCIES)}")
            fields["currency"] = cur
        elif k == "intake_kind":
            ik = (str(v or "")).lower().strip() or None
            if ik and ik not in _VALID_INTAKE_KINDS:
                raise HTTPException(400, f"intake_kind must be one of {sorted(_VALID_INTAKE_KINDS)}")
            fields["intake_kind"] = ik
        elif k == "date":
            ds = (str(v or "")).strip() or None
            if ds and not re.match(r"^\d{4}-\d{2}-\d{2}$", ds):
                raise HTTPException(400, "date must be YYYY-MM-DD")
            fields["date"] = ds
        elif k == "hidden":
            if not is_admin and v:
                raise HTTPException(403, "Only admins can hide receipts")
            fields["hidden"] = bool(v)
        elif k in ("vendor", "note"):
            fields[k] = str(v or "")[:1000]

    if not fields:
        raise HTTPException(400, "No editable fields supplied")

    edit_record = {
        "id": rid,
        "edited_by": user,
        "edited_at": datetime.utcnow().isoformat() + "Z",
        "fields": fields,
        "comment": str(payload.get("comment") or "")[:500],
    }
    _append_edit(found_month, edit_record)

    # Re-enrich + return the new view of the row so the UI can update in place.
    found_row["_parsed"] = _load_parsed_sidecar(found_month).get(rid, {})
    found_row["_edit"] = _load_edits_sidecar(found_month).get(rid, {})
    enriched = _enrich(found_row)
    return {"ok": True, "id": rid, "edit": edit_record, "row": enriched}


@router.get("/edit/{rid}/history")
async def edit_history(
    rid: str,
    x_admin_token: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
):
    """Return the full edit history for one receipt."""
    _require_admin(x_admin_token)
    user, is_admin = _resolve_user(x_forwarded_user)
    if not re.match(r"^(acct|rcpt)_[A-Za-z0-9_]+$", rid):
        raise HTTPException(400, "Invalid receipt id")
    history: list[dict] = []
    for md in _month_dirs():
        p = md / "edits.jsonl"
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("id") != rid:
                continue
            # Non-admins only see their own history.
            if not is_admin and (d.get("edited_by") or "").strip().lower() != user.strip().lower():
                continue
            history.append(d)
    return {"id": rid, "history": history, "count": len(history)}
