# SPEC d177 Telegram Push Inventory

Generated from repo grep on 2026-07-04. Live host confirmation is still required after merge because some pushers live under `/opt/fpai` and `/etc/systemd`, not fully in this repo mirror.

## James Private Lane Policy

- Keep: one morning digest, lead-in alerts, build merged/failed alerts, spend-over-cap alerts, model-degrade alerts.
- Quiet by default: intermediate loop/status notifications.
- Reroute/off: Zen Village digest to James's private chat.
- Quiet hours: batch non-failure/non-lead noise to morning during 22:00-07:00 Costa Rica time.

## Inventory

| Source | Evidence | Decision | d177 action |
|---|---|---|---|
| `fpai-morning-digest.timer` | Spec-confirmed 05:00 UTC; repo has `tools/visual/visual_digest.py`, `tools/build_loop/morning_digest.sh`, drop-ins for visual/backup status | Keep as the single morning digest lane | No disable. Future digest should carry money, decisions, overnight builds, leads, anomalies. |
| `zv-morning-digest.timer` | Spec-confirmed 13:00 UTC; docs at `docs/zen-village/runbook/morning_digest.md` | Reroute to ZV channel or off | Activation disables timer if present, guarded by `D177_DISABLE_ZV_DIGEST=1`. |
| `deploy-tools/kai-bridge.py` / live `/opt/fpai/cora-loop/kai_bridge.py` | Hard-coded fallback `TELEGRAM_CHAT_ID=8514069423`, sends “Kai steering injected” | Quiet intermediate loop status | Repo copy now requires `CORA_BRIDGE_TELEGRAM_ALERTS=1`; activation installs quieted copy if live path exists. |
| `deploy-tools/triad-bridge.py` / live `/opt/fpai/cora-loop/triad_bridge.py` | Hard-coded fallback `TELEGRAM_CHAT_ID=8514069423`, sends “Cael/Terra steering injected” | Quiet intermediate loop status | Repo copy now requires `CORA_BRIDGE_TELEGRAM_ALERTS=1`; activation installs quieted copy if live path exists. |
| `deploy-tools/lead-capture-api.py` | Hard-coded fallback `TELEGRAM_CHAT_ID=8514069423`, sends `NEW LEAD` | Keep as earned event alert | No change. |
| `deploy-tools/lead-capture-primary.py` | Hard-coded fallback `TELEGRAM_CHAT_ID=8514069423`, sends `NEW REAL LEAD` | Keep as earned event alert | No change. |
| `tools/build_loop/notify_telegram.sh` / `tools/build_loop/build_alerts.py` | Build lifecycle Telegram sender | Keep event-only build alerts | No change; d155 quiet-hour/burst rules remain owner. |
| `SERVICES/sunheart-brain/curator/tgbot.py` model-degrade alerts | d174 fallback alert path to ops/owner chat | Keep loud event alert | No change; d177 preserves d174. |
| `tools/visual/visual_digest.py` | `sendPhoto` + fallback `sendMessage` after digest | Keep inside morning digest lane | No change. |
| `tools/constitution/surface.py`, `tools/decisions/send_tg_digest.py`, `tools/decisions/scene_capture.py`, `tools/decisions/push_update.py` | Manual/decision/digest senders using Telegram env | Keep only when invoked by command/digest/event | No automatic disable in d177; review live timers before changing. |
| `infra/scripts/pulse_daily_prompt.sh`, `infra/scripts/stream_to_tg.sh`, `infra/scripts/adam-security/security-sentinel.sh`, `infra/adam-workspace-patches/*` | Older infra scripts with Telegram send paths and/or hard-coded James chat fallback | Unknown live status | Not changed; live `systemctl`/cron/LaunchAgent audit needed before disabling. |
| Aria/legacy services under `SERVICES/aria-command/**` | Many independent Telegram bots, often other chat defaults | Not necessarily James private bot | Not changed; likely separate products/legacy lanes. |

## Live Follow-Up

After merge/activation on server 162:

1. Confirm `zv-morning-digest.timer` is disabled or rerouted to a ZV channel.
2. Confirm `fpai-morning-digest.timer` remains the only daily private digest.
3. Confirm lead capture still alerts.
4. Confirm build lifecycle and model-degrade alerts still fire.
5. Review loaded cron/systemd/LaunchAgents for `pulse_daily_prompt`, `stream_to_tg`, and Adam workspace scripts before disabling anything else.
