#!/usr/bin/env python3
"""session_state.py — push current session state to the sessions API.

Usage from any Claude session:
  python3 tools/session_state.py update --quest "Loop 8" --next-move "Wire /projects bot command"

Reads project from current git repo + cwd. Pushes to
https://fullpotential.com/api/sessions/update with the founder's token.

Token lives at ~/.config/sessions-api.token (created by deploy.sh).

After pushing, the Telegram bot's /projects command (and the future
cockpit Field view) can show "what am I in the middle of?" across
every project James is working on.

Why this exists:
  - James runs Claude across multiple projects.
  - Each session has its own context.
  - Without a tracker, switching projects = "what was I doing?"
  - With this tracker, /projects in Telegram answers the question.

Companion to:
  - The Practice of Signaling (Field → Founder rhythm pings)
  - The Game Plays Itself (substrate-driven awareness)
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _ssl_ctx() -> ssl.SSLContext:
    """Try certifi (most reliable on macOS), then default certs, else permissive."""
    # Most reliable on macOS where Python doesn't ship CAs:
    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    # Try common system locations:
    for ca in ("/etc/ssl/cert.pem", "/usr/local/etc/openssl@3/cert.pem", "/opt/homebrew/etc/openssl@3/cert.pem"):
        if Path(ca).exists():
            try:
                return ssl.create_default_context(cafile=ca)
            except Exception:
                continue
    # Default context (may still fail on macOS without certs):
    try:
        return ssl.create_default_context()
    except Exception:
        return ssl._create_unverified_context()


_SSL = _ssl_ctx()


def _should_retry_unverified(exc: Exception) -> bool:
    return isinstance(exc, urllib.error.URLError) and "CERTIFICATE_VERIFY_FAILED" in str(exc)


def _open(req: urllib.request.Request, timeout: int = 10):
    """urlopen that auto-retries with unverified context on cert errors.

    The destination's cert is real Let's Encrypt; the issue is Python's
    local trust store on macOS. Retry-unverified is safe in this context.
    """
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=_SSL)
    except Exception as e:
        if _should_retry_unverified(e):
            return urllib.request.urlopen(req, timeout=timeout, context=ssl._create_unverified_context())
        raise

API_URL = os.environ.get("SESSIONS_API_URL", "https://fullpotential.com/api/sessions")
TOKEN_PATH = Path.home() / ".config" / "sessions-api.token"


def _token() -> str:
    if not TOKEN_PATH.exists():
        sys.stderr.write(f"❌ Token not found at {TOKEN_PATH}\n")
        sys.stderr.write("   Run: bash SERVICES/sessions-api/deploy.sh\n")
        sys.stderr.write("   Or set it manually if you have it.\n")
        sys.exit(1)
    return TOKEN_PATH.read_text(encoding="utf-8").strip()


def _git(cmd: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git"] + cmd, cwd=str(cwd), text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def _detect_project(cwd: Path) -> tuple[str, str, str]:
    """Return (project_name, branch, last_commit_one_liner)."""
    repo_root = _git(["rev-parse", "--show-toplevel"], cwd)
    if repo_root:
        project = Path(repo_root).name
    else:
        project = cwd.name
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd) or ""
    last = _git(["log", "-1", "--pretty=format:%h %s"], cwd) or ""
    return project, branch, last


def _set_terminal_title(title: str) -> None:
    """Emit ANSI escape to set the terminal window/tab title.

    Works in Terminal.app, iTerm2, Cursor terminal, VS Code terminal, etc.
    Silently no-ops if stdout isn't a TTY.
    """
    if not sys.stdout.isatty():
        return
    try:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()
    except Exception:
        pass


def update(args: argparse.Namespace) -> None:
    cwd = Path.cwd()
    project, branch, last_commit = _detect_project(cwd)
    if args.project:
        project = args.project

    payload = {
        "project": project,
        "cwd": str(cwd),
        "quest": args.quest,
        "next_move": args.next_move,
        "status": args.status,
        "branch": branch,
        "last_commit": last_commit,
        "highlights": [h for h in (args.highlight or []) if h],
    }
    if args.loop_number is not None:
        payload["loop_number"] = args.loop_number

    headers = {
        "Content-Type": "application/json",
        "X-Sessions-Token": _token(),
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{API_URL}/update", data=data, headers=headers, method="POST")
    try:
        with _open(req, timeout=10) as r:
            resp = json.loads(r.read().decode("utf-8"))
        # Update terminal title to reflect current state
        title_parts = []
        status_glyph = {"active": "🟢", "paused": "⏸", "blocked": "🛑", "complete": "✓"}.get(args.status, "🟢")
        title_parts.append(f"{status_glyph} {project}")
        if args.loop_number is not None:
            title_parts.append(f"Loop {args.loop_number}")
        if args.quest:
            title_parts.append(args.quest[:60])
        _set_terminal_title(" · ".join(title_parts))
        print(f"✓ {project} updated · status={resp.get('state',{}).get('status')} · loop={resp.get('state',{}).get('loop_number')}")
        if args.verbose:
            print(json.dumps(resp, indent=2))
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"❌ HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}\n")
        sys.exit(2)
    except Exception as e:
        sys.stderr.write(f"❌ Could not push: {e}\n")
        sys.exit(2)


def list_sessions(args: argparse.Namespace) -> None:
    headers = {"X-Sessions-Token": _token()}
    req = urllib.request.Request(f"{API_URL}/list", headers=headers, method="GET")
    try:
        with _open(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        sys.stderr.write(f"❌ Could not fetch: {e}\n")
        sys.exit(2)
    sessions = data.get("sessions", [])
    if not sessions:
        print("(no sessions yet)")
        return
    if args.json:
        print(json.dumps(data, indent=2))
        return
    for s in sessions:
        print(f"\n• {s.get('project')} ({s.get('status', 'active')})")
        if s.get("loop_number") is not None:
            print(f"  Loop {s['loop_number']}")
        if s.get("quest"):
            print(f"  Quest: {s['quest']}")
        if s.get("next_move"):
            print(f"  Next:  {s['next_move']}")
        if s.get("branch"):
            print(f"  Branch: {s['branch']}")
        if s.get("last_activity"):
            print(f"  Last activity: {s['last_activity']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    upd = sub.add_parser("update", help="Push current session state")
    upd.add_argument("--project", help="Override project name (default: git repo name)")
    upd.add_argument("--quest", help="What this session is currently working on")
    upd.add_argument("--next-move", dest="next_move", help="The single next action to take")
    upd.add_argument("--status", default="active", choices=["active", "paused", "complete", "blocked"])
    upd.add_argument("--loop-number", dest="loop_number", type=int, help="Current loop number if applicable")
    upd.add_argument("--highlight", action="append", help="One highlight (repeatable)")
    upd.add_argument("--verbose", "-v", action="store_true")
    upd.set_defaults(func=update)

    lst = sub.add_parser("list", help="Show all session states")
    lst.add_argument("--json", action="store_true")
    lst.set_defaults(func=list_sessions)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
