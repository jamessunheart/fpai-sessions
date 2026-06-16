# Self-Evolution L1

Layer 1 is the measurement spine only. It builds advisory preference pairs from existing local signals and evaluates a judge on a frozen held-out split. It does not train models, wire production, self-grant authority, spend money, or change live routing.

## Path

1. L1 dataset + held-out eval: `build_preference_dataset.py` writes preference JSONL and marks held-out rows `never_train: true`.
2. Session feedback seed: `session_feedback_seed.py` captures build outcomes, merge outcomes, vetoes, independent review verdicts, and explicit conversation ratings into `session-feedback-seed.v1` JSONL.
3. L2 reward-LoRA on `llama3.1:8b`: deferred until enough rows accumulate.
4. Shadow scoring: candidate judges score future work without controlling the loop.
5. DPO generator: only after shadow scores beat the frozen eval and human review approves the next layer.
6. Continuous batch retrain: batch-only, never on the held-out split.
7. Frontier real-time: last step, after consequence-ledger proof shows the local judge improves outcomes.

## Risk Controls

- Reward-hacking: consequence evidence must outweigh the vibe tag. A `good` label is weak if receipts later show regression.
- Held-out eval rows are marked `never_train: true` and must never enter reward/DPO training.
- Advisory-only: eval numbers can recommend review, not take action.
- No production writes: scripts write only the explicit JSONL/report path requested by the operator.
- No self-grants: a stronger judge does not expand its own authority.
- Session feedback rows are preference evidence, not approval. A veto row marks a boundary for later review; it does not execute a rollback or block a merge by itself.

## Commands

```bash
python3 -B tools/learn/build_preference_dataset.py --dry-run
python3 -B tools/learn/build_preference_dataset.py --output /tmp/fpai-preferences.jsonl
python3 -B tools/learn/session_feedback_seed.py --dry-run
python3 -B tools/learn/session_feedback_seed.py --output /tmp/fpai-session-feedback.jsonl
python3 -B tools/learn/eval_judge.py /tmp/fpai-preferences.jsonl --judge keyword
```

`eval_judge.py` prints one number: judge accuracy minus baseline accuracy. Positive means the judge beat the deterministic baseline on frozen held-out rows.
