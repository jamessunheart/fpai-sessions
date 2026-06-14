# Privacy Policy

**Template version:** v1.0 (2026-05-19)
**Parameterization:** Replace `{{PRODUCT_NAME}}`, `{{PRODUCT_URL}}`, `{{COMPANY}}`, `{{CONTACT_EMAIL}}`, `{{RETENTION_DAYS}}`, `{{EFFECTIVE_DATE}}`
**Defaults:** `{{COMPANY}}` = Full Potential · `{{CONTACT_EMAIL}}` = james@fullpotential.com · `{{RETENTION_DAYS}}` = 90
**Uses:** Apprentice Gateway · brain-server account · /becoming · /game · any Sunheart substrate product handling personal data
**Compliance baseline:** CCPA (California) · GDPR-adjacent (EU/UK best-effort) · standard US consumer privacy

---

## Plain-English summary (read this first)

1. We collect what you give us — your goals, journal entries, messages you share with Ember, billing info via Stripe. We do not buy data about you.
2. We store this on our own servers (the "brain server"). Not on a third-party SaaS.
3. We use it only to give you the product — context-aware AI responses, your dashboard, your records.
4. We do not sell your data. Ever.
5. You can export everything we have on you. You can delete it. Just ask.
6. If you cancel, your private data is purged {{RETENTION_DAYS}} days after lapse unless you request earlier deletion or export.
7. We use Stripe for payments. Stripe sees your billing details (we don't store card numbers).
8. We may use OpenAI or Anthropic APIs for embeddings/AI processing. Snippets of your data may flow through their APIs as part of normal product operation. They do not retain it under their commercial terms.
9. If a regulator demands data, we'll tell you (unless legally gagged) before complying.
10. Questions: {{CONTACT_EMAIL}}.

---

## 1. Who we are

This Privacy Policy covers {{PRODUCT_NAME}} (the "Service") operated by {{COMPANY}} ("we", "us", "our"). Our principal contact is {{CONTACT_EMAIL}}. This policy applies to any user ("you", "your") who creates an account, makes a purchase, or otherwise interacts with the Service.

## 2. What we collect

### 2.1 Data you provide directly
- **Account data:** name, email, optional profile fields, billing address (via Stripe).
- **Content data:** anything you write into the Service — goals, journal entries, character cards, Telegram messages forwarded to the brain server, calendar items, structured state files.
- **Communications:** messages you send to support, Telegram channels you join, any voice/audio you submit.

### 2.2 Data we collect automatically
- **Usage data:** which features you use, timestamps of interactions, error logs.
- **Device data:** IP address (for session security only — we do not geolocate beyond country level), browser type, OS.
- **Cookies:** session cookies only. We do not use third-party advertising cookies.

### 2.3 Data we receive from third parties
- **Stripe:** payment status, last-4 of card, customer ID. We never see full card numbers.
- **OAuth providers (if used):** the basic profile data you authorize.

## 3. How we use it

We use your data only to:

1. Operate the Service (run Ember-coach, surface your context, render your dashboard, sync across tools).
2. Process payments and fulfill subscriptions.
3. Communicate with you about the Service (account notices, product updates).
4. Improve the Service (aggregated, de-identified usage patterns only; we do not train external models on your personal content).
5. Comply with legal obligations (tax, accounting, regulatory).

We do **not**:
- Sell your data to anyone.
- Use your private content to train external models.
- Share your content with other users without your explicit action (e.g., you choosing to publish to /becoming).
- Run advertising or behavioral profiling.

## 4. Third-party processors

We share data only with these processors, under data-processing agreements:

| Processor | Purpose | What they see |
|---|---|---|
| Stripe | Payments | Billing info, last-4 card |
| OpenAI / Anthropic (if used) | AI inference (embeddings, completions) | Inference-time snippets only; their commercial terms prohibit training on submitted content |
| Telegram (if you opt in to TG channels) | Messaging delivery | Messages routed through their platform |
| Hosting provider (NameCheap / VPS provider) | Server hosting | Encrypted data at rest |

We will publish a current processor list at {{PRODUCT_URL}}/processors and update it when processors change.

## 5. Where data lives + security

- **Primary storage:** our own servers, encrypted at rest, accessed only by {{COMPANY}} operators with documented access controls.
- **Backups:** encrypted, retained 30 days, geographically separate.
- **Transport:** TLS 1.2+ for all client-server communication.
- **Secrets handling:** API tokens stored in environment files outside the codebase; rotated on incident.

We are a small operation. We do not claim SOC 2 or ISO 27001. We make reasonable, documented security efforts proportionate to the data we hold and the risk profile.

## 6. Retention

- **Active accounts:** we retain your content for as long as your subscription is active and for {{RETENTION_DAYS}} days after lapse.
- **After lapse + {{RETENTION_DAYS}} days:** vector memory, canonical files, and account data are purged unless you have requested export or earlier deletion.
- **Billing records:** retained 7 years for tax/accounting purposes (US federal requirement).
- **Communications:** support emails retained 2 years.

We will send you 14-day, 7-day, and 1-day warning emails before purge so you have a chance to export.

## 7. Your rights

Regardless of your jurisdiction, you may:

- **Export** — request a JSON dump of everything we have on you. Email {{CONTACT_EMAIL}} or use the in-product export endpoint. We respond within 30 days.
- **Delete** — request deletion of all your data (other than billing records we must legally retain). We honor within 30 days.
- **Correct** — request correction of any factual error in your account.
- **Object** — opt out of any specific use of your data described in this policy.
- **Complain** — file a complaint with your local data protection authority.

**California residents (CCPA):** you have additional rights including the right to know what categories of data we collect, sell (we do not sell), and disclose. You may also designate an authorized agent to make requests on your behalf. We do not discriminate against users who exercise these rights.

**EU/UK residents (GDPR best-effort):** we are not formally GDPR-registered but operate to GDPR principles. Our lawful bases for processing are: (a) contract (operating the Service you signed up for), (b) consent (specific features you opt into), and (c) legitimate interest (improving the Service, security).

## 8. Children

The Service is not intended for users under 18. We do not knowingly collect data from minors. If we learn we have data on a minor, we will delete it.

## 9. International transfers

Our servers are located in the United States. If you are outside the US, by using the Service you consent to your data being transferred to and processed in the US.

## 10. Changes

We may update this policy. Material changes will be announced via email to active users at least 30 days before taking effect. The current version always lives at {{PRODUCT_URL}}/privacy.

## 11. Contact

For privacy questions, data subject requests, or complaints:

- Email: {{CONTACT_EMAIL}}
- Postal address: available upon request

For urgent security issues: same email, prefix subject with `[SECURITY]`.

---

**Effective date:** {{EFFECTIVE_DATE}}
**Version:** v1.0
**Template lineage:** `core/INTENT/legal_templates/PRIVACY_POLICY_v1.md`
