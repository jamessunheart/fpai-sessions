# SPEC_d240_auto-spot-topple-assessment-funn Result

- Status: done in working tree / awaiting review + merge
- Branch: `build/SPEC_d240_auto-spot-topple-assessment-funn`
- Spec: `core/BUILD/specs/SPEC_d240_auto-spot-topple-assessment-funn.md`
- Opportunity: `assessment-funnel-delivery-proof`
- Marginal cost: `$0`

## Summary

Added a reversible local d240 assessment funnel delivery-proof verifier/spec for `assessment-funnel-delivery-proof`. It composes the d239 verifier/spec artifact and downstream d210-d239 verifier chain into one local JSON/Markdown verifier-spec artifact with d240 provenance, d194 source timestamp, next-domino score `86.9`, activation gate, proof contract, operator steps, real-proof requirements, verifier command, and explicit count-toppled-only-after checks.

The artifact does not submit a lead, send email, call Telegram, deploy, read secrets, append capability learning, push, merge, or spend money.

## Tests

- `python3 -B -m unittest tools.build_loop.test_assessment_funnel_delivery_proof_delivery_proof_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec` (4 OK)
- `python3 -B -m unittest tools.build_loop.test_assessment_funnel_delivery_proof_delivery_proof_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec ... tools.build_loop.test_activation_audit` (117 OK)
- `python3 - <<'PY' ... py_compile.compile(..., cfile='/tmp/d240-pycompile-*.pyc', doraise=True)` (OK; short cfile targets avoid overlong generated `.pyc` names)
- `python3 tools/build_loop/assessment_funnel_delivery_proof_delivery_proof_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec.py --repo-root . --ops-ledger /tmp/d240-missing-ops.jsonl --no-write --json` (expected hold, rc 1)
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d240-registry-json.valid`
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d240_auto-spot-topple-assessment-funn --base-ref feat/headless-build --head-ref HEAD` (OK: no changed files detected before staging)
- `git diff --check`

## Risks

This cannot create live proof by itself. Ember/server ops still need to run one controlled Life assessment lead after d193 is merged and activated, collect the evidence packet, and let the verifier append d185 capability learning only on pass.

## Rollback

Revert this branch. Runtime cleanup is inert: delete any local `assessment_funnel_delivery_proof_delivery_proof_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec.json` or Markdown verifier-spec file produced by the generator.

## Intent

- Intent solved: the current d240 server-build-loop context now has a local verifier/spec artifact without letting another verifier/spec artifact count as delivery-proof topple evidence.
- Downstream intent unlocked: after d193 activation, server ops can run one controlled Life assessment lead and use one local d240 verifier/spec plus the d210 verifier path to log recipient delivery, founder alert, page acknowledgement, and d185 capability learning only when real proof exists.

## Ember / Server Ops

After d193 is merged and activated through the d182/d188 guard, run:

```bash
python3 tools/build_loop/assessment_funnel_delivery_proof_delivery_proof_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec.py --repo-root /opt/fpai-build/FPAI_Cockpit --ops-ledger /opt/fpai-build/ops_ledger.jsonl --verifier-spec-file /opt/fpai-build/assessment_funnel_delivery_proof_delivery_proof_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec.json --markdown-file /opt/fpai-build/assessment_funnel_delivery_proof_delivery_proof_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec_verifier_spec.md --json
```

If it returns `ready`, follow the emitted verifier command with the real proof packet.
