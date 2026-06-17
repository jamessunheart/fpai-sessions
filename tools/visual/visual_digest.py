#!/usr/bin/env python3
"""Render and send the FPOS daily visual pulse.

The tool reads current repo/server state, renders the deterministic HTML
template, turns it into a PNG with headless browser tooling when available,
sends the PNG to Telegram, and appends one artifact row to the ops ledger.
"""
from __future__ import annotations

import argparse
import asyncio
import html
import inspect
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo

from tools.public_private_boundary import boundary as data_boundary

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_OUTPUT_ROOT = Path(os.environ.get("VISUAL_DIGEST_OUTPUT_ROOT", "/opt/fpai-build/visuals"))
DEFAULT_TEMPLATE = REPO_ROOT / "tools" / "visual" / "templates" / "daily_pulse.html"
DEFAULT_REGISTRY = REPO_ROOT / "core" / "BUILD" / "REGISTRY.json"
DEFAULT_SPECS_DIR = REPO_ROOT / "core" / "BUILD" / "specs"
DEFAULT_RESULTS_DIR = REPO_ROOT / "core" / "BUILD" / "results"
DEFAULT_ALIGNMENT = REPO_ROOT / "core" / "STATE" / "identity" / "ALIGNMENT.md"
ATHENS = ZoneInfo("Europe/Athens")
PROOF_EVENTS = {"merged", "deployed"}
PUBLIC_CHANNEL_ENV = ("VISUAL_DIGEST_PUBLIC_CHANNEL_ID", "CORA_PUBLIC_CHANNEL_ID", "TELEGRAM_PUBLIC_CHANNEL_ID")
BOT_LINK_ENV = ("VISUAL_DIGEST_BOT_LINK", "ONE_CHAT_BOT_LINK", "PUBLIC_STORY_BOT_LINK")
KEY_SERVICES = [
    "fpai-build-loop",
    "fpai-council",
    "fpai-morning-digest",
    "sh-brain-tgbot",
    "sh-brain-index",
    "sh-mcp-http",
]

log = logging.getLogger("visual_digest")

RAW_DECISION_ID_RE = re.compile(r"\b(?:d\d{2,}|decision[_ -]?id|SPEC_d\d+[A-Za-z0-9_-]*)\b", re.IGNORECASE)
CREDENTIAL_RE = re.compile(
    r"(?i)\b("
    r"api[_ -]?key|auth[_ -]?token|bot[_ -]?token|bearer|credential|database_url|db_url|"
    r"password|passwd|secret|private[_ -]?key|session[_ -]?cookie|telegram_bot_token"
    r")\b"
)
CORRECTION_RE = re.compile(r"(?i)\b(correction|corrections|you forgot|you said)\b")
MONEY_RE = re.compile(
    r"(?i)([$€£]\s?\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s?(?:usd|usdc|eur|gbp|sol|btc|eth)\b)"
)
WALLET_RE = re.compile(r"\b(?:0x[a-fA-F0-9]{24,}|[1-9A-HJ-NP-Za-km-z]{32,44})\b")
URL_RE = re.compile(r"https?://[^\s<>()]+")


@dataclass(frozen=True)
class DigestResult:
    png_path: Path | None
    html_path: Path | None
    rendered: bool
    sent: bool
    logged: bool
    public_sent: bool = False
    skipped: bool = False


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_jsonl(path: Path, *, since: datetime | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since:
                row_time = parse_time(row.get("ts") or row.get("timestamp") or row.get("created_at"))
                if row_time and row_time < since:
                    continue
            rows.append(row)
    return rows


def load_ops_state(path: Path = DEFAULT_OPS_LEDGER, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or utc_now()
    rows = read_jsonl(path, since=current - timedelta(hours=24))
    by_type: dict[str, int] = {}
    for row in rows:
        event_type = str(row.get("type") or row.get("event") or "unknown")
        by_type[event_type] = by_type.get(event_type, 0) + 1
    proof_count = sum(1 for row in rows if str(row.get("type") or row.get("event")) in PROOF_EVENTS)
    return {"events": rows, "event_count": len(rows), "by_type": by_type, "proof_count": proof_count}


def load_top_three(path: Path = DEFAULT_ALIGNMENT) -> list[str]:
    fallback = [
        "Keep James upstream; route build details downstream.",
        "Prefer measured proof over self-talk.",
        "Surface the next clean move, not a broad backlog.",
    ]
    if not path.exists():
        return fallback
    lines = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = raw.strip()
        if not text:
            continue
        if text.startswith(("-", "*")):
            item = text.lstrip("-* ").strip()
            if item and not item.startswith("[["):
                lines.append(item[:140])
        elif text.startswith("#") and len(text.lstrip("# ").strip()) > 4:
            lines.append(text.lstrip("# ").strip()[:140])
        if len(lines) >= 3:
            return lines
    return (lines + fallback)[:3]


def load_open_decisions(limit: int = 6) -> dict[str, Any]:
    rows = _load_open_decisions_from_db(limit)
    return {"count": len(rows), "items": rows[:limit]}


def _load_open_decisions_from_db(limit: int) -> list[dict[str, str]]:
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        return []
    try:
        import psycopg  # type: ignore
    except ImportError:
        log.warning("psycopg unavailable; skipping brain_index.decisions read")
        return []
    sql = """
        SELECT COALESCE(id::text, decision_id::text, '') AS id,
               COALESCE(title, topic, question, summary, '') AS title,
               COALESCE(status::text, state::text, '') AS status
          FROM brain_index.decisions
         WHERE lower(COALESCE(status::text, state::text, 'open')) IN ('open', 'awaiting', 'pending')
         ORDER BY COALESCE(updated_at, created_at, NOW()) DESC
         LIMIT %s
    """
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (limit,))
                return [
                    {"id": str(row[0] or ""), "title": str(row[1] or "Untitled decision")[:120], "status": str(row[2] or "open")}
                    for row in cur.fetchall()
                ]
    except Exception as exc:
        log.warning("brain_index.decisions read skipped: %s", exc)
        return []


def load_build_state(
    registry_path: Path = DEFAULT_REGISTRY,
    specs_dir: Path = DEFAULT_SPECS_DIR,
    results_dir: Path = DEFAULT_RESULTS_DIR,
) -> dict[str, Any]:
    registry = _read_json(registry_path)
    builds = list(registry.get("active_builds") or []) if isinstance(registry, dict) else []
    building = [b for b in builds if b.get("status") == "building"]
    recently_merged = [b for b in builds if b.get("status") == "merged"][:5]
    done = {Path(str(b.get("spec", ""))).stem for b in builds if b.get("status") in {"done", "merged"}}
    result_ids = {p.name.removesuffix(".result.md") for p in results_dir.glob("*.result.md")} if results_dir.exists() else set()
    queued = []
    if specs_dir.exists():
        for spec in sorted(specs_dir.glob("*.md")):
            sid = spec.stem
            if sid not in done and sid not in result_ids:
                queued.append({"id": sid, "path": str(spec)})
    return {
        "currently_building": [{"id": b.get("id") or b.get("slug"), "branch": b.get("branch")} for b in building[:5]],
        "recently_merged": [{"id": b.get("id") or b.get("slug"), "branch": b.get("branch")} for b in recently_merged],
        "queued": queued[:8],
        "queued_count": len(queued),
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def load_server_health(services: Iterable[str] = KEY_SERVICES) -> list[dict[str, str]]:
    out = []
    for service in services:
        state = service_state(service)
        out.append({"name": service, "state": state, "ok": state == "active"})
    return out


def service_state(service: str) -> str:
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return "unknown"
    try:
        result = subprocess.run(
            [systemctl, "is-active", service],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return (result.stdout or result.stderr or "unknown").strip() or "unknown"


def next_move(build_state: dict[str, Any], decisions: dict[str, Any], health: list[dict[str, str]]) -> str:
    red = [svc["name"] for svc in health if not svc["ok"]]
    if red:
        return f"Check service health: {red[0]}"
    if decisions.get("count"):
        return "Resolve the oldest awaiting decision or apply its safe default."
    if build_state.get("queued_count"):
        return "Review the next queued build for merge readiness."
    return "Hold the loop steady and wait for the next real signal."


def _first_env(names: Iterable[str]) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def is_public_sensitive(text: str) -> bool:
    """Reject strings that should not appear on the public story feed."""
    return data_boundary.classify_text(text).lane in {"private", "sensitive"}


def sanitize_public_text(text: Any) -> str | None:
    """Return a public-safe text fragment, or None if the fragment is unsafe."""
    clean = data_boundary.sanitize_public_text(text, escape=True)
    if clean is None:
        return None
    return clean[:180].strip()


def public_bot_link() -> str | None:
    link = _first_env(BOT_LINK_ENV)
    if not link:
        return None
    clean = " ".join(link.split())
    if data_boundary.classify_text(clean).lane == "sensitive":
        return None
    lowered = clean.lower()
    if not (lowered.startswith("https://t.me/") or lowered.startswith("http://t.me/") or lowered.startswith("t.me/") or clean.startswith("@")):
        return None
    return html.escape(clean[:120], quote=True)


def public_digest_context(context: dict[str, Any]) -> dict[str, Any]:
    """Reduce the private visual digest context to a public-safe summary shape."""
    health = list(context.get("server_health") or [])
    ok_count = sum(1 for svc in health if svc.get("ok"))
    service_count = len(health)
    top_three: list[str] = []
    for item in context.get("top_three") or []:
        safe = sanitize_public_text(item)
        if safe:
            top_three.append(safe)
        if len(top_three) >= 3:
            break
    if not top_three:
        top_three = [
            "Free observation first.",
            "Visible proof over private claims.",
            "A working life system should show its fruits.",
        ]
    build_state = context.get("build_state") or {}
    next_public = sanitize_public_text(context.get("next_move")) or "The loop is holding the next clean move."
    return {
        "date": sanitize_public_text(context.get("date")) or "Today",
        "proof_today": int(context.get("proof_today") or 0),
        "active_builds": len(build_state.get("currently_building") or []),
        "queued_count": int(build_state.get("queued_count") or 0),
        "services_green": ok_count,
        "services_watched": service_count,
        "top_three": top_three,
        "next_move": next_public,
        "bot_link": public_bot_link(),
    }


def render_public_summary(context: dict[str, Any]) -> str:
    public = public_digest_context(context)
    lines = [
        "<b>Cora Nation story feed</b>",
        f"{public['date']}",
        "",
        "A public glimpse of the Full Potential OS loop:",
        f"Proof events today: {public['proof_today']}",
        f"Builds moving: {public['active_builds']} active / {public['queued_count']} queued",
        f"System pulse: {public['services_green']} of {public['services_watched']} watched services green",
        "",
        "<b>What the system is practicing</b>",
    ]
    lines.extend(f"- {item}" for item in public["top_three"])
    lines.extend(["", f"<b>Next visible move</b>: {public['next_move']}"])
    if public.get("bot_link"):
        lines.extend(["", f"Get this for your life: {public['bot_link']}"])
    return "\n".join(lines)


def validate_public_summary(text: str) -> None:
    try:
        data_boundary.validate_public_text(text)
    except ValueError as exc:
        raise ValueError(f"public digest failed privacy filter: {exc}") from exc


def build_context(
    *,
    now: datetime | None = None,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    alignment_path: Path = DEFAULT_ALIGNMENT,
    registry_path: Path = DEFAULT_REGISTRY,
    specs_dir: Path = DEFAULT_SPECS_DIR,
    results_dir: Path = DEFAULT_RESULTS_DIR,
) -> dict[str, Any]:
    current_utc = now or utc_now()
    athens = current_utc.astimezone(ATHENS)
    ops = load_ops_state(ops_ledger, now=current_utc)
    decisions = load_open_decisions()
    build = load_build_state(registry_path, specs_dir, results_dir)
    health = load_server_health()
    return {
        "generated_at": athens.strftime("%Y-%m-%d %H:%M %Z"),
        "date": athens.strftime("%A, %Y-%m-%d"),
        "top_three": load_top_three(alignment_path),
        "open_decisions": decisions,
        "build_state": build,
        "server_health": health,
        "proof_today": ops["proof_count"],
        "event_count": ops["event_count"],
        "next_move": next_move(build, decisions, health),
    }


def render_template(context: dict[str, Any], template_path: Path = DEFAULT_TEMPLATE) -> str:
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError as exc:
        raise RuntimeError("Jinja2 is required to render the visual digest template") from exc
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template(template_path.name).render(**context)


def output_path(output_root: Path = DEFAULT_OUTPUT_ROOT, *, now: datetime | None = None) -> Path:
    current = (now or utc_now()).astimezone(ATHENS)
    directory = output_root / current.strftime("%Y-%m-%d")
    return directory / f"daily_pulse_{current.strftime('%H-%M')}.png"


def render_html_to_png(html: str, png_path: Path) -> bool:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as handle:
        handle.write(html)
        html_file = Path(handle.name)
    try:
        return _render_with_chromium(html_file, png_path) or _render_with_wkhtmltoimage(html_file, png_path)
    finally:
        html_file.unlink(missing_ok=True)


def _render_with_chromium(html_file: Path, png_path: Path) -> bool:
    binary = next((shutil.which(name) for name in ("chromium-browser", "chromium", "google-chrome") if shutil.which(name)), None)
    if not binary:
        log.warning("chromium headless not available; trying fallback renderer")
        return False
    cmd = [
        binary,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1200,1600",
        f"--screenshot={png_path}",
        html_file.as_uri(),
    ]
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=45)
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("chromium render failed: %s", exc)
        return False
    if result.returncode != 0:
        log.warning("chromium render failed: %s", (result.stderr or result.stdout).strip()[:300])
        return False
    return png_path.exists() and png_path.stat().st_size > 0


def _render_with_wkhtmltoimage(html_file: Path, png_path: Path) -> bool:
    binary = shutil.which("wkhtmltoimage")
    if not binary:
        log.warning("wkhtmltoimage fallback not available; skipping render")
        return False
    cmd = [binary, "--width", "1200", str(html_file), str(png_path)]
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=45)
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("wkhtmltoimage render failed: %s", exc)
        return False
    if result.returncode != 0:
        log.warning("wkhtmltoimage render failed: %s", (result.stderr or result.stdout).strip()[:300])
        return False
    return png_path.exists() and png_path.stat().st_size > 0


async def send_to_telegram(png_path: Path, send_func: Callable[..., Any] | None = None) -> bool:
    sender = send_func or _default_sender()
    if not sender:
        log.warning("Telegram sender unavailable; skipped send")
        return False
    result = sender(str(png_path))
    if inspect.isawaitable(result):
        result = await result
    return bool(result)


async def send_public_story(text: str, *, channel_id: str, send_func: Callable[..., Any] | None = None) -> bool:
    validate_public_summary(text)
    sender = send_func or _default_text_sender()
    if not sender:
        log.warning("Telegram text sender unavailable; skipped public story feed send")
        return False
    result = sender(text, chat_id=channel_id)
    if inspect.isawaitable(result):
        result = await result
    return bool(result)


def _default_sender() -> Callable[..., Any] | None:
    telegram = _load_curator_telegram()
    if not telegram:
        return None
    if hasattr(telegram, "send_photo"):
        return getattr(telegram, "send_photo")
    token = getattr(telegram, "BOT_TOKEN", None) or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = getattr(telegram, "CHAT_ID", None) or os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("OWNER_TG_ID")
    if token and chat_id:
        return lambda path: _send_photo_direct(path, token=token, chat_id=chat_id)
    if hasattr(telegram, "send"):
        return getattr(telegram, "send")
    return None


def _default_text_sender() -> Callable[..., Any] | None:
    telegram = _load_curator_telegram()
    if telegram and hasattr(telegram, "send"):
        token = getattr(telegram, "BOT_TOKEN", None) or os.environ.get("TELEGRAM_BOT_TOKEN")
        if token:
            return lambda text, *, chat_id: _send_text_direct(text, token=token, chat_id=chat_id)
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        return lambda text, *, chat_id: _send_text_direct(text, token=token, chat_id=chat_id)
    return None


def _load_curator_telegram() -> Any | None:
    service_root = REPO_ROOT / "SERVICES" / "sunheart-brain"
    if str(service_root) not in sys.path:
        sys.path.insert(0, str(service_root))
    try:
        from curator import telegram
    except Exception as exc:
        log.warning("curator.telegram unavailable: %s", exc)
        return None
    return telegram


async def _send_photo_direct(path: str, *, token: str, chat_id: str) -> bool:
    try:
        import httpx
    except ImportError:
        log.warning("httpx unavailable; skipped Telegram photo send")
        return False
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(path, "rb") as image:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, data={"chat_id": chat_id}, files={"photo": (Path(path).name, image, "image/png")})
        if response.status_code != 200:
            log.warning("Telegram sendPhoto failed %s: %s", response.status_code, response.text[:300])
            return False
        return True
    except Exception as exc:
        log.warning("Telegram sendPhoto error: %s", exc)
        return False


async def _send_text_direct(text: str, *, token: str, chat_id: str) -> bool:
    try:
        import httpx
    except ImportError:
        log.warning("httpx unavailable; skipped Telegram message send")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
            )
        if response.status_code != 200:
            log.warning("Telegram public story send failed %s: %s", response.status_code, response.text[:300])
            return False
        return True
    except Exception as exc:
        log.warning("Telegram public story send error: %s", exc)
        return False


def log_visual_digest(path: Path, ledger: Path = DEFAULT_OPS_LEDGER) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": "visual_digest",
        "event": "visual_digest",
        "path": str(path),
        "loop": "visual_digest",
        "cost": "$0",
    }
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def log_public_story_digest(*, sent: bool, ledger: Path = DEFAULT_OPS_LEDGER) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": "public_story_digest",
        "event": "public_story_digest",
        "loop": "visual_digest",
        "sent": bool(sent),
        "cost": "$0",
    }
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


async def run(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    render_func: Callable[[str, Path], bool] = render_html_to_png,
    send_func: Callable[..., Any] | None = None,
    public_send_func: Callable[..., Any] | None = None,
    public_channel_id: str | None = None,
    public_enabled: bool = True,
    write_html: bool = False,
) -> DigestResult:
    if os.environ.get("VISUAL_DIGEST_DISABLE") == "1":
        log.info("visual digest disabled by VISUAL_DIGEST_DISABLE=1")
        return DigestResult(None, None, False, False, False, skipped=True)
    context = build_context(ops_ledger=ops_ledger)
    html = render_template(context)
    png_path = output_path(output_root)
    html_path = png_path.with_suffix(".html") if write_html else None
    if html_path:
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html, encoding="utf-8")
    rendered = bool(render_func(html, png_path))
    if not rendered:
        return DigestResult(None, html_path, False, False, False)
    sent = await send_to_telegram(png_path, send_func)
    public_sent = False
    public_target = public_channel_id or (_first_env(PUBLIC_CHANNEL_ENV) if public_enabled else None)
    if public_enabled and public_target and os.environ.get("VISUAL_DIGEST_PUBLIC_DISABLE") != "1":
        public_text = render_public_summary(context)
        public_sent = await send_public_story(public_text, channel_id=public_target, send_func=public_send_func)
        log_public_story_digest(sent=public_sent, ledger=ops_ledger)
    log_visual_digest(png_path, ops_ledger)
    return DigestResult(png_path, html_path, True, sent, True, public_sent=public_sent)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render and send the FPOS daily visual pulse PNG.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--ops-ledger", default=str(DEFAULT_OPS_LEDGER))
    parser.add_argument("--write-html", action="store_true")
    parser.add_argument("--no-send", action="store_true", help="Render and log without Telegram sends.")
    parser.add_argument("--public-channel-id", default=None, help="Optional public Telegram channel id/handle for the curated Cora Nation story summary.")
    parser.add_argument("--no-public", action="store_true", help="Do not send the curated public story summary.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    args = parse_args(argv or sys.argv[1:])
    send_func = (lambda _path: True) if args.no_send else None
    public_channel_id = None if args.no_public or args.no_send else args.public_channel_id
    result = asyncio.run(
        run(
            output_root=Path(args.output_root),
            ops_ledger=Path(args.ops_ledger),
            send_func=send_func,
            public_channel_id=public_channel_id,
            public_enabled=not args.no_public and not args.no_send,
            write_html=args.write_html,
        )
    )
    if result.skipped:
        print("visual digest disabled")
        return 0
    if not result.rendered:
        print("visual digest render skipped; no headless renderer available")
        return 0
    print(json.dumps({"png": str(result.png_path), "sent": result.sent, "public_sent": result.public_sent, "logged": result.logged}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
