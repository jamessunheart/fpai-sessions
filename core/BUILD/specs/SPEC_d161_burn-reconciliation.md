# SPEC — Provider-side burn reconciliation (extends Law: NO UNMETERED BURN)

tools/burn/audit.py (live 2026-07-03) sees OUR side: keys, units, call counts. This spec adds the PROVIDER side so the system reconciles what it thinks it spends vs what it's billed — the gap that let 97 invoices accumulate.

Build `tools/burn/reconcile.py` (weekly, after audit.py):
1. Anthropic Usage & Cost Admin API (needs admin key — request from James once, store in ~/.config/fpai/burn_audit/) → $/day by API key.
2. Meta Ads spend (act_71883338 insights, creds on 198 ad-portal) → $/day.
3. Compare vs BURN_REGISTRY expected values → any consumer >2× expected OR any provider spend with no registry row → 🔴 to HEARTBEATS + TG digest.
4. Append rows to the allocation ledger (SPEC_allocation-ledger-ccd) so burn is a first-class input to allocation decisions.
Contract: read-only APIs · no key values in logs · tests with fixtures · independent review.
Done: one weekly reconciliation report with real provider numbers, and a seeded alert test proving the 🔴 path fires.
