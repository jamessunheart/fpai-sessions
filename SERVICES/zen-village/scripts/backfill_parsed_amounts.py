#!/usr/bin/env python3
"""
Backfill parsed amount/currency/vendor for every receipt in the JSONL vault.

For each row in /opt/zen-village/accounting-intake/<YYYY-MM>/intake.jsonl,
runs parse_receipt_amount.parse_one() and writes the result to a sidecar
file at /opt/zen-village/accounting-intake/<YYYY-MM>/parsed.jsonl, keyed by
the receipt's id.

The sidecar approach keeps intake.jsonl untouched (it stays the canonical
write log from the bot) and lets us re-run the backfill safely whenever the
parser improves.

Usage on the server:
    python3 backfill_parsed_amounts.py                  # all months
    python3 backfill_parsed_amounts.py --month 2026-04  # one month
    python3 backfill_parsed_amounts.py --no-llm         # skip Ollama (fast)
    python3 backfill_parsed_amounts.py --force          # re-parse already-parsed rows
    python3 backfill_parsed_amounts.py --dry-run        # show what would change

Environment:
    ACCOUNTING_ROOT  — defaults to /opt/zen-village/accounting-intake
    OLLAMA_BASE      — defaults to http://127.0.0.1:11434
    ZV_RECEIPT_LLM_MODEL — defaults to llama3.1:8b
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from hashlib import sha1
from pathlib import Path

# Allow running from /opt/zen-village/telegram/ where parse_receipt_amount lives
HERE = Path(__file__).resolve().parent
for cand in (HERE, HERE.parent, Path("/opt/zen-village/telegram")):
    if cand.exists() and str(cand) not in sys.path:
        sys.path.insert(0, str(cand))

from parse_receipt_amount import parse_one, ParsedReceipt  # noqa: E402

log = logging.getLogger("zv.backfill")

ACCOUNTING_ROOT = Path(
    os.environ.get("ZV_ACCOUNTING_ROOT", "/opt/zen-village/accounting-intake")
)


def _row_id(raw: dict) -> str:
    rid = raw.get("id")
    if rid:
        return str(rid)
    seed = f"{raw.get('ts') or raw.get('timestamp') or ''}|{raw.get('filename') or raw.get('file_name') or ''}|{raw.get('telegram_user_id') or raw.get('user_id') or ''}"
    return "rcpt_" + sha1(seed.encode("utf-8")).hexdigest()[:16]


def _load_existing(parsed_path: Path) -> dict[str, dict]:
    if not parsed_path.exists():
        return {}
    out: dict[str, dict] = {}
    for line in parsed_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            if d.get("id"):
                out[d["id"]] = d
        except Exception:
            continue
    return out


def _write_atomic(parsed_path: Path, rows: dict[str, dict]) -> None:
    tmp = parsed_path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as fp:
        for rid in sorted(rows.keys()):
            fp.write(json.dumps(rows[rid], ensure_ascii=False) + "\n")
    tmp.replace(parsed_path)
    try:
        os.chmod(parsed_path, 0o600)
    except Exception:
        pass


def process_month(month_dir: Path, *, use_llm: bool, force: bool, dry_run: bool) -> dict:
    intake = month_dir / "intake.jsonl"
    parsed_path = month_dir / "parsed.jsonl"
    if not intake.exists():
        return {"month": month_dir.name, "skipped": "no intake.jsonl"}

    existing = _load_existing(parsed_path)
    out: dict[str, dict] = dict(existing)  # carry forward already-parsed entries

    stats = {
        "month": month_dir.name,
        "total": 0,
        "skipped_already_parsed": 0,
        "newly_parsed": 0,
        "by_method": {},
    }

    for line in intake.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except Exception:
            continue

        stats["total"] += 1
        rid = _row_id(raw)
        if not force and rid in existing and existing[rid].get("amount") is not None:
            stats["skipped_already_parsed"] += 1
            continue

        caption = str(raw.get("caption") or raw.get("note") or "")
        ocr = str(raw.get("extracted_text") or "")

        try:
            result: ParsedReceipt = parse_one(
                caption=caption, ocr_text=ocr, use_llm=use_llm,
            )
        except Exception as e:
            log.warning("parse_one failed for %s: %s", rid, e)
            continue

        # Slim down the row we persist (drop raw_response unless useful).
        d = result.to_dict()
        d["id"] = rid
        d["parsed_at"] = datetime.utcnow().isoformat() + "Z"
        if d.get("method") != "llm":
            d.pop("raw_response", None)

        out[rid] = d
        stats["newly_parsed"] += 1
        stats["by_method"][result.method] = stats["by_method"].get(result.method, 0) + 1

        # Friendly progress for long Ollama runs
        amt = result.amount
        cur = result.currency or ""
        log.info("  %s · %s %.2f via %s (conf %.2f)",
                 rid[:14], cur or "—", amt or 0, result.method, result.confidence)

    if not dry_run and out != existing:
        _write_atomic(parsed_path, out)
        log.info("wrote %d entries to %s", len(out), parsed_path)
    return stats


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--month", help="YYYY-MM; if omitted, processes all months")
    p.add_argument("--no-llm", action="store_true", help="skip Ollama (caption + OCR-keyword only)")
    p.add_argument("--force", action="store_true", help="re-parse rows that already have an amount")
    p.add_argument("--dry-run", action="store_true", help="don't write parsed.jsonl, just report")
    p.add_argument("--root", default=str(ACCOUNTING_ROOT))
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    root = Path(args.root)
    if not root.exists():
        log.error("Accounting root not found: %s", root)
        return 2

    if args.month:
        month_dirs = [root / args.month]
    else:
        month_dirs = sorted(p for p in root.glob("20??-??") if p.is_dir())

    if not month_dirs:
        log.warning("No month directories found in %s", root)
        return 0

    started = time.time()
    total_stats = []
    for md in month_dirs:
        if not md.exists():
            log.warning("Skipping missing month: %s", md)
            continue
        log.info("Processing %s …", md.name)
        s = process_month(md, use_llm=not args.no_llm, force=args.force, dry_run=args.dry_run)
        total_stats.append(s)

    elapsed = time.time() - started
    log.info("=" * 60)
    log.info("Backfill complete in %.1fs", elapsed)
    for s in total_stats:
        log.info("  %s: total=%d new=%d skipped=%d methods=%s",
                 s.get("month"), s.get("total", 0), s.get("newly_parsed", 0),
                 s.get("skipped_already_parsed", 0), s.get("by_method", {}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
