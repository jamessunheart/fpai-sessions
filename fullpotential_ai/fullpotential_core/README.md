# FullPotential Core

This repository is now the single source of truth for the autonomous build
system. All code, droplets, specs, SOPs, and documentation from the legacy
service catalog and droplet bundles were audited, deduped, and relocated into a
clean modern tree that matches the operational reality.

## Directory map

- `agents/` – production-ready agents and services (canonically synced from
  the unified `agents/services/` catalog).
- `core/` – architecture references plus application source for flagship
  offerings (church guidance, magnet trading, analytics, proactive ops, etc.).
- `docs/` – documentation stack separated into guides, strategy, status,
  reports, and the full research library (JSON + MD logs from the backup).
- `droplets/` – delivery-ready droplets from both teams: `claude1/` for the
  packaged product bundles and `hteam/` for the high-touch deployment code.
- `infra/` – delegation platform code and ops scripts for deployments and
  verifications.
- `orchestration/` – command center: runbooks, dashboards, SOPs, missions,
  overnight logs, and status rituals.
- `specs/` – curated spec canon grouped by domain (`autonomy`, `coordination`,
  `outreach`, `treasury`, `udc`, `products`).

## Source + dedup decisions

| Domain | Primary Source | Notes |
| --- | --- | --- |
| Agents/Services | `agents/services/` | Consolidates the legacy service trees so newest implementations now live here. |
| Core Apps | `core/applications/` (`church-guidance-funnel`, `custom-gpt-services`, `magnet-trading-system`, `fpai-analytics`, `i-proactive`, `systems/mission-portal`, `white-rock-landing`) | Pulled complete source + deployment guides. |
| Specs | Specs from `agents/services/*/SPEC*.md`, `docs/coordination/*SPEC*.md`, treasury packs, and TIE/UDC docs | Organized by domain with per-service subdirectories. |
| Droplets – Claude | `droplets/claude1/` | Retains automation bundles, dashboards, treasury packs, etc. |
| Droplets – HTeam | `droplets/hteam/` (minus `venv`, `.env*`, `*.pem`) | Keeps every shipped droplet (1–18) with tests and SOPs. |
| Orchestration | `_scripts`, `_guides`, `_status`, `missions/`, `overnight-logs/`, `DASHBOARDS/` plus standalone tooling scripts | Tools vs SOPs split to mirror daily operating rhythm. |
| Docs | `docs/` tree (minus sensitive `coordination/credentials`) + root MD files grouped into `guides`, `strategy`, `status`, `reports` | Removes duplicate placements; each doc now lives in a single best-fit bucket. |
| Infra | `infra/` | Brings delegation system code and infra scripts. |

## How to navigate

1. **Runbooks first:** `orchestration/` holds every switch you need to wake or
   sleep the system plus SOPs for activation, overnight mode, and missions.
2. **Specs before code:** reference the relevant file in `specs/{domain}` before
   editing an agent or droplet to confirm interface contracts.
3. **Agents vs Core apps:** customer-facing products live under `core/`, while
   reusable automation services stay under `agents/services/` with their original
   README + infra (docker, compose, etc.).
4. **Documentation:** quick instructions are in `docs/guides`, strategic moves
   in `docs/strategy`, and live-state audits in `docs/status` & `docs/reports`.
5. **Droplets:** `droplets/hteam` contains heavy engineering builds; `droplets/claude1`
   keeps packaged bundles + automation kits ready for resale.

## Automation Helpers
- `orchestration/tools/spec_task_sync.py` – generates `specs/_meta/traceability.json` and `orchestration/missions/reports/spec_task_report.md` to map each SPEC to its owner (mission vs sprint) without auto-creating work.
- `orchestration/scripts/generate_intent_snapshot.py` – compiles `core/architecture/STATE/NOW.md`, fast-load scripts, and the active mission board into `docs/status/overnight-report.md`.
- `orchestration/scripts/update_status_index.py` – keeps `docs/status/INDEX.md` current so humans can find the latest health reports quickly.
- `core/applications/TEST_MATRIX.md` – documents the test command (or gap) for every flagship application.

## Next actions

- Re-link any CI/CD or deployment jobs to the new paths (use `infra/scripts`
  for health checks and deployments).
- When creating new services, drop specs into the correct domain folder and add
  the implementation under `agents/services` or `core/applications` as
  appropriate.
- Update mission dashboards or overnight trackers to point at `orchestration/`
  so logging stays centralized.

This repository is safe to extend—backup sources remain untouched in their
original locations for historical reference.
