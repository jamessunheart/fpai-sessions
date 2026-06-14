# SPEC_recruiting-hub-rung4

*Rung 4 · recruiting hub. The substrate sources, screens, and stages human candidates;
James only sees finalists. First target: the Human Context Steward seat (unhired since
2026-05-09). Sunheart Rule applied to hiring itself — AI does everything up to the
irreducibly-James acts (final conversation · hire decision · trust). Owner: Codex (build) ·
Ember (review). Publishes to James via `core/COMMS/outbox/` (see SPEC_comms-hub-james-interface).*

## Source / why

James, 2026-06-12: *"spec the recruiting hub."* The roster names roles the substrate needs
but can't fill itself: Human Context Steward (`core/STATE/roster/HUMAN_CONTEXT_STEWARD_SPEC.md`,
🔴 unhired, candidate Alice noted) and future hires (Phase 2 onboarding per NOW.md). Today
recruiting = James remembering to think about it. The hub turns each open role into a
pipeline the substrate advances autonomously: role spec → sourcing drafts → screening →
ranked shortlist → James gate.

This is the strongest single-point-of-failure reducer in the FPOS North Star: every filled
seat moves context-holding off James.

Buildstream intent: `rung4-hubs`.

## Scope decisions (decided — don't re-litigate)

- **V1 is pipeline + screening + staging. NO autonomous outreach.** Every message to a
  candidate is Reserved-Class (`public_outbound_send`) → human-edge gate → James blesses.
- **First role:** Human Context Steward. The pipeline must be role-generic (a new role =
  one new YAML file), but v1 ships with HCS loaded.
- **Candidate data is sensitive:** names/contacts live in `~/.config/fpai/recruiting/`
  (outside repo). The repo holds role specs, pipeline code, and anonymized status only.

## The three declarations

- **Milestone (DoD):** `python3 tools/recruiting/hub.py --status` shows each open role with
  its pipeline: candidates per stage (sourced → screened → shortlist → gated → hired/passed).
  Given a role YAML + candidate fixtures, the hub scores candidates against the role spec,
  produces a ranked shortlist with per-candidate rationale, drafts (never sends) outreach,
  and enqueues a yellow-priority comms message: *"HCS shortlist ready — 3 candidates,
  top match 87%. Review?"* Demonstrated end-to-end on fixtures.
- **Dependency:** `core/STATE/roster/HUMAN_CONTEXT_STEWARD_SPEC.md` ✅ · Reserved-Class
  boundary (`tools/reserved/`) ✅ · comms outbox (SPEC_comms-hub-james-interface — soft
  dependency: fall back to writing `core/RECRUITING/NOTIFY.md` if outbox absent).
  Forks from `feat/headless-build`.
- **Landing target:** `feat/headless-build`. Never `main` without explicit review.

## Definition of Done

1. **`core/RECRUITING/roles/hcs.yaml`** — role spec as data: title · mission one-liner ·
   owns[] · must-haves[] · nice-to-haves[] · disqualifiers[] · comp band · trial-task
   description · sourcing channels[]. Generated from the existing HCS markdown spec;
   the markdown stays canonical for humans, the YAML is the machine view.

2. **`tools/recruiting/hub.py`**:
   - `status()` — pipeline pane per role.
   - `screen(role, candidate) -> ScreenResult` — scores a candidate file
     (`~/.config/fpai/recruiting/candidates/<id>.md`: resume text · notes · source)
     against the role YAML: must-have coverage · disqualifier check · 0-100 fit score ·
     3-line rationale. Pure function over the two inputs; no network.
   - `shortlist(role) -> list` — ranks screened candidates, writes anonymized
     `core/RECRUITING/<role>/SHORTLIST.md` (candidate ids + scores + rationale, NO
     names/contacts), enqueues the comms notification.
   - `draft_outreach(role, candidate_id)` — writes a draft to
     `core/RECRUITING/<role>/drafts/<id>.md` + a Reserved-Class human-edge gate
     ("Send to candidate <id>? approve / edit / skip"). **Never sends.**
   - `advance(candidate_id, stage)` / `pass(candidate_id, reason)` — stage transitions,
     append-only history per candidate.

3. **Trial-task lane** — `core/RECRUITING/<role>/trial/` holds the trial-task brief
   (from role YAML) + per-candidate submission notes + an Ember evaluation template.
   The hub stages the brief with the outreach draft; sending it is the same gated act.

4. **Sourcing drafts (not sends)** — `tools/recruiting/sourcing.py` renders a job post
   per role from the YAML (one general + one per channel in `sourcing_channels`), staged
   to `core/RECRUITING/<role>/posts/`. Posting anywhere public is Reserved-Class →
   gate. Run drafts through the compliance-scanner agent before staging is complete.

5. **Tests** — `tools/recruiting/test_hub.py`, fixture candidates (synthetic, no real
   PII in repo): disqualifier rejects · must-have scoring · shortlist ordering ·
   stage transitions append-only · outreach draft creates a gate and sends nothing ·
   anonymization (no fixture "name"/"email" strings appear in any `core/RECRUITING/` output).

## Files

- **Files ALLOWED:** `tools/recruiting/**` (new) · `core/RECRUITING/**` (new — anonymized
  only) · `~/.config/fpai/recruiting/**` (candidate PII store, created at runtime, never
  committed) · read-only: `core/STATE/roster/**`, `tools/reserved/`, comms outbox enqueue.
- **Files FORBIDDEN:** any PII in repo paths · live sends / posting APIs · payroll or
  money movement · `core/STATE/roster/*.md` edits (role canon stays human-edited) ·
  identity stack · unrelated refactors.

## Safety

- 🔴 **No candidate ever contacted without James's blessing.** All outreach/posting is
  Reserved-Class gated. V1 ships with zero send credentials wired.
- 🔴 **PII boundary:** names/contacts/resumes only under `~/.config/fpai/recruiting/`;
  repo artifacts use candidate ids. Leak-scan in tests enforces it.
- 🔴 **Hire decision is irreducibly James.** The hub ranks and recommends; it cannot mark
  `hired` without a James-confirmed gate token.
- 🔵 Kill-switch: `FPAI_RECRUITING_DISABLE=1` → hub is read-only status.
- Rollback: `git revert <commit>` · `rm -rf core/RECRUITING/` · PII store untouched.

## Tests

- `python3 -m pytest tools/recruiting/test_hub.py -v`
- `python3 tools/recruiting/hub.py --status` renders the pipeline pane.
- Leak-scan: `grep -ri "<fixture-name>" core/RECRUITING/` returns nothing.

## Rollback

- `git revert <this-commit>` · delete `core/RECRUITING/` · candidate store under
  `~/.config/fpai/recruiting/` is preserved (it's the durable asset).

## Close-out

Update `docs/codex/HANDOFF.md`: files changed · tests green · fixture end-to-end proof.
Downstream intent unlocked: HCS pipeline live → first non-AI context holder → James's
physical-world bottleneck starts dissolving; same rails serve every Phase 2 hire.
