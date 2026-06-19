# SPEC_d121_self-evolution-l1-preference-dat Result

## Status
done in working tree / awaiting merge review

## Summary
Verified d121 as an idempotent retry of d010. The requested Layer 1 measurement spine already exists in tracked `tools/learn` files from `SPEC_d010_self-evolution-l1-preference-dat`: advisory preference-pair assembly from local decision/receipt/feedback signals, deterministic hash-based held-out split with `never_train: true`, a held-out eval judge that prints one go/no-go number, README risk controls, and focused tests.

No existing implementation files were edited. This preserves the spec's new-file-only posture while registering d121 and adding this result artifact for merge review.

## Files Changed
- `core/BUILD/specs/SPEC_d121_self-evolution-l1-preference-dat.md`
- `core/BUILD/results/SPEC_d121_self-evolution-l1-preference-dat.result.md`
- `core/BUILD/REGISTRY.json`

## Existing Implementation Verified
- `tools/learn/build_preference_dataset.py`
- `tools/learn/eval_judge.py`
- `tools/learn/README.md`
- `tools/learn/test_learn.py`

## Tests
- `python3 -B -m unittest tools.learn.test_learn`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/learn/build_preference_dataset.py tools/learn/eval_judge.py tools/learn/test_learn.py`
- `python3 -B tools/learn/build_preference_dataset.py --root /tmp/d121-learn-fixture --dry-run --eval-percent 100`
- `python3 -B tools/learn/build_preference_dataset.py --root /tmp/d121-learn-fixture --output /tmp/d121-preferences.jsonl --eval-percent 100`
- `python3 -B tools/learn/eval_judge.py /tmp/d121-preferences.jsonl --judge baseline`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Risks
- This branch does not create a second copy of `tools/learn`; it relies on the existing d010 implementation already tracked on the branch.
- Live `brain_index.decisions` database extraction was not exercised in this sandbox; the assembler was verified through file-based fixture signals.
- The judge remains advisory/shadow only and does not train, route, deploy, or self-grant authority.

## Rollback
Remove `core/BUILD/specs/SPEC_d121_self-evolution-l1-preference-dat.md`, remove this result file, and remove the d121 registry entry. No runtime rollback is required because no production wiring or model training occurred.

## Intent solved
d121 has a reviewed, tested Layer 1 measurement spine available without duplicating or mutating the already-built d010 implementation.

## Downstream intent unlocked
Future Layer 2 reward-LoRA or shadow-scoring specs can depend on the existing L1 dataset/eval boundary, with held-out `never_train` rows preserved and advisory-only risk controls explicit.
