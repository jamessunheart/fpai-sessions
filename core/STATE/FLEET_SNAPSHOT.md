# FLEET SNAPSHOT — live server truth

**Verified:** 2026-06-12 17:24 UTC via read-only SSH survey (session f98f2f16)
**Refresh rule:** re-survey on any infra task, or when >14 days old. Each fact below carries the verified-at date of this header — if this file is stale, trust the servers, not this file.
**Companions:** `docs/codex/HOST_REGISTRY.md` (access lanes) · `docs/codex/SERVICE_REGISTRY.md` (repo-side service scan) · memory `reference_server_access.md` + `reference_fleet_stream_map.md`

---

## 198.54.123.234 · zen-host — PRIMARY APP FLEET

- Uptime 130d · disk 22% · 🔴 **RAM-saturated: 193M free of 7.9G, swap 2.8G/4G used**
- **28 FP services running:** zen-village (8770) · zv-wallet · zen-village-bot · fp-game-bot · fpai-{credits-gateway, fp-index, chief-of-staff, nerve-center, lead-capture, alerts, ad-portal, apprentice-gateway, cocoon, proactive-monitor, projects} · whaletrack-{live, magnet, telegram-bot, bridge-btc/eth/sol/xrp} · concierge-outbound-engine · sapphire-bot · jsservers-bot · nocodb · postgresql@14
- 🔴 **postfix FAILED since 2026-04-30 (6 weeks). Ports 25/587 NOT listening.** Dovecot up (993). This box cannot send/receive SMTP directly. Outbound relays via Brevo (per mail-stack memory) — INBOUND path needs verification.
- Server-only state: `/opt/fpai/BOOT.md` (stale 2025-11-17) · `apps/ACTUAL_SYSTEM_STATE.md` · `LIVE_SERVICES_REPORT.md` · `api_keys.json` · `hyperliquid_credentials.json`
- Web roots: fullpotential.ai · zenvillage-live · whiterock · cheyenne-sapphire · marketplace · church-guidance-funnel

## 162.0.208.88 · fpai-substrate — BRAIN

- Uptime 195d · disk 26% · RAM healthy (19G avail of 32G)
- **19 FP services running:** ai-brain v4.0 · brain-mesh-gateway · sh-brain-{index, tgbot} · sh-mcp-http · zv-mcp-http · zv-telegram-bot · **intake-agent (ACTIVE — Cal.com+TG wired, 30s poll)** · kai-bridge · memory-bus · reasoning-engine · legal-critic · streasury-bot · fpai-{ai-gateway, lead-capture, voice-caller} · gpu-bridge · infra-metrics · security-watch
- 🟡 Failed: **certbot** (cert-renewal risk) · **fail2ban** (brute-force protection down) · fpai-vnc-desktop · zv-morning-digest
- 🟡 Drift: `/opt/fpai/NOW.md` last updated **2026-04-14** (2 months behind laptop) · own FPAI_Cockpit clone · `system-handoff.json` v1.0 (2026-03-15)
- Reachable via plain SSH (old "tailscale-only" note is wrong)

## 209.74.93.72 · server1.outbounders.com — cPanel/WHM

- Uptime 385d · 🟡 disk **67%** (1.2T/1.8T — watch) · RAM healthy (115G avail of 128G)
- FP services: fpai-health-agent · ob-dashboard
- 🟡 Failed: cpgreylistd · ea-php72-php-fpm (EOL PHP 7.2) · irqbalance
- Hosts 39 cPanel accounts incl. outbounders.com, sunheart.ai

---

## CORRECTIONS this snapshot makes to prior memory

1. ✅ **intake-agent is RUNNING** — `reference_fleet_stream_map.md` ("intake FAILING, revenue funnel broken") was stale. Corrected 2026-06-12.
2. 🔴 **postfix dead 6 weeks** on the mail host — new finding, was not tracked anywhere.
3. 🟡 **Server-side NOW.md copies are months stale** — servers must not be treated as canonical for priorities; laptop repo wins (per SSOT_REGISTRY.md).

## OPEN ITEMS (for James / integration session)

- ☐ 🔴 postfix on 198: decide — repair (if inbound mail matters) or formally retire SMTP on this box (outbound already via Brevo)
- ☐ 🟡 certbot + fail2ban on 162: restart/repair (security + cert renewal)
- ☐ 🟡 198 RAM saturation: candidates to stop = cruft services (cocoon, whaletrack-magnet?) per NOW.md cruft-watch
- ☐ 🟡 Delete or repoint stale `/opt/fpai/NOW.md` on 162 (no live consumer per NOW.md latent notes)
