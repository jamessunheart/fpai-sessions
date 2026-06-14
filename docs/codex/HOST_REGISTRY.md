---
generated: true
source: tools/host_registry/refresh.py
last_generated: 2026-06-06 16:12 MDT
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
| Last generated | 2026-06-06 16:12 MDT |

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
| Service Registry / World Map | `docs/codex/SERVICE_REGISTRY.md` | archived: 75 · live: 16 · paused: 2 · ❓ needs-human-classify: 34. | 2026-06-05 17:06 UTC | L0 metadata | report only |
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
