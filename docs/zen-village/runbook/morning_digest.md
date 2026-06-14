# Morning Digest

The Zen Village Brain sends a short Telegram summary every day at 7am Costa Rica time.

Implemented as:

- Script: `/opt/zen-village/telegram/morning_digest.py`
- Local source: `docs/zen-village/telegram/morning_digest.py`
- Service: `zv-morning-digest.service`
- Timer: `zv-morning-digest.timer`
- Log: `/var/log/zv-morning-digest.log`

Schedule:

- `OnCalendar=*-*-* 13:00:00`
- Costa Rica is UTC-6 year-round, so 13:00 UTC = 7am CR.

Recipients:

- Defaults to `ZV_TG_ALLOWED_IDS` from `/etc/zen-village/telegram.env`.
- Override with `ZV_MORNING_DIGEST_IDS` if you want a narrower recipient list.

## What It Sends

- Brain connection count (`7/7 DBs connected`)
- Open Master List item count
- Pending Edit count
- Upcoming Event count
- Top 5 priorities
- Top 5 Pending Edits
- Top 5 upcoming events
- Quick action reminders: `/today`, `/edits`, `/note`, `/standup`, `/digest`

## Commands

Check timer:

```bash
ssh root@162.0.208.88 'systemctl list-timers --all zv-morning-digest.timer --no-pager'
```

Dry run without sending Telegram messages:

```bash
ssh root@162.0.208.88 '/opt/zen-village/telegram/.venv/bin/python3 /opt/zen-village/telegram/morning_digest.py --dry-run'
```

Send immediately:

```bash
ssh root@162.0.208.88 'systemctl start zv-morning-digest.service'
```

Disable:

```bash
ssh root@162.0.208.88 'systemctl disable --now zv-morning-digest.timer'
```

View logs:

```bash
ssh root@162.0.208.88 'less /var/log/zv-morning-digest.log'
```

## Notes

The first install was dry-run only. The timer is enabled and next runs automatically on 2026-04-25 at 13:00 UTC.
