# SPEC d097 — Pipecat Voice Pipeline (Telegram two-way voice)

**Status:** queued | **Stream:** Game | **Blast radius:** additive

## What
Wire Pipecat + faster-whisper + Kokoro as the voice pipeline for Telegram. James sends a voice note → transcribed locally → LLM responds → TTS plays back. $0 marginal, sovereign, runs on 162.

## Stack
- **Pipecat** (Apache-2.0) — pipeline orchestrator, native Ollama LLM support
- **faster-whisper** — local STT, faster than openai-whisper, same quality
- **Kokoro** (82M params, Apache-2.0) — CPU-capable TTS, natural voice
- **Telegram transport** — custom Pipecat transport for voice note in/out

## Why over hand-rolling
Pipecat handles: VAD (voice activity detection), turn management, frame streaming, STT↔LLM↔TTS chaining. Building this by hand is weeks. Pipecat + config is days.

## Proof
James sends voice note to @sunheartbrain_bot → receives voice reply within 5 seconds
