# claude_review Mastery Card

## What it does best
Claude review is best as an independent skeptical merge gate: find bugs, scope creep, guardrail bypasses, missing tests, and risky assumptions in a Codex-authored diff before Ember merges.

## Optimal use patterns (concrete, with examples)
- Frame the job as protecting the live system, not being agreeable. Example: "Review skeptically. When in doubt, REQUEST_CHANGES."
- Provide the diff, base branch, spec intent, and protected-path rules in the same prompt.
- Force structured output with a small verdict schema: approve/request changes, risk, summary, findings.
- Ask it to look specifically for money, production, secrets, identity/memory, main-branch, and autonomous guardrail changes.
- Keep the diff bounded; truncate oversized diffs and flag for manual review instead of pretending coverage is complete.

## Anti-patterns (what silently degrades it)
- Approving because no findings were obvious on a quick read.
- Trusting Codex output uncritically or reviewing only style.
- Missing scope creep outside the spec because the prompt lacks the spec boundary.
- Allowing prose-only verdicts that cannot be parsed by the merge gate.
- Reviewing protected audit/improve paths with AI instead of hard-blocking them.

## Effort/parameter settings for this system
Use high effort and a strict JSON schema for merge review. Keep `REQUEST_CHANGES` as the safe default on parse errors, model errors, missing diff, or uncertainty.

## Key constraints and hard limits
The reviewer does not merge. Protected paths are blocked without model consultation. Review output is advisory unless the merge gate and Ember accept it.

## How to detect it's not performing well
It returns malformed JSON, empty findings on a high-risk diff, vague praise, no file-grounded concerns, or misses forbidden domains named in the prompt.

## Last updated + source
Seeded 2026-06-16 from `tools/merge/ai_review.py`, merge-gate doctrine, and d046 prompt requirements.

