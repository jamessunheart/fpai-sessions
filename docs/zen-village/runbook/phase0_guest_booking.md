# Phase 0 Guest Booking + Credits Setup

Phase 0 goal: prove the guest booking/payment loop with real money before building custom checkout or exposing credits.

## Locked Legal Framing

For Phase 0 guest booking and event intake, guest PII (name, email, phone, payment references, booking status, attendance status, and booking notes) will be stewarded by **Zen Village / CR under Sunheart stewardship**, pending final legal entity setup.

Data use is limited to booking, guest communication, payment reconciliation, event operations, safety, and follow-up. Once the appropriate legal entity is finalized, this responsibility should transfer to that entity.

Guest-facing short copy:

```text
Your information is used only for booking, guest communication, payment reconciliation, event operations, safety, and follow-up.
```

## Phase 0 Build

Use:

- Stripe Payment Link
- Hand-made QR
- Manual roster
- AppFlowy Brain records

Do not build:

- custom checkout
- guest account system
- public UC/credits interface
- guest Telegram bot

## Minimum Guest Journey

QR/link -> payment/deposit page -> guest pays -> team records booking -> guest receives confirmation.

## Manual Roster Fields

Until `08 · Bookings` exists, use temporary `[Booking]` rows in Master List or Weekly Log.

Capture:

- guest_name
- guest_email
- phone
- event
- amount_paid_usd
- payment_status
- source (`qr`, `url`, `referral`, `walk-in`)
- stripe_payment_id
- notes

## Next Schema

Add:

- `08 · Bookings`
- `09 · Credits Ledger`
- People fields: `credits_balance`, `first_touch_source`, `last_event_attended`

Credits rule remains:

```text
1 UC = $1 USD
```

Guest-facing language stays concrete:

- deposit
- ticket
- retreat credit
- event credit
- dollar balance

Use UC internally only where it reduces friction.
