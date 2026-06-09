# sapphire-bot — @LilSapphirebot

Cheyenne Sapphire's personal AI co-pilot on Telegram. Lead intake, pipeline tracking, drafts in her voice, and a memory that grows as she teaches it.

## Architecture

- **Long-polling Telegram worker** (no webhook, no public port).
- **SQLite** at `/var/lib/sapphire-bot/sapphire.db` — full conversation log, business facts, leads.
- **Anthropic Claude** (Sonnet 4.6 by default) for natural conversation. The system prompt is dynamically assembled per turn from the `business_facts` table — that's how the bot grows its memory.
- **Owner gate**: only Cheyenne's Telegram ID can use the privileged commands. First `/start` with no owner set auto-claims ownership.

## Files

```
main.py                  # bot worker (long-polling getUpdates)
requirements.txt         # httpx
sapphire-bot.service     # systemd unit
deploy.sh                # rsync + systemd deploy to PRIMARY
```

## First deploy

Both keys live ONLY in `/etc/sapphire-bot/sapphire-bot.env` on the server (chmod 600). Never commit them.

```bash
SAPPHIRE_BOT_TOKEN="<bot-token-from-BotFather>" \
ANTHROPIC_API_KEY="<sk-ant-...>" \
bash SERVICES/sapphire-bot/deploy.sh
```

Optional: `OWNER_TG_ID=<cheyenne-tg-numeric-id>` to lock ownership before first `/start`. If omitted, whoever sends `/start` first becomes owner — tell Cheyenne to do it before anyone else finds the bot.

## Commands

Owner-only:

| command | purpose |
|---|---|
| `/start`, `/help` | menu |
| `/teach <fact>` | add a durable business fact to the bot's memory |
| `/memory` | list all stored facts with ids |
| `/forget <id>` | drop a fact |
| `/lead Name \| contact \| notes` | log a lead (pipe-separated, any field optional) |
| `/leads [status]` | show pipeline (optional: filter by status) |
| `/status <id> <new\|qualified\|replied\|booked\|lost>` | update lead status |
| `/draft <paste lead msg>` | Sapphire drafts a reply in Cheyenne's voice |
| `/digest` | morning summary — new in last 24h, qualified-but-stale |

Anything that's not a slash command is a real conversation with full context (last 20 turns + all stored facts as system prompt).

Non-owners get a warm "Cheyenne will see this" acknowledgment and the message is auto-logged as a lead.

## Memory model

Three tables, all in `sapphire.db`:

- **`messages`** — full transcript (chat_id, role, content, ts). Never truncated. Used both for conversation context and for future "what did we talk about last week" recall.
- **`business_facts`** — Cheyenne's `/teach`-ed facts. Inlined into every system prompt. This is how the bot's understanding compounds.
- **`leads`** — pipeline (name, contact, status, notes, created/updated timestamps).

## Operations

```bash
# Logs
ssh root@198.54.123.234 'journalctl -u sapphire-bot -f'

# Status
ssh root@198.54.123.234 'systemctl status sapphire-bot'

# Restart
ssh root@198.54.123.234 'systemctl restart sapphire-bot'

# Backup the DB
ssh root@198.54.123.234 'sqlite3 /var/lib/sapphire-bot/sapphire.db ".backup /tmp/sapphire-$(date +%Y%m%d).db"'
```

## Onboarding script for Cheyenne

After first `/start`, she should `/teach` these, one per command (so each gets its own row and can be edited individually):

1. Her services and starting prices
2. Her location / service area
3. Her ideal client + who's NOT a fit
4. Her voice / how she talks (e.g. "lowercase, warm, real, no corporate")
5. Her booking link or how clients book
6. Anything she always says yes/no to
7. Her schedule / availability rules

Then she just talks to it. The more she teaches, the more useful it gets.
