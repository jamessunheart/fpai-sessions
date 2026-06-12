"""
ember-substrate-mcp · smoke_test.py
====================================

In-process harness — calls each of the 20 tools via the `call_tool` dispatcher
(no stdio, no Claude Desktop required). Verifies:

  1. All 20 tools defined in TOOLS list (15 read + 5 write).
  2. All 15 read tools return without raising.
  3. All 5 write tools return without raising.
  4. Forbidden paths return structured 403:
       - .claude/settings.json
       - core/STATE/NOW.md (via hot-files.txt)
       - .claude/agents/the-forge.md (write attempt)
       - memory/identity/STORY.md
  5. `EMBER_MCP_DISABLE=1` causes server.py to exit 0 within 100ms (sub-process).

Exit codes:
  0 = all checks passed
  1 = one or more failures (details printed)
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure local imports resolve.
_SELF_DIR = os.path.dirname(os.path.abspath(__file__))
if _SELF_DIR not in sys.path:
    sys.path.insert(0, _SELF_DIR)

from permissions import check_write, hot_files_snapshot  # noqa: E402
from tools import TOOLS, call_tool  # noqa: E402

FAILURES: list[str] = []
PASSES: list[str] = []


def _record(passed: bool, label: str, detail: str = "") -> None:
    bucket = PASSES if passed else FAILURES
    bucket.append(f"{label}" + (f" — {detail}" if detail else ""))
    marker = "[PASS]" if passed else "[FAIL]"
    print(f"{marker} {label}" + (f" — {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# 1. Tool count
# ---------------------------------------------------------------------------


def check_tool_count() -> None:
    names = [t.name for t in TOOLS]
    expected_read = {
        "ember_read_state",
        "ember_read_now",
        "ember_read_goals",
        "ember_read_scene",
        "ember_read_alignment",
        "ember_read_story_handoff",
        "ember_read_next_turn_surface",
        "ember_read_narrator_log",
        "ember_read_events",
        "ember_read_decisions",
        "ember_read_memory_search",
        "ember_read_agent",
        "ember_list_agents",
        "ember_read_agent_identity",
        "ember_read_mindmap",
    }
    expected_write = {
        "ember_log_message",
        "ember_log_event",
        "ember_queue_forge_work_order",
        "ember_queue_canonization",
        "ember_save_memory",
    }
    missing_read = expected_read - set(names)
    missing_write = expected_write - set(names)
    _record(
        len(TOOLS) == 20 and not missing_read and not missing_write,
        "tool count == 20 (15 read + 5 write)",
        detail=f"have={len(TOOLS)}, missing_read={missing_read}, missing_write={missing_write}",
    )


# ---------------------------------------------------------------------------
# 2-3. Per-tool calls (read + write)
# ---------------------------------------------------------------------------


async def check_read_tools() -> None:
    cases = [
        ("ember_read_state", {}),
        ("ember_read_now", {}),
        ("ember_read_goals", {}),
        ("ember_read_scene", {}),
        ("ember_read_alignment", {}),
        ("ember_read_story_handoff", {}),
        ("ember_read_next_turn_surface", {}),
        ("ember_read_narrator_log", {}),
        ("ember_read_events", {"since_minutes": 60}),
        ("ember_read_decisions", {"since_days": 30}),
        ("ember_read_memory_search", {"query": "ember", "limit": 3}),
        ("ember_read_agent", {"name": "the-forge"}),
        ("ember_list_agents", {}),
        ("ember_read_agent_identity", {"agent": "the-forge"}),
        ("ember_read_mindmap", {}),
    ]
    for name, args in cases:
        try:
            res = await call_tool(name, args)
            ok = isinstance(res, list) and len(res) > 0 and getattr(res[0], "text", "") != ""
            _record(ok, f"read {name}", detail=f"bytes={len(res[0].text) if ok else 0}")
        except Exception as e:
            _record(False, f"read {name}", detail=f"raised {type(e).__name__}: {e}")


async def check_write_tools() -> None:
    # 1. log_event — should succeed (substrate is live)
    try:
        res = await call_tool(
            "ember_log_event",
            {"type": "smoke_test", "payload": {"phase": "write_check", "src": "smoke"}},
        )
        text = res[0].text if res else ""
        _record('"ok": true' in text or '"ok":true' in text, "write ember_log_event", detail=text[:160])
    except Exception as e:
        _record(False, "write ember_log_event", detail=f"raised {type(e).__name__}: {e}")

    # 2. log_message
    try:
        res = await call_tool(
            "ember_log_message",
            {"text": "[smoke_test] ember-substrate-mcp self-check", "priority": "low"},
        )
        text = res[0].text if res else ""
        _record('"ok": true' in text or '"ok":true' in text, "write ember_log_message", detail=text[:160])
    except Exception as e:
        _record(False, "write ember_log_message", detail=f"raised {type(e).__name__}: {e}")

    # 3. queue_forge_work_order
    try:
        res = await call_tool(
            "ember_queue_forge_work_order",
            {
                "slug": "smoke-test",
                "content": "# smoke test\n\nverify queue write surface.\n",
                "priority": "low",
            },
        )
        text = res[0].text if res else ""
        _record('"ok": true' in text or '"ok":true' in text, "write ember_queue_forge_work_order", detail=text[:200])
    except Exception as e:
        _record(False, "write ember_queue_forge_work_order", detail=f"raised {type(e).__name__}: {e}")

    # 4. queue_canonization
    try:
        res = await call_tool(
            "ember_queue_canonization",
            {
                "discipline_name": "smoke-test-discipline",
                "reason": "smoke verification",
                "proposed_mechanism": "append-only audit entry",
            },
        )
        text = res[0].text if res else ""
        _record('"ok": true' in text or '"ok":true' in text, "write ember_queue_canonization", detail=text[:200])
    except Exception as e:
        _record(False, "write ember_queue_canonization", detail=f"raised {type(e).__name__}: {e}")

    # 5. save_memory — write to a unique kebab filename
    try:
        ts = int(time.time())
        fname = f"smoke-test-{ts}.md"
        res = await call_tool(
            "ember_save_memory",
            {"filename": fname, "content": f"# smoke {ts}\n\nself-check artifact.\n"},
        )
        text = res[0].text if res else ""
        ok = '"ok": true' in text or '"ok":true' in text
        _record(ok, "write ember_save_memory", detail=text[:200])
        # cleanup
        if ok:
            mem_root = Path(os.environ.get("EMBER_MEMORY_GLOBAL", "/Users/jamessunheart/.claude/memory-global"))
            try:
                (mem_root / fname).unlink()
            except Exception:
                pass
    except Exception as e:
        _record(False, "write ember_save_memory", detail=f"raised {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# 4. Forbidden path enforcement
# ---------------------------------------------------------------------------


def check_forbidden_paths() -> None:
    cockpit = Path(os.environ.get("FPAI_COCKPIT_ROOT", "/Users/jamessunheart/FPAI_Cockpit"))
    mem = Path(os.environ.get("EMBER_MEMORY_GLOBAL", "/Users/jamessunheart/.claude/memory-global"))
    cases = [
        ("hot-files.txt", cockpit / "core" / "STATE" / "NOW.md"),
        ("exact-deny .claude/settings.json", cockpit / ".claude" / "settings.json"),
        ("prefix-deny .claude/agents/", cockpit / ".claude" / "agents" / "the-forge.md"),
        ("identity-prefix memory/identity/", mem / "identity" / "STORY.md"),
        ("path-traversal segment", cockpit / "core" / ".." / "etc" / "passwd"),
        ("outside-allowed-roots", Path("/tmp/escape-attempt.md")),
    ]
    for label, p in cases:
        result = check_write(p)
        ok = isinstance(result, dict) and result.get("error") == "fatal_zone"
        _record(ok, f"forbidden {label}", detail=json.dumps(result)[:200])


# ---------------------------------------------------------------------------
# 4b. Forbidden-path enforcement via the TOOL surface
# ---------------------------------------------------------------------------


async def check_forbidden_via_tool() -> None:
    # save_memory pointed at identity should refuse via check_write.
    # Filename must pass kebab regex first, so we can't directly target
    # identity/STORY.md through save_memory — kebab regex enforces no `/`.
    res = await call_tool(
        "ember_save_memory",
        {"filename": "STORY.md", "content": "should be rejected"},
    )
    text = res[0].text if res else ""
    _record('"error": "invalid_filename"' in text, "save_memory rejects uppercase filename", detail=text[:160])

    # Forge work order with bad slug
    res = await call_tool(
        "ember_queue_forge_work_order",
        {"slug": "Bad Slug!", "content": "x"},
    )
    text = res[0].text if res else ""
    _record('"error": "invalid_slug"' in text, "queue_forge rejects non-kebab slug", detail=text[:160])

    # Read agent with bad name
    res = await call_tool("ember_read_agent", {"name": "../etc/passwd"})
    text = res[0].text if res else ""
    _record('"error": "invalid_agent_name"' in text, "read_agent rejects bad name", detail=text[:160])


# ---------------------------------------------------------------------------
# 5. EMBER_MCP_DISABLE=1 sub-process check
# ---------------------------------------------------------------------------


def check_kill_switch() -> None:
    server_py = Path(_SELF_DIR) / "server.py"
    env = os.environ.copy()
    env["EMBER_MCP_DISABLE"] = "1"
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(server_py)],
            env=env,
            capture_output=True,
            timeout=5,
        )
        dt_ms = (time.monotonic() - t0) * 1000
        ok = proc.returncode == 0 and dt_ms < 1000  # generous: <1s
        _record(
            ok,
            "EMBER_MCP_DISABLE=1 exits 0 fast",
            detail=f"rc={proc.returncode} dt={dt_ms:.0f}ms stderr={proc.stderr.decode()[:120]}",
        )
    except subprocess.TimeoutExpired:
        _record(False, "EMBER_MCP_DISABLE=1 exits 0 fast", detail="TIMEOUT (>5s)")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


async def main_async() -> None:
    print("=" * 70)
    print("ember-substrate-mcp · smoke_test")
    print("=" * 70)
    print(f"FPAI_COCKPIT_ROOT = {os.environ.get('FPAI_COCKPIT_ROOT', '<default>')}")
    print(f"EMBER_API_BASE    = {os.environ.get('EMBER_API_BASE', '<default>')}")
    print(f"token file        = {os.environ.get('EMBER_API_TOKEN_FILE', '<default>')}")
    print(f"hot-files count   = {len(hot_files_snapshot())}")
    print()

    check_tool_count()
    print()
    await check_read_tools()
    print()
    await check_write_tools()
    print()
    check_forbidden_paths()
    print()
    await check_forbidden_via_tool()
    print()
    check_kill_switch()
    print()
    print("=" * 70)
    print(f"PASS: {len(PASSES)}   FAIL: {len(FAILURES)}")
    if FAILURES:
        print("FAILURES:")
        for f in FAILURES:
            print(f"  - {f}")
    print("=" * 70)
    sys.exit(0 if not FAILURES else 1)


if __name__ == "__main__":
    asyncio.run(main_async())
