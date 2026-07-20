---
name: 2026-07-11_email-canary-chronic-false-alarm-fix
description: Email canary kept crying wolf — root cause was laptop-vantage TLS throttle, not mail health. Fixed via 162 re-verification.
metadata:
  type: session
  originSessionId: 20a0d98a-e05a-4585-992e-f63db3c04d7e
---

# 2026-07-11 · Email canary chronic false-alarm — killed at the root

## The arc
James forwarded a 🟡 "POP3 CONNECT FAILED (network/TLS)" canary alert, then asked
the sharp question: **"how come it keeps crying wolf? we want to reduce signals not needed."**
Not "is mail down" — "why is my monitor lying to me." That reframed it from a mail
problem to a **signal-quality** problem. The right instinct: an alert that fires when
nothing is wrong is worse than no alert (manufactured false confidence's evil twin —
manufactured false alarm).

## What I found
Read the log (`~/.config/fpai/email_health/log.jsonl`): `james@fullpotential.com` POP3
returned `net: SSLEOFError` on **every** check for hours, while:
- `james.stinson@outbounders.com` POP3 = ok (different host)
- receiving-via-162 round-trip = delivered
- (Gmail's real fetch runs from Google IPs, unaffected)

So mail was 100% healthy. Proved the vantage hypothesis live: from **162** the same
`mail.fullpotential.com:995` login is **TLSv1.3 OK**; from the **laptop** it drops the
handshake. The laptop's RESIDENTIAL IP is fail2ban/rate-throttled by 198's dovecot.
The 2-consecutive gate "worked" but the condition never healed, so it re-tripped and
paged every 3h. **Same class of bug as 2026-06-17** (receiving probe had to move to 162
for the identical reason) — the POP3 read-check never got that lesson.

## What shipped
- **Code:** `~/.config/fpai/email_health/check_pop3.py` — added `_verify_pop3_via_162()`
  and wired it into `check_pop3`. A persistent `net:` failure now escalates to a 162-side
  POP3 login (password via stdin). 162 clean → `ok (via162; laptop-vantage throttled)`,
  no alert. 162 also fails → real, surfaces 162's verdict (auth:/net:). 162 runner can't
  run → `via162:` class → transient-gated 🟡, never 🔴. (NOT repo-tracked — laptop-local.)
- **Verified live:** ran it → exit 0, `all_healthy`, zero alert. Wolf silenced.
- **Memory:** updated `reference_email_health_canary.md` with the 2026-07-11 fix block.

## What's open
- The canary file lives only on the laptop (`~/.config/fpai/`), not in git. No durable
  backup beyond memory. If the laptop dies the fix is gone — same fragility flagged before.
  Consider: move the whole POP3 canary to run on 162 (it already has the recv probe there),
  retiring the laptop as a probe origin entirely. Would eliminate the vantage class of bug
  for good rather than patching around it.
- Two Stop/preflight hooks fired this session (settle + canonical-read gate) — expected.

## Late addendum — laptop disk near-full (same session)
James: *"whatsapp says storage full, why is computer so full — check recently deleted photos, dump if possible."* Diagnosed: **10 GB free on a 460 GB disk.** The whale is `~/Pictures/Photos Library.photoslibrary` = **269 GB** (225 GB originals). Not WhatsApp. Queried the Photos DB read-only (`/tmp/photos_ro.sqlite` copy): **Recently Deleted = 499 photos ≈ 6.1 GB** (via `ZADDITIONALASSETATTRIBUTES.ZORIGINALFILESIZE`, `ZTRASHEDSTATE=1`, trashed Jun 13→Jul 11). Did NOT auto-empty — permanent photo deletion is irreversible = James's call (correctly RESERVED, not substrate). Gave him: (1) ⚡ empty Recently Deleted in Photos (~6 GB, band-aid), (2) 🔵 the real fix = iCloud "Optimize Mac Storage" (offload originals, 100 GB+), (3) 🟡 move library to external. **Open:** James hasn't picked yet; 6 GB is hours, the 269 GB library is the actual problem. **Reusable:** the read-only Photos.sqlite copy + `ZTRASHEDSTATE=1` join is the pattern to size Recently Deleted without touching the live library.

## Alignment
- **INTENT:** DISCOVERY phase — reality is the authority. Today: keep the signal layer honest
  so real signals aren't drowned (a reduce-James's-load act).
- **TOP 3:** (1) prove transformative conversations (unchanged frontier), (2) value capture /
  growth engine (downstream), (3) signal hygiene — monitors that only fire on truth.
- **BLOCKERS:** none.
- **NEXT MOVE:** if it recurs, promote the canary to 162-native. Otherwise silent.
