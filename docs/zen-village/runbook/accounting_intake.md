# Restricted Accounting Intake

Use this lane for Zen Village receipts, numbers, expense notes, and accounting source material.

## Security Boundary

Accounting intake is **not** written to general AppFlowy by default.

Private storage:

```text
/opt/zen-village/accounting-intake/
```

Permissions:

```text
drwx------ root root
```

Who can use/view through Telegram:

- Bot admins (`ZV_TG_ADMIN_IDS`)
- Accounting-authorized users (`ZV_TG_ACCOUNTING_IDS`)

Current accounting IDs:

- Sunheart

Do not add someone to the general Brain allowlist unless they should access normal operational commands. For accounting-only users, use:

```text
/authorize_accounting <telegram_user_id>
```

## Halley Setup

1. Halley opens `@zenvillagebot`.
2. She sends `/start` or `/whoami`.
3. Bot shows her numeric Telegram `user_id`.
4. Sunheart sends:

```text
/authorize_accounting <her_user_id>
```

5. Halley sends:

```text
/accounting_help
```

## How To Submit

Text/numbers:

```text
/acct paid 18,000 colones for cleaning supplies, receipt photo next
```

Receipt photo:

```text
send photo with caption: /acct
```

Documents:

```text
send .pdf/.jpg/.png/.csv/.txt/.docx with caption: /acct
```

Latest entries:

```text
/acct_last
```

## What Gets Stored

Each intake creates:

- timestamp
- Telegram user ID
- username
- caption/note
- original filename
- stored private file path if media/document
- extracted OCR/document text where available

Records are appended to:

```text
/opt/zen-village/accounting-intake/YYYY-MM/intake.jsonl
```

Uploaded files are stored beside that JSONL file.

## Promotion To Brain

Only promote sanitized summaries to AppFlowy when useful.

Examples:

- Monthly total
- Reimbursable amount
- Vendor spend summary
- Event cost summary

Raw receipts and sensitive notes stay in the private accounting vault unless Sunheart explicitly decides otherwise.
