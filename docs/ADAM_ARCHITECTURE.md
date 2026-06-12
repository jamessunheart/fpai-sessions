# ADAM ARCHITECTURE — Post 2026-04-24 Optimization

Adam is the OpenClaw agent on secondary server `162.0.208.88`. Role per `NOW.md`: **Telegram relay to James** for the Zen Village engine.

## One-Line Mental Model

```
Telegram (@Adamclaw_bot) → OpenClaw Gateway → metaclaw (proxy) → Claude/Ollama → reply
```

Anything more elaborate than that (consciousness loops, heartbeat chains, self-healing daemons) has been pruned. Adam should feel boring.

## Servers

| Server | IP | Role |
|--------|-----|------|
| Primary | `198.54.123.234` | Web, trading, revenue, data (Zen Village site, WhaleTrack, etc.) |
| Secondary | `162.0.208.88` | **Adam lives here**. AI/Ollama/consciousness (most paused) |

## Adam's Core Stack (Secondary Server)

| Component | Port | Status | Purpose |
|-----------|------|--------|---------|
| `openclaw-gateway.service` (systemd --user, root) | 18789 | **running, auto-restart** | Main gateway, handles Telegram polling + message routing |
| `metaclaw` (python module) | 30000 | running | Model proxy — routes to Claude via Anthropic API |
| `ollama` | 11434 | running | 8 local models, $0/call. Primary: `llama3.2:3b` |
| `ai-brain.service` | 8101 | running | Shared AI brain (optional) |
| `shared-brain API` | 8770 | available | Cross-instance memory (used on Mac Mini setup) |

## Security — smartest Adam (Sonnet path)

| Layer | What to enforce | On secondary (`162.0.208.88`) |
|--------|------------------|-------------------------------|
| **OpenClaw gateway** | Not on the public internet; auth on | `gateway.bind` = **loopback**, `gateway.mode` = **local**, `gateway.auth` token set. Listens **`127.0.0.1:18789`** only. |
| **MetaClaw (Claude proxy)** | **Loopback only** — was `0.0.0.0:30000` (world-reachable) by default | **`~/.metaclaw/config.yaml`** → `proxy.host: 127.0.0.1`, `proxy.port: 30000`. OpenClaw already uses `http://127.0.0.1:30000/v1`. After edits: `systemctl restart fpai-metaclaw.service` — confirm `ss` shows **`127.0.0.1:30000`**, not `0.0.0.0`. |
| **Brain Mesh** | Local + bearer policy | **`127.0.0.1:8860`**, tokens in `/etc/brain-mesh/policy.json`; adapter rate limits in `brain-mesh.env`. |
| **Telegram** | Only you (and paired DMs) drive the bot | **`dmPolicy: pairing`**, `groupPolicy: allowlist` in `openclaw.json` `channels.telegram`. Keep **`@Adamclaw_bot`** token out of chat; rotate via BotFather if leaked. |
| **Secrets on disk** | Root-only | `chmod 600` on **`~/.metaclaw/config.yaml`**, **`/root/.openclaw/openclaw.json`** (contains provider keys), **`secrets/brain-mesh.env`**. |
| **Host firewall (optional)** | Belt-and-suspenders | If any service ever binds `0.0.0.0` again, **`ufw`** / cloud SG: allow **22/443** (and what you need), deny inbound **18789**, **30000**, **8860** from the internet. |

**Revert Ollama-first Telegram (quality):** run `infrastructure/tools/disable_openclaw_telegram_ollama_route.py` so your DMs use **`main`** + full Sonnet, not a local model first.

## Survival Guarantees

1. **Auto-restart**: `systemctl --user enable openclaw-gateway.service` + `loginctl enable-linger root`. Unit has `Restart=always`, `RestartSec=5`. Verified recovery in **8 seconds** after SIGKILL.
2. **Regression test**: `/opt/fpai/tests/test_openclaw_autorecover.sh` — runs the kill-and-recover cycle. Exit 0 = pass.
3. **Trimmed PULSE**: `/opt/fpai/pulse/heartbeat.py` now monitors only the 3 services that keep Adam alive (openclaw_gateway, metaclaw, ai_brain). Other services don't trigger escalations.

## Regenerative Tools (all in `/opt/fpai/openclaw/workspace/tools/`)

| Tool | What it does | Cost |
|------|--------------|------|
| `ollama-ask.sh "<prompt>" [model]` | Local inference via Ollama | $0 |
| `daily-zv-check.sh` | Cron 08:00 UTC — scan `NOW.md` for unchecked ZV commitments, Telegram James if any | $0 (Telegram sendMessage free) |
| `adam-daily-log.sh` | Cron 23:59 UTC — write daily P&L to `/opt/fpai/logs/adam_daily_value.log` | $0 |

`NOW.md` sync: lives at `/opt/fpai/NOW.md` on server. When James edits the local copy (`/Users/jamessunheart/FPAI_Cockpit/core/STATE/NOW.md`), re-sync with `scp NOW.md root@162.0.208.88:/opt/fpai/NOW.md`.

## Daily P&L Format

`/opt/fpai/logs/adam_daily_value.log`:

```
2026-04-24 | claude=46 $1.38 | ollama=0 $0 | james_tg=3 wa=4 | cron=1 heartbeat=1
```

Self-throttle triggers:
- `>50 Claude calls` AND `0 James interactions` → `[SELF-THROTTLE]` alert
- `>100 Claude calls` → `[HIGH-BURN]` alert

## What We Killed (Do Not Restart Without Reason)

| Service | Why killed | Cost saved |
|---------|------------|------------|
| `cora-loop.service` (systemd) | Generated strategic directives not aligned with ZV | ~$7.50/mo |
| PULSE memory-staleness loop | False alarms firing every 30 min | ~$35/mo |
| `aria-command.service` | 83,698 recorded failures, no API key, port 8750 unused | Ongoing CPU + mem0.ai pollution |
| `aria-memory.service` | Hourly OpenAI call producing "0 insights" | ~$X/mo OpenAI |
| `jobs.json` "Evening Breaking News Check" cron | Used `kimi` model (no key), not ZV-aligned | ongoing errors |
| `shared-brain.sh pending` cron (5 min) | Target dead, log spam only | noise |

To bring any back: `systemctl start <service>` or edit `/root/.openclaw/cron/jobs.json` and set `enabled=true`.

## Adam's Charter

`/opt/fpai/openclaw/workspace/ADAM_CHARTER.md` — Adam's self-authored survival doc, amended by James + fixer agent. Defines what regenerative behavior looks like. Read first if doing anything that affects Adam's token budget.

## Debugging Playbook

| Symptom | First check |
|---------|------------|
| Telegram unresponsive | `./adam status`, `./adam health` (from `/Users/jamessunheart/FPAI_Cockpit/`) |
| Gateway crashed | `journalctl --user -u openclaw-gateway -n 50` |
| High cost surprise | `tail /opt/fpai/logs/adam_daily_value.log` |
| "409 Conflict" Telegram error | Ghost poller exists — rotate bot token via BotFather |
| PULSE noisy | `tail /opt/fpai/pulse/logs/*.log` — confirm only 3 services monitored |

## Open Items (Require James Decision)

1. **Rotate `@Adamclaw_bot` token** via BotFather to kill 409-conflict ghost poller.
2. **Upgrade openclaw** `v2026.2.9` → `v2026.4.23` (backup + test before).
3. **Purge dead systemd units** (`aria.service`, `fpai-consciousness_network.service`, `gpu-bridge.service`, `fpai-ad-monitor.service`) — currently inactive but units exist.

## Last Verified

- 2026-04-24 18:51 UTC: Adam healthy, Telegram responding in 888ms, auto-restart verified (8s recovery), daily scripts smoke-tested, all known token-burn loops eliminated.

## Transcript Reference

Full optimization session: [Fix Adam and optimize for ZV](3bf759eb-2c3b-4318-a57c-bebc0a97ac7d)
