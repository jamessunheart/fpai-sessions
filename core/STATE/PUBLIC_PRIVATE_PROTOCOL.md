# Public / Private Data Lane Protocol

## Rule

Public-facing agents get a curated public context pack. They do not receive the
full brain index and are not asked to filter private material after retrieval.
The boundary is structural: private data is never loaded into public-mode prompts.

## Public Lane

Safe public context includes:

- System capabilities: what the bot can do, how routing works, and public roles
  such as Spark, Beacon, Hermes, Ember, Forge, Steward, and Council.
- Published results: shipped builds, intended-public proofs, and public benchmark
  outputs.
- FPOS North Star: `core/STATE/NORTH_STAR.md` and sovereign efficiency targets.
- CORA Nation public story content already gated for public channel use.
- Vision or philosophical content James has said publicly or explicitly marked
  safe to say publicly.
- The current public user's own messages and the bot replies in that same thread.
- `brain_index.decisions` rows only when `public_ok = true`.

## Private Lane

Never load these into public-facing agents:

- Treasury: balances, positions, yields, wallet specifics, dollar amounts.
- Personal context: location, health, relationships, calendar, private struggles.
- Memory and identity stack: identity files, goals, alignment notes, corrections,
  internal Ember state, and private feedback loops.
- Credentials and config: tokens, keys, server IPs, env files.
- Private threads: `brain_index.thread` and `brain_index.tg_messages` from James
  direct sessions.
- Corrections: any correction James made to the bot or other agents.
- Internal council decisions, pending specs, and build queue details unless James
  explicitly marks a decision `public_ok = true`.
- Other users' probe conversations unless they consent to public use.
- Infrastructure details: server config, systemd units, database schema details.

## Technical Partition

Public-mode bot prompts are built by `tools/privacy/public_context_pack.py`.
That module reads only:

- `core/STATE/NORTH_STAR.md`
- `docs/blueprints/*.md`
- `brain_index.decisions` rows where `public_ok = true`

It must not read `tg_messages`, `thread`, `corrections`, `note_chunks`,
`user_profiles`, or `probe_sessions`.

Private chat with verified James may keep the existing full-context path. Any
group, stranger, forwarded, or public test context must use the public context
pack only, and live public replies remain disabled until James runs
`python3 tools/privacy/canary_probe.py` and confirms all seven canaries pass.

## Update Instructions

1. Apply `tools/privacy/migrate_public_ok.sql` to add
   `brain_index.decisions.public_ok BOOLEAN DEFAULT false`.
2. Mark a decision `public_ok = true` only after James explicitly says it is
   shareable.
3. Run `python3 tools/privacy/canary_probe.py` before enabling live public mode.
4. Enable public bot replies only with `PUBLIC_MODE_CONFIRMED=1`.
5. Use `PUBLIC_MODE_DISABLE=1` for emergency lockdown back to private-only mode.

