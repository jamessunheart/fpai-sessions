# Comms Hub - James Interface SPEC

Canonical spec: `docs/codex/specs/SPEC_comms-hub-james-interface.md`.

This service implements the v0.1 local, dry-run-safe comms hub:

- one routed outbox
- one routed inbox
- inbox dispatch into system/builder work attempts
- terminal adapter
- Obsidian adapter
- Telegram text adapter gated by env and allowlist
- Telegram voice metadata handling gated by env
- kill switches before poll, route, drain, send, and write
