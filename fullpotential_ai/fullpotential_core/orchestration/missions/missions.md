# Missions Dashboard

_Source of truth for mission queue. For cadence + rituals see `docs/library/coordination/missions/MISSIONS_INDEX.md`._

## Active Mode Protocol
1. **Continuous generation:** When a new blocker is spotted, draft a mission (see templates) and add it to `open/`.
2. **Priority taxonomy:** Classify every mission using P0–P3 (P0 = critical blocker, P3 = nice-to-have).
3. **Single source of truth:** Reflect each status update here first, then propagate to portals or chat.

## Access Rules
- Missions in this board are **only for internal operators** (core team, trusted human reviewers).
- Apprentices execute separate sprint tasks generated from approved SPEC files (`specs/*`); those stay outside this board.
- Do **not** auto-create or publish public missions unless explicitly requested.

## Pipeline
- **Missions → Humans:** Internal operators pull from this list, execute the work, and update the buckets.
- **Sprints → Apprentices:** SPEC-derived tasks flow through the apprentice sprint tracker; never mix them with missions.

## Status Buckets
- `open/` – ready for assignment
- `in-progress/` – claimed missions with active owners
- `done/` – completed with evidence attached

## Active Missions

| Mission | Priority | Human Role Needed | Files / Systems | Expected Deliverable |
| --- | --- | --- | --- | --- |
| [Path Consistency QA](open/path_consistency_qa.md) | P0 | Technical Editor / QA | `docs/guides`, `docs/status`, `orchestration/scripts`, `orchestration/tools` | Proof that no docs/scripts reference legacy paths; notes saved in this dashboard |
| [Reddit Launch Blast](open/reddit_launch.md) | P1 | Outreach Specialist (Reddit) | Reddit submission flow, `docs/strategy/LEVERAGE_SYSTEM_FOR_OUTREACH.md` | Live fatFIRE post URL + notes on reception |
| [Magnet Trading Testnet Keys](open/magnet_trading_testnet_keys.md) | P1 | Treasury Ops (Binance testnet) | `core/applications/magnet-trading-system/backend/.env`, Binance Testnet | Health + fuse JSON confirming keys wired locally (no secrets committed) |

## Frozen Backlog (P2–P3)
- [Mission Portal Sync](in-progress/mission_portal_sync.md) — P2 — Frozen until Phase 4 (Ops Coordinator)
- [Dual Activation (Reddit + Trading)](open/dual_activation.md) — P2 — Frozen until portal + outreach readiness confirmed
- [Phase 1 – Path Cleanup](done/phase1_path_cleanup.md) — P3 — Historical reference only

## Templates & Reviewer Resources
- `templates/mission_brief_template.md` – use when drafting new missions.
- `templates/human_review_checklist.md` – step-by-step guide for human validation runs.

## Next Actions for Humans (P0–P1)
1. **P0 – Path Consistency QA:** [Mission brief](open/path_consistency_qa.md) — Technical editor to certify every doc/script references the new paths.
2. **P1 – Reddit Launch Blast:** [Mission brief](open/reddit_launch.md) — Outreach specialist with a Reddit account to post the fatFIRE update.
3. **P1 – Magnet Trading Testnet Keys:** [Mission brief](open/magnet_trading_testnet_keys.md) — Treasury operator to wire Binance testnet keys locally (no secrets committed).

_Add new missions by copying the template, storing it in the right folder, then appending a row to the table above. Avoid assignments that require personal secrets or non-public credentials; instead, document the dependency and escalate via Ops._

_Mission creation is currently paused per directive; do not add new missions until authorized._
