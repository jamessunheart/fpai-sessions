# SPEC d098 — Cognee Graph Memory Layer

**Status:** queued | **Stream:** Game | **Blast radius:** additive

## What
Layer Cognee over brain_index to add relationship graph: person↔becoming-stage↔proofs↔corrections connected. Runs on existing Postgres + pgvector. Don't replace brain_index — add the graph tissue it lacks.

## Why
brain_index has facts (rows). Cognee adds relationships (edges). The becoming-engine needs to know: "Josh is connected to regenerative cities AND Cheyenne via shared interest AND is at awaken stage" — not just three separate rows. Graph memory makes that traversal native.

## Stack
- Cognee v1.1.3 (shipped today, Apache-2.0)
- Runs on our existing Postgres + pgvector (zero new infra)
- Has Claude Code plugin (integrates with our toolchain)

## Proof
- Cognee indexes 10 probe_pool contacts + their becoming stages
- Graph query: "who is connected to regenerative cities?" returns Josh + related contacts
- Relationship preserved across sessions
