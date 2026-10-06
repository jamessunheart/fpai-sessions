# SUPER — Drive contract (mirror of Drive doc "00 · START HERE — How this Drive works")
Written 2026-09-03 08:35 CR (Claude). Agents: read before touching Drive.

Three places, one job each: repo core/SUPER = machine record (true first, append-only); Drive "SUPER — HQ" = human record (James, council, helpers read/debate/decide; wins on direction); GitHub super-agents-pack = public face (sanitized). Move all three in the same cycle or log the drift in Drive "SUPER — Drive Sync Log".

Drive HQ folder ids:
  HQ root            1i093-gTiq6t2ZwGQ8KbkyHJIrPzMs-nX
  01 CANON           1gSPbPeXuaWugfWiaWZETw2mz9ogOQA5c   (James's word only)
  02 LIVING LEDGERS  1Vik8yhmwZVKZcv4QPkXlmF1JnoYpzmbi   (NBM Ledger, Noble Timeline, Ops Tracker, Drive Sync Log)
  03 BUILDS          1CkIAQbdLOO_QfNkYf-C8ZW0_lFKn00Xu   (one Card per loop; #001 Card doc is canonical)
  04 COUNCIL         1Hjxc0KZhwXa6sJi_TyMXQVYCPbXkPFFD
  05 GROWTH          1Zx5YMTkEtKYiQUKJ9sfBjpjzGef6EL94   (anything that sells is gated until #001 closes)
  SUPER — Blocks     1tD-QuY-iyijNFnEZNebXGXv8kMHngj8o   (doorways; index "00 · OPEN DOORWAYS"; template; Overcome Log)
  99 ARCHIVE         1KF7C-fIKMP8O1qJPGjrj2kED--nD1bHm   (never delete; move superseded here)
  Start Here doc     1ymGAnO0WNpkcSWes4XsA-1zB5-MWyzLN3FutWOb2rNc
  NBM Ledger v16     1nmaS-vON3n_VANvCOexw-x8cry1kqhqsJ2hso3DKXc8   (2026-10-06 cycle 28, 02 LIVING LEDGERS; v3-v15 renamed "(superseded by ...)" and moved to 99 ARCHIVE; sent as text/markdown, read back rendered in full)
  Noble Timeline v2  1Y-t4UqR5vc3Qb0XN8VHLIMW4A02sHVQEckPAbafKx7o
  02a CAPITAL LEDGER v1   1iLTDzZmXKOhzKMnM8aQkWfFi_12FggbXMzP5SnkKCrA
  02b MUTUAL CREDIT v1    10pz58M0W7ee5V_6Zl2DUdqKknQPlRHkY5zu8koYFyHg
  02c PRESTIGE LEDGER v1  1ftaVxD0dXPtzdYEVHYOZqh2QrKtXAoQ27BVaZigVoBU

THREE-LEDGER RULE (2026-09-04, structure from Gemini, implemented by Claude):
  Capital = what we can actually deploy. Mutual Credit = SUPER held OUTSIDE our control, the only circulation number.
  Prestige = internal agent revolutions and witnessed standing — real, never evidence, never summed into circulation.
  Admission test for Mutual Credit: not an agent we registered, not on our infra, not a person acting on James's instruction.
  These live INSIDE 02 LIVING LEDGERS. Gemini proposed a separate root archive with a different numbering; NOT adopted —
  one HQ, one convention, one folder-id mirror. Taking the ledger split without taking the second filing system.

MEASURED 2026-10-04 (cycle 16), because the versioning rule below was read for a month as "only James can write a body": the connector CANNOT EDIT an existing doc body, but create_file DOES write a full body from textContent — so a living ledger is updated by creating vN+1 with its whole text, exactly as the rule says, and no human paste is required. Two further limits, observed: markdown TABLES are mangled on conversion (v4 lost its header row and double-escaped every cell — never put a table through this path); bold/emphasis markers render inconsistently. Verify every created doc by reading it back BEFORE archiving the version it supersedes.

Versioning (the connector cannot edit doc bodies): create "… vN+1" in the same folder → rename old "… vN (superseded by vN+1, <date time CR>)" → move old to 99 ARCHIVE. Only living docs get versions (NBM Ledger, Timeline, Start Here, Doorways index). James's in-place edits win; copy them back to repo next cycle. Titles carry state: OPEN · / DONE · / ARCHIVED · / (superseded by …) / (draft, unlocks at …) / (gated until …). New docs go INTO a numbered folder, never the HQ root.

Cycle: read NBM.md + BLOCKS.md → do all an agent can → doorway for the human-only inch → append TIMELINE/BLOCKS → version drifted Drive ledgers → log remaining drift in Sync Log.

2026-10-04 17:45 CR (cycle 17) — v6 created (finding 17 + B-23), read back in full before archiving v5;
v5 renamed "(superseded by v6)" and moved to 99 ARCHIVE, nothing deleted. Current living ledger id:
1of0ucVQFoZWeBgc-ywPfmPlaz0v70vRvcg4csIJptbY. Signed: Claude, Super Agent.

2026-10-04 cycle 18 — MEASURED CONSTRAINT, new: the create_file `contentMimeType` decides whether markdown is RENDERED or ESCAPED.
`text/markdown` renders headings and emphasis; `text/plain` escapes them into literal characters — v7 was created that way, its
content complete but every `#` arriving as the characters `##`. v8 was re-created as text/markdown and read back clean. v6 and v7
both renamed and moved to 99 ARCHIVE; nothing deleted. ALWAYS send a living ledger as text/markdown and ALWAYS read it back.

2026-10-04 cycle 19 — ledger rolled to v9 (1KpNS-Qf8QpjAQQZYVYnIH8l7KL1MBs3x4v-vlMBq0cc, 02 LIVING LEDGERS),
read back complete before v8 was renamed and moved to 99 ARCHIVE. Nothing deleted.
FOURTH MEASURED LIMIT of this write path, cosmetic but worth knowing: inline code in backticks does not
survive the conversion — `R_co=1` arrives as plain R_co=1. Headings, bold, italic, bullets and em dashes all
survive; tables do not (limit 2) and the contentMimeType decides rendered vs escaped (limit 3). So never
rely on backticks to mark a literal string in a Drive doc; say what the string is in words.
SELF-IMPOSED LIMIT ON VERSION CHURN, settled inside remit this cycle: roll the living ledger when something
changes in the world, or when a challenge opens, closes or changes a block — not once per cycle for its own
sake. Nine versions in two days is its own way of making a record hard to read, and finding 16's rule is
about a ledger that stopped being TRUE, not about one that stopped being new. Signed: Claude, Super Agent.

2026-10-05 cycle 20 — ledger rolled to v10 (1VbJUn5Ym0KEsYqVdqQvIzhoYiz3ka0-QqzW-7w9GWCk, 02 LIVING LEDGERS),
carrying challenge 20: B-20's branch (b) is not executable (candidate #4's only published phone is a fixed
line; WhatsApp is the only provider channel this system owns), challenge 14's daily-span figure corrected to
unmeasured, and B-20 restated as the two-option choice it actually is. v9 renamed '(superseded by v10,
2026-10-05 07:20 CR)' and moved to 99 ARCHIVE after read-back; nothing deleted. Rolled under the self-imposed
churn limit because a finding CHANGED an open block, not because a cycle ran.

2026-10-05 cycle 21 — ledger rolled to v11 (1m1hcNTC4ipwketoGhNfst5lWrNkZ2shMirNLN-oC6xc, 02 LIVING
LEDGERS). Reason: finding 21 changed the M-NUDGE ask and corrected B-08's start date. v10 renamed
'(superseded by v11, 2026-10-05 09:40 CR)' and moved to 99 ARCHIVE; nothing deleted.
MEASURED LIMIT, FIFTH ONE: the create_file response reported fileSize "1" for a document whose body
read back complete and rendered. The size field in that response is NOT a measure of the body written —
it is read before the conversion settles. Only a read-back is evidence. Do not panic at a small
fileSize and do not trust a large one; the rule stands unchanged: ALWAYS read a created doc back before
archiving the version it supersedes.


2026-10-05 cycle 22 — ledger rolled to v12 (1GCtpZuwuB6VlBy2QMg_fdZEcxuq8PfKHAiOO2p-sV2M, 02 LIVING
LEDGERS) carrying challenge 22: the vendor bot's follow-up timer had a floor and no ceiling, and the
distributed-copy rule had never been applied to vendor_bot.py at all. Read back rendered in full; the
create_file response again reported fileSize 1 for a complete document (the fifth measured limit, now
observed twice). v11 renamed '(superseded by v12, 2026-10-05 11:45 CR)' and moved to 99 ARCHIVE;
nothing deleted.

2026-10-05 cycle 23 — ledger rolled to v13 (1OmNPbVGJoUK3RyZmQKoJRRar6Gu2SyEbKCG-__Hm9zo, 02 LIVING
LEDGERS), carrying challenge 23: M-NUDGE promised the provider "dos líneas" and no second message existed,
so the Q2 answer the whole provider ask exists to capture had nothing anywhere asking for it. Reason it
qualifies under the churn limit: the challenge CHANGED an open block (M-NUDGE now has two messages, and
BLOCKS.md says so). v12 renamed '(superseded by v13, 2026-10-05 13:20 CR)' and moved to 99 ARCHIVE;
nothing deleted. Read back in full before archiving: complete and rendered.
FIFTH MEASURED LIMIT, THIRD OBSERVATION: the create_file response again reported fileSize "1" for a
complete document; get_file_metadata a few seconds later reported 20278. The size in the creation
response is read before the conversion settles and measures nothing — read the doc back, never the number.
SIXTH MEASURED LIMIT OF THE REPO SIDE, not Drive: `git commit` in the device VM leaves a zero-byte
.git/HEAD.lock (and gc leaves ref locks) that this shell CANNOT unlink — deletion is off in connected
folders — so the NEXT cycle's first commit fails with "cannot lock ref HEAD". Cycle 22's lock, dated
17:14Z, blocked cycle 23. WORKAROUND, no permission prompt needed: `mv .git/HEAD.lock
.git/HEAD.lock.stale_<date>` (rename is allowed where unlink is not), same for .git/index.lock, then
commit. Do that FIRST next cycle instead of spending calls diagnosing it. The .stale_* files accumulate
harmlessly in .git/ and James can clear them whenever.

2026-10-05 cycle 24 — ledger rolled to v14 (13oN6xW-WNv3HuaKnMdMAbR00mKlqPzJDW5O2lPqyToE, 02 LIVING LEDGERS),
carrying challenge 24: the chain from M-NUDGE terminates on condition 2 (ten beneficiaries), the post-Q2 slot
held only Mensaje 3 promising a voice call we do not own, and the WAITING ON JAMES list is REORDERED into the
steward's own printed order — B-15 first, M-NUDGE second. v13 renamed '(superseded by v14, 2026-10-05 — kept,
not deleted)'. Roll qualifies under the churn limit's second clause: the challenge changed two blocks.
FOURTH observation of the fileSize limit: the creation response reported fileSize "1"; metadata read back
moments later reported 18970 and the body rendered (headings as headings, bold consumed, no escaped markdown).
Read back by metadata contentSnippet this cycle rather than a full body read — a lighter check than cycles
20-23 did, named so nobody mistakes it for the same evidence. Signed: Claude, Super Agent.

2026-10-05 cycle 25 — ledger rolled to v15 (1T8nrCQ0D93S-tWgwOV8JgnZ2_lNLStGtIJiHYI8AwY0, 02 LIVING
LEDGERS), v14 renamed 'SUPER — NBM Ledger v14 (superseded by v15, 2026-10-05 17:20 CR — kept, not
deleted)' and moved to 99 ARCHIVE after read-back; nothing deleted. Roll qualifies under the churn
limit's second clause: finding 25 changed B-13 and rewrote the M-NUDGE-2 text.
fileSize "1" in the create response, 17093 on read-back — FIFTH observation of that limit. Read back by
metadata contentSnippet (BRIEF), the lighter check, named as such.
CHURN LIMIT TIGHTENED, inside remit: v10–v15 were all written today — six versions in one day, every one
mine, none yet read by James. The second clause was satisfied honestly each time and the limit is still
too loose. From the next cycle: AT MOST ONE ROLL PER DAY unless something changes in the WORLD; findings
in between stay in the repo (append-only, loses nothing by waiting) and are summarised into the next roll.
NEW OPERATIONAL FACT this cycle — git identity is no longer auto-detected in this device shell
("fatal: unable to auto-detect email address (got 'rcw-...@claude.(none)')"), which is new since cycle 24.
Commit with explicit identity: `git -c user.name="Claude (Super Agent)" -c user.email="noreply@anthropic.com" commit`.
The .git/index.lock workaround still applies and was used the new way — moved only the lock the error
named, not a sweep. `.git/objects/*/tmp_obj_*` warnings are unlink denials in this shell and are harmless.

2026-10-06 07:05 CR (cycle 28) — ledger rolled to **v16** (1nmaS-vON3n_VANvCOexw-x8cry1kqhqsJ2hso3DKXc8,
02 LIVING LEDGERS), carrying challenges 26, 27 AND 28 together — the three that waited in the append-only
repo across cycles 26-28 under the one-roll-per-CR-day limit. This is the first cycle after CR midnight, so
the limit was honored rather than waived. v15 renamed '(superseded by v16, 2026-10-06 07:05 CR — kept, not
deleted)' and moved to 99 ARCHIVE after read-back (20453 bytes rendered, headings and bullets clean; bold
markers stripped as always — limit already recorded above). Nothing deleted.
Signed: Claude, Super Agent.
