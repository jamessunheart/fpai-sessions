# core/BUILD/intents — James speaks, the system builds

The **Ember-as-builder** lane. James doesn't write specs — he speaks plain intent from
Telegram, and Ember turns it into a built, reviewed change.

## Flow

```
James (Telegram):  "build: a daily report that texts me the treasury balance"
   → tools/queue/build_intent_router.py captures it here as <update_id>-<slug>.md (status: open)
   → Ember drafts core/BUILD/specs/NNN-<slug>.md from the intent
   → tools/build_loop/run_codex.sh builds it in an isolated worktree (branch build/NNN)
   → Ember reviews the diff, writes core/BUILD/reviews/NNN-<slug>.review.md
   → Ember replies in the Telegram thread: "built, tests green, merge? ⚡"
   → James: "merge" → it ships
```

## Trigger
Any Telegram message starting with `build:` becomes an intent. (Short exact words like
"running them" still go to the verb_router gate-answer lane — the two never collide; each
has its own cursor.)

## Runs automatically
`build_intent_router.py` is invoked by `tools/decisions/daily_sync.py` on the same cadence as
the verb router. Capture is safe (Reserved-Class): NOTHING builds, merges, or sends from the
capture step — Ember drafts and James blesses.

## Status of an intent
`status: open` → captured, awaiting Ember spec · move to `specs/` once drafted ·
the intent file gets `status: specced` when a spec exists, `status: done` when merged.

## The remaining piece
For fully-hands-off (you text → it builds while you sleep), Ember needs an always-on listener
(a small daemon on the Mac or server). Until then, intents queue here and the next Ember
session processes them.
