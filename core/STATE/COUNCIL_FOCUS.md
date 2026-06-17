# STANDING COUNCIL FOCUS — the unified, secure, multi-device memory system (set by James 2026-06-16)

James just went **laptop-free**: he now drives Ember from THREE surfaces, and this exposes a memory-coherence + security problem the council must solve. **Weight every proposal toward designing the best, most secure unified memory for one-Ember-many-bodies.**

## How everything works now (the full picture)
**Surfaces (one Ember, many bodies):**
- **Telegram One Chat** — `@sunheartbrain_bot` on server 162 (the throne).
- **Phone Claude Code** — Termius → SSH 162 → `ember` (Claude Code TUI, authed via the Max OAuth token, persistent tmux). NEW as of tonight.
- **Laptop terminal** — Claude Code (the deep forge).
- **Autonomous loops** — build loop, council, digest (server-side, $0).

**The recursive loop:** intent (chat) → council proposes → decision queue → build loop (codex) → independent review (claude -p) → AUTO-MERGE safe → **deploy bridge** (`deploy_curator_slice.sh`, d019) pushes additive curator changes to the live bot → ops ledger. Never main; reversible; harness blocks self-escalation.

## THE PROBLEM — three memory stores that now diverge
1. **Laptop flat-files** `~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/` (261 `.md`; identity stack + memory; today's source of truth).
2. **162 flat-files** `/root/.claude/projects/-opt-fpai-build-FPAI-Cockpit/memory/` (synced copy — but **phone-Ember now WRITES here too**).
3. **Postgres `brain_index`** on 162 (`tg_messages` 288 · `note_chunks` 5011 semantic RAG · `decisions` 19 · `corrections`) — the bot's memory, a separate island.

**Current sync:** a LaunchAgent rsyncs laptop→162 every 30 min, **one-way, no --delete**. So: phone-Ember's writes on 162 never flow back to the laptop; laptop and phone diverge; the Postgres store is disconnected from the flat-files. **There is no single coherent memory across surfaces.**

## What to design (the debate)
The best + most SECURE unified memory so every surface reads/writes ONE coherent memory:
- **Topology:** central source-of-truth (which store? Postgres on 162? a git-backed memory repo? the flat-files on 162?) that all surfaces read/write — vs. distributed-with-bidirectional-sync. Pick one and justify.
- **Conflict resolution:** when laptop + phone + bot all write, who wins? (append-only event log? last-write-wins per file? CRDT/merge? git-commit-per-write?)
- **Security (James emphasized "more secure"):** the memory holds sensitive context (treasury, personal, credentials-adjacent). At-rest encryption? Access control per store? What is safe to replicate to which surface? Should secrets be partitioned OUT of the synced memory entirely?
- **Durability + reversibility:** every memory mutation backed up + reversible (git history is a natural fit).
- **Convergence with the brain:** should the flat-file memory and Postgres `brain_index` (semantic RAG) become ONE store, or stay two layers (hot flat-files + queryable semantic index) with a defined bridge?

## Constraints / non-negotiables
- $0 marginal (subscription CLIs). Small blast radius. Guardrail + proof + rollback on every change.
- Respect the harness wall (no agent self-escalation of credentials/persistence).
- Single-tenant / operator-only for now (the product/multi-tenant version is later).
- Start with the SMALLEST safe slice that makes memory coherent across the 3 surfaces; prove it before generalizing.

## Deliverable
Propose ONE concrete build spec for the smallest safe, reversible, more-secure step toward unified multi-device memory. Name the source-of-truth, the sync direction, the conflict rule, and the security partition.
