"""
inbox_cmd.py — `/inbox` command handler for fp-game-bot (Veto Inbox v0.1)

Owner-only. Reads the local veto_inbox queue (on this server). Producer
side (Mac CLI) syncs items to this server via SSH push.

Usage in TG (owner only):
  /inbox                — top 10 pending sorted by leverage/min
  /inbox <category>     — filter by category
  /inbox show <id>      — full detail
  /inbox resolve <id>   — mark resolved
  /inbox veto <id>      — mark vetoed
  /inbox progress <id>  — mark in_progress
  /inbox stats          — counts snapshot
  /inbox resolved       — recent resolved

The handler shells out to veto_inbox.py — which is the SSOT module.
"""
from __future__ import annotations

import asyncio
import os
import shlex
from pathlib import Path
from typing import Optional

import httpx

INBOX_PY = os.environ.get(
    "VETO_INBOX_PY",
    "/opt/fpai/services/veto-inbox/veto_inbox.py",
)
PYTHON_BIN = os.environ.get("VETO_INBOX_PYTHON", "/usr/bin/python3")
INBOX_STATE_DIR = os.environ.get(
    "VETO_INBOX_STATE_DIR",
    "/var/lib/fpai/veto_inbox",
)


async def _run(cmd: list[str]) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "VETO_INBOX_STATE_DIR": INBOX_STATE_DIR},
    )
    out, err = await proc.communicate()
    return proc.returncode or 0, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


def esc(s) -> str:
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def cmd_inbox(client: httpx.AsyncClient, chat_id: int, args: str) -> None:
    """Owner-only inbox handler. Signature matches other cmd_* in main.py."""
    # Import here to avoid circular at module load
    from main import tg_send, is_owner  # type: ignore

    if not is_owner(chat_id):
        await tg_send(client, chat_id,
            "📥 Inbox is owner-only. (You're not the owner of this substrate.)")
        return

    if not Path(INBOX_PY).exists():
        await tg_send(client, chat_id,
            f"⚠️ Inbox engine not deployed at <code>{esc(INBOX_PY)}</code>.\n"
            f"v0.1 setup pending. Run sync script on Mac.")
        return

    args_t = (args or "").strip()
    sub = ""
    rest = ""
    if args_t:
        parts = args_t.split(None, 1)
        sub = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

    # No args → list top 10
    if not sub:
        rc, out, err = await _run([PYTHON_BIN, INBOX_PY, "list", "--limit", "10"])
        if rc != 0:
            await tg_send(client, chat_id, f"⚠️ inbox list failed: <code>{esc(err[:200])}</code>")
            return
        if out.strip() == "(inbox empty)":
            await tg_send(client, chat_id, "📥 <b>Inbox empty.</b> Nothing waiting on James.")
            return
        await tg_send(client, chat_id,
            "📥 <b>VETO INBOX — top 10 pending</b>\n\n<pre>" + esc(out) + "</pre>\n"
            "<i>/inbox show &lt;id&gt; · /inbox resolve &lt;id&gt; · /inbox &lt;cat&gt;</i>")
        return

    # /inbox show <id>
    if sub == "show":
        if not rest:
            await tg_send(client, chat_id, "Usage: <code>/inbox show &lt;id&gt;</code>")
            return
        rc, out, err = await _run([PYTHON_BIN, INBOX_PY, "show", rest.strip()])
        if rc != 0:
            await tg_send(client, chat_id, f"⚠️ not found: <code>{esc(rest)}</code>")
            return
        await tg_send(client, chat_id, f"📥 <pre>{esc(out)}</pre>")
        return

    # /inbox resolve <id> [note]
    if sub in ("resolve", "veto", "progress", "reopen"):
        if not rest:
            await tg_send(client, chat_id, f"Usage: <code>/inbox {sub} &lt;id&gt; [note...]</code>")
            return
        parts = rest.split(None, 1)
        item_id = parts[0]
        note = parts[1] if len(parts) > 1 else ""
        cmd = [PYTHON_BIN, INBOX_PY, sub, item_id]
        if note:
            cmd += ["--note", note]
        rc, out, err = await _run(cmd)
        if rc != 0:
            await tg_send(client, chat_id, f"⚠️ {esc(err[:200] or out[:200])}")
            return
        emoji = {"resolve": "✓", "veto": "✗", "progress": "▶", "reopen": "↺"}.get(sub, "•")
        await tg_send(client, chat_id, f"{emoji} {esc(out.strip())}")
        return

    # /inbox stats
    if sub == "stats":
        rc, out, err = await _run([PYTHON_BIN, INBOX_PY, "stats"])
        if rc != 0:
            await tg_send(client, chat_id, f"⚠️ stats failed: <code>{esc(err[:200])}</code>")
            return
        await tg_send(client, chat_id, f"📊 <b>INBOX STATS</b>\n<pre>{esc(out)}</pre>")
        return

    # /inbox resolved
    if sub == "resolved":
        rc, out, err = await _run([PYTHON_BIN, INBOX_PY, "resolved", "--limit", "10"])
        if rc != 0:
            await tg_send(client, chat_id, f"⚠️ resolved failed: <code>{esc(err[:200])}</code>")
            return
        await tg_send(client, chat_id, f"📥 <b>RECENT RESOLVED</b>\n<pre>{esc(out)}</pre>")
        return

    # /inbox <category>
    rc, out, err = await _run([PYTHON_BIN, INBOX_PY, "list", "--category", sub, "--limit", "20"])
    if rc != 0:
        await tg_send(client, chat_id,
            f"⚠️ Unknown subcommand or category: <code>{esc(sub)}</code>\n"
            "Try: <code>/inbox</code> · <code>/inbox stats</code> · <code>/inbox resolved</code> · "
            "<code>/inbox show &lt;id&gt;</code> · <code>/inbox resolve &lt;id&gt;</code>")
        return
    if out.strip() == "(inbox empty)":
        await tg_send(client, chat_id, f"📥 No pending items in category <b>{esc(sub)}</b>.")
        return
    await tg_send(client, chat_id,
        f"📥 <b>INBOX · category={esc(sub)}</b>\n\n<pre>{esc(out)}</pre>")
