# AI Review — build/SPEC_d010_self-evolution-l1-preference-dat

**Verdict:** APPROVE · **Risk:** med

**Summary:** Advisory-only L1 measurement tools, new files + sanctioned REGISTRY entry; no prod/money/identity writes; meaningful tests; minor surfaces to note.

## Findings
- Scope OK: only new files under tools/learn/ plus the contractually-required REGISTRY.json self-registration (status=done, tests_passed=true) — does not set merged, so the Ember-only merge gate is respected. No money/treasury, prod server (162/198/209), or identity/memory writes.
- load_judge() in eval_judge.py uses importlib.import_module on an arbitrary 'module:function' CLI arg — an operator-controlled code-execution surface. Acceptable as a plugin mechanism (operator already has shell), but should never accept untrusted input or be wired into an automated/headless path.
- Default --root is REPO_ROOT with very broad globs (**/feedback_*.md, **/*decision*.json, **/*receipt*.json) that ingest memory/feedback_*.md and other private/identity-adjacent content into the preference JSONL. In-scope by design and held-out rows are marked never_train, but private data lands in a dataset file — keep output paths off prod/shared surfaces (examples correctly use /tmp).
- Held-out leakage check OK: _public_eval_row strips label + preferred/rejected and order is hash-randomized before the judge sees it; eval_judge filters on split==eval AND never_train AND eval-view present. Frozen split is sha256-deterministic and test-verified stable across runs.
- Reads are defensively wrapped (errors='ignore', try/except on JSON), SKIP_PARTS excludes .git/.venv/node_modules; no obvious crash or injection in the parsing path. Advisory/shadow only — no model training, no routing changes, reversible.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
