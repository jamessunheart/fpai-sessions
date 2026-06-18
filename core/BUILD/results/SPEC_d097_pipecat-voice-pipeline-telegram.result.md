# SPEC d097 — Pipecat Voice Pipeline (Telegram two-way voice)

## Status
Done in working tree / awaiting merge review.

## Files Changed
- `SERVICES/sunheart-brain/curator/voice_pipeline.py`
- `SERVICES/sunheart-brain/curator/tgbot.py`
- `SERVICES/sunheart-brain/curator/test_voice_pipeline.py`
- `SERVICES/sunheart-brain/curator/requirements.txt`
- `core/BUILD/activate/SPEC_d097_pipecat-voice-pipeline-telegram.sh`
- `core/BUILD/specs/SPEC_d097_pipecat-voice-pipeline-telegram.md`
- `core/BUILD/results/SPEC_d097_pipecat-voice-pipeline-telegram.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary
Added a local-first Telegram voice adapter for `@sunheartbrain_bot`.

The existing long-polling bot, owner/team gates, privacy mode, Linear capture,
brain search, and text reply flow remain intact. Voice notes now download once,
then try local faster-whisper STT before the previous OpenAI Whisper fallback.
Voice replies now try local Kokoro TTS, transcode to OGG Opus for Telegram voice
bubbles with `ffmpeg`, then fall back to the previous OpenAI TTS path unless
`SH_TGBOT_VOICE_LOCAL_STRICT=1` is set.

`/voice` now reports local dependency readiness for Pipecat, faster-whisper,
Kokoro, ffmpeg, and audio-writing support. The activation script installs the
curator requirements into the existing `/opt/sh-brain-src/.venv` and restarts
`sh-brain-tgbot.service` when present.

## Tests
- `timeout 20s python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_voice_pipeline.py'`
- `python3 -B SERVICES/sunheart-brain/curator/tests/test_voice_tts_strip.py`
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_bot_mode_gate.py'`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/voice_pipeline.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_voice_pipeline.py`
- `bash -n core/BUILD/activate/SPEC_d097_pipecat-voice-pipeline-telegram.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Risks
- This sandbox did not install Pipecat, faster-whisper, Kokoro, or model
  weights, and did not send a live Telegram voice note.
- Kokoro package/API compatibility is guarded best-effort; live proof must check
  `/voice` dependency status on server 162 after activation.
- If local STT/TTS is unavailable and strict mode is off, the bot falls back to
  the existing OpenAI voice path to avoid breaking live voice usage.
- The proof target, "James sends voice note and receives voice reply within 5
  seconds", remains a post-merge live-host validation because it requires bot
  credentials, local models, and Telegram.

## Rollback
Revert the listed files. If activation has run, restart `sh-brain-tgbot.service`
after rollback. Runtime mitigation without reverting: set
`SH_TGBOT_VOICE_PROVIDER=openai` to use the legacy OpenAI voice path, set
`EMBER_TGBOT_VOICE_DISABLE=1` or `/voice off` for text-only replies, or set
`SH_TGBOT_VOICE_LOCAL_STRICT=1` to fail closed when local voice dependencies are
not ready.

## Intent Solved
Telegram voice now has a local-first Pipecat/faster-whisper/Kokoro pipeline
boundary instead of being hardwired to OpenAI STT/TTS.

## Downstream Intent Unlocked
Ember can activate on server 162, run `/voice` for readiness, and perform the
live proof: one James voice note to `@sunheartbrain_bot` returns a text plus
voice answer within 5 seconds using local models.
