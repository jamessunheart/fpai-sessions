#!/usr/bin/env python3
"""
veto_inbox.py — James's Veto Inbox (v0.1)

Single SSOT for ALL pending-James-irreducible items across the substrate.
Append-only JSONL queue + resolved log. CLI for producer/consumer ops.

Files:
  ~/.config/fpai/veto_inbox/queue.jsonl     — active items
  ~/.config/fpai/veto_inbox/resolved.jsonl  — resolved/vetoed items
  ~/.config/fpai/veto_inbox/inbox.log       — operational log

Schema (one JSON per line):
  id              (str)   — short hex id, generated at add
  created_at      (ISO8601 UTC)
  category        (str)   — yield · savings · sales · voice · zv · bridge · strategic · quick · other
  description     (str)   — what James needs to decide / approve / do
  time_cost_min   (int)   — estimated minutes of James-time
  leverage        (str)   — "high" | "med" | "low"
  urgency         (str)   — "high" | "med" | "low"
  status          (str)   — "pending" | "in_progress" | "resolved" | "vetoed"
  resolver        (str)   — who acts (defaults "james"; could be "ember" w/ context)
  context_link    (str)   — optional path to memory file / proof / runbook
  classification  (str)   — PRIVATE | COUNCIL-RESTRICTED | COUNCIL-OPEN | PUBLIC
  notes           (str)   — optional human notes / resolution detail

CLI:
  add        — JSON or KV; emits item id
  list       — pending sorted by leverage-per-minute (default)
  show <id>  — full detail
  resolve <id> [--note ""]   — mark resolved
  veto <id> [--note ""]      — mark vetoed
  progress <id>              — mark in_progress
  reopen <id>                — back to pending
  category <cat>             — filter list to category
  counter                    — emit "N pending · K high-leverage" for footer use
  resolved [--limit N]       — recent resolved items
  stats                      — top-line snapshot (counts by category × status)
  dump_pwa                   — emit JSON for PWA consumption (combined active + recent resolved)

Phoenix discipline:
- This file is the OWN source of truth. TG bot reads from it. PWA reads from it.
- If TG breaks, this CLI still works. If PWA breaks, TG + CLI still work.
- Backups handled by enclosing system (cron rsync to brain server — separate concern).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterator

STATE_DIR = Path(os.path.expanduser("~/.config/fpai/veto_inbox"))
QUEUE = STATE_DIR / "queue.jsonl"
RESOLVED = STATE_DIR / "resolved.jsonl"
LOG = STATE_DIR / "inbox.log"

VALID_CATEGORIES = {
    "yield", "savings", "sales", "voice", "zv", "bridge", "strategic", "quick",
    "other", "treasury", "ops", "village", "champion", "infra",
}
VALID_LEVERAGE = {"high", "med", "low"}
VALID_URGENCY = {"high", "med", "low"}
VALID_STATUS = {"pending", "in_progress", "resolved", "vetoed"}
VALID_CLASSIFICATION = {"PRIVATE", "COUNCIL-RESTRICTED", "COUNCIL-OPEN", "PUBLIC"}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    for p in (QUEUE, RESOLVED, LOG):
        if not p.exists():
            p.touch()


def _log(line: str) -> None:
    _ensure()
    with LOG.open("a") as fh:
        fh.write(f"{_now()}  {line}\n")


def _gen_id(description: str) -> str:
    seed = f"{_now()}-{description}-{os.getpid()}"
    return hashlib.sha1(seed.encode()).hexdigest()[:8]


def _iter_items(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with path.open("r") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                yield json.loads(ln)
            except json.JSONDecodeError:
                continue


def _load_queue() -> list[dict]:
    return list(_iter_items(QUEUE))


def _write_queue(items: list[dict]) -> None:
    """Rewrite queue.jsonl. Atomic via tmp file."""
    _ensure()
    tmp = QUEUE.with_suffix(".jsonl.tmp")
    with tmp.open("w") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    tmp.replace(QUEUE)


def _append_resolved(item: dict) -> None:
    _ensure()
    with RESOLVED.open("a") as fh:
        fh.write(json.dumps(item, ensure_ascii=False) + "\n")


def _leverage_per_minute(item: dict) -> float:
    """Score for sort: high leverage + low time = top."""
    weight = {"high": 3.0, "med": 1.5, "low": 0.7}
    lev = weight.get(item.get("leverage", "med"), 1.5)
    urg = weight.get(item.get("urgency", "med"), 1.5)
    tc = max(1, int(item.get("time_cost_min", 5) or 5))
    return (lev * urg) / tc


# ─── Commands ──────────────────────────────────────────────────────

def cmd_add(args) -> int:
    _ensure()
    if args.json:
        try:
            payload = json.loads(args.json)
        except json.JSONDecodeError as e:
            print(f"ERROR: invalid --json: {e}", file=sys.stderr)
            return 2
    else:
        payload = {
            "category": args.category,
            "description": args.description,
            "time_cost_min": args.time_cost_min,
            "leverage": args.leverage,
            "urgency": args.urgency,
            "resolver": args.resolver,
            "context_link": args.context_link or "",
            "classification": args.classification,
            "notes": args.notes or "",
        }

    desc = (payload.get("description") or "").strip()
    if not desc:
        print("ERROR: description required", file=sys.stderr)
        return 2
    cat = (payload.get("category") or "other").strip().lower()
    if cat not in VALID_CATEGORIES:
        print(f"ERROR: invalid category '{cat}' (valid: {sorted(VALID_CATEGORIES)})", file=sys.stderr)
        return 2

    item = {
        "id": _gen_id(desc),
        "created_at": _now(),
        "category": cat,
        "description": desc,
        "time_cost_min": int(payload.get("time_cost_min", 5) or 5),
        "leverage": (payload.get("leverage") or "med").lower(),
        "urgency": (payload.get("urgency") or "med").lower(),
        "status": "pending",
        "resolver": payload.get("resolver") or "james",
        "context_link": payload.get("context_link") or "",
        "classification": payload.get("classification") or "PRIVATE",
        "notes": payload.get("notes") or "",
    }
    # Validate enums (soft — coerce on invalid)
    if item["leverage"] not in VALID_LEVERAGE:
        item["leverage"] = "med"
    if item["urgency"] not in VALID_URGENCY:
        item["urgency"] = "med"
    if item["classification"] not in VALID_CLASSIFICATION:
        item["classification"] = "PRIVATE"

    with QUEUE.open("a") as fh:
        fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    _log(f"ADD {item['id']} [{item['category']}] {desc[:80]}")
    print(item["id"])
    return 0


def cmd_list(args) -> int:
    items = _load_queue()
    items = [it for it in items if it.get("status") in ("pending", "in_progress")]
    if args.category:
        items = [it for it in items if it.get("category") == args.category.lower()]
    items.sort(key=_leverage_per_minute, reverse=True)
    if args.limit:
        items = items[: args.limit]
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0
    if not items:
        print("(inbox empty)")
        return 0
    for it in items:
        lpm = _leverage_per_minute(it)
        flag = ""
        if it.get("status") == "in_progress":
            flag = " [WIP]"
        print(
            f"[{it['id']}] {it['category']:<10} "
            f"lev={it['leverage']:<4} urg={it['urgency']:<4} "
            f"~{it['time_cost_min']}m  L/m={lpm:.2f}{flag}\n"
            f"          {it['description'][:200]}"
        )
        if it.get("context_link"):
            print(f"          → {it['context_link']}")
    return 0


def cmd_show(args) -> int:
    items = _load_queue()
    matches = [it for it in items if it["id"].startswith(args.id)]
    if not matches:
        # Try resolved
        for it in _iter_items(RESOLVED):
            if it["id"].startswith(args.id):
                matches.append(it)
    if not matches:
        print(f"NOT FOUND: {args.id}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(matches[0], ensure_ascii=False, indent=2))
    else:
        for k, v in matches[0].items():
            print(f"{k:>16}: {v}")
    return 0


def _set_status(args, status: str) -> int:
    items = _load_queue()
    found = False
    for it in items:
        if it["id"].startswith(args.id):
            it["status"] = status
            if args.note:
                existing = it.get("notes") or ""
                it["notes"] = (existing + "\n" if existing else "") + f"[{status} {_now()}] {args.note}"
            it["resolved_at"] = _now() if status in ("resolved", "vetoed") else it.get("resolved_at", "")
            found = True
            chosen = it
    if not found:
        print(f"NOT FOUND: {args.id}", file=sys.stderr)
        return 1
    if status in ("resolved", "vetoed"):
        # Move to resolved log; remove from active queue
        remaining = [it for it in items if not it["id"].startswith(args.id)]
        _write_queue(remaining)
        _append_resolved(chosen)
    else:
        _write_queue(items)
    _log(f"{status.upper()} {chosen['id']} {chosen['description'][:60]}")
    print(f"OK {chosen['id']} → {status}")
    return 0


def cmd_resolve(args) -> int:
    return _set_status(args, "resolved")


def cmd_veto(args) -> int:
    return _set_status(args, "vetoed")


def cmd_progress(args) -> int:
    return _set_status(args, "in_progress")


def cmd_reopen(args) -> int:
    return _set_status(args, "pending")


def cmd_counter(args) -> int:
    """Emit single line for alignment-footer use."""
    items = [it for it in _load_queue() if it.get("status") in ("pending", "in_progress")]
    n = len(items)
    n_high = sum(1 for it in items if it.get("leverage") == "high")
    n_wip = sum(1 for it in items if it.get("status") == "in_progress")
    parts = [f"{n} pending"]
    if n_high:
        parts.append(f"{n_high} high-lev")
    if n_wip:
        parts.append(f"{n_wip} WIP")
    print(" · ".join(parts))
    return 0


def cmd_resolved(args) -> int:
    items = list(_iter_items(RESOLVED))
    items.reverse()  # most recent first
    if args.limit:
        items = items[: args.limit]
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0
    if not items:
        print("(no resolved items)")
        return 0
    for it in items:
        when = it.get("resolved_at", it.get("created_at", "?"))
        status_emoji = {"resolved": "✓", "vetoed": "✗"}.get(it.get("status", ""), "?")
        print(f"{status_emoji} [{it['id']}] {when}  {it['category']:<10}  {it['description'][:100]}")
        if it.get("notes"):
            tail = it["notes"].splitlines()[-1] if it["notes"] else ""
            if tail:
                print(f"        note: {tail[:140]}")
    return 0


def cmd_stats(args) -> int:
    active = [it for it in _load_queue() if it.get("status") in ("pending", "in_progress")]
    resolved = list(_iter_items(RESOLVED))
    by_cat: dict[str, int] = {}
    by_lev: dict[str, int] = {}
    total_time = 0
    for it in active:
        by_cat[it["category"]] = by_cat.get(it["category"], 0) + 1
        by_lev[it["leverage"]] = by_lev.get(it["leverage"], 0) + 1
        total_time += int(it.get("time_cost_min", 0) or 0)
    out = {
        "pending": sum(1 for it in active if it["status"] == "pending"),
        "in_progress": sum(1 for it in active if it["status"] == "in_progress"),
        "resolved_total": sum(1 for it in resolved if it.get("status") == "resolved"),
        "vetoed_total": sum(1 for it in resolved if it.get("status") == "vetoed"),
        "by_category": by_cat,
        "by_leverage": by_lev,
        "estimated_james_time_min": total_time,
    }
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Active: {out['pending']} pending · {out['in_progress']} WIP")
        print(f"Resolved/vetoed: {out['resolved_total']}/{out['vetoed_total']}")
        print(f"Estimated James-time to clear queue: {out['estimated_james_time_min']} min")
        print(f"By category: {by_cat}")
        print(f"By leverage: {by_lev}")
    return 0


def cmd_dump_pwa(args) -> int:
    """Emit combined JSON for PWA. Active items + last 20 resolved."""
    active = sorted(
        [it for it in _load_queue() if it.get("status") in ("pending", "in_progress")],
        key=_leverage_per_minute,
        reverse=True,
    )
    resolved = list(_iter_items(RESOLVED))
    resolved.reverse()
    payload = {
        "generated_at": _now(),
        "active": active,
        "recent_resolved": resolved[:20],
        "version": "v0.1",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


# ─── argparse ──────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="James's Veto Inbox CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("add", help="add a pending item")
    s.add_argument("--json", help="full item as JSON (overrides individual flags)")
    s.add_argument("--category", default="other")
    s.add_argument("--description", default="")
    s.add_argument("--time-cost-min", dest="time_cost_min", type=int, default=5)
    s.add_argument("--leverage", default="med")
    s.add_argument("--urgency", default="med")
    s.add_argument("--resolver", default="james")
    s.add_argument("--context-link", dest="context_link", default="")
    s.add_argument("--classification", default="PRIVATE")
    s.add_argument("--notes", default="")
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("list", help="list pending items (sorted by leverage-per-minute)")
    s.add_argument("--category")
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="show full detail of one item by id prefix")
    s.add_argument("id")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_show)

    for status_cmd, fn in (
        ("resolve", cmd_resolve),
        ("veto", cmd_veto),
        ("progress", cmd_progress),
        ("reopen", cmd_reopen),
    ):
        s = sub.add_parser(status_cmd, help=f"mark item as {status_cmd}")
        s.add_argument("id")
        s.add_argument("--note", default="")
        s.set_defaults(func=fn)

    s = sub.add_parser("counter", help="emit one-line counter for alignment footer")
    s.set_defaults(func=cmd_counter)

    s = sub.add_parser("resolved", help="list recently resolved/vetoed items")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_resolved)

    s = sub.add_parser("stats", help="top-line snapshot")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_stats)

    s = sub.add_parser("dump_pwa", help="emit combined JSON for PWA consumption")
    s.set_defaults(func=cmd_dump_pwa)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
