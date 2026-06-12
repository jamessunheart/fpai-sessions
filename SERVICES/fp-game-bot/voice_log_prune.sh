#!/bin/bash
# voice_log_prune.sh - daily audio TTL enforcement for fp-game-bot voice persistence
# Transcripts (.md, summary.md) are preserved forever; audio (.oga/.opus/.ogg) prunes after VOICE_AUDIO_TTL_DAYS.
# Install path on server: /usr/local/bin/voice_log_prune.sh
# Cron: 0 4 * * * /usr/local/bin/voice_log_prune.sh >> /var/log/voice_log_prune.log 2>&1
cd /opt/fpai/services/fp-game-bot || exit 1
set -a
. /etc/fp-game-bot/fp-game-bot.env
set +a
.venv/bin/python -c 'import voice_persistence as vp; n = vp.prune_old_audio(); print("pruned", n, "audio files")'
