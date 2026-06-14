#!/usr/bin/env python3
"""
Cartographer first-pass index builder · v1 · 2026-05-26
Walks memory + repo + (eventually servers) and produces a compressed map
the AI council reads at session start.

Per [[spec-the-cartographer-internal-index]] · the Tier-0 build of the WIDE organ.

Output: ~/.config/fpai/cartographer/index.md
Cadence (when wired to LaunchAgent): daily 06:00 CR refresh.

This v1 covers:
- Identity stack (file names + descriptions from frontmatter)
- All memory files grouped by type prefix (feedback/reference/project/spec/draft)
- core/STATE files
- core/INTENT/SPECS recent files
- .claude/agents roster
- tools/ directory listing
- LaunchAgents loaded
- ~/.config/fpai/ key/cred presence (no values)
- Recent narrator sessions (last 5)
- Recent decision log summary

Future iterations (queued):
- Live server-side service inventory (SSH to 162.0.208.88 + 198.54.123.234 + 209.74.93.72)
- TG bot inventory (@sunheartbrain_bot · @fullpotentialgamebot · @zenvillagebot)
- Domain inventory
- Stripe / SaaS / wallet inventory
- Values-alignment surface (IDEALS / VIRTUES / ALIGNMENT.md cross-link)
"""

import json
import os
import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
MEMORY_DIR = HOME / ".claude" / "projects" / "-Users-jamessunheart-FPAI-Cockpit" / "memory"
REPO = Path("/Users/jamessunheart/FPAI_Cockpit")
OUT = HOME / ".config" / "fpai" / "cartographer" / "index.md"


def read_frontmatter_description(path: Path) -> str:
    """Extract `description: ...` line from YAML frontmatter."""
    try:
        with open(path) as f:
            text = f.read(4000)
        m = re.search(r"^description:\s*(.+?)(?:\n[a-z]+:|^\s*$)", text, re.M | re.S)
        if m:
            desc = m.group(1).strip().strip('"').strip("'")
            # collapse newlines + truncate
            desc = re.sub(r"\s+", " ", desc)[:200]
            return desc
    except Exception:
        pass
    return ""


def list_memory_files() -> dict:
    """Group memory files by prefix-type."""
    groups = {
        "identity": [],
        "feedback": [],
        "reference": [],
        "project": [],
        "spec": [],
        "draft": [],
        "user": [],
        "other": [],
    }
    if not MEMORY_DIR.exists():
        return groups

    for path in sorted(MEMORY_DIR.glob("*.md")):
        if path.name == "MEMORY.md":
            continue
        name = path.stem
        # Identify prefix
        if name.startswith("feedback_"):
            key = "feedback"
        elif name.startswith("reference_"):
            key = "reference"
        elif name.startswith("project_"):
            key = "project"
        elif name.startswith("spec_"):
            key = "spec"
        elif name.startswith("draft_"):
            key = "draft"
        elif name.startswith("user_"):
            key = "user"
        else:
            key = "other"
        desc = read_frontmatter_description(path)
        groups[key].append((name, desc))

    # Identity files (separate dir)
    identity_dir = MEMORY_DIR / "identity"
    if identity_dir.exists():
        for path in sorted(identity_dir.glob("*.md")):
            if path.name == "_TEMPLATE.md":
                continue
            desc = read_frontmatter_description(path)
            groups["identity"].append((f"identity/{path.stem}", desc))

    return groups


def list_core_state() -> list:
    out = []
    state = REPO / "core" / "STATE"
    if state.exists():
        for path in sorted(state.glob("*.md")):
            desc = read_frontmatter_description(path)
            out.append((path.name, desc))
    return out


def list_recent_specs(limit: int = 12) -> list:
    specs_dir = REPO / "core" / "INTENT" / "SPECS"
    if not specs_dir.exists():
        return []
    files = sorted(specs_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in files[:limit]:
        try:
            text = p.read_text()[:2000]
            # Take first header
            m = re.search(r"^# (.+?)$", text, re.M)
            title = m.group(1).strip() if m else p.stem
        except Exception:
            title = p.stem
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d")
        out.append((p.name, title[:120], mtime))
    return out


def list_agents() -> list:
    out = []
    agents_dir = REPO / ".claude" / "agents"
    if not agents_dir.exists():
        return out
    for path in sorted(agents_dir.glob("*.md")):
        try:
            with open(path) as f:
                head = f.read(2000)
            m = re.search(r"^description:\s*(.+?)(?:\n[a-z]+:|^\s*$)", head, re.M | re.S)
            desc = ""
            if m:
                desc = re.sub(r"\s+", " ", m.group(1).strip().strip('"').strip("'"))[:180]
        except Exception:
            desc = ""
        out.append((path.stem, desc))
    return out


def list_tools() -> list:
    out = []
    tools_dir = REPO / "tools"
    if not tools_dir.exists():
        return out
    for path in sorted(tools_dir.iterdir()):
        if path.is_dir():
            files = sorted([p.name for p in path.iterdir() if not p.name.startswith(".")])
            out.append((f"tools/{path.name}/", files[:8]))
    return out


def list_launch_agents() -> list:
    try:
        r = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10)
        out = []
        for line in r.stdout.splitlines():
            if "com.fpai." in line:
                parts = line.split()
                if len(parts) >= 3:
                    pid, status, label = parts[0], parts[1], parts[2]
                    out.append((label, pid, status))
        return out
    except Exception:
        return []


def list_credentials() -> list:
    """Show what credentials/keys are resident (PATH only, never values)."""
    out = []
    config_root = HOME / ".config" / "fpai"
    if not config_root.exists():
        return out
    for path in sorted(config_root.rglob("*")):
        if path.is_file() and (path.name.endswith(".token") or path.name.endswith(".cache") or path.name.endswith(".env") or path.name == "api.token"):
            rel = str(path.relative_to(config_root))
            size = path.stat().st_size
            out.append((rel, size))
    return out


def recent_narrator_sessions(limit: int = 5) -> list:
    sessions = MEMORY_DIR / "identity" / "sessions"
    if not sessions.exists():
        return []
    files = sorted(sessions.glob("2026-*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in files[:limit]:
        try:
            text = p.read_text()[:3000]
            m = re.search(r"^# (.+?)$", text, re.M)
            title = m.group(1).strip() if m else p.stem
        except Exception:
            title = p.stem
        out.append((p.name, title[:120]))
    return out


def recent_decisions(limit: int = 15) -> list:
    log = HOME / ".config" / "fpai" / "decisions" / "log.jsonl"
    if not log.exists():
        return []
    lines = log.read_text().splitlines()[-limit:]
    out = []
    for line in lines:
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            et = e.get("event_type", "decision")
            ts = (e.get("timestamp") or e.get("started_at") or "")[:19]
            did = (e.get("decision_id") or "")[:24]
            summary = ""
            if et == "decision":
                summary = (e.get("ember_summary") or e.get("topic") or "")[:120]
            elif et == "ACTIONS_TAKEN":
                summary = f"{len(e.get('actions',[]))} actions · {e.get('sub_action','')[:80]}"
            elif et == "REVERSAL":
                summary = f"reason: {e.get('reason','')[:80]}"
            else:
                summary = et
            out.append((ts, et, did, summary))
        except Exception:
            pass
    return out


def intent_queue_open() -> list:
    queue = HOME / ".config" / "fpai" / "intent_queue" / "queue.jsonl"
    if not queue.exists():
        return []
    out = []
    for line in queue.read_text().splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            if e.get("status", "open") in ("open", "in_progress"):
                out.append(e)
        except Exception:
            pass
    return out


def render() -> str:
    """Compose the index markdown."""
    now_iso = datetime.now(timezone.utc).isoformat()
    lines = []
    a = lines.append

    a(f"# Substrate Index · {now_iso}")
    a("")
    a("**Generated by the cartographer · Tier-0 of the WIDE organ.**")
    a("This file is the compressed map the AI council reads at session start.")
    a("Built by `tools/cartographer/build_index.py` · refreshed daily 06:00 CR (LaunchAgent pending).")
    a("")
    a("---")
    a("")

    # Identity stack
    a("## Identity (Layer 0)")
    a("")
    groups = list_memory_files()
    for name, desc in groups["identity"]:
        a(f"- **{name}** — {desc or '(no description)'}")
    a("")

    # Canonical state
    a("## Canonical State (core/STATE/)")
    a("")
    for name, desc in list_core_state():
        a(f"- **{name}** — {desc or '(no description)'}")
    a("")

    # Feedback memories (the disciplines)
    a("## Feedback memories · disciplines")
    a("")
    for name, desc in groups["feedback"]:
        a(f"- **{name}** — {desc or ''}")
    a("")

    # Reference memories
    a("## Reference memories · patterns & frameworks")
    a("")
    for name, desc in groups["reference"]:
        a(f"- **{name}** — {desc or ''}")
    a("")

    # Project memories
    a("## Project memories · in-flight projects + canon")
    a("")
    for name, desc in groups["project"]:
        a(f"- **{name}** — {desc or ''}")
    a("")

    # Spec memories
    a("## Spec memories · drafts ready to build")
    a("")
    for name, desc in groups["spec"]:
        a(f"- **{name}** — {desc or ''}")
    a("")

    # Draft memories
    if groups["draft"]:
        a("## Draft memories (incoming · unprocessed · pending review)")
        a("")
        for name, desc in groups["draft"]:
            a(f"- **{name}** — {desc or ''}")
        a("")

    # User memories
    if groups["user"]:
        a("## User memories (James-facts)")
        a("")
        for name, desc in groups["user"]:
            a(f"- **{name}** — {desc or ''}")
        a("")

    if groups["other"]:
        a("## Other memories")
        a("")
        for name, desc in groups["other"]:
            a(f"- **{name}** — {desc or ''}")
        a("")

    # Recent specs (live disk)
    a("## Recent specs on disk (core/INTENT/SPECS/, last 12)")
    a("")
    for fname, title, mtime in list_recent_specs():
        a(f"- **{fname}** ({mtime}) — {title}")
    a("")

    # Agents
    a("## Agents (.claude/agents/)")
    a("")
    for name, desc in list_agents():
        a(f"- **{name}** — {desc or ''}")
    a("")

    # Tools directories
    a("## Tools (tools/)")
    a("")
    for dirname, files in list_tools():
        a(f"- **{dirname}** — {', '.join(files)}")
    a("")

    # LaunchAgents
    a("## LaunchAgents loaded (com.fpai.*)")
    a("")
    for label, pid, status in list_launch_agents():
        a(f"- **{label}** · pid={pid} · last_status={status}")
    a("")

    # Credentials (presence only)
    a("## Credentials resident (~/.config/fpai/ · presence only)")
    a("")
    for rel, size in list_credentials():
        a(f"- `{rel}` ({size} bytes)")
    a("")

    # Recent narrator sessions
    a("## Recent narrator sessions (last 5)")
    a("")
    for fname, title in recent_narrator_sessions():
        a(f"- **{fname}** — {title}")
    a("")

    # Recent decisions
    a("## Recent decision log entries (last 15)")
    a("")
    for ts, et, did, summary in recent_decisions():
        a(f"- {ts} · {et} · {did} · {summary}")
    a("")

    # Intent queue (open)
    a("## Intent queue (open items)")
    a("")
    open_i = intent_queue_open()
    if not open_i:
        a("- (empty)")
    else:
        for e in open_i:
            a(f"- **{e.get('intent_id','?')}** · {e.get('status','open')} by {e.get('created_by','?')} — {(e.get('description') or '')[:160]}")
    a("")

    # Sources for verification
    a("---")
    a("")
    a("**Sources walked by this index:**")
    a(f"- `{MEMORY_DIR}` · all .md files grouped by prefix")
    a(f"- `{REPO}/core/STATE/` · canonical state")
    a(f"- `{REPO}/core/INTENT/SPECS/` · recent specs")
    a(f"- `{REPO}/.claude/agents/` · agent roster")
    a(f"- `{REPO}/tools/` · substrate tools")
    a("- `launchctl list | grep com.fpai.` · loaded LaunchAgents")
    a(f"- `{HOME}/.config/fpai/` · credentials presence + decision log + intent queue")
    a("- `identity/sessions/2026-*.md` · recent narrator sessions")
    a("")
    a("**Future iterations (queued):**")
    a("- SSH inventory of services on 162.0.208.88 · 198.54.123.234 · 209.74.93.72")
    a("- TG bot inventory + domain inventory + Stripe/SaaS/wallet inventory")
    a("- Values-layer surface (IDEALS / VIRTUES / ALIGNMENT.md content extracted)")

    return "\n".join(lines)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rendered = render()
    OUT.write_text(rendered)
    print(f"Cartographer index written to {OUT}")
    print(f"Size: {OUT.stat().st_size} bytes · {len(rendered.splitlines())} lines")


if __name__ == "__main__":
    main()
