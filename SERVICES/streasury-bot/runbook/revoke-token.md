# Revoking the bot token

The original token (`8619444452:AAH…`) was pasted into a chat session and a
git working tree, so it must be treated as compromised. Anyone with that
string can read every message you send the bot and impersonate it back to you.

## Rotate via @BotFather

1. Open Telegram, message [@BotFather](https://t.me/BotFather).
2. Send `/revoke`.
3. Choose `STreasury_Bot` from the list.
4. Confirm. BotFather replies with a brand-new token — the old one is dead
   immediately.
5. Copy the new token into `/etc/streasury-bot/streasury.env` (server) and
   any `.env` you use locally. Never paste it into chat or commit it.
6. Restart the bot:

   ```bash
   systemctl restart streasury-bot
   journalctl -u streasury-bot -f
   ```

7. Send `/whoami` from your account to confirm the bot is back online.

## Audit the leak

The leaked token will show up in:

- This Cursor chat session (immutable history; nothing to do).
- Any agent transcripts the workspace persists under
  `~/.cursor/projects/.../agent-transcripts/`. If those are sync'd anywhere
  off-device, scrub the token from those copies.
- The `feat/streasury-bot` branch's commit messages and code: it was never
  written there, but check with `git grep '8619444452'` before merging.

If `git grep` finds anything, fix the file and commit BEFORE pushing.
