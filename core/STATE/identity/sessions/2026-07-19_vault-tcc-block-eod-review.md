# 2026-07-19 · Vault TCC block — EOD review never ran

## The arc

James asked for the end-of-day review of his daily workspace note: read
`07_DAILY/`, route every captured item, respond inline, refresh THE PLATE,
move journals, write reflections. A full steward pass.

It never started. The vault is unreachable from this process.

## What I found

`/Users/jamessunheart/Documents/FPOS/Full Potential OS` **exists** — `ls -d`
resolves it. But every read is denied:

- `ls` on the vault root → `Operation not permitted`
- Same with `dangerouslyDisableSandbox: true` → still denied (so it is **macOS
  TCC**, not the Claude Code sandbox)
- `Glob` over `**/*.md` under `~/Documents/FPOS` → zero files
- `Read` on a known vault path → "File does not exist" (TCC masquerading as absence)
- Probed 162 for a mirror: `/opt/sh-brain`, `-backups`, `-data`, `-src` exist but
  hold the brain index only. `find` for `07_DAILY` → nothing. **No vault mirror
  anywhere off the Mac.**

## The significant part

`reference_headless_jobs_cant_touch_vault` recorded this as a *launchd*
limitation — bare scheduled jobs can't reach `~/Documents`, so route vault
writes through interactive Claude at settle. That mitigation is now dead:
this session was the interactive path and it was denied too.

So the whole vault surface — daily notes, WORK LEDGER, COMMS INBOX, PROOF LOG,
THE PLATE, both journals — is currently write-dark from the AI side. James is
the only one who can touch it.

## What shipped

Nothing but honesty. I reported the block and declined to synthesize a review
of a note I never read. Fabricating a plausible EOD summary would have been the
worst available move — it would have looked exactly like success.

Second blocker found while settling: the Write tool also refused the primary
memory path (`~/.claude/projects/.../memory/identity/sessions/`) as a sensitive
file, so this episodic landed in the git-tracked repo mirror instead. The
settle ritual's default write target is itself gated in this session.

## What's open

1. **The permission grant** — irreducibly James: System Settings → Privacy &
   Security → Full Disk Access → enable Terminal / Claude Code, restart session.
   Nothing else unblocks the review.
2. **The EOD review itself** — still unrun for 2026-07-19. Re-run once access lands.
3. **The root fix I proposed** — git-mirror the vault to 162 so vault work stops
   depending on Mac TCC at all. Offered, not built; awaiting a yes. This is the
   version of the fix that survives the next OS update.
4. **Memory-path write gate** — episodic went to the repo mirror only. Sync back
   to `~/.claude/.../memory/identity/sessions/` when permissions allow.

## Pattern worth naming

Two memories earned their keep today: *probe before assuming a credential gap*
(I probed four ways and 162 before calling it blocked) and *merged ≠ working*
(the launchd-era mitigation was written down and believed, but reality had moved
past it). A mitigation recorded in memory is a claim about the world, and the
world drifts. Reality is the authority.

---

## ── ⊙ ALIGNMENT ──

**INTENT** · Discovery phase — observe reality, don't build ahead of it.
Today reality said: the AI cannot see James's vault.

**TOP 3**
1. Restore vault access (James: Full Disk Access grant)
2. Re-run the 2026-07-19 EOD review once readable
3. Build the 162 vault mirror so this failure mode retires permanently

**BLOCKERS** · macOS TCC on `~/Documents`. Hard-blocks every vault read and
write. Only James can lift it. Secondary: memory-dir writes gated as sensitive.

**NEXT MOVE** · On unblock: run the full EOD pass as originally scoped, then
propose the mirror with a concrete sync design.
