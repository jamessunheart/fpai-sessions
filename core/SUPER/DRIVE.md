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
  NBM Ledger v6      1of0ucVQFoZWeBgc-ywPfmPlaz0v70vRvcg4csIJptbY   (2026-10-04 cycle 17; v3, v4, v5 renamed '(superseded by ...)' and moved to 99 ARCHIVE)
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
