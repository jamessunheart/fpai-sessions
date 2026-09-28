# SUPER Agent missed-beat alert pause

## Scope

This switch pauses only the missed-beat Telegram escalation emitted by
`infra/scripts/super_agent_heartbeat.sh` after a gap longer than five hours.

It does not stop or pause:

- the Full Potential Game;
- the four-hour SUPER Agent heartbeat schedule;
- the SUPER Agent's Claude/steward work;
- the vendor-log mirror or vendor-delta alert;
- brain-offline or evidence-mirror alerts;
- production services or unrelated monitors.

While paused, the heartbeat still measures the interval between beats and updates
`~/.cache/super_agent/last_beat_epoch`. A detected gap is written locally to
`~/.cache/super_agent/missed_beat_detections.log` with `alert=suppressed`, rather
than being appended to the Telegram-bound heartbeat entry.

## Status

```sh
/Users/jamessunheart/FullPotentialOS/infra/scripts/super_agent_heartbeat.sh --missed-beat-alert-status
```

`missed_beat_alerts=paused` means the scoped pause file is present. This status
command exits before the heartbeat, model, mirror, logs, or Telegram sender run.

## Resume (preserves the pause record)

Move the active pause file to a timestamped historical name:

```sh
pause_file="$HOME/.config/fpai/super_agent/missed_beat_alerts.disabled"
resume_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
mv "$pause_file" "${pause_file%.disabled}.resumed-${resume_stamp}"
```

No service restart or cron change is required. Confirm that the status command
reports `missed_beat_alerts=active`. The next scheduled heartbeat will again raise
a missed-beat escalation if the interval exceeds five hours.

Do not use `~/.config/fpai/SUPER_AGENT_DISABLE` for this purpose; that broader
switch stops the entire heartbeat and is outside this pause's authority.
