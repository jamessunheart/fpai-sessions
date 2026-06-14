#!/usr/bin/env python3
"""
brain-ingest — ingest notes from Bear / ChatGPT / Claude / Cursor transcripts
into the Sunheart Brain.

Runs from your Mac. Talks to brain-index and sh-mcp over HTTPS.

Examples:
    # Dry-run: count what WOULD be imported from every enabled source
    ./brain_ingest.py dry-run --all

    # Pull Bear only, with a progress bar
    ./brain_ingest.py run --source bear

    # Pull everything
    ./brain_ingest.py run --all

    # PDFs + markdown/text from a folder (Google Drive sync → same folder works)
    ./brain_ingest.py dry-run --source papers
    ./brain_ingest.py run --source papers

    # Re-import a specific source from scratch (clears dedup flags first)
    ./brain_ingest.py run --source chatgpt --reembed

Environment (or .env beside this file):
    SH_BRAIN_BASE        https://brain.sunheart.com
    SH_INGEST_TOKEN      (bearer token with ingest permission)
    SH_DATA_DIR          ~/SunheartBrainData (where ChatGPT/Claude exports live)
    SH_PAPERS_DIR        ~/SunheartBrainData/papers (PDF / .md / .txt for --source papers)
    SH_BEAR_TAG_OPT_IN   if set (e.g. brain), only Bear notes that contain #brain are ingested
    SH_CLAUDE_CONVERSATIONS_JSON  optional explicit path to Claude export conversations.json
    OPENAI_API_KEY       optional — enables `--prefer openai` embeddings
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from itertools import islice
from typing import Callable, Iterator

import click
import httpx
from dateutil import parser as dateparser
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from filters import classify

SOURCE_DEFAULT_SENSITIVITY = {
    "bear":    "🟡 Personal",
    "papers":  "🟡 Personal",
    "chatgpt": "🟢 Public",
    "claude":  "🟡 Personal",  # exports often contain private context; promote with #public in text if needed
    "cursor":  "🟢 Public",
}

console = Console()

_ENV_FILE = Path(__file__).with_name(".env")
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

BRAIN_BASE    = os.environ.get("SH_BRAIN_BASE", "https://brain.sunheart.com")
INGEST_TOKEN  = os.environ.get("SH_INGEST_TOKEN")
DATA_DIR      = Path(os.environ.get("SH_DATA_DIR", "~/SunheartBrainData")).expanduser()
PAPERS_DIR    = Path(os.environ.get("SH_PAPERS_DIR", str(DATA_DIR / "papers"))).expanduser()

BEAR_DB = Path(
    "~/Library/Group Containers/9K33E3U3T4.net.shinyfrog.bear/Application Data/database.sqlite"
).expanduser()

# If set (e.g. "brain"), only Bear notes whose body contains that #tag are ingested. Empty = all notes (still subject to classify / skip tags).
BEAR_TAG_OPT_IN = os.environ.get("SH_BEAR_TAG_OPT_IN", "").strip().lower().lstrip("#")


# ---------------------------------------------------------------------------
# Unified note record
# ---------------------------------------------------------------------------

@dataclass
class Note:
    source: str                  # "Bear" | "ChatGPT" | "Claude" | "Cursor"
    source_id: str               # stable external id (Bear uuid, chat_id + msg_idx, …)
    title: str
    content: str
    created_at: datetime | None
    tags: list[str]
    source_url: str | None
    note_type: str               # "User Message" | "AI Response" | "Journal" | "Snippet" | …
    conversation_external_id: str | None = None  # links to 03 · Conversations
    conversation_source: str | None = None
    conversation_title: str | None = None
    conversation_started_at: datetime | None = None

    def fingerprint(self) -> str:
        return hashlib.sha1(f"{self.source}|{self.source_id}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# Source adapters — each yields Note records
# ---------------------------------------------------------------------------

def bear_adapter() -> Iterator[Note]:
    if not BEAR_DB.exists():
        console.print(f"[yellow]Bear DB not found at {BEAR_DB} — skipping[/yellow]")
        return
    if BEAR_TAG_OPT_IN:
        console.print(
            f"[cyan]Bear: only notes tagged #{BEAR_TAG_OPT_IN} (set SH_BEAR_TAG_OPT_IN empty to ingest all)[/cyan]"
        )
    con = sqlite3.connect(f"file:{BEAR_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    # Bear's schema: ZSFNOTE table. ZTRASHED=0 excludes trash.
    q = """
        SELECT n.ZUNIQUEIDENTIFIER as uuid,
               n.ZTITLE            as title,
               n.ZTEXT             as text,
               n.ZCREATIONDATE     as created,
               n.ZMODIFICATIONDATE as modified
          FROM ZSFNOTE n
         WHERE n.ZTRASHED = 0
           AND n.ZARCHIVED = 0
    """
    for r in con.execute(q):
        if not (r["text"] or "").strip():
            continue
        # Bear timestamps are Core Data epoch (seconds since 2001-01-01 UTC).
        created = None
        if r["created"]:
            created = datetime(2001, 1, 1, tzinfo=timezone.utc).fromtimestamp(
                978307200 + float(r["created"]), tz=timezone.utc
            )
        # Tags are inline (#tag #nested/tag) — extract via regex.
        tags = re.findall(r"(?:^|\s)#([\w\-\/]+)", r["text"] or "")
        if BEAR_TAG_OPT_IN:
            tl = {t.lower() for t in tags}
            nested = any(t.lower().startswith(BEAR_TAG_OPT_IN + "/") for t in tags)
            if BEAR_TAG_OPT_IN not in tl and not nested:
                continue
        yield Note(
            source="Bear",
            source_id=r["uuid"],
            title=(r["title"] or "").strip() or (r["text"][:80]),
            content=r["text"] or "",
            created_at=created,
            tags=sorted(set(tags)),
            source_url=f"bear://x-callback-url/open-note?id={r['uuid']}",
            note_type="Journal",
        )
    con.close()


def chatgpt_adapter(export_path: Path | None = None) -> Iterator[Note]:
    p = export_path or (DATA_DIR / "chatgpt-export" / "conversations.json")
    if not p.exists():
        console.print(f"[yellow]ChatGPT export not found at {p} — skipping[/yellow]")
        return
    data = json.loads(p.read_text())
    for conv in data:
        chat_id    = conv.get("id", "")
        chat_title = conv.get("title", "Untitled")
        created    = _ts(conv.get("create_time"))
        # Walk the message tree
        mapping = conv.get("mapping", {})
        for node_id, node in mapping.items():
            msg = node.get("message")
            if not msg:
                continue
            parts = msg.get("content", {}).get("parts", []) or []
            text = "\n\n".join(str(p) for p in parts if p).strip()
            if not text:
                continue
            role   = msg.get("author", {}).get("role", "user")
            msg_id = msg.get("id", node_id)
            when   = _ts(msg.get("create_time"))
            yield Note(
                source="ChatGPT",
                source_id=f"{chat_id}:{msg_id}",
                title=f"{chat_title} — {role}",
                content=text,
                created_at=when,
                tags=[],
                source_url=f"https://chat.openai.com/c/{chat_id}",
                note_type="User Message" if role == "user" else "AI Response",
                conversation_external_id=chat_id,
                conversation_source="ChatGPT",
                conversation_title=chat_title,
                conversation_started_at=created,
            )


def _claude_conversations_json_path() -> Path | None:
    """Resolve Claude export: env override → claude-export/ → SunheartBrainData/clde/**/conversations.json."""
    env = (os.environ.get("SH_CLAUDE_CONVERSATIONS_JSON") or "").strip()
    if env:
        p = Path(env).expanduser()
        return p if p.exists() else None
    p = DATA_DIR / "claude-export" / "conversations.json"
    if p.exists():
        return p
    clde = DATA_DIR / "clde"
    if clde.is_dir():
        found = sorted(clde.rglob("conversations.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        if found:
            return found[0]
    return None


def claude_adapter(export_path: Path | None = None) -> Iterator[Note]:
    p = export_path or _claude_conversations_json_path()
    if not p or not p.exists():
        console.print(
            f"[yellow]Claude export not found — set SH_CLAUDE_CONVERSATIONS_JSON or add "
            f"{DATA_DIR / 'claude-export' / 'conversations.json'} or {DATA_DIR / 'clde'}/…/conversations.json[/yellow]"
        )
        return
    console.print(f"[dim]Claude export: {p}[/dim]")

    def _yield_from_conv(conv: dict) -> Iterator[Note]:
        chat_id = conv.get("uuid", "")
        chat_title = conv.get("name") or "Untitled"
        created = _ts(conv.get("created_at"))
        for m in conv.get("chat_messages") or []:
            text = (m.get("text") or "").strip()
            if not text:
                continue
            sender = m.get("sender", "human")
            msg_id = m.get("uuid", "")
            when = _ts(m.get("created_at"))
            yield Note(
                source="Claude",
                source_id=f"{chat_id}:{msg_id}",
                title=f"{chat_title} — {sender}",
                content=text,
                created_at=when,
                tags=[],
                source_url=f"https://claude.ai/chat/{chat_id}",
                note_type="User Message" if sender == "human" else "AI Response",
                conversation_external_id=chat_id,
                conversation_source="Claude",
                conversation_title=chat_title,
                conversation_started_at=created,
            )

    # Large exports (~300MB JSON): stream root array so dry-run --limit stays fast.
    try:
        import ijson
        with p.open("rb") as f:
            for conv in ijson.items(f, "item"):
                if not isinstance(conv, dict):
                    continue
                yield from _yield_from_conv(conv)
    except ImportError:
        data = json.loads(p.read_text())
        for conv in data:
            yield from _yield_from_conv(conv)


def cursor_adapter(transcripts_root: Path | None = None) -> Iterator[Note]:
    """Walks ~/.cursor/projects/*/agent-transcripts/*.jsonl. Each .jsonl is one
    chat session; lines are {role, content, ...}."""
    root = transcripts_root or Path("~/.cursor/projects").expanduser()
    if not root.exists():
        console.print(f"[yellow]Cursor projects dir not found at {root} — skipping[/yellow]")
        return
    # Layout: <project>/agent-transcripts/<uuid>/<uuid>.jsonl
    # (subagents live under .../<uuid>/subagents/*.jsonl — we skip them;
    # AGENTS.md says to cite only parent uuids.)
    for jsonl in root.glob("*/agent-transcripts/*/*.jsonl"):
        if jsonl.parent.name == "subagents" or jsonl.stem != jsonl.parent.name:
            continue
        chat_id = jsonl.stem
        project_name = jsonl.parent.parent.parent.name
        chat_title = f"Cursor · {project_name} · {chat_id[:8]}"
        started = datetime.fromtimestamp(jsonl.stat().st_mtime, tz=timezone.utc)
        try:
            idx = 0
            for line in jsonl.read_text(errors="ignore").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                role = rec.get("role") or rec.get("type") or "user"
                content = rec.get("content") or rec.get("text") or rec.get("message") or ""
                if isinstance(content, list):
                    content = "\n".join(
                        c.get("text", "") if isinstance(c, dict) else str(c)
                        for c in content
                    )
                content = str(content).strip()
                if not content:
                    continue
                idx += 1
                yield Note(
                    source="Cursor",
                    source_id=f"{chat_id}:{idx}",
                    title=f"{chat_title} — {role}",
                    content=content,
                    created_at=started,
                    tags=["cursor"],
                    source_url=None,
                    note_type="User Message" if role in ("user", "human") else "AI Response",
                    conversation_external_id=chat_id,
                    conversation_source="Cursor",
                    conversation_title=chat_title,
                    conversation_started_at=started,
                )
        except Exception as e:
            console.print(f"[red]failed to read {jsonl}: {e}[/red]")


# Max characters sent per file (AppFlowy / index also cap; keep one note per file).
PAPERS_MAX_CHARS = int(os.environ.get("SH_PAPERS_MAX_CHARS", "200000"))

_SKIP_DIR_PARTS = frozenset({
    ".git", "node_modules", ".venv", "__pycache__", ".Trash",
    "System Volume Information",
})


def _papers_path_skipped(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    for part in rel.parts:
        if part in _SKIP_DIR_PARTS or part.startswith("."):
            return True
    return False


def _extract_pdf_text(path: Path) -> str | None:
    try:
        import fitz  # pymupdf
    except ImportError:
        console.print("[red]pymupdf not installed — run: pip install -r requirements.txt[/red]")
        return None
    try:
        doc = fitz.open(path)
        try:
            chunks: list[str] = []
            for i in range(len(doc)):
                chunks.append(doc.load_page(i).get_text() or "")
        finally:
            doc.close()
        text = "\n\n".join(chunks).strip()
        return text or None
    except Exception as e:
        console.print(f"[yellow]PDF unreadable {path.name}: {e}[/yellow]")
        return None


def _read_text_file(path: Path) -> str | None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        return raw.strip() or None
    except Exception as e:
        console.print(f"[yellow]text unreadable {path.name}: {e}[/yellow]")
        return None


def _title_from_markdown(content: str, fallback: str) -> str:
    for line in content.splitlines()[:30]:
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()[:200] or fallback
    return fallback


def papers_adapter() -> Iterator[Note]:
    """Walk SH_PAPERS_DIR (default: ~/SunheartBrainData/papers) for .pdf, .md, .txt.

    One Note per file. ``source_id`` is stable per absolute path so re-runs dedupe.
    Use Google Drive for Desktop: point SH_PAPERS_DIR at a synced folder.
    """
    root = PAPERS_DIR
    if not root.is_dir():
        console.print(
            f"[yellow]Papers folder not found: {root} — create it or set SH_PAPERS_DIR[/yellow]"
        )
        return

    exts = {".pdf", ".md", ".markdown", ".txt"}
    paths = sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in exts and not _papers_path_skipped(p, root)
    )
    for path in paths:
        suffix = path.suffix.lower()
        rel = path.relative_to(root).as_posix()
        source_id = "papers:" + hashlib.sha1(str(path.resolve()).encode()).hexdigest()

        if suffix == ".pdf":
            body = _extract_pdf_text(path)
            title = path.stem
            extra_tags: list[str] = ["papers", "pdf"]
        elif suffix in (".md", ".markdown"):
            body = _read_text_file(path)
            title = path.stem
            if body:
                title = _title_from_markdown(body, path.stem)
            extra_tags = ["papers", "markdown"]
        else:  # .txt
            body = _read_text_file(path)
            title = path.stem
            extra_tags = ["papers", "text"]

        if not body:
            continue

        if len(body) > PAPERS_MAX_CHARS:
            tail = "\n\n---\n*(truncated after %d chars; open original file for full text)*" % PAPERS_MAX_CHARS
            body = body[: PAPERS_MAX_CHARS - len(tail)] + tail

        tag_set = set(extra_tags)
        tag_set.update(re.findall(r"(?:^|\s)#([\w\-\/]+)", body))
        tags = sorted(tag_set)

        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except OSError:
            mtime = None

        yield Note(
            source="Manual",
            source_id=source_id,
            title=title[:200],
            content=(
                f"**File:** `{rel}`\n\n"
                + body
            ),
            created_at=mtime,
            tags=tags,
            source_url=path.resolve().as_uri(),
            note_type="Reference",
        )


ADAPTERS: dict[str, Callable[[], Iterator[Note]]] = {
    "bear":    bear_adapter,
    "papers":  papers_adapter,
    "chatgpt": chatgpt_adapter,
    "claude":  claude_adapter,
    "cursor":  cursor_adapter,
}


def _ts(v) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(float(v), tz=timezone.utc)
    if isinstance(v, str):
        try:
            return dateparser.parse(v).astimezone(timezone.utc)
        except Exception:
            return None
    return None


# ---------------------------------------------------------------------------
# Brain client (talks to /mcp/messages/ + /index/ over HTTPS)
# ---------------------------------------------------------------------------

class BrainClient:
    def __init__(self, base: str, token: str):
        self.base = base.rstrip("/")
        self.token = token
        self.http = httpx.Client(
            timeout=120,
            headers={"Authorization": f"Bearer {token}"},
        )
        self._conversations: dict[str, str] = {}   # external_id -> appflowy_row_id

    def close(self):
        self.http.close()

    def add_note(self, n: Note, classification, conversation_row_id: str | None = None) -> str:
        payload = {
            "source": n.source,
            "source_id": n.source_id,
            "title": n.title,
            "content": n.content,
            "tags": n.tags,
            "note_type": n.note_type,
            "source_url": n.source_url,
            "original_created_at": n.created_at.isoformat() if n.created_at else None,
            "conversation_row_id": conversation_row_id,
            # Force local embeddings for anything 🟡 Personal; Public can use provider default.
            "prefer": "local" if classification.sensitivity != "🟢 Public" else "local",
            "sensitivity": classification.sensitivity,
            "pii_flags": classification.pii_flags,
        }
        r = self.http.post(f"{self.base}/index/ingest/add_note", json=payload)
        r.raise_for_status()
        return r.json()["note_row_id"]

    def ensure_conversation(self, n: Note) -> str | None:
        if not n.conversation_external_id:
            return None
        ext = n.conversation_external_id
        if ext in self._conversations:
            return self._conversations[ext]
        payload = {
            "source": n.conversation_source or n.source,
            "external_id": ext,
            "title": n.conversation_title or "Untitled",
            "started_at": n.conversation_started_at.isoformat() if n.conversation_started_at else None,
        }
        r = self.http.post(f"{self.base}/index/ingest/ensure_conversation", json=payload)
        r.raise_for_status()
        row_id = r.json()["conversation_row_id"]
        self._conversations[ext] = row_id
        return row_id


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """brain-ingest — populate Sunheart Brain from your sources."""


@cli.command("dry-run")
@click.option("--source", type=click.Choice(list(ADAPTERS.keys())), default=None)
@click.option("--all", "all_", is_flag=True)
@click.option("--show-skipped", is_flag=True, help="Print title of every SKIPPED note (for review)")
@click.option("--limit", type=int, default=None, help="Max notes per source (large Claude exports)")
def dry_run(source: str | None, all_: bool, show_skipped: bool, limit: int | None):
    """Count what WOULD be imported + skip reasons. No writes."""
    sources = list(ADAPTERS.keys()) if all_ else [source] if source else []
    if not sources:
        console.print("[red]Specify --source <name> or --all[/red]")
        sys.exit(1)
    grand_total = {"ingest": 0, "personal": 0, "skip": 0}
    for s in sources:
        total = skipped = personal = public = 0
        skip_reasons: dict[str, int] = {}
        pii_reasons: dict[str, int] = {}
        console.print(f"\n[bold cyan]{s}[/bold cyan]")
        floor = SOURCE_DEFAULT_SENSITIVITY.get(s, "🟢 Public")
        gen = ADAPTERS[s]()
        note_iter = islice(gen, limit) if limit else gen
        for n in note_iter:
            total += 1
            c = classify(n.content, n.tags, default_sensitivity=floor)
            if c.decision == "skip":
                skipped += 1
                skip_reasons[c.reason] = skip_reasons.get(c.reason, 0) + 1
                if show_skipped:
                    console.print(f"  [red]SKIP[/red] {n.title[:70]!r} — {c.reason}")
            elif c.decision == "personal":
                personal += 1
                for p in c.pii_flags:
                    pii_reasons[p] = pii_reasons.get(p, 0) + 1
            else:
                public += 1
        console.print(
            f"  total={total}  "
            f"[green]🟢 public={public}[/green]  "
            f"[yellow]🟡 personal={personal}[/yellow]  "
            f"[red]🔴 skipped={skipped}[/red]"
        )
        if skip_reasons:
            console.print("  skip reasons:")
            for r, c_ in sorted(skip_reasons.items(), key=lambda x: -x[1]):
                console.print(f"    · {c_:5d}  {r}")
        if pii_reasons:
            console.print("  PII flags (→ personal tier):")
            for r, c_ in sorted(pii_reasons.items(), key=lambda x: -x[1]):
                console.print(f"    · {c_:5d}  {r}")
        grand_total["ingest"]   += public
        grand_total["personal"] += personal
        grand_total["skip"]     += skipped
    console.print("\n[bold]TOTALS[/bold]")
    console.print(f"  🟢 public   → {grand_total['ingest']:5d}   (all clients can read)")
    console.print(f"  🟡 personal → {grand_total['personal']:5d}   (local embeddings only, GPT Connector blocked)")
    console.print(f"  🔴 skipped  → {grand_total['skip']:5d}   (never leaves the laptop)")
    if show_skipped is False and grand_total["skip"] > 0:
        console.print("\n  Re-run with --show-skipped to see every skipped note's title.")


@cli.command("run")
@click.option("--source", type=click.Choice(list(ADAPTERS.keys())), default=None)
@click.option("--all", "all_", is_flag=True)
@click.option("--limit", type=int, default=None, help="Cap per source (useful for first tests)")
@click.option("--reembed", is_flag=True, help="Force re-embedding even if content_sha1 matches")
@click.option("--concurrency", type=int, default=int(os.environ.get("SH_INGEST_CONCURRENCY") or "16"),
              help="Parallel HTTP workers per source (default 16). Set 1 for old serial behavior.")
def run(source: str | None, all_: bool, limit: int | None, reembed: bool, concurrency: int):
    """For-real import. Pushes notes + embeddings to Sunheart Brain."""
    if not INGEST_TOKEN:
        console.print("[red]SH_INGEST_TOKEN not set[/red]")
        sys.exit(1)
    sources = list(ADAPTERS.keys()) if all_ else [source] if source else []
    if not sources:
        console.print("[red]Specify --source <name> or --all[/red]")
        sys.exit(1)

    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    bc = BrainClient(BRAIN_BASE, INGEST_TOKEN)
    conv_lock = threading.Lock()
    try:
        for s in sources:
            console.rule(f"[bold]{s}[/bold]")
            gen = ADAPTERS[s]()
            notes = list(islice(gen, limit)) if limit else list(gen)
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                          BarColumn(), TextColumn("{task.completed}/{task.total}"),
                          TimeElapsedColumn(), console=console) as prog:
                task = prog.add_task(f"ingest:{s}", total=max(len(notes), 1))
                errors = skipped = personal = public = 0
                floor = SOURCE_DEFAULT_SENSITIVITY.get(s, "🟢 Public")

                def _ingest_one(n):
                    """Returns (status, error_msg). status in {'skip','personal','public','error'}."""
                    try:
                        c = classify(n.content, n.tags, default_sensitivity=floor)
                        if c.decision == "skip":
                            return ("skip", None)
                        if n.conversation_external_id:
                            with conv_lock:
                                conv_id = bc.ensure_conversation(n)
                        else:
                            conv_id = None
                        bc.add_note(n, c, conversation_row_id=conv_id)
                        return ("personal" if c.decision == "personal" else "public", None)
                    except Exception as e:
                        return ("error", f"{n.source}:{n.source_id} — {e}")

                if concurrency <= 1 or len(notes) < 4:
                    for n in notes:
                        status, err = _ingest_one(n)
                        if status == "skip":     skipped += 1
                        elif status == "error":  errors += 1
                        elif status == "personal": personal += 1
                        elif status == "public": public += 1
                        if err and errors <= 5:
                            console.print(f"[red]{err}[/red]")
                        prog.advance(task)
                else:
                    with ThreadPoolExecutor(max_workers=concurrency) as pool:
                        futs = [pool.submit(_ingest_one, n) for n in notes]
                        for fut in as_completed(futs):
                            status, err = fut.result()
                            if status == "skip":     skipped += 1
                            elif status == "error":  errors += 1
                            elif status == "personal": personal += 1
                            elif status == "public": public += 1
                            if err and errors <= 5:
                                console.print(f"[red]{err}[/red]")
                            prog.advance(task)
            console.print(
                f"[green]✓[/green] {s}: "
                f"public={public} personal={personal} skipped={skipped} errors={errors}"
            )
    finally:
        bc.close()


if __name__ == "__main__":
    cli()
