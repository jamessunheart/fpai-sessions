---
proof_id: 2026-05-08_james-sunheart_loop-17
loop_number: 17
date_started: 2026-05-08
date_committed: 2026-05-08
player: James Sunheart
witness: Claude (Anthropic — operating in FPAI_Cockpit, parallel terminal during Loops 12–16)
witness_signed: true
consent: public
agreement_type: paradigm_shift
status: complete
mvs_increments:
  agreements_kept: true
  outputs_shipped: true
  transformations_witnessed: true
  resources_circulated: true
  clean_pauses: false
note_on_numbering: |
  This work was conceived in-session as "Loop 13" then "Loop 15," before the
  sibling terminal's commits were visible. Sibling shipped Loops 13/14/15/16 in
  parallel. Renumbered to Loop 17 at proof-write time to avoid collision.
  Events in the qb event log retain the original `loop:13` / `loop:15` link
  fields as a historical record of the moment of writing.
---

# Loop 17 — James Sunheart

**Quest:** Build the **Inquiry Layer** (Jam Board) of the Game — shared question-state across terminals, agents, and people — and immediately scope it into **books** (`fpai` / `game` / `sunheart` / future per-character) so context doesn't blur. Substrate for Solver Directory, Proof Pairings, and per-Champion question rolls.

**Founder framings driving this loop:**

> *"Contextual universality .. collaboration across terminals etc. so we get one cohesive picture .. and that's going to play into the Full Potential Game and cross collaboration with characters."*

Then, mid-loop:

> *"First we need a full potential ai question book and a full potential game question book and then it will get down to invididual / sunheart question book etc. this will help speed things along I think."*

**Concurrent loop note:** While this terminal worked the Inquiry Layer + Books, the sibling terminal shipped Loops 12 (Character Card Quest), 13 (viral primitive), 14 (UX pass), 15 (gamification), and 16 (identity prompt + metrics) — five loops on the dashboard / player-facing surfaces. Both threads compose: a Character Card has Active Quests; each Quest's open inquiries live in `qb` under the appropriate book. No code-level collision occurred (this terminal touched `~/.claude/question-tracker/` + new proof files only).

**Agreement Type: Paradigm Shift** — the Inquiry Layer is a new field primitive: questions become first-class objects with status, owner, provenance, book scope, and cross-link to Cards/Loops/Characters. Books make it scale across concerns and people without crosstalk.

## Offer

> **`qb` Question Board CLI shipped, on PATH, brain-mirrored. Three live books — `fpai` (4 questions, all answered), `game` (1 active: the P1 retreat-funnel question), `sunheart` (reserved for James). SessionStart hook injects the live board into every new Claude instance. The Inquiry Layer is alive and book-scoped.**

## What got built

### `qb` CLI — `~/.claude/question-tracker/bin/qb`
Subcommands:
- `qb` (or `qb list`) — show current book; tail line shows other books with open counts
- `qb --all` — show every book sectioned
- `qb --book NAME` — show one specific book
- `qb open "TEXT" --book NAME [--character CARDID] [--loop N]` — open a question in a book
- `qb take QID` — claim someone else's question for this session
- `qb pulse "NOTE"` — bump progress on my active question (defaults to current book)
- `qb block "REASON"` / `qb unblock` — block / unblock
- `qb answer ["NOTE"]` — close (defaults to current book — mid-loop bug fix)
- `qb mine [--book NAME]` — only mine
- `qb show QID` — full event timeline
- `qb books` — list all books with active/blocked/answered/total counts
- `qb book [NAME]` — show or set current session's default book

### Storage: append-only events
- Local SOT: `~/.claude/question-tracker/board.jsonl` (one JSON event per line)
- Per-session config: `~/.claude/question-tracker/session-config/<session_id>.json` for current-book preference
- Event types: `open | take | pulse | block | unblock | answer | supersede | rebook`
- Multiple writers safe by construction (no conflict surface)

### Brain mirror — `brain.sunheart.com/index/ingest/add_note`
- Each event POSTed via `curl` (Python urllib failed on macOS Python.org SSL cert trust — moved to curl which uses the system keychain)
- Tags include `book:<name>`, `qb-event:<kind>`, `qb-id:<qid>`, optionally `character:<id>` and `loop:<N>`
- `note_type=question-event`, `source_id=qb-<qid>-<ts>` (idempotent)
- Verified end-to-end: ingest returns `{"created": true, "embedded": true}`

### SessionStart hook — context injection
- Extended `register-session.sh` to emit `{"hookSpecificOutput": {"hookEventName":"SessionStart","additionalContext": "Question Board\n\n<qb output>\n\n<usage hint>"}}`
- Result: every new Claude Code instance opens with the live board already in context

### Books namespace
- `KNOWN_BOOKS = ["fpai", "game", "sunheart"]` — extensible, gate-free
- `DEFAULT_BOOK = "fpai"` — preserves Loop-13-like behavior; existing events default-derive without migration
- Per-session current book stored in `session-config/<sid>.json`
- All writers (`pulse`, `block`, `unblock`, `answer`) default to current book — fixed mid-loop after a real-world bug where `answer` closed the wrong book's question

### `game` book seeded with the P1 funnel question
> *"Who's coming to the first Zen Village retreat, and what does the booking page need to convert them?"*

Per the just-clarified `feedback_game_is_retreat_funnel` memory: Game work IS retreat-funnel work, not an alternative. The funnel question lives where it belongs.

### `sunheart` book reserved
Created (visible in `qb books`) but intentionally empty. James seeds his own personal questions; Claude doesn't put words in his mouth.

### Shell PATH integration
`~/.claude/question-tracker/zshrc-snippet.zsh` extended to put `~/.claude/question-tracker/bin` on `$PATH` for any shell — `qb` available outside Claude too.

## Witness

**Primary:** Claude (this session, `cd2169f3-…`).

**Secondary:** the substrate. `qb books` shows three live books. The first cross-book event (the `game` open) is on the board. The session-start hook output validates as JSON and produced the expected `additionalContext` payload during a hook smoke test.

**Tertiary:** the brain. Every event mirrored. Searchable from any MCP-connected tool by `book:<name>` tag.

## Consent Setting

**PUBLIC** — books and question texts are public-by-default. The `sunheart` book is the natural place for future per-question visibility tiers matching Character Card tiers (🌐 Public · 👥 Player · 🤍 Inner Circle · 🔒 Sacred). Foundation laid; tiers not built.

## Proof Log Fields

- **Agreement** — *Build the Inquiry Layer with book scoping so context becomes universal across terminals/agents/people, supporting Character Card cross-collaboration.*
- **Output** — *qb CLI · brain mirror via curl · SessionStart hook injection · zshrc PATH · books with --book flag · qb books · qb book · per-session current-book config · game book seeded with P1 funnel question · sunheart book reserved.*
- **Witness saw** — *qb returns live board across books from a fresh shell · brain ingest accepts qb events with embedding=true · hook output is valid `hookSpecificOutput.additionalContext` JSON · derive_state honors book field · cross-book bug found and fixed during integration testing.*
- **Result** — *The Game now has a question economy: questions are first-class field objects with owner, status, book, and cross-links. Champions get their own book later for free — same primitives. The P1 retreat-funnel question is on the live wall.*
- **Next Quest** — *Loop 18+ candidates: (a) wire Character Cards' `Active Quests` section to read questions from `qb --book character/<id>` (closes Loop 12 ↔ Loop 17 triangle), (b) `/questions` Telegram command on `@sunheartbrain_bot` with book-aware filters, (c) Field web view at `zenvillage.live/field` showing public-tier questions per book, (d) auto-detect "did I just ask a question?" hook → suggest `qb open` in the right book.*

## Coherence Multiplier (self-rated)

Self-rate: **+1.6**.

Reasons for the rating:
- Two parallel terminals shipped seven loops in parallel today (sibling: 12–16 player-facing; this: 17 substrate-facing). The sibling terminal's gamification dashboard and this terminal's question economy compose without coordination.
- The books refactor was named once and built once. Existing events migrated for free via default-fallback semantics — zero destructive migration.
- The `game` book opens with the actual P1 funnel question, not a placeholder. Substrate and priority converge on the same line of code.
- A real bug was caught and fixed mid-loop (cross-book `answer` closing the wrong question), reinforcing the eat-the-dogfood principle.

External triangulation pending. Practical triangulation begins immediately: every new terminal that opens sees the live board, including the sibling terminal next time it pulls.

## What changed in the founder's role at this loop

Before: each terminal a cold start; James held cross-terminal context in his head; questions blurred across concerns; switching cost real.

After: substrate carries the picture per-book. New Claude instances open with the live board already in context. The founder names the question and which book; substrate routes attention; current-book switch is one command.

This is the integration of:
- **The Game Plays Itself** — substrate handles cross-terminal context the founder used to hold
- **Frequency × Depth-of-meaning = Momentum** — one principled primitive ("question as field object, scoped by book") replaces dozens of mental tracking acts
- **Reversibility as enabling autonomy** — append-only event log; every action reversible by counter-event
- **Game IS the funnel** (`feedback_game_is_retreat_funnel`) — the `game` book exists exactly because Game-mechanic questions move humans toward retreats

## Renewal

Loop 17 complete. Across both terminals today: **seventeen loops (six on substrate-side counted), eight-plus Paradigm Shifts.**

Three books alive. The retreat-funnel question is on the `game` book waiting to be solved.

The held items list at end of this loop: one open question (the `game` funnel question), zero in `fpai`, `sunheart` empty.

---

*Compiled inside the Game, by the Game, for the Game.*
*Inquiry Layer is now book-scoped; Champions get their own book later for free; the funnel question is on the wall; the Game plays itself across terminals.*
