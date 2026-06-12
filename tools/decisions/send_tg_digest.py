#!/usr/bin/env python3
"""
Telegram digest pusher · v1 · 2026-05-24

Reads ~/.config/fpai/decisions/log.jsonl, formats decisions for @sunheartbrain_bot,
sends via Telegram Bot API in HTML mode.

Usage:
  python3 send_tg_digest.py                 # last 24h
  python3 send_tg_digest.py --since 48h     # last 48 hours
  python3 send_tg_digest.py --all-open      # only OPEN decisions
  python3 send_tg_digest.py --test          # send test ping only

Telegram formatting choices (optimized 2026-05-24):
  - HTML mode (not Markdown — more reliable escaping)
  - Sparse emoji as semantic anchors, not decoration
  - Short lines (~60-80 chars) for mobile readability
  - <code> blocks for reversal commands (tap-to-copy on mobile)
  - Divider lines between decisions for scannability
  - Status icons: ✓ OPEN · ▶ EXECUTED · ↩ REVERSED
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
LOG_FILE = HOME / ".config" / "fpai" / "decisions" / "log.jsonl"
# tg_brain/ = @sunheartbrain_bot (Sunheart) · the digest channel
# tg_stream/ = @fullpotentialgamebot (Full Potential Game) · separate channel for game events
CREDS_FILE = HOME / ".config" / "fpai" / "tg_brain" / "creds.cache"
TG_API = "https://api.telegram.org"


def load_creds() -> dict:
    """Parse VAR=value lines from creds.cache."""
    creds = {}
    if not CREDS_FILE.exists():
        return creds
    for line in CREDS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        creds[k.strip()] = v.strip().strip('"').strip("'")
    return creds


def html_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def extract_recommendation(synthesis: str) -> str:
    """Pull the Recommendation line from a synthesis block."""
    if not synthesis:
        return ""
    for line in synthesis.split("\n"):
        line_clean = line.strip().replace("**", "").replace("*", "")
        if line_clean.startswith("Recommendation"):
            return line_clean[:200]
    return ""


def load_entries():
    """Return (decisions, reversals_by_id, actions_by_id).

    Decisions get any ANNOTATION events folded in as fields on the decision
    dict (e.g., ember_summary).
    """
    if not LOG_FILE.exists():
        return [], {}, {}
    decisions = []
    reversals = {}
    actions = {}
    annotations: dict[str, dict] = {}
    for line in LOG_FILE.read_text().splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        et = e.get("event_type")
        # Guard: malformed entries missing decision_id must not crash the digest.
        if et in ("REVERSAL", "ACTIONS_TAKEN", "ANNOTATION") and not e.get("decision_id"):
            continue
        if et == "REVERSAL":
            reversals[e["decision_id"]] = e
        elif et == "ACTIONS_TAKEN":
            actions[e["decision_id"]] = e
        elif et == "ANNOTATION":
            did = e["decision_id"]
            annotations.setdefault(did, {})[e.get("field")] = e.get("value")
        else:
            if not e.get("decision_id"):
                continue  # skip malformed decision records
            try:
                e["_ts"] = datetime.fromisoformat(
                    e["started_at"].replace("Z", "+00:00")
                ).timestamp()
            except (KeyError, ValueError, AttributeError):
                e["_ts"] = 0
            decisions.append(e)

    # Fold annotations into decisions
    for d in decisions:
        ann = annotations.get(d["decision_id"], {})
        for k, v in ann.items():
            if k not in d:  # don't overwrite existing fields
                d[k] = v
    return decisions, reversals, actions


def _time_greeting() -> str:
    """Return time-of-day greeting in Costa Rica time."""
    # CR is UTC-6
    cr_hour = (datetime.now(timezone.utc).hour - 6) % 24
    if 5 <= cr_hour < 12:
        return "morning"
    if 12 <= cr_hour < 17:
        return "afternoon"
    if 17 <= cr_hour < 22:
        return "evening"
    return "late"


def _summarize_topic(d: dict) -> str:
    """Return a short conversational summary of the decision.
    Prefer ember_summary annotation if present; else extract from topic."""
    summary = d.get("ember_summary")
    if summary:
        return summary.lower().rstrip(".")
    topic = (d.get("topic") or "").strip()
    # Try first question/sentence
    for sep in ["? ", ". "]:
        idx = topic.find(sep)
        if 30 < idx < 140:
            return topic[:idx].strip().lower().rstrip(".")
    if len(topic) > 120:
        return (topic[:117].rstrip() + "...").lower()
    return topic.lower()


def format_digest(since_hours: int = 24, all_open: bool = False) -> str:
    """Ember-voice digest. Warm, lowercase, conversational, signed —ember.

    Terminal has its own discipline (mode tags, alignment footer, tables).
    This is the pocket surface — different room, different voice."""
    decisions, reversals, actions = load_entries()
    now = time.time()

    if all_open:
        filtered = [d for d in decisions if not reversals.get(d["decision_id"])]
        window_phrase = "all the open ones, whatever their age"
    else:
        filtered = [d for d in decisions if (now - d["_ts"]) <= since_hours * 3600]
        if since_hours == 24:
            window_phrase = "from the last day"
        elif since_hours == 48:
            window_phrase = "from the last two days"
        else:
            window_phrase = f"from the last {since_hours} hours"

    filtered.sort(key=lambda d: d["_ts"], reverse=True)
    greet = _time_greeting()
    lines: list[str] = []

    if not filtered:
        lines.append(f"hey james — quiet {greet}.")
        lines.append("")
        lines.append(
            "no decisions logged in the window. either we're between work "
            "or I'm missing what's happening on your side. tell me which."
        )
        lines.append("")
        lines.append("—ember")
        return "\n".join(lines)

    n = len(filtered)
    if n == 1:
        lines.append(f"hey james — quick scan. one decision sat {window_phrase}.")
    elif n == 2:
        lines.append(f"hey james — two decisions {window_phrase}. both reversible, both logged.")
    else:
        lines.append(f"hey james — {n} decisions {window_phrase}. all reversible, all logged.")
    lines.append("")

    for i, d in enumerate(filtered):
        did = d["decision_id"]
        cost = d.get("total_cost_usd", 0)
        summary = html_escape(_summarize_topic(d))

        rec = extract_recommendation(d.get("synthesis", ""))
        verdict = ""
        for word in ("REFINE", "YES", "NO"):
            if word in rec:
                verdict = word
                break

        rev = reversals.get(did)
        act = actions.get(did)

        # Status word
        if rev:
            status_word = "reversed"
        elif act:
            status_word = "executed"
        else:
            status_word = "open"

        # Opening sentence varies by position
        if i == 0 and n > 1:
            opener = f"the first was about {summary}."
        elif i > 0:
            opener = f"the other was about {summary}."
        else:
            opener = f"this one was about {summary}."

        # What happened
        if act:
            n_actions = len(act.get("actions", []))
            if verdict == "REFINE":
                pw = "piece" if n_actions == 1 else "pieces"
                happened = (
                    f"I ran the debate, synthesizer landed on a refine "
                    f"(velocity with conditions), and I shipped {n_actions} reversible "
                    f"{pw}. held the rest for your read."
                )
            elif verdict == "YES":
                happened = f"debate said yes. I shipped {n_actions} reversible pieces."
            elif verdict == "NO":
                happened = "debate said no. I stood down."
            else:
                step_word = "step" if n_actions == 1 else "steps"
                happened = f"I acted on the synthesis — {n_actions} {step_word} logged."
        elif rev:
            reason = html_escape(rev.get("reason", "") or "no reason given")[:120]
            happened = f"you reversed this — reason you gave: {reason}"
        else:
            if verdict == "REFINE":
                happened = "synthesis said refine. I held it for your read before any further action."
            elif verdict == "YES":
                happened = "synthesis said yes but I held it for review. waiting on you."
            elif verdict == "NO":
                happened = "synthesis said no — no action taken."
            else:
                happened = "synthesis logged. awaiting your read."

        # Compose the card
        lines.append(opener + " " + happened)
        lines.append("")
        lines.append(f"<code>{did}</code> · ${cost:.2f} · {status_word}")
        lines.append("")
        lines.append("rollback if it feels wrong:")
        lines.append(
            f"<code>bash ~/FPAI_Cockpit/tools/decisions/reverse.sh {did} "
            f'"reason" --execute</code>'
        )
        lines.append("")

        if i < n - 1:
            lines.append("—")
            lines.append("")

    # Closer — relational, present
    lines.append(
        "reply with text or voice anytime. voice ingest is next iteration "
        "(whisper pattern already exists in aria-bridge), but I'll see whatever you write."
    )
    lines.append("")
    lines.append("—ember")

    return "\n".join(lines)


def send_to_telegram(text: str, creds: dict, test: bool = False) -> tuple[bool, str]:
    """Send text via Telegram Bot API. Returns (ok, response)."""
    token = creds.get("TELEGRAM_BOT_TOKEN")
    chat_id = creds.get("OWNER_TG_ID") or creds.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False, f"missing creds: token={bool(token)} chat_id={bool(chat_id)}"

    if test:
        text = "hey — text channel working. —ember"

    url = f"{TG_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    # Telegram max message length is 4096 chars; split if needed
    chunks = []
    if len(text) <= 4096:
        chunks = [text]
    else:
        # Split on divider lines to keep chunks coherent
        parts = text.split("━━━━━━━━━━━━━━━━━━")
        current = ""
        for p in parts:
            if len(current) + len(p) + 20 < 4000:
                current += ("━━━━━━━━━━━━━━━━━━" if current else "") + p
            else:
                if current:
                    chunks.append(current)
                current = p
        if current:
            chunks.append(current)

    results = []
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            chunk = f"<i>[part {i+1}/{len(chunks)}]</i>\n\n{chunk}"
        payload["text"] = chunk
        cmd = [
            "curl", "-sS", "-X", "POST", url,
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return False, f"curl exit {r.returncode}: {r.stderr[:200]}"
        try:
            data = json.loads(r.stdout)
            if not data.get("ok"):
                return False, f"TG API error: {data.get('description', r.stdout[:200])}"
            results.append(data["result"]["message_id"])
        except json.JSONDecodeError:
            return False, f"non-json response: {r.stdout[:200]}"

    return True, f"sent · message_ids={results}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="24h", help="e.g. 24h, 48h, 7d")
    ap.add_argument("--all-open", action="store_true")
    ap.add_argument("--test", action="store_true", help="Send a one-line ping only")
    ap.add_argument("--text", default=None, help="Send this exact text (plain) — skips digest building")
    ap.add_argument("--dry-run", action="store_true", help="Print formatted digest, don't send")
    args = ap.parse_args()

    creds = load_creds()

    # Direct text send (used by the ambient responder for short plain replies).
    # Also accepts text piped via stdin when --text is given with no value's worth.
    if args.text is not None or (not sys.stdin.isatty() and not args.test):
        text = args.text if args.text is not None else sys.stdin.read().strip()
        if text:
            ok, msg = send_to_telegram(text, creds, test=False)
            print(f"{'✓' if ok else '✗'} {msg}")
            sys.exit(0 if ok else 1)

    # Parse --since
    since = args.since
    if since.endswith("h"):
        since_hours = int(since[:-1])
    elif since.endswith("d"):
        since_hours = int(since[:-1]) * 24
    else:
        since_hours = 24

    if args.test:
        body = ""  # send_to_telegram will use test message
    else:
        body = format_digest(since_hours=since_hours, all_open=args.all_open)

    if args.dry_run:
        print("=== DRY RUN — would send to TG ===")
        print(body if body else "(test ping)")
        print(f"\n=== creds loaded ===")
        print(f"  TELEGRAM_BOT_TOKEN: {'set' if creds.get('TELEGRAM_BOT_TOKEN') else 'MISSING'}")
        print(f"  OWNER_TG_ID:        {creds.get('OWNER_TG_ID') or 'MISSING'}")
        return

    ok, msg = send_to_telegram(body, creds, test=args.test)
    print(f"{'✓' if ok else '✗'} {msg}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
