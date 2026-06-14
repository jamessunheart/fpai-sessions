# Zen Village Brain — Telegram Bot

Ground-team interface to the brain. Short messages in Telegram → structured
rows in AppFlowy, with local Ollama (free) doing the natural-language parsing.

- **Bot handle:** `@zenvillagebot`
- **Webhook:**  `https://flow.zenvillagecr.com/tg/webhook`
- **Service:**  `zv-telegram-bot.service` on Secondary (162.0.208.88)
- **Port:**      127.0.0.1:8700 (only nginx talks to it)
- **Logs:**      `/var/log/zv-telegram.log`

## First-time onboarding (Sunheart)

1. Open Telegram → search `@zenvillagebot` → tap **Start**.
2. The bot is in **setup mode** (no allowlist yet). It will reply with **your Telegram user_id**.
3. Copy that number and add it to the allowlist:
   ```bash
   ssh root@162.0.208.88
   # edit /etc/zen-village/telegram.env and set:
   #   ZV_TG_ALLOWED_IDS=<your-id>
   #   ZV_TG_ADMIN_IDS=<your-id>
   systemctl restart zv-telegram-bot
   ```
4. Say `/status` — you should see row counts for all 7 databases.
5. Add Atlas and ground-team members by appending their ids to `ZV_TG_ALLOWED_IDS`
   (comma-separated) and restarting.

## Commands

| Command | Example | What it does |
|---|---|---|
| `/status` | `/status` | Health + row counts for every DB |
| `/add` | `/add Call retreat venue Monday` | Add row to Master List |
| `/find` | `/find Atlas` | Keyword search (people by default) |
| `/decide` | `/decide Launch Ecstatic Weekend May 10` | Log a decision |
| `/event` | `/event Sound Healing June 2` | Create event row |
| `/whoami` | `/whoami` | Show your Telegram user_id |
| `/help` | `/help` | Reprint this table |

Or just type normally — the bot parses intent with `llama3.1:8b` and falls
back to `mistral:7b` as a cross-check. Examples:
- _"Remind me to call the retreat venue Monday, high priority"_
- _"Who's on the ground team?"_
- _"Decided: launching Ecstatic Weekend May 10. Rationale: capacity booked."_

## Ops

```bash
# Status + logs
systemctl status zv-telegram-bot
journalctl -u zv-telegram-bot -n 200 --no-pager
tail -f /var/log/zv-telegram.log

# Re-register webhook after domain/cert change
TOKEN=$(grep ^TELEGRAM_BOT_TOKEN /root/zen-village-secrets/appflowy.env.secrets | cut -d= -f2)
SECRET=$(grep ^TELEGRAM_WEBHOOK_SECRET /root/zen-village-secrets/appflowy.env.secrets | cut -d= -f2)
curl -sS -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -d "url=https://flow.zenvillagecr.com/tg/webhook" \
  -d "secret_token=${SECRET}"

# Rotate token (if leaked)
#   1. /revoke with BotFather → receive new token
#   2. sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=<new>|" /root/zen-village-secrets/appflowy.env.secrets
#   3. also update /etc/zen-village/telegram.env
#   4. systemctl restart zv-telegram-bot
#   5. re-run setWebhook above
```

## Files

- `bot.py` — FastAPI app, intent parser, command handlers
- `requirements.txt` — pinned deps (fastapi, uvicorn, httpx, mcp)
- `zv-telegram-bot.service` — systemd unit
- `nginx-flow-telegram.conf` — nginx snippet (already injected into the flow vhost)

## Failure modes + recovery

| Symptom | Likely cause | Fix |
|---|---|---|
| Bot doesn't reply | uvicorn down | `systemctl restart zv-telegram-bot` |
| Replies but "something broke on my end" | AppFlowy token expired | bot auto-reloads; check `/var/log/zv-telegram.log` for specific error |
| Intent parsing is slow/wrong | Ollama under load | check `curl http://127.0.0.1:11434/api/tags`, consider switching to `llama3.2:3b` |
| Unauthorized user messages | Setup mode still on | add ids to `ZV_TG_ALLOWED_IDS` |
| 401 from Telegram on webhook | secret mismatch | re-run setWebhook with the correct secret |

## Cost

- **$0/mo.** Telegram Bot API is free; Ollama is local; no third-party LLM
  calls in the hot path.
