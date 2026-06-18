# SPEC d099 — Postiz Social Scheduler (MCP-wired)

**Status:** queued | **Stream:** Game | **Blast radius:** additive

## What
Self-host Postiz on 162. Wire its MCP server into Ember's toolchain. Council/Ember drive social posting as a tool call — no human scheduling, no per-post approval.

## Why
Postiz covers 30+ networks, is Apache-2.0, self-hosted $0, and exposes an MCP server. Stop building social automation — adopt this. The MCP wire means it's a tool in Ember's hands, not a separate system to manage.

## Platforms to wire first
- Mastodon (can create account autonomously today)
- Instagram (needs Meta token refresh from James — one-time)
- Twitter/X (after Twilio/CAPTCHA — autonomous signup)

## Proof
- Postiz running on 162 Docker
- MCP server registered in Ember's tool config
- One post scheduled and published via MCP tool call
