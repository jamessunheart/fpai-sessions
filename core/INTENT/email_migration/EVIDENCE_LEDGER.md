# Conversation OS — Evidence Ledger

_Precise capability status. Claims scoped to exactly what has executable evidence. Updated 2026-07-10._

| Capability | Status | Evidence |
|-----------|--------|----------|
| RFC822 → canonical Event | ✅ **proven (local delivery)** | `maildir_observer.poll()` on real Maildir · commit 32a4f1a0 |
| Retry / poll idempotency | ✅ **proven** | poll×2 + duplicate delivery → emitted 0 (`dedup_key`) |
| Crash recovery | ✅ **proven** | adapter raise mid-poll → inbox intact → deferred msg emitted next poll |
| Production isolation | ✅ **proven** | delivery (Maildir write) independent of observer; disable flag halts observation |
| First Email → Event evidence | ✅ **accepted** | commit `32a4f1a0` |
| **Remote IMAP/provider → Event (over the wire)** | ⬜ **not yet proven** | needs a real external sender → real isolated inbox → authenticated remote observer |
| Event → Conversation projection | ⬜ **not yet proven** | shadow-only, next after over-the-wire |
| Conversation → Intent proposal | ⬜ **not yet proven** | shadow-only |
| Intent → Room | ⬜ **not yet proven** | explicitly NOT built (no Rooms, no replies, no Brain promotion yet) |

**Naming discipline (James, 2026-07-10):**
- **Greenfield onboarding proof** — a fresh neutral domain, one control plane, no legacy. Proves ownership → DNS → mailbox → observe → Event.
- **Brownfield migration proof** — an *existing* domain, only after business dependencies are understood. Not the same proof; do not conflate.

**Two frozen assets (do not touch):** `expresspayfranchise.com` (business significance unknown — James does not recognize it), `jamesrickstinson.com` (live cPanel zone + broken delegation).
