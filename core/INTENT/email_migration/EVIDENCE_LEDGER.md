# Conversation OS — Evidence Ledger

_Precise capability status. Claims scoped to exactly what has executable evidence. Updated 2026-07-10._

| Capability | Status | Evidence |
|-----------|--------|----------|
| RFC822 → canonical Event | ✅ **proven (local delivery)** | `maildir_observer.poll()` on real Maildir · commit 32a4f1a0 |
| Retry / poll idempotency | ✅ **proven** | poll×2 + duplicate delivery → emitted 0 (`dedup_key`) |
| Crash recovery | ✅ **proven** | adapter raise mid-poll → inbox intact → deferred msg emitted next poll |
| Production isolation | ✅ **proven** | delivery (Maildir write) independent of observer; disable flag halts observation |
| First Email → Event evidence | ✅ **accepted** | commit `32a4f1a0` |
| **Remote provider → Event (over the wire)** | ✅ **proven live** | real external email (james@fullpotential.ai) → Mailsac public inbox → authenticated API observer → 1 canonical Event; dedup on re-poll = 0; UA+certifi fixes · trace `trace-beae3f0bf54d` |
| Event → Conversation projection | ✅ **proven (shadow)** | `shadow_projections.project()` on the live Event → conversation `conv-…`, rebuildable-from-stream, no Room |
| Conversation → Intent proposal | ✅ **proven (shadow)** | heuristic intent proposal, `action_taken: null`, side_effects NONE |
| Identity candidate (from Event) | ✅ **proven (shadow)** | candidate id, `resolved: false` — needs resolution gate |
| Multi-Event Conversation merging | ✅ **proven (shadow)** | `conversation_state.reduce()` — related Events merge, unrelated stay separate (same sender), duplicates add no state |
| Evolving Shared State | ✅ **proven (shadow)** | observed_facts vs interpretations vs decisions/commitments/unresolved_questions/intent; intent evolves append-only with source Event IDs |
| Out-of-order + replay determinism | ✅ **proven** | 5 shuffled reductions → identical `state_hash` (deterministic dedup representative) |
| Two-gate promotion boundary | ✅ **proven (INERT contract)** | `promotion_boundary.evaluate()` — durability + verification + approval gates independent; PRIVATE alone never promotes; NOT wired to Brain |
| Intent → Room | ⬜ **not built (by design)** | awaits Conversation+Shared-State (now proven) → explicit go; no Rooms, replies, Brain sync, or live promotion yet |

**Note (over-the-wire, 2026-07-10):** send path could not be automated (port 25 blocked · Mailsac free tier can't send · prod/personal mail disallowed) — James sent one synthetic email; the observe/persist/project path is fully machine-run. Mailsac = disposable test adapter, not a production channel. Test messages deleted (HTTP 204, inbox empty). Mailsac key passed through chat → flagged for rotation.

**Naming discipline (James, 2026-07-10):**
- **Greenfield onboarding proof** — a fresh neutral domain, one control plane, no legacy. Proves ownership → DNS → mailbox → observe → Event.
- **Brownfield migration proof** — an *existing* domain, only after business dependencies are understood. Not the same proof; do not conflate.

**Two frozen assets (do not touch):** `expresspayfranchise.com` (business significance unknown — James does not recognize it), `jamesrickstinson.com` (live cPanel zone + broken delegation).
