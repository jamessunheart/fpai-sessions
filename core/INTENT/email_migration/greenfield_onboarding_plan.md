# Greenfield Onboarding Proof — plan + the "do we even need to buy?" question

_2026-07-10 · proves ownership → DNS → mailbox delivery → over-the-wire observation → canonical Event. NOT a migration proof._

## ★ First: can an EXISTING/FREE asset give equivalent over-the-wire isolation? — YES.

The **priority evidence** James named is the over-the-wire trace (external sender → real isolated inbox → authenticated observer → one Event). That does **not** require buying a domain. Options that need **$0 and touch no production**:

| Asset | Real external delivery? | Auth observer? | Cost | Prod touch | IMAP? |
|-------|------------------------|----------------|------|-----------|-------|
| **Mailsac** (free tier) | ✅ anything@mailsac.com receives real mail | ✅ API key | $0 | none | REST/WS (not IMAP) |
| **mail.tm** (free) | ✅ disposable inbox | ✅ JWT | $0 | none | REST (not IMAP) |
| New cPanel mailbox on an unused subdomain we own | ✅ | ✅ IMAP | $0 | ⚠️ touches prod cPanel box | ✅ real IMAP |
| Fresh dedicated domain + mailbox | ✅ | ✅ IMAP | ~$10/yr | none | ✅ real IMAP |

**Recommendation for the over-the-wire trace:** use **Mailsac free tier** — real external delivery to an isolated address, authenticated API observer, zero cost, zero production, fully disposable. It proves "remote provider → Event" honestly. The only gap vs. a domain: it's REST not IMAP, and it's a 3rd-party service (so: your OK to use it).

**A domain purchase is only needed for the *full greenfield onboarding* proof** (the ownership→DNS→MX→mailbox chain), which is a *separate, optional* deliverable — not required for the next unit of evidence.

## Greenfield onboarding proof (only if you want the full ownership→DNS chain proven)

| Item | Recommendation |
|------|----------------|
| **Domain** | a neutral, meaningless label (e.g. `convos-proof-<rand>.com` or a cheap `.me`/`.dev`) — zero brand value, disposable |
| **Registrar** | **Namecheap** — we already hold the account, it's a single clean control plane (BasicDNS), and it's the plane fullpotential.com/jamesrick.com already use. No new vendor. |
| **First-year cost** | `.com` ≈ **$10–13**, `.me` ≈ $4–9 first year, `.dev` ≈ $12. All within a coffee-budget. |
| **Renewal** | `.com` ≈ $13–15/yr (or don't renew — it's a proof, let it lapse). |
| **Required access** | Namecheap login (you hold it) + ~$10 payment. Nothing else. |
| **Rollback authority** | Total — we own it outright, single control plane, can delete/lapse anytime. |

**Test plan (greenfield onboarding):**
1. Register domain (Namecheap, BasicDNS).
2. MX → a mailbox host we control (cPanel new account, or a mail provider).
3. Create one isolated mailbox.
4. Send a real external email to it (from a normal external account).
5. Authenticated observer polls it over the wire.
6. → exactly one canonical Event persisted, trace visible, dedup on re-poll, disable clean.
7. Tear down (delete mailbox / let domain lapse).

## Smallest unavoidable approval

- **For the priority (over-the-wire ingestion):** `$0` — just your OK to use a **free third-party disposable-mail service (Mailsac)**. No purchase, no prod.
- **For the full greenfield onboarding proof (optional):** ~**$10** for a throwaway Namecheap domain.

No external spend or purchase happens without your explicit approval.
