"""
Auto-parse new accounting intakes and reply to the submitter on Telegram
with the AI's best guess + a deep-link to fix it in the browser.

Wires into bot.py at the point where `_save_accounting_record(record)` is
called. The hook runs as a background asyncio task so the original
confirmation message goes out immediately and parsing latency (~10s for
LLM, instant for caption regex) doesn't block the bot's webhook handler.

Effects:
  * Computes the receipt id (matching the admin browser's id scheme).
  * Runs parse_one(caption, ocr_text) — caption regex first (free), then
    OCR keyword (free), then Ollama LLM (~10s).
  * Persists the result to <accounting-root>/<YYYY-MM>/parsed.jsonl so it
    shows up in the admin browser instantly.
  * Sends a follow-up Telegram message:
      "AI: vendor — ₡amount CRC (88% confident)
       Looks wrong? Fix: <edit-link>"
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from typing import Awaitable, Callable, Optional

log = logging.getLogger("zv.autoparse")

ACCOUNTING_ROOT = Path(
    os.environ.get("ZV_ACCOUNTING_ROOT", "/opt/zen-village/accounting-intake")
)
ADMIN_BASE_URL = (
    os.environ.get("ZV_ADMIN_BASE_URL")
    or "https://brain.zenvillagecr.com/accounting"
).rstrip("/")


def _row_id(record: dict) -> str:
    rid = record.get("id")
    if rid:
        return str(rid)
    seed = "|".join([
        str(record.get("ts") or record.get("timestamp") or ""),
        str(record.get("filename") or record.get("file_name") or ""),
        str(record.get("telegram_user_id") or record.get("user_id") or ""),
    ])
    return "rcpt_" + sha1(seed.encode("utf-8")).hexdigest()[:16]


def _month_dir_for(record: dict) -> Path:
    """Match the bot's _accounting_dir() convention (YYYY-MM in UTC)."""
    ts = str(record.get("ts") or record.get("timestamp") or "")
    if len(ts) >= 7:
        ym = ts[:7]
    else:
        ym = datetime.utcnow().strftime("%Y-%m")
    return ACCOUNTING_ROOT / ym


def _persist_parsed(month_dir: Path, rid: str, parsed: dict) -> None:
    """Merge the parsed result into parsed.jsonl atomically (id-keyed)."""
    month_dir.mkdir(parents=True, exist_ok=True)
    parsed_path = month_dir / "parsed.jsonl"
    existing: dict[str, dict] = {}
    if parsed_path.exists():
        try:
            for line in parsed_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if d.get("id"):
                    existing[d["id"]] = d
        except Exception:
            pass
    parsed["id"] = rid
    parsed["parsed_at"] = datetime.utcnow().isoformat() + "Z"
    if parsed.get("method") != "llm":
        parsed.pop("raw_response", None)
    existing[rid] = parsed
    tmp = parsed_path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as fp:
        for k in sorted(existing.keys()):
            fp.write(json.dumps(existing[k], ensure_ascii=False) + "\n")
    tmp.replace(parsed_path)
    try:
        os.chmod(parsed_path, 0o600)
    except Exception:
        pass


def _format_amount(parsed: dict) -> str:
    amt = parsed.get("amount")
    cur = parsed.get("currency") or ""
    if amt is None:
        return ""
    sym = {"CRC": "₡", "USD": "$"}.get(cur, "")
    return f"{sym}{float(amt):,.2f}".rstrip("0").rstrip(".") + (f" {cur}" if cur and cur != "UNK" else "")


def _build_reply(parsed: dict, rid: str) -> str:
    """Render a friendly Telegram reply with the AI result + edit link."""
    edit_url = f"{ADMIN_BASE_URL}/?id={rid}"
    method = parsed.get("method") or "none"
    confidence = float(parsed.get("confidence") or 0)
    pct = int(round(confidence * 100))

    if parsed.get("amount") is None:
        return (
            "🤖 I couldn't read an amount from this one.\n"
            f"Tap to add it: {edit_url}\n"
            "Or just send another with the amount in the caption — like `/receipt $45 vendor name`."
        )

    method_human = {
        "caption": "from your caption",
        "ocr_keyword": "from receipt OCR",
        "llm": "AI from receipt",
        "human": "manually entered",
    }.get(method, method)

    vendor = parsed.get("vendor") or ""
    vendor_line = f"*{vendor}*\n" if vendor else ""
    amt_str = _format_amount(parsed)

    return (
        f"🤖 Captured ✓\n"
        f"{vendor_line}"
        f"Amount: *{amt_str}*  _( {method_human} · {pct}% sure )_\n\n"
        f"Looks wrong? Fix it here:\n{edit_url}"
    )


async def autoparse_and_notify(
    record: dict,
    chat_id: int,
    tg_send: Callable[..., Awaitable[None]],
    *,
    use_llm: bool = True,
) -> None:
    """Run the parser on a freshly-saved record and notify the user.

    Designed to be scheduled with asyncio.create_task() — never raises;
    failures are logged but don't propagate.
    """
    try:
        rid = _row_id(record)
        # Lazy import so a failure in the parser module never breaks
        # the bot's main webhook handler.
        try:
            from parse_receipt_amount import parse_one
        except ImportError as e:
            log.warning("parse_receipt_amount unavailable, autoparse skipped: %s", e)
            return

        # Caption text (Telegram caption) and OCR text (Tesseract / Paperless).
        caption = str(record.get("caption") or record.get("text") or record.get("note") or "")
        ocr = str(record.get("extracted_text") or "")

        # Skip text-only intakes that have no text to parse — would be noisy.
        if not caption and not ocr:
            return

        # Run in a thread so we don't block the asyncio loop on Ollama.
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: parse_one(caption=caption, ocr_text=ocr, use_llm=use_llm),
        )
        parsed_dict = result.to_dict() if hasattr(result, "to_dict") else dict(result or {})

        month_dir = _month_dir_for(record)
        _persist_parsed(month_dir, rid, parsed_dict)

        reply = _build_reply(parsed_dict, rid)
        await tg_send(chat_id, reply, parse_mode="Markdown")
    except Exception:
        log.exception("autoparse_and_notify failed for record")


def schedule(
    record: dict,
    chat_id: int,
    tg_send: Callable[..., Awaitable[None]],
    *,
    use_llm: bool = True,
) -> asyncio.Task:
    """Fire-and-forget convenience wrapper for use inside the intake handlers."""
    return asyncio.create_task(autoparse_and_notify(record, chat_id, tg_send, use_llm=use_llm))
