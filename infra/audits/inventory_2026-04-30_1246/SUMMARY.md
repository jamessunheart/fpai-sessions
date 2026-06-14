# System Inventory — 2026-04-30 12:46

Read-only SSH probe across all three servers. Source files: `primary_*.txt`, `secondary_*.txt`, `legacy_*.txt` in this directory.

## At-a-glance

| Server | OS | Uptime | RAM (used/total) | Disk (used%) | Services | Errors 24h |
|---|---|---|---|---|---|---|
| Primary `198.54.123.234` | Ubuntu 22.04 | 87 days | 5.5G / 7.7G (71%) | 20% | ~50 systemd units | 158 |
| Secondary `162.0.208.88` | Ubuntu 22.04 | 152 days | 8.7G / 31G (28%) + 3.8G swap | 26% | ~50 systemd + 28 docker | 311 |
| Legacy `209.74.93.72` | CloudLinux 9.6 | **342 days** | 13G / 125G (10%) | **66%** | cPanel + 39 sites | 221 |

## Major contradictions with NOW.md (the SSOT)

NOW.md (2026-04-14) labels several stacks as paused/inactive. Reality from systemd:

| NOW.md says | Reality | Notes |
|---|---|---|
| Concierge "P2, dark-shipped behind flags" | **13 concierge services running on primary right now** | tenant-api/voice-router/handoff-broker/compliance-gate/skills-mesh/etc. all active uvicorn processes. |
| WhaleTrack "paused, separate from engine" | **6 services running**: bridges (BTC/ETH/SOL/XRP) + magnet + live + telegram-bot | Active on primary, ports 8600–8602. |
| Credits gateway / cocoon "paused, zero transactions" | `fpai-credits-gateway.service` + `fpai-cocoon.service` running on primary | |
| AI Brain on secondary "not serving ZV guests" | `ai-brain` + `zv-telegram-bot` + `zv-mcp-http` + `sh-brain-tgbot` + `reasoning-engine` all active | Plus 20 docker containers (AppFlowy Cloud, sh-brain). |
| Legacy server has **44 cPanel accounts** | **39 cPanel accounts** | 5 must have been removed. |

NOW.md's "paused" list is largely fictional. Either kill these services (free RAM) or remove them from the "paused" list — the contradiction itself is noise.

## Significant undocumented infrastructure on secondary

Not mentioned in NOW.md or SERVICE_REGISTRY:
- **AppFlowy Cloud** — full stack, 10 docker containers (separate from sh-brain)
- **sh-brain** — sunheart-brain stack, 10 docker containers (memory bridge)
- **Firefly III** — financial tracking app + MariaDB
- **Paperless-ngx** — document management + Postgres + Redis
- **n8n** — workflow automation (up 6 days)
- **Ollama** — local LLM service
- Plus: Tailscale (100.127.118.106), MinIO, gpu-bridge, intake-agent, kai-bridge, memory-bus, security-watch

## Operational concerns surfaced

1. **Primary RAM is tight: 1.9G available.** Concierge stack alone runs ~10 uvicorn processes. Any spike risks OOM kills. Worth deciding which services actually need to run vs. stopping the truly-paused ones.

2. **Postgres on primary listening on `198.54.123.234:5432` (public IP).** Should bind to 127.0.0.1 only, or be firewalled. Currently exposed to the internet.

3. **Legacy disk 66% full (1.2T of 1.8T).** No immediate emergency, but trending. cPanel backups + accumulated MySQL likely the drivers.

4. **Legacy uptime 342 days.** No kernel updates applied in nearly a year. Kernel CVEs accumulate; reboot eventually requires a planned cutover for the call center.

5. **Secondary has 3.8G of swap in use** despite 22G of available RAM. Some process is being unfairly swapped — usually means a memory-hungry service was paged out and never came back. Worth a `swapoff/swapon` cycle when convenient.

## Cross-server dependencies (visible from this audit)

- **`fpai-health-agent.service` runs on legacy** — FPAI already has a foothold there for monitoring. Worth investigating what it reports.
- **`ob-dashboard.service` runs on legacy** — internal Outbounders dashboard, separate from `.workspace/active/outbounders_live_dashboard.py`. Probably the production version.
- **streasury-bot lives on secondary** (`162.0.208.88:8620`). Ollama on the same box — could be wired for cheap local AI.
- **Postgres on primary** (5432) is the FPAI DB. **Postgres on secondary** is for AppFlowy/Paperless docker stacks. **MariaDB on legacy** is the cPanel/Outbounders DB.

## Domain inventory (from nginx server_name + cPanel accounts)

**Primary nginx serves:** aimail.fullpotential.ai, fullpotential.ai, fullpotential.com, zenvillagecr.com.
**Secondary nginx serves:** triad.fullpotential.ai.
**Legacy cPanel accounts** (39): cmgrb1bpo, coracom, coradev, coraorg, corasupp, coravida, delray, devfiart, devonebpo, emponebpo, experiencescorav, expresspay, fiart, fiartapp, fpai, fpapps, fparchive, fpdir3, fpnews, fpstore, fullbhza, globalsky, helpdesk, helpdeskob, jamesrick, jamesrickstinson, maschristo, **obapp**, obmail, obpo, obposervices, obsmail, **onebpo**, onebpo2, **outbndrs**, runbookobpo, sunheart2, system, **zenvill**.

The Outbounders ecosystem is 5 of those 39 accounts. The Cora ecosystem is 6. FullPotential ecosystem is 8. The rest are mostly legacy/dormant — but each has its own DB and disk footprint.

## What's still missing (next pass)

1. **Per-cPanel-account activity:** which of the 39 are actually used vs. dormant? Last login per user, last DB activity, disk usage per account. Closing dormant accounts is the path to reducing the 1.2T disk usage.
2. **DNS records** for owned domains — which point at legacy, which moved.
3. **Provider billing reconciliation** — DigitalOcean / Hostgator (or whoever owns legacy) / Cloudflare. Need API tokens or scrape.
4. **Outbounders revenue rate** — `ob-dashboard.service` on legacy probably has it; check what port/path it listens on.
5. **What `fpai-health-agent.service` on legacy actually reports** — may already be a monitoring channel we're not surfacing.
