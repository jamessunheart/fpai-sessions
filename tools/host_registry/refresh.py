#!/usr/bin/env python3
"""Refresh the repo-side Host Registry from safe local metadata only.

No SSH. No network. No process mutation. This deliberately separates repo
metadata from live heartbeat truth so old service docs do not become fake
operational state.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SERVICE_REGISTRY = REPO / "docs" / "codex" / "SERVICE_REGISTRY.md"
HOST_REGISTRY = REPO / "docs" / "codex" / "HOST_REGISTRY.md"


def stamp() -> str:
    return dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")


def service_summary() -> tuple[str, str]:
    if not SERVICE_REGISTRY.exists():
        return "missing service registry", "unknown"
    text = SERVICE_REGISTRY.read_text(encoding="utf-8")
    summary = "unknown"
    generated = "unknown"
    m = re.search(r"Status counts:\s*([^\n]+)", text)
    if m:
        summary = m.group(1).strip()
    g = re.search(r"last_generated:\s*([^\n]+)", text)
    if g:
        generated = g.group(1).strip()
    return summary, generated


def render() -> str:
    now = stamp()
    counts, generated = service_summary()
    return f"""---
generated: true
source: tools/host_registry/refresh.py
last_generated: {now}
edit_policy: regenerate, do not hand-edit generated sections
---

# Host Registry

Safe registry for live-server and host truth. This file does **not** prove live process state unless a heartbeat is recorded.

## Status

| Field | Value |
|---|---|
| Confidence | PARTIAL |
| Live heartbeat coverage | none yet |
| SSH/network action taken | no |
| Last generated | {now} |

## Host Truth Levels

| Level | Meaning | Current status |
|---|---|---|
| L0 · Repo metadata | Files, service dirs, systemd unit files, deployment hints. | available via `docs/codex/SERVICE_REGISTRY.md` |
| L1 · Host inventory | Host aliases, roles, repo paths, allowed access lanes. | not yet complete |
| L2 · Heartbeat | Recent safe check from host or service endpoint. | not yet implemented |
| L3 · Action authority | Explicit allowed actions and rollback path. | James/Ember gated |

## Known Host / Server Surfaces

| Surface | Source | What is known | Last observed | Confidence | Allowed action |
|---|---|---|---|---|---|
| Service Registry / World Map | `docs/codex/SERVICE_REGISTRY.md` | {counts}. | {generated} | L0 metadata | report only |
| Always-on dev servers | James report | James reports 3 always-on dev servers exist. | 2026-06-06 conversation | needs L1 inventory | ask James/Ember before SSH |
| Brain server | `SERVICES/sunheart-brain/`, `tools/verify_cross_surface.sh`, `tools/ember_audit.sh` | Repo contains brain server/MCP code and verification scripts. | repo metadata | L0 metadata | safe read/check only when authorized |
| Local Mac / Codex desktop | current worktree | Local truth for vault, repo, screenshots, and unpushed artifacts. | current session | high for local files | repo/vault edits with approval |
| Phone/cloud Codex | GitHub `main` | GitHub-only Buildstream surface; no iCloud/local secrets. | docs pushed to `main` | high for repo docs | build approved specs only |

## Current Gaps

- Need names/aliases for the 3 always-on dev servers.
- Need which host is safe for SSH Codex Build Host, if any.
- Need per-host role, repo path, allowed actions, cost/risk class, and rollback/contact path.
- Need heartbeat command that is read-only, non-secret, and safe to run.

## Proposed Heartbeat Schema

```text
host_alias:
role:
access_lane: mac-local / phone-remote-mac / github-cloud / ssh-build-host / production
repo_path:
services:
last_heartbeat:
heartbeat_method:
cost_risk:
allowed_ai_actions:
forbidden_ai_actions:
rollback_contact:
notes:
```

## Next Unlock

```text
Intent solved: first Host Registry surface exists without pretending metadata is heartbeat.
Downstream intent unlocked: James/Ember can bless one safe host inventory pass or designate an SSH Build Host.
Proof: registry separates L0 metadata from L2 heartbeat and lists gaps explicitly.
Next unlocked move: write a read-only heartbeat spec once James names the host lane.
```
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Refresh Host Registry from safe local metadata.")
    ap.add_argument("--dry-run", action="store_true", help="print output instead of writing")
    args = ap.parse_args(argv)
    text = render()
    if args.dry_run:
        print(text)
        return 0
    HOST_REGISTRY.write_text(text, encoding="utf-8")
    print(f"refreshed -> {HOST_REGISTRY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
