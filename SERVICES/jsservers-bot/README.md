# JSServers Bot

Telegram bot that gives James a secure, mobile-friendly view of FPAI infrastructure: server health, service status, websites, signals, and strategic AI state.

**Bot:** [@JSServers_bot](https://t.me/JSServers_bot)
**Lives on:** Primary server (`198.54.123.234`)
**Deploy path:** `/opt/fpai/jsservers-bot/`
**systemd unit:** `jsservers-bot.service`

## What it does

Aggregates data from systems already running on primary + secondary:

- `fpai-cockpit-status` — operational state (RAM/services/errors) cross-server
- `/opt/fpai/pulse/state.json` (secondary) — strategic AI health, goals, blockers
- `/opt/fpai/learnings.json` — last error→learning entries
- Direct `/health` probes — for live up/down checks
- Direct HTTPS probes — for public-facing site liveness

## Commands

| Command | What it shows |
|---|---|
| `/start` | Welcome + command list |
| `/status` | One-screen overview: RAM, load, services up/down, sites |
| `/services` | Per-service up/down/unhealthy across both servers |
| `/health` | Live `/health` probes of critical services |
| `/sites` | Public site HTTPS status (zenvillagecr.com, fullpotential.ai, brain.sunheart.com, app.outbounders.com) |
| `/signals` | Latest WhaleTrack signals |
| `/pulse` | Strategic AI state (health 0-100, current goals, blockers) |
| `/learnings` | Last 5 entries from `/opt/fpai/learnings.json` |
| `/costs` | Monthly spend across servers + APIs, total, kill-candidate savings |
| `/whoami` | Your Telegram user ID (useful for whitelist setup) |

**Natural language also works.** "how are things", "are sites up", "show me costs", "what's our spend", "any blockers" — all routed to the matching command via keyword matching.

## Updating costs

Costs are baked into `bot.py` as `DEFAULT_COSTS` (sourced from `core/STATE/NOW.md`). To override without redeploying code, drop a JSON file at `/opt/fpai/jsservers-bot/costs.json`:

```json
{
  "servers": [
    {"name": "Primary", "monthly_usd": 69.88, "serves_engine": true, "purpose": "..."}
  ],
  "apis": [
    {"name": "Anthropic", "monthly_usd_low": 30, "monthly_usd_high": 50, "purpose": "..."}
  ],
  "notes": "..."
}
```

Then `systemctl restart jsservers-bot`.

## Security model

- **Token:** stored in `/root/.jsservers-bot.env` on primary, mode 600. Never in repo, never in logs.
- **Whitelist:** `ALLOWED_USER_IDS` env var, comma-separated. Bot replies politely to anyone else but reveals nothing.
- **Discover mode:** if `ALLOWED_USER_IDS=DISCOVER`, bot logs every user ID that messages it and replies with their ID. Used once on first deploy to learn James's ID, then locked down.
- **Token rotation:** rotate immediately after first deploy via [@BotFather](https://t.me/BotFather) → `/revoke` (the original token was leaked into a chat transcript). Update `/root/.jsservers-bot.env` and `systemctl restart jsservers-bot`.

## Files

```
SERVICES/jsservers-bot/
├── README.md           # this file
├── bot.py              # main bot logic
├── requirements.txt    # python-telegram-bot, requests
├── jsservers-bot.service  # systemd unit
└── deploy.sh           # one-shot install/update script (run from local)
```

## Deploy

```bash
# First-time deploy (in DISCOVER mode):
./SERVICES/jsservers-bot/deploy.sh

# After James messages the bot once, lock the whitelist:
./SERVICES/jsservers-bot/deploy.sh --user-ids 123456789
```

## Maintenance

```bash
# Logs
ssh -i ~/.ssh/fpai_deploy_ed25519 root@198.54.123.234 'journalctl -u jsservers-bot -n 50 --no-pager'

# Restart
ssh -i ~/.ssh/fpai_deploy_ed25519 root@198.54.123.234 'systemctl restart jsservers-bot'

# Status
ssh -i ~/.ssh/fpai_deploy_ed25519 root@198.54.123.234 'systemctl status jsservers-bot'
```
