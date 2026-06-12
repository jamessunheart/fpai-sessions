# SPEC_financial-hub-rung4

*Rung 4 · financial hub. One live, secret-free pane of the whole money picture —
consolidation (what is) + anomaly watch (what changed) + a daily digest line through the
comms hub. Promotes and supersedes `SPEC_financial-consolidation-hub.md` (2026-06-03,
James: "build it") into the rung-4 hub format; that spec's consolidation scope is folded
in here. Owner: Codex (build) · Ember/Treasurer (review). Read-only — moves no money, ever.*

## Source / why

James, 2026-06-12: *"spec the financial hub."* Financial truth is scattered: treasury
snapshots (`~/.config/fpai/treasury/`) · Watchfire/HL positions · cost ledger · sol_live ·
Zen Village accounting · banks/crypto/bullion in the encrypted SENSITIVE blob · burn/green
ledger. James sees the whole picture only when a session hand-assembles it. The hub makes
that assembly a script: 10-second whole-picture read, plus the substrate noticing drift
(stale snapshot · burn spike · position move) instead of waiting to be asked.

Treasury SSOT discipline applies (`feedback-treasury-ssot-discipline`): the hub READS
canonical sources fresh every refresh; it never becomes a second source of truth — it is
a render.

Buildstream intent: `rung4-hubs`.

## Scope decisions (decided — don't re-litigate)

- **Read-only forever.** No transaction, transfer, trade, or approval path. Money movement
  is Reserved-Class and lives outside this hub entirely.
- **Posture-B output:** the pane shows the picture (totals · splits · deltas · alerts),
  never raw keys/addresses/account numbers. Exact balances round to whole dollars;
  the encrypted bridge holds detail with a "decrypt for detail" pointer.
- **Whaletrack stays quarantined:** the pane SHOWS Watchfire/HL state read-only; it must
  not imply live execution is validated (it isn't — stops bug, `spec_whaletrack_stop_execution_fix`).

## The three declarations

- **Milestone (DoD):** `python3 tools/financial_hub/refresh.py` reads all canonical
  sources and writes `core/STATE/FINANCIAL_HUB.md`: net spendable · banks/crypto/bullion
  split · idle-vs-deployed · monthly burn vs green (crossover distance) · open positions
  with liq distance · this-week cost-meter spend · per-source freshness stamps. A second
  run with changed fixtures emits anomaly alerts through the comms outbox. Leak-scan
  proves zero secrets in output. Demonstrated on live sources + fixture anomalies.
- **Dependency:** canonical sources exist ✅ (`~/.config/fpai/treasury/` ·
  `cost/ledger.jsonl` · sol_live · HL via watchfire reader) · comms outbox
  (SPEC_comms-hub-james-interface — soft dependency: fall back to writing
  `core/STATE/FINANCIAL_HUB_ALERTS.md` if outbox absent) · Treasurer agent canon
  (`core/STATE/roster/TREASURER_CANONICAL.md`) for thresholds. Forks from `feat/headless-build`.
- **Landing target:** `feat/headless-build`. Never `main` without explicit review.

## Definition of Done

1. **`tools/financial_hub/sources.py`** — one reader per canonical source, each returning
   `{data, as_of_utc, fresh: bool}` with a per-source staleness threshold (treasury
   snapshot 7d · cost ledger 2d · sol_live 1h · HL positions 1h). A source that errors
   reports `fresh: false` with the error string — the hub never crashes on one bad source.

2. **`tools/financial_hub/refresh.py`** — pulls all sources → computes the pane →
   renders `core/STATE/FINANCIAL_HUB.md` (git-tracked render; sources stay canonical).
   Sections: HEADLINE (net spendable · burn · green · crossover distance) · ALLOCATION
   (idle vs deployed vs reserve) · POSITIONS (read-only · liq distance · 🔴 quarantine
   banner on Watchfire until stops fix validated) · SPEND (cost-meter week) · FRESHNESS
   (per-source stamps, stale sources flagged 🟡).

3. **`tools/financial_hub/watch.py`** — anomaly pass comparing this refresh to the prior
   render's state file (`core/STATE/.financial_hub_state.json`):
   - any source stale past threshold → yellow alert
   - burn this month > 1.25× trailing-3-month average → yellow
   - any position liq distance < 20% → red
   - net spendable delta > 10% between refreshes → yellow
   - daily cost-meter spend > $20 (the cost-cap rule) → red
   Alerts enqueue to `core/COMMS/outbox/` (or the fallback file). Red = immediate;
   yellow = daily digest.

4. **Leak-scan gate** — `tools/financial_hub/leak_scan.py` runs at the end of every
   refresh: regex for key/address/account-number/seed patterns over the rendered pane;
   any hit aborts the write and alerts red. Test fixtures include a poisoned source to
   prove the abort path.

5. **Cadence wiring** — refresh called from `tools/decisions/daily_sync.py` (one import +
   one call, after existing steps) guarded by `FPAI_FINANCIAL_HUB_DISABLE=1`. The
   Obsidian vault mirror (per the old spec's `00_MEMORY/FINANCIAL HUB.md`) goes through
   the comms hub's `obsidian_bridge` vault-blocked-safe path — never a direct iCloud write
   from a cron.

6. **Tests** — `tools/financial_hub/test_hub.py`, fixture-backed (no live reads in CI):
   pane renders from fixtures · per-source failure isolation · each anomaly rule fires on
   its fixture · leak-scan abort on poisoned fixture · idempotent re-render.

## Files

- **Files ALLOWED:** `tools/financial_hub/**` (new) · `core/STATE/FINANCIAL_HUB.md` +
  `core/STATE/.financial_hub_state.json` (renders) · `tools/decisions/daily_sync.py`
  (one wire) · comms outbox enqueue · read-only: `~/.config/fpai/treasury/**`,
  `cost/ledger.jsonl`, sol_live, watchfire position reader.
- **Files FORBIDDEN:** any write to treasury/wallet/exchange state · keys or secrets in
  any output · `SPEC_whaletrack_stop_execution_fix` scope (don't touch executor code) ·
  vault direct-writes from cron · NOW.md / identity stack · unrelated refactors.

## Safety

- 🔴 **Read-only is structural:** no source module may import or shell to anything that
  signs, sends, or trades. Test asserts no such imports exist in `tools/financial_hub/`.
- 🔴 **Leak-scan is a hard gate** — a failed scan means no pane written, red alert sent.
- 🟡 The pane is a render, not an SSOT — header line says so and names the canonical
  sources, so future sessions don't treat it as ground truth (SSOT discipline).
- 🔵 Kill-switch: `FPAI_FINANCIAL_HUB_DISABLE=1` skips refresh in daily_sync.
- Rollback: `git revert <commit>` · delete the two render files; sources untouched.

## Tests

- `python3 -m pytest tools/financial_hub/test_hub.py -v`
- `python3 tools/financial_hub/refresh.py --dry-run` — prints pane to stdout, writes nothing.
- Leak-scan poisoned-fixture test proves the abort path.

## Rollback

- `git revert <this-commit>` · `rm core/STATE/FINANCIAL_HUB.md core/STATE/.financial_hub_state.json` ·
  remove the daily_sync wire. Canonical sources are never modified, so rollback is total.

## Close-out

Update `docs/codex/HANDOFF.md`: files changed · tests green · one live refresh proof ·
mark `SPEC_financial-consolidation-hub.md` superseded-by this spec. Downstream intent
unlocked: Treasurer agent + James read one pane; anomaly watch gives the substrate
financial reflexes — the burn/green crossover becomes a visible, alerting number.
