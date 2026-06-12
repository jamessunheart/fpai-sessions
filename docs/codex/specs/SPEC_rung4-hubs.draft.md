# SPEC_rung4-hubs

> DRAFT - review before dispatch.
> This file is a proposal generated from a buildstream intent. Do not auto-dispatch,
> auto-build, kickoff, merge, deploy, move money, touch secrets, or treat it as
> approved until Ember/James reviews and promotes it from `.draft.md` to `.md`.

*Draft generated for intent `rung4-hubs` in stream `Game`. Weight: 0.*

## Source / why
Buildstream intent: **Rung 4**

Next move from intent:
```text
apprentice fleet builds comms · financial · recruiting hubs, sequenced by leverage
```

Notes:
```text
TODO(review): add source notes
```

## The three declarations
- **Milestone (DoD):** TODO(review): turn `apprentice fleet builds comms · financial · recruiting hubs, sequenced by leverage` into one concrete, testable milestone.
- **Dependency:** TODO(review): confirm dependency before build
- **Landing target:** TODO(review): choose landing target branch; never main without explicit review

## Definition of Done
1. TODO(review): name the exact artifact, function, command, or document this spec will produce.
2. TODO(review): list the observable behavior that proves the artifact works.
3. TODO(review): list the narrow test command(s), dry-run command(s), or review checks.
4. TODO(review): confirm no Reserved-Class action is executed by this spec.

## Files
- **Files ALLOWED:** TODO(review): list exact paths or globs the builder may touch.
- **Files FORBIDDEN:** production deploy state; secrets; money movement; public sends; non-draft specs unless explicitly promoted by Ember/James; unrelated refactors.

## Safety
- This draft is not dispatchable until human review promotes it.
- Unknowns stay as `TODO(review):` markers.
- No live autoloop wiring, sends, money movement, deploys, secrets, merges, or approvals.
- If the implementation reaches a Reserved-Class boundary, stop and write a human-edge gate instead of proceeding.

## Tests
- TODO(review): add focused unit tests for the artifact.
- TODO(review): add a dry-run or fixture check that writes no live state.
- `git diff --check` scoped to the allowed files.

## Rollback
- Delete the files created by this future spec.
- Remove any draft/review artifacts it writes.
- Remove this draft if Ember/James rejects it.

## Close-out
- Update `docs/codex/HANDOFF.md` in the Codex -> Ember lane.
- Report files changed, summary, tests, risks, rollback, intent solved, downstream intent unlocked.
- Do not merge or dispatch without James/Ember review.
