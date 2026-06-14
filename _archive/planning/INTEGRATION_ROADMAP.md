# 🔗 Integration Roadmap: Alerts + Treasury → Unified Telegram Digest

**Status:** Two streams deployed, integration point identified
**Next:** Build the daily digest aggregator

---

## 🎯 The Convergence Point

**Both streams feed the same surface:** One Telegram bot (@sunheartbrain_bot), one morning digest (9am)

### Stream 1: Alerts/Monitoring (deployed 2026-04-30)
- ✅ Proactive Monitor checks 5 services every 5 min
- ✅ Chief of Staff filters signals (30-day decision criteria)
- ✅ Telegram bot connected to Sunheart Brain
- 🔲 Daily digest aggregator (not built yet)

### Stream 2: Treasury/Observability (deployed 2026-04-30)
- ✅ Outbounders revenue ($194k/yr) → streasury-bot every 30 min
- ✅ System inventory across 3 servers
- ✅ Cockpit polls all servers every 5 min
- 🔲 Revenue summary API (not exposed yet)

---

## 📊 What the 9am Digest Should Show

```
🌅 Good morning! Daily System Digest — 2026-04-30

💰 REVENUE (Last 24h)
- Outbounders: $540 (3 invoices paid)
- Trend: ↑ 12% vs yesterday
- Trailing 30d: $14,838

🚨 ALERTS (Overnight)
- 2 important signals
  • whaletrack-magnet slow response (3.2s avg)
  • credits-gateway 2 timeouts
- 0 urgent (good!)

🖥️ SYSTEM HEALTH
- Primary: ✅ 1.9GB RAM free (tight)
- Secondary: ✅ 12GB free
- Legacy: ✅ 342d uptime (kernel update needed)
- Services: 23/25 healthy

📌 ACTION ITEMS
- [ ] Check whaletrack response times
- [ ] Review credits-gateway logs

Full status: fullpotential.ai/cockpit/status/
```

---

## 🔧 What Needs to Be Built

### Option A: Extend Chief of Staff (Recommended)

**Why:** Chief of Staff already filters signals, this is just adding data sources

**Add to Chief of Staff (8107):**
1. `/digest/generate` endpoint
2. Fetches from:
   - Internal signal storage (already has this)
   - `http://162.0.208.88:8620/api/revenue/summary?period=24h` (needs streasury API)
   - `http://198.54.123.234/cockpit/status/health` (cockpit has this)
   - `http://localhost:8108/status` (proactive monitor)
3. Formats into Markdown message
4. Returns digest

**Add cron job on server:**
```bash
# /etc/cron.d/chief-digest
0 9 * * * root curl -X POST http://localhost:8107/digest/deliver
```

**Estimated:** 1-2 hours work

---

### Option B: Separate Digest Service (Over-engineering)

**Why avoid:** Adds complexity, another service to maintain

---

## 🚧 Blockers to Resolve First

### 1. streasury-bot needs revenue summary API

**Current:** streasury-bot has `/balance` and `/report month` for Telegram commands
**Needed:** HTTP API endpoint that returns JSON:

```python
GET /api/revenue/summary?period=24h

Response:
{
  "period": "24h",
  "total": 540.00,
  "count": 3,
  "change_pct": 12.5,
  "trailing_30d": 14838.00
}
```

**Add to:** `SERVICES/streasury-bot/app/main.py`
**Estimated:** 30 min

### 2. Cockpit needs health summary endpoint

**Current:** Cockpit has full HTML status page
**Needed:** JSON endpoint for programmatic access:

```python
GET /cockpit/status/health.json

Response:
{
  "primary": {"status": "healthy", "ram_free_gb": 1.9},
  "secondary": {"status": "healthy", "ram_free_gb": 12.0},
  "legacy": {"status": "healthy", "uptime_days": 342},
  "services_healthy": 23,
  "services_total": 25
}
```

**Add to:** Cockpit's `snapshot.sh` or FastAPI wrapper
**Estimated:** 30 min

---

## 📋 Implementation Steps (Recommended Path)

### Phase 1: Expose Data (1 hour)
1. Add `/api/revenue/summary` to streasury-bot
2. Add `/cockpit/status/health.json` to cockpit
3. Test both endpoints

### Phase 2: Build Digest (1 hour)
1. Add `/digest/generate` to Chief of Staff
2. Fetch from all 4 sources
3. Format Markdown
4. Test generation

### Phase 3: Deliver Daily (30 min)
1. Add `/digest/deliver` to Chief of Staff (calls generate + sends to Telegram)
2. Add cron job for 9am delivery
3. Test end-to-end

**Total estimated time:** 2-3 hours

---

## 🔍 Alternative: Start with Manual Digest

**Quickest path to value:** Skip cron, just build `/digest/generate` and call it manually

James can trigger:
```bash
curl http://198.54.123.234:8107/digest/generate | \
  xargs -I {} curl -X POST http://198.54.123.234:8766/send \
    -d '{"channel":"telegram","recipient":"default","message":"{}"}'
```

Then add cron later once format is validated.

---

## 🎯 Decision Point

**Question for James:**

1. **Build the daily digest now?** (2-3 hours)
   - Pro: Complete the integration, see value immediately
   - Con: More code before validating format

2. **OR address security/operational flags first?** (from treasury handoff Q3-Q5)
   - fail2ban failed on secondary
   - Postgres on primary bound to public IP
   - certbot failed on secondary

3. **OR resolve strategic questions first?** (from treasury handoff Q6-Q10)
   - Update NOW.md with real service status
   - Audit cPanel zombies on legacy
   - Decide if Outbounders deserves more attention

**Default recommendation:** Build digest endpoints (Phase 1+2), test manually, then ask James if format is good before adding cron. Gives immediate value without committing to automation.

---

## 📚 References

- **Alerts handoff:** `docs/coordination/ALERTS_SYSTEM_HANDOFF.md`
- **Treasury handoff:** `infra/audits/inventory_2026-04-30_1246/HANDOFF.md`
- **Chief of Staff code:** `SERVICES/chief-of-staff/app/main.py`
- **Streasury code:** `SERVICES/streasury-bot/app/main.py`
- **Cockpit code:** `/opt/fpai/cockpit/status/snapshot.sh` on primary

---

**Bottom line:** The plumbing exists, the integration point is clear (daily digest), the work is 2-3 hours. The blocker is: which of the 10 open questions should be addressed first, or should we complete the digest integration before addressing any of them?
