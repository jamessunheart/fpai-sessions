# SPEC_d035_cora-v0-2-monetary-policy-earn-r Result

Status: done / awaiting James review and merge review

## Files Changed

- `docs/policy/CORA_POLICY_v0.2.md`
- `docs/policy/test_cora_policy.py`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/specs/SPEC_d035_cora-v0-2-monetary-policy-earn-r.md`
- `core/BUILD/results/SPEC_d035_cora-v0-2-monetary-policy-earn-r.result.md`

## Summary

Drafted the review-only CORA v0.2 closed-loop rewards credit policy. The policy defines CORA as a non-cash, non-investment, non-transferable attention credit; proposes provisional earn amounts and spend/burn costs; lists backing assets; defines daily/event/circulation caps and review triggers; includes the seven required legal containment items; sets inactivity decay and Hermes notices; and keeps a non-empty gap log for James/compliance decisions before launch.

No CORA feature references, product wiring, deployment, money movement, outreach, secrets, or legal adoption steps were added.

## Tests

- `python3 -B -m unittest docs.policy.test_cora_policy`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile docs/policy/test_cora_policy.py`
- `git diff --check -- docs/policy/CORA_POLICY_v0.2.md docs/policy/test_cora_policy.py core/BUILD/REGISTRY.json core/BUILD/specs/SPEC_d035_cora-v0-2-monetary-policy-earn-r.md`

## Independent Review

Independent AI review found no content/spec blockers: all 8 sections are present, all 7 legal containment cannot-do items are present, the gap log is non-empty, tests are focused and appropriate, and no product wiring or prohibited action was added.

Review blocker: the branch is not committed in this sandbox. `git commit -m "Add CORA v0.2 policy draft"` failed because Git could not create `/opt/fpai-build/FPAI_Cockpit/.git/worktrees/SPEC_d035_cora-v0-2-monetary-policy-earn-r/index.lock`: read-only file system. Ember must commit from a writable Git context before merge.

## Risks

- Amounts, caps, and prices are provisional policy drafts, not launch-approved economics.
- Compliance/legal review is explicitly incomplete.
- The launch capacity model for AI session credits, Camp Zen seats, Fi-Art slots, service hours, and content inventory is not complete.
- This sandbox could not create the local Git commit because the shared `.git/worktrees` path is read-only.

## Rollback

Remove `docs/policy/CORA_POLICY_v0.2.md`, `docs/policy/test_cora_policy.py`, and this result file; remove the d035 row from `core/BUILD/REGISTRY.json`; leave the generated spec file only if Ember still wants the queued decision record.

## Intent Solved

CORA now has a complete reviewable v0.2 closed-loop policy draft before onboarding, Fi-Art, marketplace, or retention features reference the credit.

## Downstream Intent Unlocked

James and compliance can review the concrete earn, burn, cap, decay, and containment policy before CORA becomes visible or product-bound.

## Questions For Ember/James

- Approve or revise the proposed earn amounts.
- Approve or revise the redemption menu pricing.
- Decide whether CORA is visible immediately or hidden until policy finalization.
- Complete compliance/legal review before launch.
