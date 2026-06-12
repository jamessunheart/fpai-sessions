# Session Handoff — 2026-04-30

**For:** any Claude (or other AI agent) picking up where this session left off.
**Branch:** `feat/streasury-bot`
**Latest commits:** `c400e03a` (Outbounders adapter + dedup fix), `ee0ce5a9` (coordination archive + agent guidance).

## ⚠️ Parallel work also in flight (not from this session)

A separate session deployed three new services on 2026-04-30. **Don't duplicate them:**

- **Alerts service** (port 8766) — central notification system
- **Chief of Staff** (port 8107)
- **Proactive Monitor** (port 8108)
- Telegram `@sunheartbrain_bot` integrated with Sunheart Brain

If you're working on **notifications, monitoring, telegram bots, or chief-of-staff features**, read these BEFORE writing code:
- `TELL_OTHER_CLAUDE_INSTANCES.md` (root) — orientation
- `docs/coordination/ALERTS_SYSTEM_HANDOFF.md` — full technical handoff
- `docs/coordination/QUICK_REF_ALERTS_SYSTEM.md` — fast lookup
- `docs/coordination/SERVICE_REGISTRY.md` — has the new ports

The streams are independent: that work is alerts/monitoring; this session's work is treasury/observability. Both committed to `feat/streasury-bot`. No file conflicts expected, but the **shared question is: what does the daily Telegram digest aggregate?** — Alerts + Outbounders revenue + cockpit health all want a place there.

---

## What we were working on

**Big goal:** *Know the truth of what's going on across the system, in something close to real time, as efficiently as possible.* Specifically — surface money flow, server health, and "what's actually deployed where" in one place James can glance at, instead of opening 5 tabs.

**Sub-goal that just landed:** Get Outbounders.com call-center revenue (~$200k/yr) into `streasury-bot` so it shows up in `/balance` and `/report month` alongside everything else. Done.

**Why this matters:** The legacy server `209.74.93.72` was tagged for elimination in `core/STATE/NOW.md` (-$330/mo runway). Audit revealed it actually hosts Outbounders production (15+ active call-center agents, 39 cPanel sites, $12.16M lifetime revenue). NOW.md was inverted — legacy is the highest-revenue surface in the portfolio, not an expense to cut.

---

## Read these first

1. **`core/STATE/NOW.md`** — SSOT for priorities. Already current as of 2026-04-29 (mostly — see contradictions below).
2. **`infra/audits/inventory_2026-04-30_1246/SUMMARY.md`** — system-wide inventory across all 3 servers; what's running, what's failed, undocumented infra.
3. **This file** — open questions to resolve.
4. **Memory:** `~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/` — user/project/feedback/reference notes.

---

## What's done (this session)

### Cleanup
- Archived 117 stale entries from `docs/coordination/` and `core/STATE/{PROGRESS,HEALTH}.md` into `.archive/deprecated/`.
- Added "READ THIS FIRST" blocks to `.ai-agent-guide.md`, `STRUCTURE.md`, `QUICK_START.md` pointing AI agents at NOW.md.
- Wrote 8 memory files (user, projects, feedback, references).

### System inventory
- Inventoried all 3 servers via SSH. Output in `infra/audits/inventory_2026-04-30_1246/`.
- Cockpit at `fullpotential.ai/cockpit/status/` now polls all three (extended `snapshot.sh` on primary). Refreshes every 5 min.

### Outbounders revenue → streasury
- CSF whitelist on legacy: `162.0.208.88` allowed for MySQL access.
- New MariaDB user `streasury_ro@'162.0.208.88'` with SELECT only on `obapp_outbounders.*`.
- Credential stored in `/etc/streasury-bot/streasury.env` (mode 600).
- New adapter at `SERVICES/streasury-bot/app/sources/outbounders.py` filters `paid IN ('P','Y')` and uses `iid` (int PK) as `source_ref`.
- Bug fix in `app/ledger.py`: skip dedup_hash when source_ref is provided (was falsely colliding on recurring same-amount payments).
- Backfill complete: 27,879 paid invoices, $12.16M lifetime, **$194,545 trailing 365d**.
- `streasury-sync.service` + `streasury-sync.timer` installed on secondary, fires every 30 min.

### Side fixes
- **`streasury-bot.service` was silently broken on every DB call** for ~24 hours. The `DATABASE_URL` in env had `?host=/var/run/postgresql` pointing at a non-existent socket. Replaced with TCP, restarted bot. `/health` now returns OK.
- **Primary's SSH pubkey** was added to legacy's `authorized_keys` so cockpit's snapshot.sh can poll it.

---

## Verified facts to share

- **Outbounders revenue rate (paid invoices, trailing 365d):** $194,545.34
- **Trailing 30 days:** $14,838.00
- **Trailing 90 days:** $48,019.00
- **Lifetime (since 2012-08):** $12,159,907.41 across 27,879 paid invoices
- **Active customer base:** 6,409 clients, 71 logged in last 30d (1.1%); 6,200 agents, 149 logged in last 30d (2.4%)
- **Total monthly cost:** ~$805/mo (servers $474, AI tools $300, API $30-50, domains $1)
- **Net burn:** ~$805/mo cost vs ~$15k/mo cash revenue from Outbounders → currently **net positive**, contrary to NOW.md's "runway" framing

---

## Open questions for James

### Operational (small, blocking)

1. **Zen Village morning digest** is failing with `400 Bad Request` from `https://brain.zenvillagecr.com/gotrue/token?grant_type=password`. Started Apr 29. Need new credential to put in `/etc/zen-village/telegram.env` on secondary. (You probably haven't been getting your morning digest for ~2 days.)

2. **Old DB password rotation.** The credential `G9$1I_a4-KNu!rE.` is hardcoded in:
   - `/opt/ob_dashboard.py` on legacy (the live dashboard)
   - `.workspace/active/outbounders_live_dashboard.py` on James's Mac (untracked, but `.workspace/` not gitignored)
   Now that `streasury_ro` exists as proper read-only credential, the old one could be rotated/removed. Needs coordination with whoever runs `ob-dashboard.service`.

### Security (flagged in inventory)

3. **`fail2ban` is failed on secondary.** The box runs financial tools (Firefly III, streasury, AppFlowy). Failed = no brute-force protection. Should be revived.

4. **Postgres on primary bound to public IP** (`198.54.123.234:5432` instead of `127.0.0.1:5432`). Anyone on the internet can attempt connections. Should be rebound.

5. **`certbot` failed on secondary** — cert renewals will miss. Should be looked at before next renewal cycle.

### Strategic (needs James's judgment)

6. **The "paused" services in NOW.md aren't actually paused.** Concierge stack (13 services), WhaleTrack stack (6 services), credits-gateway, cocoon, AI brain on secondary, are all running per `systemctl`. James confirmed in this session: WhaleTrack is intentionally still running, Concierge is in active development. The "paused" framing in NOW.md was wrong. NOW.md hasn't been updated yet — should it be? Or should the truly-paused services (consciousness stack on secondary?) be stopped to free RAM (primary has only 1.9G free)?

7. **The 39 cPanel accounts on legacy** are mostly opaque. Many look like dead/dormant projects (jamesrick, jamesrickstinson, fparchive, sunheart2, maschristo, delray, fullbhza). Per-account activity audit could surface zombies eating disk (legacy is at 66% / 1.2T used). Worth doing? It's a 30-min job.

8. **Outbounders revenue ($200k/yr) wasn't visible to NOW.md or any cockpit before this session.** Now that it is, does it change the strategic priorities? Currently P1 is still Zen Village retreat, but Outbounders is the only confirmed revenue surface — does it deserve more attention than "don't break it"?

9. **Cross-tool memory bridge (`sunheart-brain` on secondary):** Cursor pushes conversations into it (4,783 chunks, last Cursor push 2026-04-25, last Claude push 2026-04-28). Verify whether Claude Code actually reads back from it, or whether the bridge is one-way. If one-way, it's wasted infrastructure.

### Long-running

10. **Recurring system inventory.** This session built a one-shot SSH-based inventory. To keep "truth of what's going on" current, the next iteration is a daily diff into Telegram (only surface what changed vs yesterday). Not built yet. Decision pending: build it on streasury-bot's secondary, or extend cockpit on primary?

---

## Key infrastructure facts (so other Claude doesn't have to rediscover)

### Servers
- **Primary** `198.54.123.234` (Ubuntu 22.04, 7.7G RAM, 87 days uptime). FPAI services + Zen Village booking + nginx + Postgres. RAM tight (1.9G free).
- **Secondary** `162.0.208.88` (Ubuntu 22.04, 31G RAM, 152 days). AppFlowy Cloud, sh-brain, Firefly III, Paperless-ngx, n8n, Ollama, streasury-bot. Plenty of headroom.
- **Legacy** `209.74.93.72` (CloudLinux 9.6, 125G RAM, **342 days uptime — no kernel updates in nearly a year**). cPanel + 39 sites. Hosts Outbounders.com production. Disk 66% full.

### SSH access
- This Mac has direct SSH to all three (root). Pubkey on each.
- Primary can SSH to legacy + secondary using `/root/.ssh/id_ed25519` (cockpit pattern).

### Where the streasury work lives
- Source repo: `SERVICES/streasury-bot/` in this monorepo
- Deployed to: `/opt/streasury-bot/` on secondary (`162.0.208.88`)
- Database: Postgres in `sh-brain-postgres` docker container, exposed on `127.0.0.1:25432`, schema `streasury` in DB `fpai_brain`
- Run as: user `streasury`, env file `/etc/streasury-bot/streasury.env` (mode 600)
- Bot service: `streasury-bot.service` (always on, port 8620)
- Sync service: `streasury-sync.service` (oneshot) + `streasury-sync.timer` (every 30 min)

### Where the Outbounders data lives
- Server: `209.74.93.72` (legacy)
- DB: MariaDB 10.11.15, database `obapp_outbounders` on port 3306
- Read-only user: `streasury_ro@'162.0.208.88'` with SELECT on `obapp_outbounders.*`
- Source schema: `main_invoice` (paid IN ('P','Y') filter), `main_users`, `main_transaction`
- Live dashboard: `ob-dashboard.service` on legacy port 8960 (password `outbounders2026`, firewalled externally)

### Things that exist but you probably don't need
- `god-mode` service (paused per NOW.md, but unit files exist on primary)
- `autonomous-brain.service` on secondary — was never started; legacy's `fpai-health-agent.service` was pushing health data to it for nothing
- `docs/coordination/*` — most archival, only ~35 entries actively referenced by code

---

**Bottom line for other Claude:** The hard plumbing is done. Next moves are James-decisions (questions above) plus operational small-fixes (security flags). If James asks "what's next," default to surfacing the open questions list and let him pick — don't start new work without alignment on which question to act on.
