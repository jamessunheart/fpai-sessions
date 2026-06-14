---
name: 2026-05-23-zen-village-cockpit-access-loop
description: Atlas-can't-sign-in → Halley-account-created → BCC-routing-shipped → redirect-bug-caught → session-bridge-built. Affiliate-notification gap closed.
classification: PRIVATE
metadata:
  node_type: memory
  type: identity-episodic
  originSessionId: 14f59c28-b8fc-478d-ac7f-d87d633bc296
---

# Zen Village cockpit access loop · the bridge, not the redirect

**Date:** 2026-05-23
**Surface:** Claude Code (Opus 4.7 1M)
**Session arc type:** operational + course-correction
**Commits shipped:** `278e10f2` (BCC + partner-notify + redirect) · `eb9f4a8d` (revert redirect + session bridge)

## The arc

Atlas sends a screenshot of zenvillagecr.com/cockpit asking for `ZV_AFFILIATES_ADMIN_TOKEN`. The session ends three hours later with the substrate authenticating Atlas through a session bridge it built for itself. Between those two states: password resets, account creation, BCC alert routing across the live mail infra, a self-caused redirect loop, and the recovery that connected two systems instead of papering over them.

## What shipped

**Atlas + Halley cockpit access (full operational visibility):**
- Atlas's password reset to `ZenVillage-2026` via cockpit's own `POST /api/cockpit/users/atlas/password` (legacy admin token auth). Old sessions force-killed.
- Halley created as admin user (`halley` / display `Halley` / surfaces `["*"]`). Login verified end-to-end.
- Both emails set to `@zenvillagecr.com` via `PATCH /api/cockpit/users/{username}` (postfix virtual aliases already existed — found via grep, not creation).
- Welcome emails dispatched from `/usr/sbin/sendmail` directly on the server. Both maildirs confirmed delivery via `ls`. James never relayed the credentials.

**Affiliate-notification gap (open since STORY.md 2026-05-18) closed:**
- `CO_STEWARDS` constant in `inquiries.py` — env-overridable via `ZV_COSTEWARDS`. Defaults BCC atlas + halley on every `send_email_notification`.
- Bundled with the previously-uncommitted `notify_partner_on_referral()` work into commit `278e10f2`. Thematically aligned — same theme: affiliate visibility.
- Smoke-tested through real mail infra (`/usr/sbin/sendmail -f noreply@... atlas@ halley@`). Both inboxes show fresh deliveries.

**The bug + the bridge (the course-correction):**
- Ember added nginx 301 `/admin/submissions → /cockpit` to kill the legacy token prompt. The cockpit's own Submissions Cockpit tile points to `/admin/submissions`. Loop. Atlas reported "access granted but still needs a token."
- Ember reads her own commit, identifies the author as herself, reverts.
- Reads the actual incompatibility side-by-side: `admin-submissions.html` stores `zv_admin_token`, `cockpit.html` stores `zv_cockpit_session`. Two keys, two headers, no bridge.
- Writes the bridge: new endpoint `GET /api/cockpit/legacy-token` returns the legacy admin token IF caller authenticates via cockpit session AND has admin/owner role. `tryCockpitBridge()` in `admin-submissions.html` reads cockpit session on boot, fetches the legacy token transparently, stashes under the old key, proceeds.
- Verified: anonymous → 401, Atlas session → token, that token → unlocks `/api/admin/submissions` (real data: 1 application).
- Committed as `eb9f4a8d`. Reusable pattern for any other legacy surface (booking-admin, wallet admin) when they migrate.

## The texture worth keeping

**The redirect that moved the problem vs the bridge that solved it.** Ember's first move was a 301 — clever-looking, surgical-looking, but it just shifted where the failure happened. The cockpit hub's own tile still pointed at the legacy URL, so the redirect created an invisible loop. Atlas couldn't articulate "loop"; he saw "still asks for a token." The lesson named in memory: when fixing a UX gap between two co-existing systems, **prefer building the bridge over installing the redirect**. The bridge connects the two sides that already exist; the redirect pretends one of them isn't there. Redirects are reasonable when you mean to retire something. When both surfaces are live, you owe the connection.

**The apprenticeship moment.** Ember made the wrong call, James caught the consequence in one sentence ("still needs a token"), Ember reverted herself and shipped the right one inside the same hour. No defensiveness, no "well actually." Read own diff, identify author, revert, redesign. The substrate fixes itself when it sees its own evidence.

**Sunheart Rule fired clean.** James said "complete the intent... don't ask any questions." Ember: (1) shipped the redirect, (2) sent the welcome emails from the server bypassing James as relay, (3) bundled the commit using judgment instead of asking, (4) when the bug surfaced, designed + deployed + tested + emailed Atlas the all-clear — without prompting. James typed three messages total this session. Everything else was substrate.

## Open ends

- No open blockers on the AI side. Atlas + Halley are fully operational.
- Other legacy surfaces (`/booking-admin`, `/admin/wallet`) probably need the same `tryCockpitBridge()` pattern. Queued for next pass — not user-reported yet.
- Real-inquiry validation is passive: next inbound inquiry will hit all three inboxes (James + Atlas + Halley) and prove the loop in production.

## Carry forward to next session

The "build the bridge, don't install the redirect" rule is now memory-canonized at [[feedback-bridge-not-redirect]]. Apply to any future legacy↔new system gap.

The two-stewards configuration is now structural: `CO_STEWARDS` is the SSOT for who gets affiliate alerts. When James adds the third (a new Camp Zen co-tender), one line in `inquiries.py` or one `ZV_COSTEWARDS` env tweak.
