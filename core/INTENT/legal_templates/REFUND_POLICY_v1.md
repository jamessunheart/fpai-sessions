# Refund Policy

**Template version:** v1.0 (2026-05-19)
**Parameterization:** Replace `{{PRODUCT_NAME}}`, `{{PRODUCT_URL}}`, `{{COMPANY}}`, `{{CONTACT_EMAIL}}`, `{{REFUND_DAYS}}`, `{{FOUNDING_REFUND_DAYS}}`, `{{EFFECTIVE_DATE}}`
**Defaults:** `{{REFUND_DAYS}}` = 30 · `{{FOUNDING_REFUND_DAYS}}` = 90
**Companion documents:** Terms of Service · Income Disclosure Statement

---

## Plain-English summary

- Full refund within {{REFUND_DAYS}} days. No questions.
- Founding Tier: pro-rated refund within {{FOUNDING_REFUND_DAYS}} days.
- Cancel anytime; you keep access through your paid period.
- Refunds go back to original payment method, 5-10 business days.
- Email {{CONTACT_EMAIL}} to request.

---

## 1. Standard refund — {{REFUND_DAYS}} days

Within {{REFUND_DAYS}} days of your **first** subscription purchase, you may request a full refund of all fees paid (subscription fee plus any optional add-ons like the Founding Tier).

- No questions asked.
- No requirement to provide a reason.
- Initiated by email to {{CONTACT_EMAIL}} or via the Service's refund flow.

We process within 3 business days. Funds return to your original payment method (typically 5-10 business days to appear depending on bank).

## 2. Founding Tier — pro-rated refund within {{FOUNDING_REFUND_DAYS}} days

The optional Founding Tier one-time upgrade is refundable on a pro-rated basis within {{FOUNDING_REFUND_DAYS}} days of purchase:

```
refund_amount = founding_fee × ({{FOUNDING_REFUND_DAYS}} − days_elapsed) / {{FOUNDING_REFUND_DAYS}}
```

Example: $497 Founding Tier purchased, refund requested on day 30:
```
refund = $497 × (90 − 30) / 90 = $497 × 0.667 = $331.33
```

After {{FOUNDING_REFUND_DAYS}} days, the Founding Tier is non-refundable.

## 3. Cancellation (separate from refund)

You may cancel your monthly subscription anytime — this is **separate** from refund:

- Cancellation stops future billing.
- You retain access through the end of your current paid period.
- Past charges are not automatically refunded (use the refund flow above if eligible).

To cancel:
- In-Service: account settings
- Email: {{CONTACT_EMAIL}}

## 4. What's not refundable

- Past monthly subscription fees after {{REFUND_DAYS}} days from initial purchase (only the most recent cycle, on a case-by-case basis if there's a service-quality issue).
- Founding Tier purchases after {{FOUNDING_REFUND_DAYS}} days.
- Fees paid by accounts that have violated the Terms of Service.

## 5. Exceptional refunds

We may issue refunds outside this policy at our sole discretion in cases of:
- Documented service outages affecting your specific use
- Mistaken double-charges (always refunded)
- Bona fide hardship (case-by-case)

Email {{CONTACT_EMAIL}} with the details if you believe your case qualifies.

## 6. How to request a refund

1. Email {{CONTACT_EMAIL}} with subject `Refund request` and include:
   - Email on the account
   - Order date or Stripe receipt ID
   - Reason (optional but appreciated for product improvement)
2. We respond within 3 business days.
3. If approved, refund is issued within 3 business days of approval.
4. Bank processing: 5-10 business days for funds to appear.

## 7. Effect on account

Issuing a refund within the refund window:
- Cancels the active subscription
- Closes the Founding Tier benefits (if Founding Tier was refunded)
- Triggers brain-server data retention per Privacy Policy (data purged after retention period)
- Champion Game seat is preserved (Game state is permanent regardless of subscription status)

## 8. Chargebacks

We prefer you contact us first. Chargebacks initiated without first contacting {{CONTACT_EMAIL}} may result in account suspension while disputes are resolved. We will work in good faith to resolve any billing concern through normal refund processes.

## 9. Contact

{{COMPANY}}
{{CONTACT_EMAIL}}
{{PRODUCT_URL}}/refund

---

**Effective date:** {{EFFECTIVE_DATE}}
**Version:** v1.0
**Template lineage:** `core/INTENT/legal_templates/REFUND_POLICY_v1.md`
