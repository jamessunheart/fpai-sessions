# AI Pairing Account Security

Repo-side implementation for d062. The goal is to bind AI-facing user pairings
to a verified identity and make hijack/account-takeover drift visible before an
AI surface accepts commands.

## What Shipped

- `brain_index.ai_user_pairings` stores one verified binding per AI surface,
  provider, and provider user id.
- `brain_index.ai_pairing_security_events` records allow/challenge/block
  decisions from runtime guards.
- `tools.identity_pairing.guard` evaluates observed identities against verified
  pairings and detects multi-subject binding anomalies.
- `sh-brain-tgbot` can enforce verified pairings when
  `AI_PAIRING_ENFORCE=1`.

## Runtime Posture

Default is compatibility mode. Existing Telegram owner/team env allowlists still
work unless `AI_PAIRING_ENFORCE=1` is set.

When enforcement is enabled, owner/team messages and approval callbacks must
match an active `ai_user_pairings` row:

- `ai_agent = sunheart-brain`
- `provider = telegram`
- `provider_user_id = Telegram from.id`
- `chat_id = Telegram chat.id`
- `status IN ('verified', 'active')`
- `assurance_level >= 2`
- `verified_at` not stale
- optional `identity_fingerprint` matches the observed provider identity

If a verified row is missing, revoked, stale, low-assurance, or drifted, the bot
blocks/challenges the action and appends an event. It does not mutate accounts,
send external alerts, deploy, or revoke users.

## Seeding A Verified Telegram Pairing

Live seeding is Ember/host work because it touches production identity state.
Use a one-time verified human check, then insert a row similar to:

```sql
INSERT INTO brain_index.ai_user_pairings
  (subject_id, ai_agent, provider, provider_user_id, chat_id, username,
   verification_method, assurance_level, status, verified_at)
VALUES
  ('james', 'sunheart-brain', 'telegram', '<telegram-from-id>',
   '<telegram-chat-id>', '<telegram-username>', 'manual-human-confirmed', 2,
   'verified', NOW());
```

For fingerprint enforcement, set `AI_PAIRING_FINGERPRINT_SECRET` and store the
HMAC emitted by `tools.identity_pairing.guard.identity_fingerprint(...)` in
`identity_fingerprint`. The fingerprint is not a secret, but the HMAC key is.

## Account-Takeover Signals

Treat these as high-priority review signals:

- one provider user id bound to multiple subjects;
- one chat id bound to multiple subjects;
- provider user id or chat id mismatch on a previously verified row;
- `identity_fingerprint_mismatch`;
- revoked/suspended/compromised pairing reuse;
- repeated challenge/block events for the same subject.

## Rollback

Unset `AI_PAIRING_ENFORCE` to restore compatibility mode immediately. To remove
the feature, revert the d062 files and ignore/drop the two schema tables only
after preserving audit events needed for security review.

