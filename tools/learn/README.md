# Self-Evolution L1

Layer 1 is the measurement spine only. It builds advisory preference pairs from existing local signals and evaluates a judge on a frozen held-out split. It does not train models, wire production, self-grant authority, spend money, or change live routing.

## Path

1. L1 dataset + held-out eval: `build_preference_dataset.py` writes preference JSONL and marks held-out rows `never_train: true`.
2. L2 reward-LoRA on `llama3.1:8b`: deferred until enough rows accumulate.
3. Shadow scoring: candidate judges score future work without controlling the loop.
4. DPO generator: only after shadow scores beat the frozen eval and human review approves the next layer.
5. Continuous batch retrain: batch-only, never on the held-out split.
6. Frontier real-time: last step, after consequence-ledger proof shows the local judge improves outcomes.

## Risk Controls

- Reward-hacking: consequence evidence must outweigh the vibe tag. A `good` label is weak if receipts later show regression.
- Held-out eval rows are marked `never_train: true` and must never enter reward/DPO training.
- Advisory-only: eval numbers can recommend review, not take action.
- No production writes: scripts write only the explicit JSONL/report path requested by the operator.
- No self-grants: a stronger judge does not expand its own authority.

## Commands

```bash
python3 -B tools/learn/build_preference_dataset.py --dry-run
python3 -B tools/learn/build_preference_dataset.py --output /tmp/fpai-preferences.jsonl
python3 -B tools/learn/eval_judge.py /tmp/fpai-preferences.jsonl --judge keyword
```

`eval_judge.py` prints one number: judge accuracy minus baseline accuracy. Positive means the judge beat the deterministic baseline on frozen held-out rows.
