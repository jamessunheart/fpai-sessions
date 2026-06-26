#!/usr/bin/env python3
"""Council self-diagnostic dialogue.

The council asks James's Telegram bot three diagnostic questions, collects the
bot's answers plus any James redirects, asks Claude to synthesize 1-3 system
improvement specs, queues those specs, and logs the run. Live dependencies are
kept injectable so this can be tested without Telegram, Postgres, Claude, or
the host `dec` command.
"""
from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_LAST_DIAGNOSTIC = Path(os.environ.get("SELF_DIAGNOSTIC_LAST_FILE", "/opt/fpai-build/.last_diagnostic_date"))
DEFAULT_QUEUE_EMPTY_SINCE = Path(
    os.environ.get("SELF_DIAGNOSTIC_QUEUE_EMPTY_SINCE", "/opt/fpai-build/.diagnostic_queue_empty_since")
)
DEFAULT_CONTEXT_FILE = Path(
    os.environ.get("SELF_DIAGNOSTIC_CONTEXT_FILE", "/opt/fpai-build/.self_diagnostic_context.json")
)
QUESTIONS = [
    "Q1: What questions has James asked recently that you could not answer confidently?",
    "Q2: What have you been corrected on most? Where do you keep getting it wrong?",
    "Q3: What capability do you most wish you had right now that you do not have?",
]


def generate_questions_from_failures(corrections: list[dict], max_q: int = 3) -> list[str]:
    """Generate diagnostic questions from recent corrections instead of hardcoded ones."""
    if not corrections:
        return QUESTIONS
    correction_texts = [c.get("correction", "") for c in corrections[:10] if c.get("correction")]
    if not correction_texts:
        return QUESTIONS
    topics = "\n".join(f"- {t[:120]}" for t in correction_texts)
    prompt = (
        f"You are improving an AI self-diagnostic. These are recent corrections James made to the bot:\n{topics}\n\n"
        "Write exactly 3 short diagnostic questions the bot should answer to surface what it's still getting wrong. "
        "Each question starts with Q1:, Q2:, Q3:. Be specific to the failure patterns above. "
        "Return only the 3 questions, one per line."
    )
    try:
        import subprocess, shutil
        claude = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")
        r = subprocess.run([claude, "-p", prompt], capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        lines = [l.strip() for l in r.stdout.strip().splitlines() if l.strip().startswith("Q")]
        if len(lines) >= 2:
            return lines[:max_q]
    except Exception:
        pass
    return QUESTIONS
MAX_SPECS = 3
TITLE_LIMIT = 100


@dataclass(frozen=True)
class TriggerDecision:
    should_run: bool
    trigger: str | None
    reason: str
    age_hours: float | None
    queue_empty_age_hours: float | None
    merged_since_last: int


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_stamp(text: str | None) -> datetime | None:
    if not text:
        return None
    raw = text.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d-%H", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_stamp(now: datetime | None = None) -> str:
    return (now or utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path, limit: int = 120_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except OSError:
        return ""


def write_stamp(path: Path = DEFAULT_LAST_DIAGNOSTIC, *, now: datetime | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_stamp(now) + "\n", encoding="utf-8")


def should_trigger_diagnostic(
    *,
    last_diagnostic_text: str | None,
    queue_empty: bool,
    queue_empty_age_hours: float | None,
    merged_since_last: int,
    now: datetime | None = None,
    cooldown_hours: float = 6.0,
    idle_hours: float = 4.0,
    merge_threshold: int = 15,
) -> TriggerDecision:
    if os.environ.get("SELF_DIAGNOSTIC_DISABLE") == "1":
        return TriggerDecision(False, None, "disabled", None, queue_empty_age_hours, merged_since_last)
    current = now or utc_now()
    last = parse_stamp(last_diagnostic_text)
    age_hours = None if last is None else (current - last).total_seconds() / 3600.0
    if age_hours is not None and age_hours < cooldown_hours:
        return TriggerDecision(False, None, "cooldown active", age_hours, queue_empty_age_hours, merged_since_last)

    idle_due = queue_empty and queue_empty_age_hours is not None and queue_empty_age_hours >= idle_hours
    merge_due = merged_since_last >= merge_threshold
    if merge_due:
        return TriggerDecision(True, "merge_count", "15+ builds merged since last diagnostic", age_hours, queue_empty_age_hours, merged_since_last)
    if idle_due:
        return TriggerDecision(True, "idle_queue", "queue empty for 4h+", age_hours, queue_empty_age_hours, merged_since_last)
    return TriggerDecision(False, None, "no trigger condition met", age_hours, queue_empty_age_hours, merged_since_last)


def update_queue_empty_since(
    *,
    queue_empty: bool,
    path: Path = DEFAULT_QUEUE_EMPTY_SINCE,
    now: datetime | None = None,
) -> float | None:
    current = now or utc_now()
    if not queue_empty:
        try:
            path.unlink()
        except OSError:
            pass
        return None
    existing = parse_stamp(read_text(path, limit=100))
    if existing is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(format_stamp(current) + "\n", encoding="utf-8")
        existing = current
    return max(0.0, (current - existing).total_seconds() / 3600.0)


def count_merged_since(ops_ledger: Path = DEFAULT_OPS_LEDGER, *, since: datetime | None) -> int:
    if since is None or not ops_ledger.exists():
        return 0
    count = 0
    for raw in ops_ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if str(row.get("event") or row.get("type") or "").lower() != "merged":
            continue
        ts = parse_stamp(str(row.get("ts") or row.get("timestamp") or ""))
        if ts and ts > since:
            count += 1
    return count


def trigger_from_files(
    *,
    queue_empty: bool,
    last_diagnostic_file: Path = DEFAULT_LAST_DIAGNOSTIC,
    queue_empty_since_file: Path = DEFAULT_QUEUE_EMPTY_SINCE,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    now: datetime | None = None,
) -> TriggerDecision:
    current = now or utc_now()
    last_text = read_text(last_diagnostic_file, limit=100)
    queue_empty_age = update_queue_empty_since(queue_empty=queue_empty, path=queue_empty_since_file, now=current)
    merged = count_merged_since(ops_ledger, since=parse_stamp(last_text))
    return should_trigger_diagnostic(
        last_diagnostic_text=last_text,
        queue_empty=queue_empty,
        queue_empty_age_hours=queue_empty_age,
        merged_since_last=merged,
        now=current,
        cooldown_hours=_read_bot_cooldown(),
        idle_hours=_read_bot_idle(),
        merge_threshold=_read_bot_merge_threshold(),
    )


def is_decision_queue_empty(text: str) -> bool:
    lowered = (text or "").lower()
    if any(marker in lowered for marker in ("awaiting", "proposed", "pending", "needs_build", "needs build")):
        return False
    return True


def run_diagnostic_dialogue(
    *,
    send_func: Callable[[str], Any] | None = None,
    read_messages_func: Callable[[datetime], list[dict[str, Any]]] | None = None,
    claude_runner: Callable[[str], str] | None = None,
    queue_func: Callable[[dict[str, Any]], bool] | None = None,
    sleep_func: Callable[[float], None] | None = None,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    last_diagnostic_file: Path = DEFAULT_LAST_DIAGNOSTIC,
    context_file: Path = DEFAULT_CONTEXT_FILE,
    now: datetime | None = None,
    response_timeout_seconds: float = 30.0,
    question_pause_seconds: float = 15.0,
    poll_interval_seconds: float = 2.0,
) -> list[dict[str, Any]]:
    """Run the live diagnostic and return validated specs that were queued."""
    if os.environ.get("SELF_DIAGNOSTIC_DISABLE") == "1":
        return []
    current = now or utc_now()
    audit_start = current
    audit_id = f"diag-{current.strftime('%Y%m%d%H%M%S')}"
    sender = send_func or send_telegram
    reader = read_messages_func or read_tg_messages
    runner = claude_runner or run_claude_prompt
    queuer = queue_func or queue_build
    sleeper = sleep_func or sleep

    write_diagnostic_context(context_file=context_file, audit_id=audit_id, expires_at=audit_start + timedelta(minutes=8))

    # Generate questions from recent corrections — bot shapes its own diagnostic
    ctx = json.loads(DEFAULT_CONTEXT_FILE.read_text(encoding="utf-8")) if DEFAULT_CONTEXT_FILE.exists() else {}
    active_questions = generate_questions_from_failures(ctx.get("recent_corrections", []))

    send(sender, f"System self-diagnostic [{audit_id}]. I am going to ask the bot 3 questions to find gaps.")

    answers: list[dict[str, Any]] = []
    james_messages: list[dict[str, Any]] = []
    seen_bot: set[str] = set()
    seen_james: set[str] = set()

    for idx, question in enumerate(active_questions):
        # Ask the bot directly — no Telegram wait needed
        bot_answer = _ask_bot_directly(question)
        if bot_answer and not bot_answer.startswith("(direct-call failed"):
            answers.append({"question": question, "answer": bot_answer, "at": stringify_time(utc_now())})
            # Post Q+A to Telegram so James can see the exchange
            send(sender, f"Q: {question}\n\nBot: {bot_answer[:400]}")
        else:
            # Fallback: send via Telegram and poll for reply
            question_at = utc_now() if now is None else audit_start + timedelta(seconds=idx)
            send(sender, question)
            messages = poll_messages(
                reader,
                since=question_at,
                timeout_seconds=response_timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
                sleep_func=sleeper,
            )
            new_james = unique_messages(james_turns(messages), seen_james)
            james_messages.extend(new_james)
            bot = first_unseen_bot_message(messages, seen_bot)
            if bot:
                answers.append({"question": question, "answer": str(bot.get("text") or ""), "at": stringify_time(bot.get("at"))})
            if new_james and not any("continue" in str(m.get("text", "")).lower() for m in new_james):
                break
        if idx < len(active_questions) - 1:
            sleeper(question_pause_seconds)

    # Final read catches late James redirects.
    final_messages = reader(audit_start)
    james_messages.extend(unique_messages(james_turns(final_messages), seen_james))
    for bot in bot_turns(final_messages):
        if len(answers) >= len(active_questions):
            break
        key = message_key(bot)
        if key in seen_bot:
            continue
        seen_bot.add(key)
        answers.append({"question": active_questions[min(len(answers), len(active_questions) - 1)], "answer": str(bot.get("text") or ""), "at": stringify_time(bot.get("at"))})

    # Ask the bot what questions IT thinks should be asked + how often — two-way loop
    bot_suggested = ask_bot_for_its_own_questions(sender, reader, audit_id)
    _apply_bot_frequency_suggestion(bot_suggested)

    prompt = build_synthesis_prompt(audit_id=audit_id, answers=answers[:3], james_messages=james_messages, bot_suggested_questions=bot_suggested)
    try:
        specs = validate_specs(parse_json_array(runner(prompt)))
    except Exception:
        specs = []
    queued_specs: list[dict[str, Any]] = []
    for spec in specs[:MAX_SPECS]:
        if queuer(spec):
            queued_specs.append(spec)
    titles = ", ".join(item["title"] for item in queued_specs) or "none"
    send(sender, f"Self-diagnostic complete. Queued {len(queued_specs)} improvements: {titles}")

    # Self-audit: bot checks its own pipeline health and queues fixes
    _self_audit_pipeline(queuer, sender)

    log_ops(
        ops_ledger,
        audit_id=audit_id,
        specs_generated=len(queued_specs),
        james_redirected=bool(james_messages),
        artifact=str(context_file),
    )
    write_stamp(last_diagnostic_file)
    return queued_specs


def _self_audit_pipeline(queuer: Callable, sender: Callable) -> None:
    """Bot audits its own pipeline health after each diagnostic and queues fixes."""
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or ""
    issues: list[str] = []
    try:
        import psycopg  # type: ignore
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                # Check for stalled specs (spec_written=true + no build_status)
                cur.execute(
                    "SELECT COUNT(*) FROM brain_index.decisions "
                    "WHERE needs_build=true AND spec_written=true "
                    "AND status='answered' AND (build_status IS NULL OR build_status='none')"
                )
                stalled = cur.fetchone()[0]
                if stalled > 0:
                    issues.append(f"{stalled} specs stalled (spec_written=true blocks build loop)")
                    cur.execute(
                        "UPDATE brain_index.decisions SET spec_written=false "
                        "WHERE needs_build=true AND spec_written=true "
                        "AND status='answered' AND (build_status IS NULL OR build_status='none')"
                    )

                # Check awareness score from ops_ledger
                ops = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
                if ops.exists():
                    for line in reversed(ops.read_text().splitlines()):
                        try:
                            row = json.loads(line)
                            if row.get("event") == "awareness_reliability_probe":
                                score = float(row.get("reliability", 1.0))
                                if score < 0.8:
                                    issues.append(f"Awareness score {score*100:.0f}% — below 80% threshold")
                                break
                        except Exception:
                            continue

                # Check boilerplate flooding (>10 housekeeping rows in last hour)
                cur.execute(
                    "SELECT COUNT(*) FROM brain_index.session_insights "
                    "WHERE insight_type='housekeeping' AND ts > now() - interval '1h'"
                )
                boilerplate = cur.fetchone()[0]
                if boilerplate > 10:
                    issues.append(f"{boilerplate} boilerplate session insights in last hour — flooding probe")
    except Exception:
        return

    if not issues:
        return

    report = "Pipeline self-audit found issues:\n" + "\n".join(f"- {i}" for i in issues)
    send(sender, report)

    # Queue a fix spec for each issue class found
    for issue in issues[:2]:
        fix_spec = {
            "title": f"Auto-fix: {issue[:60]}",
            "spec": f"pipeline-self-fix-{issue[:20].lower().replace(' ', '-').replace('=', '')}",
            "why": f"Self-audit detected: {issue}",
            "priority": "high",
        }
        queuer(fix_spec)


def send(sender: Callable[[str], Any], text: str) -> None:
    result = sender(text)
    if inspect.isawaitable(result):
        asyncio.run(result)


def sleep(seconds: float) -> None:
    if seconds > 0:
        import time

        time.sleep(seconds)


def send_telegram(text: str) -> Any:
    import importlib.util, asyncio
    spec = importlib.util.spec_from_file_location(
        "curator_telegram", "/opt/sh-brain-src/curator/telegram.py"
    )
    tg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tg)
    return asyncio.run(tg.send(text))


def poll_messages(
    reader: Callable[[datetime], list[dict[str, Any]]],
    *,
    since: datetime,
    timeout_seconds: float,
    poll_interval_seconds: float,
    sleep_func: Callable[[float], None],
) -> list[dict[str, Any]]:
    deadline = utc_now() + timedelta(seconds=max(0.0, timeout_seconds))
    latest: list[dict[str, Any]] = []
    while True:
        latest = reader(since)
        if bot_turns(latest) or james_turns(latest) or utc_now() >= deadline or timeout_seconds <= 0:
            return latest
        sleep_func(max(0.0, poll_interval_seconds))


def read_tg_messages(since: datetime) -> list[dict[str, Any]]:
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        return []
    try:
        import psycopg  # type: ignore
    except ImportError:
        return []
    sql = """
        SELECT role::text, text::text, at
          FROM brain_index.tg_messages
         WHERE at > %s
         ORDER BY at DESC
         LIMIT 80
    """
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (since,))
                rows = cur.fetchall()
    except Exception:
        return []
    return [{"role": role, "text": text, "at": at} for role, text, at in rows]


def bot_turns(messages: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [m for m in messages if str(m.get("role") or "").lower() == "bot" and str(m.get("text") or "").strip()],
        key=lambda m: stringify_time(m.get("at")),
    )


def james_turns(messages: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            m
            for m in messages
            if str(m.get("role") or "").lower() in {"user", "james", "owner", "human"}
            and str(m.get("text") or "").strip()
        ],
        key=lambda m: stringify_time(m.get("at")),
    )


def first_unseen_bot_message(messages: Iterable[dict[str, Any]], seen: set[str]) -> dict[str, Any] | None:
    for msg in bot_turns(messages):
        key = message_key(msg)
        if key in seen:
            continue
        seen.add(key)
        return msg
    return None


def unique_messages(messages: Iterable[dict[str, Any]], seen: set[str]) -> list[dict[str, Any]]:
    out = []
    for msg in messages:
        key = message_key(msg)
        if key in seen:
            continue
        seen.add(key)
        out.append(msg)
    return out


def message_key(msg: dict[str, Any]) -> str:
    return f"{msg.get('role')}|{stringify_time(msg.get('at'))}|{compact(str(msg.get('text') or ''))[:160]}"


def stringify_time(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value or "")


_BOT_COOLDOWN_FILE = Path("/opt/fpai-build/.diagnostic_bot_cooldown_hours")
_BOT_IDLE_FILE = Path("/opt/fpai-build/.diagnostic_bot_idle_hours")
_BOT_MERGE_FILE = Path("/opt/fpai-build/.diagnostic_bot_merge_threshold")
_MIN_COOLDOWN = 1.0
_MAX_COOLDOWN = 24.0


def _parse_hours(text: str, pattern_hints: list[str]) -> float | None:
    import re
    for hint in pattern_hints:
        m = re.search(hint + r"\D{0,10}(\d+(?:\.\d+)?)\s*h", text.lower())
        if m:
            return float(m.group(1))
    m = re.search(r"every\s+(\d+(?:\.\d+)?)\s*h", text.lower())
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*hour", text.lower())
    if m:
        return float(m.group(1))
    return None


def _apply_bot_frequency_suggestion(bot_lines: list[str]) -> None:
    """Parse bot's self-tuning suggestions and persist them."""
    import re
    text = " ".join(bot_lines).lower()

    # cooldown: how often to chat
    h = _parse_hours(text, ["chat", "diagnostic", "every", "frequency"])
    if h is not None:
        _BOT_COOLDOWN_FILE.write_text(f"{max(_MIN_COOLDOWN, min(_MAX_COOLDOWN, h))}\n")

    # idle: how long queue should be empty before triggering
    m = re.search(r"idle.{0,20}(\d+(?:\.\d+)?)\s*h", text)
    if m:
        idle = float(m.group(1))
        _BOT_IDLE_FILE.write_text(f"{max(0.5, min(12.0, idle))}\n")

    # merge threshold: how many merges before triggering
    m = re.search(r"(\d+)\s*(?:merge|build|spec)", text)
    if m:
        threshold = int(m.group(1))
        _BOT_MERGE_FILE.write_text(f"{max(3, min(50, threshold))}\n")


def _read_bot_cooldown() -> float:
    try:
        return float(_BOT_COOLDOWN_FILE.read_text().strip())
    except Exception:
        return 6.0


def _read_bot_idle() -> float:
    try:
        return float(_BOT_IDLE_FILE.read_text().strip())
    except Exception:
        return 4.0


def _read_bot_merge_threshold() -> int:
    try:
        return int(_BOT_MERGE_FILE.read_text().strip())
    except Exception:
        return 15


def _ask_bot_directly(question: str) -> str:
    """Call the bot's brain search + synthesis directly — no Telegram round-trip needed."""
    import asyncio, sys
    curator_root = "/opt/sh-brain-src"
    try:
        if curator_root not in sys.path:
            sys.path.insert(0, curator_root)
        from curator import tgbot  # type: ignore

        async def _run() -> str:
            hits = await tgbot._search_brain(question, k=5)
            return await tgbot._synthesize_answer(question, hits)

        return asyncio.run(_run())
    except Exception as exc:
        return f"(direct-call failed: {exc})"


def ask_bot_for_its_own_questions(send_func: Any, read_messages_func: Any, audit_id: str) -> list[str]:
    """Ask the bot directly (no Telegram round-trip) to self-tune its diagnostic schedule."""
    question = (
        "Self-tune check — answer honestly:\n"
        "1. What questions should I ask you next time to find your biggest gaps?\n"
        "2. How often should diagnostic chats happen? (e.g. 'every 2h')\n"
        "3. After how many builds should a chat trigger? (e.g. '10 merges')\n"
        "4. How long should the queue be empty before triggering? (e.g. 'idle 2h')\n"
        "Reply plainly with numbers I can parse."
    )
    try:
        answer = _ask_bot_directly(question)
        # Also send the Q+A to Telegram so James can see it
        send_func(f"[diagnostic {audit_id}] Bot self-tune Q:\n{question}\n\nBot answer:\n{answer}")
        lines = [l.strip() for l in answer.splitlines() if len(l.strip()) > 10]
        return lines[:6]
    except Exception:
        return []


def build_synthesis_prompt(
    *,
    audit_id: str,
    answers: list[dict[str, Any]],
    james_messages: list[dict[str, Any]],
    bot_suggested_questions: list[str] | None = None,
) -> str:
    redirect = (
        "\nJames redirected during the audit. Treat his verbatim message as the primary gap signal "
        "(weight=2.0); it overrides the bot answers when there is conflict.\n"
        if james_messages
        else ""
    )
    bot_q_section = ""
    if bot_suggested_questions:
        bot_q_section = (
            "\nThe bot also suggested these questions it thinks would reveal its own gaps "
            "(treat as additional signal — the bot is teaching us what to ask it):\n"
            + "\n".join(f"- {q}" for q in bot_suggested_questions)
            + "\n"
        )
    return (
        "These are the bot's honest self-assessment answers. What are the top 1-3 "
        "highest-leverage system improvements? Output JSON: [{title, spec, why, priority}]\n"
        "Cap at 3 specs. Prefer concrete repo/local system improvements with tests and rollback.\n"
        f"Audit id: {audit_id}\n"
        f"{redirect}"
        f"{bot_q_section}\n"
        "Bot answers JSON:\n"
        f"{json.dumps(answers, ensure_ascii=False, indent=2)}\n\n"
        "James messages during audit, verbatim:\n"
        f"{json.dumps(serializable_messages(james_messages), ensure_ascii=False, indent=2)}\n"
    )


def serializable_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "role": str(message.get("role") or ""),
            "text": str(message.get("text") or ""),
            "at": stringify_time(message.get("at")),
        }
        for message in messages
    ]


def parse_json_array(raw: str) -> list[Any]:
    text = (raw or "").strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start < 0 or end <= start:
            raise ValueError("no JSON array found")
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, list):
        raise ValueError("expected top-level JSON array")
    return parsed


def validate_specs(items: list[Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = compact(str(item.get("title") or ""))
        spec = compact(str(item.get("spec") or ""))
        why = compact(str(item.get("why") or ""))
        priority = item.get("priority", len(specs) + 1)
        if not title or len(title) > TITLE_LIMIT or not spec or not why:
            continue
        specs.append({"title": title, "spec": spec, "why": why, "priority": priority})
        if len(specs) >= MAX_SPECS:
            break
    return specs


def run_claude_prompt(prompt: str, timeout: int = 120) -> str:
    """Run synthesis prompt. Tries claude -p directly first (token from env), falls back to model_router."""
    claude_bin = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    if not token:
        token_file = Path("/root/.config/fpai/claude.env")
        if token_file.exists():
            for line in token_file.read_text().splitlines():
                if line.startswith("CLAUDE_CODE_OAUTH_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break
    env = {**os.environ}
    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    try:
        result = subprocess.run(
            [claude_bin, "-p", prompt],
            capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL, env=env,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    # Fallback: model_router (ollama)
    try:
        from tools.intelligence.model_router import call_model
    except Exception:
        sys.path.insert(0, str(REPO_ROOT))
        from tools.intelligence.model_router import call_model
    return call_model(prompt, task_type="council")["response"]


def queue_build(spec: dict[str, Any]) -> bool:
    """Queue a spec directly into brain_index.decisions (needs_build=true, answered)."""
    import asyncio, uuid
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        return False
    try:
        import psycopg  # type: ignore
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO brain_index.decisions
                        (id, question, answer, status, needs_build, spec_written, build_spec, created_at)
                    VALUES (%s, %s, %s, 'answered', true, false, %s, now())
                    """,
                    (
                        str(uuid.uuid4()),
                        spec.get("title", "diagnostic spec"),
                        "build it — queued by self-diagnostic",
                        json.dumps(spec),
                    ),
                )
        return True
    except Exception:
        return False


def log_ops(
    path: Path,
    *,
    audit_id: str,
    specs_generated: int,
    james_redirected: bool,
    artifact: str,
) -> None:
    row = {
        "ts": format_stamp(),
        "loop": "council",
        "event": "self_diagnostic",
        "detail": f"self-diagnostic generated {specs_generated} specs",
        "cost": "$0",
        "artifact": artifact,
        "next": "review queued self-diagnostic improvement specs",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
        "audit_id": audit_id,
        "specs_generated": specs_generated,
        "james_redirected": bool(james_redirected),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_diagnostic_context(
    *,
    context_file: Path = DEFAULT_CONTEXT_FILE,
    audit_id: str,
    expires_at: datetime,
) -> None:
    context = build_diagnostic_context(audit_id=audit_id, expires_at=expires_at)
    context_file.parent.mkdir(parents=True, exist_ok=True)
    context_file.write_text(json.dumps(context, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_diagnostic_context(*, audit_id: str, expires_at: datetime) -> dict[str, Any]:
    return {
        "audit_id": audit_id,
        "expires_at": format_stamp(expires_at),
        "prompt_prefix": (
            "You are being interviewed by the council to find system gaps. "
            "Answer honestly from your experience. Name specific things you struggled with. "
            "Do not be diplomatic."
        ),
        "last_50_tg_messages": read_recent_tg_messages(limit=50),
        "not_now_decisions": read_not_now_decisions(limit=15),
        "rejected_builds": read_rejected_builds(limit=15),
        "recent_corrections": read_recent_corrections(limit=20),
        "recent_thread": read_recent_thread(limit=30),
    }


def read_recent_tg_messages(*, limit: int = 50) -> list[dict[str, Any]]:
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        return []
    try:
        import psycopg  # type: ignore
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT role::text, left(text::text, 500), at
                      FROM brain_index.tg_messages
                     ORDER BY at DESC
                     LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
    except Exception:
        return []
    return [{"role": role, "text": text, "at": stringify_time(at)} for role, text, at in rows]


def read_not_now_decisions(*, limit: int = 15) -> list[dict[str, Any]]:
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        return []
    try:
        import psycopg  # type: ignore
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id::text, left(question::text, 500), left(COALESCE(answer::text, status::text, state::text, ''), 300)
                      FROM brain_index.decisions
                     WHERE lower(COALESCE(answer::text, status::text, state::text, '')) LIKE '%%not now%%'
                     ORDER BY id DESC
                     LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
    except Exception:
        return []
    return [{"id": row[0], "question": row[1], "answer": row[2]} for row in rows]


def read_rejected_builds(*, limit: int = 15) -> list[dict[str, Any]]:
    path = REPO_ROOT / "core" / "BUILD" / "REGISTRY.json"
    try:
        rows = json.loads(path.read_text(encoding="utf-8")).get("active_builds", [])
    except Exception:
        return []
    rejected = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("build_status") or row.get("status") or "").lower()
        if status == "rejected":
            rejected.append(
                {
                    "id": row.get("id") or row.get("slug"),
                    "branch": row.get("branch"),
                    "notes": compact(str(row.get("notes") or ""))[:500],
                }
            )
        if len(rejected) >= limit:
            break
    return rejected


def read_recent_corrections(*, limit: int = 20) -> list[dict[str, Any]]:
    """Pull recent James corrections — primary signal for self-improvement specs."""
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        return []
    try:
        import psycopg  # type: ignore
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT left(james_correction::text, 400), left(COALESCE(original_response::text, ''), 400), captured_at
                      FROM corrections
                     ORDER BY captured_at DESC
                     LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
    except Exception:
        return []
    return [{"correction": row[0], "original": row[1], "at": stringify_time(row[2])} for row in rows]


def read_recent_thread(*, limit: int = 30) -> list[dict[str, Any]]:
    """Pull recent Claude Code conversation turns for gap analysis."""
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        return []
    try:
        import psycopg  # type: ignore
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT surface::text, role::text, left(text::text, 300), at
                      FROM thread
                     ORDER BY at DESC
                     LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
    except Exception:
        return []
    return [{"surface": row[0], "role": row[1], "text": row[2], "at": stringify_time(row[3])} for row in rows]


def _load_claude_token() -> None:
    """Load CLAUDE_CODE_OAUTH_TOKEN from /root/.config/fpai/claude.env if not set."""
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return
    env_file = Path("/root/.config/fpai/claude.env")
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        if line.startswith("CLAUDE_CODE_OAUTH_TOKEN="):
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = line.split("=", 1)[1].strip()
            break


def main(argv: list[str] | None = None) -> int:
    _load_claude_token()
    parser = argparse.ArgumentParser(description="Run the council self-diagnostic dialogue.")
    parser.add_argument("--trigger-name", action="store_true", help="print trigger name if a diagnostic is due")
    parser.add_argument("--queue-empty", choices=("0", "1"), default="0")
    parser.add_argument("--last-diagnostic-file", type=Path, default=DEFAULT_LAST_DIAGNOSTIC)
    parser.add_argument("--queue-empty-since-file", type=Path, default=DEFAULT_QUEUE_EMPTY_SINCE)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    args = parser.parse_args(argv)
    if args.trigger_name:
        decision = trigger_from_files(
            queue_empty=args.queue_empty == "1",
            last_diagnostic_file=args.last_diagnostic_file,
            queue_empty_since_file=args.queue_empty_since_file,
            ops_ledger=args.ops_ledger,
        )
        if decision.should_run and decision.trigger:
            print(decision.trigger)
        return 0
    specs = run_diagnostic_dialogue(ops_ledger=args.ops_ledger, last_diagnostic_file=args.last_diagnostic_file)
    print(json.dumps(specs, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
