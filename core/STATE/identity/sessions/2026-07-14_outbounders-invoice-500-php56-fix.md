# 2026-07-14 · Outbounders invoice 500 — FIXED (PHP 5.6 vs `??`)

## The arc
James forwarded a staff email + screenshots: Outbounders backend (ADMINCI) Invoice
tab erroring, blocking DIY Payroll. Started framed as "Undefined index" notices;
mid-turn Dani reported the harder truth — `app.outbounders.com/adminci/invoice`
was **HTTP 500**, dead since Jul 10. Pure ops fire-fight. James gave explicit go
to write the prod fix. **Shipped and verified live.**

## Root cause (confirmed)
- Docroot `/home/obapp/public_html/app` on `209.74.93.72` (server1, cPanel).
- `adminci/error_log`: **PHP Parse error: unexpected '?' in
  `application/modules/invoice/views/list.php:164`**, recurring Jul 10→14.
- Lines 164-165 used `?? ''` (null-coalescing, PHP 7.0+). File edited **Jul 9 17:32**
  (someone patching the original undefined-index notices with modern syntax).
- Domain runs **`alt-php56`** (PHP 5.6) per `/var/cpanel/userdata/obapp/app.outbounders.com`.
  CLI php is 8.1 (red herring — web handler is the 5.6 lsphp). `??` = fatal on 5.6.

## What shipped (the fix, LIVE)
Replaced 2 lines with PHP-5.6-clean `isset() ? :` (also kills the original notices):
```php
$id        = isset($row['iid'])       ? $row['iid']       : '';
$client_id = isset($row['client_id']) ? $row['client_id'] : '';
```
- Backup: `list.php.bak-20260714-php56fix` (one-cmd revert).
- `alt-php56 -l` → No syntax errors. `curl /adminci/invoice` → **HTTP 200**. Verified.
- **Method note:** sed/perl quote-escaping through ssh mangled it twice
  (`$rowisset()`, stripped quotes). Base64-piped Python one-shot was the clean win —
  use that pattern for prod file edits with embedded quotes.

## What's open
- Optional: draft staff confirmation reply to Carl/Dani (offered, James not yet answered).
- Systemic: this legacy CI app has **no deploy guardrail** — a hand-edit with wrong-version
  syntax took down a revenue page for 4 days silently. Worth a pre-commit `php -l` gate.
- Who edited list.php Jul 9 with PHP-7 syntax on a 5.6 host? Unresolved.

## Alignment
- **INTENT:** Restore Outbounders payroll/invoice page fast + reversibly. ✅ done.
- **TOP 3:** (1) ✅ Fix live, 200 verified. (2) Optional staff reply. (3) Flag no-guardrail risk.
- **BLOCKERS:** none — fix verified.
- **NEXT MOVE:** If James wants, draft Carl/Dani confirmation; else session closes clean.
