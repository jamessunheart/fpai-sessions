# SPEC_reserved-class-boundary

*Rung 0 of the System-That-Builds-The-System ladder. Encode the irreducible-James gates — the exact line where a move stops being AI/apprentice-doable and must escalate to James — as a canonical definition + a FAIL-SAFE classifier the loop and apprentices call before any consequential move. This is the keystone: apprentices cannot safely self-run until escalation is encoded. Owner: Codex. Advisory/read-only — it gates, it never executes.*

## Source / why
James, 2026-06-09: build the system that builds the system; push the delegation line up to where he's *still required*, and let everything below self-construct via apprentices. Before any apprentice can own work end-to-end (Rung 1) or the loop can self-direct (Rung 2), the system must know — mechanically, not by vibe — when to proceed vs escalate. This spec encodes that boundary.

## The irreducible core (what is Reserved-Class — James only)
1. **Money out** — any spend, transfer, withdrawal, position change, commitment of funds.
2. **Public / outbound send** — anything leaving to a non-James human or the world (messages, posts, emails, publishes).
3. **Irreversible / legal / people** — deletes, deploys to prod, legal/compliance, hiring/firing, relationship-affecting acts.
4. **Strategic positioning** — offer pricing, brand/positioning, doctrine, what the business *is*.
5. **Final blessing** — approving a consequential diff before merge/activation.
Everything NOT in these categories is delegable (AI-draft or apprentice-execute).

## The three declarations (per cadence doctrine)
- **Milestone (DoD):** a `is_reserved(action) -> (bool, category, reason)` classifier + a canonical `core/STATE/RESERVED_CLASS.yaml`, with a test suite of example actions → expected classification, including ambiguous cases that MUST default to escalate.
- **Dependency:** none (this is Rung 0, the root). Forks from `feat/headless-build`.
- **Landing target:** `feat/headless-build` (the loop's branch). Never `main`.

## Definition of Done
1. **`core/STATE/RESERVED_CLASS.yaml`** — the 5 categories above, each with: keywords/signals, examples, and the escalation verb-set. Human-readable + machine-loadable.
2. **`tools/reserved/classify.py`** — `is_reserved(action_text, context=None) -> {reserved: bool, category: str|None, reason: str, confidence: float}`. **FAIL-SAFE: if uncertain or unmatched-but-consequential-looking, return `reserved: true` (escalate).** Never auto-clear a consequential move. A pure-advisory function — it returns a verdict, it performs no action.
3. **Integration hook (stub only, not wired live):** a documented `gate_or_proceed(action)` helper that, given a reserved verdict, writes a human-edge gate via `tools.queue.build.add_gate()` instead of proceeding. (Rungs 1–2 wire it; here just provide + test it.)
4. **Tests** (`tools/reserved/test_classify.py`): each category's examples classify correctly; clearly-delegable actions (draft a doc, run a read-only scan, propose a lead list) classify `reserved: false`; ambiguous/unknown consequential actions default to `reserved: true`.

- Files ALLOWED: `core/STATE/RESERVED_CLASS.yaml` (new) · `tools/reserved/**` (new) · read-only of `tools/queue/build.py`. Files FORBIDDEN: wiring it into the live loop/apprentices (that's Rung 1–2) · any send/money/deploy · secrets · auto-approving anything.
- Tests: as above; plus `git diff --check`.

## Safety
- The classifier is the safety boundary itself — it must err toward escalation, never toward auto-proceed. 🔴 Hard line: it NEVER executes an action, NEVER approves money/send/deploy, and defaults uncertain calls to James.
- Rollback: delete `tools/reserved/` + `RESERVED_CLASS.yaml`; nothing was wired live.

## Close-out
HANDOFF 📥 · PROOF LOG (Rung 0 — the delegation boundary is encoded) · BRICK (the Reserved-Class definition — reused by every apprentice + the self-directing loop). Then Rung 1 (apprentice-execution tier) unblocks.
