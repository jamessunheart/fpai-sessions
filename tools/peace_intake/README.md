# tools/peace_intake/

**The WPAP signing intake pipeline.** Takes inbound emails to a signing
address, validates them, creates World Peace Agreement files via the
Agreement Builder, regenerates the registry, and (optionally) commits
+ deploys.

This is what makes WPAP **live, not sandboxed.** Anyone with email can
sign; their signature appears on the public roll without manual
mediation.

---

## What's in here

- `sign_intake.py` — core intake script (parses an email, creates Agreement file)
- `README.md` — this file (deployment guide)

The script imports the Agreement Builder library (`tools/registry/new_agreement.py`)
and reuses `tools/registry/build_index.py` + `build_public_roll.py` for
registry regeneration, and `sites/zenvillage-peace/deploy.sh` for site deploy.

---

## Local smoke test

Send yourself a test email or save one to disk, then:

```bash
# Create a sample email file
cat > /tmp/test_sign.eml <<'EOF'
From: "Test Signer" <test@example.com>
Subject: I sign the World Peace Agreement
Message-ID: <test-001@example.com>

My name: Test Signer

I agree to practice peace in thought, word, and action.
I agree to reduce unnecessary suffering.
I agree to seek understanding before hatred.
I agree to repair where I have caused harm.
I agree to protect life, truth, beauty, and future generations.
I agree to become trustworthy with intelligence, influence, and resources.
I agree that peace must become visible through action.

Signed not in perfection, but in sincere participation.
EOF

# Dry run — preview without writing
python3 tools/peace_intake/sign_intake.py --email-file /tmp/test_sign.eml --dry-run

# Real run — write Agreement file and regenerate registry
python3 tools/peace_intake/sign_intake.py --email-file /tmp/test_sign.eml

# Full pipeline — write, regen, commit, deploy
python3 tools/peace_intake/sign_intake.py \
  --email-file /tmp/test_sign.eml \
  --commit \
  --deploy
```

The script prints a confirmation reply to stdout (ready for SMTP send back to
the signer) and writes the Agreement file to `core/INTENT/AGREEMENTS/`.

---

## Email format expected

**Subject** must match `/i sign the world peace agreement/i` (case-insensitive).

**Body** should contain the signer's name in one of:

```
My name: Maria López
```
```
I am Maria López
```
```
Name: Maria López
```
```
Signed by: Maria López
```

If no body name found, falls back to:
1. `From:` header display name
2. Email username (before `@`), title-cased

**Privacy flag (optional):** include `private` or `do not publish` or `not public`
in the body to mark the Agreement as `public: false`. Default is `public: true`.

---

## Production deployment (v0 — IMAP polling)

The intake script processes ONE email. The polling loop is added at deployment.
Three-step deployment path on the production server (`198.54.123.234`):

### Step 1 — Configure email account

The `hello@zenvillagecr.com` mailbox (or whichever signing address you choose)
needs IMAP access. Get:
- IMAP server hostname (e.g. `imap.gmail.com`, `imap.fastmail.com`)
- IMAP port (usually 993 for SSL)
- Credentials (username + app-specific password if 2FA)

### Step 2 — Add an IMAP poller wrapper

Create `tools/peace_intake/imap_poll.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/opt/fpai/peace_intake_repo"  # production checkout
cd "$REPO_ROOT"
git pull --ff-only origin main

# Fetch unread emails matching subject pattern, process each
# (using imapsync, fetchmail, or a small Python imap wrapper)
python3 tools/peace_intake/imap_fetcher.py \
  --imap-host "${IMAP_HOST}" \
  --imap-user "${IMAP_USER}" \
  --imap-pass "${IMAP_PASS}" \
  --search 'UNSEEN SUBJECT "I sign the World Peace Agreement"' \
  --output-dir /tmp/peace_intake \
  --mark-seen

# Process each fetched email
for eml in /tmp/peace_intake/*.eml; do
  python3 tools/peace_intake/sign_intake.py \
    --email-file "$eml" \
    --commit \
    --deploy

  # Send confirmation back via SMTP (separate wrapper, e.g. mailx)
  python3 tools/peace_intake/sign_intake.py \
    --email-file "$eml" \
    --dry-run \
    | mailx -s "$(grep -m1 '^Subject:' | cut -d: -f2-)" "$signer_email"

  rm "$eml"
done
```

The `imap_fetcher.py` and SMTP-send wrappers are intentionally **not yet built** —
they need credentials at deploy time. Build them as v0a, v0b respectively.

### Step 3 — Schedule the poller

Use a systemd timer (recommended):

```ini
# /etc/systemd/system/peace-intake.service
[Unit]
Description=WPAP signing intake (poll for new World Peace Agreement signers)

[Service]
Type=oneshot
EnvironmentFile=/opt/fpai/peace_intake/env
ExecStart=/opt/fpai/peace_intake_repo/tools/peace_intake/imap_poll.sh
StandardOutput=append:/var/log/peace-intake.log
StandardError=append:/var/log/peace-intake.log
User=peace
Group=peace
```

```ini
# /etc/systemd/system/peace-intake.timer
[Unit]
Description=Poll for World Peace Agreement signers every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable --now peace-intake.timer
sudo systemctl status peace-intake.timer
journalctl -u peace-intake.service -f
```

---

## Security & spam handling

The script has built-in guards:

- **Subject regex match** — only emails matching the signing pattern pass
- **Sender pattern blocklist** — rejects `noreply@`, `mailer-daemon`, `postmaster`, etc.
- **Name length sanity check** — body-extracted name must be 2–100 chars
- **Filename collision guard** — appends `_02`, `_03` if same date+name signs twice

Recommended additions for production:

- **Rate limiting** — max N signings per IP per hour (track in a simple SQLite or flat file)
- **Subject lock** — IMAP search filters by subject before download to limit attack surface
- **DKIM/SPF check** — only accept signed emails from authenticated senders
- **Manual review queue** — high-cardinality flag (e.g. unusual characters, suspicious patterns) → queue for human review instead of auto-process

---

## Roadmap

| Stage | What | Status |
|---|---|---|
| v0 | Core intake script that processes one email | ✅ shipped (this commit) |
| v0a | IMAP fetcher (poll + download to .eml files) | pending — needs credentials |
| v0b | SMTP confirmation sender | pending — needs credentials |
| v0c | systemd timer + service config | pending — needs server access |
| v1 | Web form alternative (POST → Agreement file) | future |
| v2 | DKIM/SPF authentication validation | future |
| v3 | Webhook intake (e.g. from contact-form services) | future |

---

## Why this matters

Per the manifesto: *"Peace must become visible through action."*
Per WPAP: *"AI helps humans form, witness, and remember agreements."*

When this pipeline is live, the read/write asymmetry of the public site
collapses. Anyone, anywhere, with an email account, can become a signer
of the World Peace Agreement and appear in the public ledger within
minutes — without the founder, the AI, or any human gatekeeper having
to mediate the act.

That is what *live, not sandboxed* means.
