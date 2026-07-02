# FLEET SNAPSHOT — live server truth

**Verified:** 2026-07-02 03:14 UTC via read-only SSH survey (session 23537d81)
**Refresh rule:** re-survey on any infra task, or when >14 days old. Each fact below carries the verified-at date of this header — if this file is stale, trust the servers, not this file.
**Companions:** `docs/codex/HOST_REGISTRY.md` (access lanes) · `docs/codex/SERVICE_REGISTRY.md` (repo-side service scan) · memory `reference_server_access.md` + `reference_fleet_stream_map.md`

---

## 198.54.123.234 · zen-host — PRIMARY APP FLEET

- Uptime 150d · disk 23% · 🟡 RAM: 1.27G free of 7.9G, swap 2.8G/4G used (improved from 193M free on 06-12, still swap-heavy)
- **38 FP services running** (was 28 on 06-12)
- 🔴 **postfix STILL FAILED (since 2026-04-30, now 9 weeks).** This box cannot send/receive SMTP directly. Outbound relays via Brevo — INBOUND path still needs verification.
- Server-only state: `/opt/fpai/BOOT.md` (stale 2025-11-17) · `apps/ACTUAL_SYSTEM_STATE.md` · `api_keys.json` · `hyperliquid_credentials.json`
- Web roots: fullpotential.ai · zenvillage-live · whiterock · cheyenne-sapphire · marketplace · church-guidance-funnel

## 162.0.208.88 · fpai-substrate — BRAIN

- Uptime 215d · disk 27% · RAM healthy (24G avail of 32G)
- **22 FP services running** · build loop timer ACTIVE (10-min cadence, drains correctly, auto-merge live — d137)
- 🟢 certbot.timer active (renewal risk from 06-12 resolved — the failed `certbot.service` unit is the oneshot, timer is what matters)
- 🔴 **fail2ban failed — root cause FOUND 2026-07-02:** `/etc/fail2ban/jail.local` line 13 has a duplicate `[sshd]` section header. Fix = delete line 13 (its `ignoreip` line then merges into the first `[sshd]` block). Classifier blocks AI from editing security config — **James runs:** `ssh root@162.0.208.88 'cp /etc/fail2ban/jail.local /etc/fail2ban/jail.local.bak && sed -i 13d /etc/fail2ban/jail.local && systemctl restart fail2ban'`
- 🟡 Other failed: hive-daemon · zv-morning-digest · systemd-networkd-wait-online
- Governance layer (CONSTITUTION.md / OPERATING_PRINCIPLE.md / LEARNING_METRICS.md) landed on feat/headless-build 2026-07-02 (`0c0497e`)

## 209.74.93.72 · server1.outbounders.com — cPanel/WHM

- Uptime 404d · 🟡 disk **70%** (1.2T/1.8T — up from 67% on 06-12, watch trend)
- RAM healthy (116G avail of 128G)
- 🟡 Failed: cpgreylistd · ea-php72-php-fpm (EOL PHP 7.2) · irqbalance
- 🟡 SSH warns: no post-quantum key exchange (server OpenSSH old)
- Hosts 39 cPanel accounts incl. outbounders.com, sunheart.ai

---

## CORRECTIONS this snapshot makes to prior state

1. 🟢 **198 RAM pressure eased** — 1.27G free (was 193M). Swap use unchanged; keep cruft-stop candidates on the list but urgency down.
2. 🟢 **certbot on 162 is fine** — timer active; 06-12 flag was reading the oneshot service unit.
3. 🔴 **fail2ban root cause diagnosed** (duplicate section) — fix is a one-liner, James-gated (security config).
4. 🟡 **209 disk crept 67% → 70%** in 19 days — ~0.16%/day; at this rate ~6 months to 90%.

## OPEN ITEMS (for James / integration session)

- ☐ ⚡ 🔴 fail2ban fix one-liner (above) — 30 seconds, restores brute-force protection
- ☐ 🔴 postfix on 198: decide — repair (if inbound mail matters) or formally retire SMTP on this box (outbound already via Brevo)
- ☐ 🟡 209 disk trend: identify top growth dirs before it becomes urgent
- ☐ 🟡 198 swap still heavy: cruft services (cocoon, whaletrack-magnet?) per NOW.md cruft-watch
