# AI Review — build/SPEC_d097_pipecat-voice-pipeline-telegram

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds a local-first (faster-whisper/Kokoro/ffmpeg) Telegram voice pipeline for the brain bot with graceful OpenAI fallback; targets feat/headless-build, no money/secrets/main touched, safe defaults.

## Findings
- Perf: WhisperModel and KPipeline are instantiated on EVERY transcribe/synthesize call (voice_pipeline.py _transcribe_sync/_synthesize_sync) — no module-level caching. On the live CPU-only bot this reloads/re-downloads models per voice note, causing latency/RAM spikes and likely missing the stated 5s proof target. Cache the model objects.
- Default flip: SH_TGBOT_VOICE_PROVIDER defaults to 'local', so after activation the live bot prefers local voice. Mitigated because import failures fall back to OpenAI (strict mode off by default), so merging code alone won't break live voice — but verify on 162 before relying on it.
- Scope/clarity: pipecat-ai is added as a heavy dependency but only used as a find_spec readiness signal, never actually wired into a pipeline. Module docstring is honest about this, but the dep adds install weight for no runtime use yet.
- Activation script (SPEC_d097...sh) restarts the live sh-brain-tgbot.service and pip-installs into the prod venv — correct pattern and manually gated, but confirm it runs only via the normal Ember-blessed activation path, not auto-merge.
- Minor: dependency_status() find_spec calls and _ffmpeg_available subprocess run on every /voice command; cheap but worth noting.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
