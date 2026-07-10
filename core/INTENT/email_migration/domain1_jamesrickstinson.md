# Domain 1 Migration Runbook — jamesrickstinson.com

_2026-07-10 · lowest-risk first domain · proves the runbook before higher-risk domains_
_Parent architecture: `../EMAIL_ARCHITECTURE_2026-07.md`_

## Facts (verified live 2026-07-10T17:28Z)

- **Registrar:** Namecheap · expires 2027-03-18
- **Nameservers:** `ns1.fullpotential.com` / `ns2.fullpotential.com` → **DNS edited in cPanel DNS Zone Editor** on the FP nameserver box (209.74.93.72), NOT the Namecheap dashboard.
- **Current DNS: EMPTY** — no MX, TXT, SPF, DKIM, DMARC, A. Domain is dormant.
- **Implication:** zero live mail to break. Rollback = delete added records → returns to empty.

## Receiving method (decision)

**Google Workspace domain alias** on the existing `fullpotential.ai` Workspace.
- Every existing Workspace user auto-receives `user@jamesrickstinson.com`. So `james@fullpotential.ai` inbox receives `james@jamesrickstinson.com` — no new mailbox, no new seat, no cost.
- Gives real DKIM + aligned SPF → proper deliverability + DMARC pass.
- Fully reversible (remove alias domain + delete DNS records).
- _Lighter alt if you'd rather not touch Workspace admin: ImprovMX free forwarding (MX → mx1/mx2.improvmx.com, SPF include:spf.improvmx.com). Inbound-only; weaker outbound DKIM. Not recommended — domain-alias is the right long-term shape._

---

## STEP 0 — FULL ZONE INVENTORY (do this FIRST · risk-reducer)

**Why:** a domain can host a website, subdomains, or third-party verification records that a blind email edit would wipe. Confirm what exists before adding anything.

**External check (Ember ran, 2026-07-10T17:31Z):** via public resolver 8.8.8.8, jamesrickstinson.com publishes **nothing** — no SOA/NS/A/AAAA/MX/TXT/CAA, no `www`. Domain resolves to nothing publicly (no live website, no mail).

**⚠️ Caveat — external check is not authoritative here.** The authoritative NS `ns1/ns2.fullpotential.com` (= 198.54.123.234) does not answer direct queries from Ember's sandbox (port 53 firewalled). If the cPanel zone holds records the NS isn't publishing publicly, external `dig` can't see them. **The cPanel zone file is the source of truth.**

**Action (James):** open cPanel DNS Zone Editor for jamesrickstinson.com on 198.54.123.234 → **export or screenshot the complete zone** (all A, AAAA, CNAME, MX, TXT, SRV, CAA, NS records). This is:
1. The definitive inventory — confirms whether anything beyond email exists.
2. The exact rollback artifact — restore from it if needed.

**Rule:** the 5 email records below are **additive only**. Preserve every existing record. If the zone shows a website A record, subdomains, or verification TXT → leave them all untouched; only ensure there's no conflicting existing MX or second SPF TXT (there should be none, per external check).

### Step 0b — FUNCTIONAL baseline (record current email flow)

Config rollback = restore the zone. **Functional rollback = know what "working" looked like.** Capture both.

Before any change, record current behavior with real test messages:
- Send external → `james@jamesrickstinson.com` → **does anything arrive today?** (Expected here: no — domain is dormant. Note the actual result.)
- Note current Gmail "Send As" list (which identities already work) — screenshot.
- For higher-risk domains (later), this baseline is critical: send/receive a test on the LIVE address first, so you can prove the migration preserved — not just changed — behavior.

Two rollback artifacts now exist: **zone export** (config) + **this functional baseline** (behavior).

---

## PRE-VALIDATION (before any change)

Baseline external snapshot captured (publicly empty). Re-confirm nothing changed:

```bash
d=jamesrickstinson.com
for t in MX TXT NS; do echo "--- $t ---"; dig @8.8.8.8 +short $t $d; done
dig @8.8.8.8 +short TXT _dmarc.$d
dig @8.8.8.8 +short TXT google._domainkey.$d
```
**Expect:** MX/TXT/DMARC/DKIM empty · NS = ns1/ns2.fullpotential.com. If MX is non-empty, STOP — domain isn't dormant, re-assess.

---

## STEP 1 — Admin console (Google Workspace)

1. admin.google.com → **Account → Domains → Manage domains → Add a domain**.
2. Enter `jamesrickstinson.com` → choose **"User alias domain"** (NOT secondary domain).
3. Google shows a **verification TXT** (`google-site-verification=…`) — copy it for Step 2.
4. **Apps → Google Workspace → Gmail → Authenticate email** → select `jamesrickstinson.com` → **Generate new record** (2048-bit) → copy the `google._domainkey` **DKIM value** for Step 2. (Click "Start authentication" only AFTER the DNS record is live.)

---

## STEP 2 — DNS records (cPanel DNS Zone Editor, zone = jamesrickstinson.com)

Add exactly these. `@` = the root/domain itself.

| # | Type | Host/Name | Value | TTL |
|---|------|-----------|-------|-----|
| 1 | TXT | `@` | `google-site-verification=…` _(from Step 1.3)_ | 3600 |
| 2 | MX | `@` | `1 smtp.google.com.` _(modern single MX; note trailing dot + priority 1)_ | 3600 |
| 3 | TXT | `@` | `v=spf1 include:_spf.google.com ~all` | 3600 |
| 4 | TXT | `google._domainkey` | `v=DKIM1; k=rsa; p=…` _(the full value from Step 1.4)_ | 3600 |
| 5 | TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@fullpotential.com; fo=1` | 3600 |

Notes:
- **SPF:** only ONE SPF TXT per domain ever. Domain is empty so #3 is the only one — good.
- **DKIM `p=`** value is long; paste the whole thing, no line breaks.
- **DMARC starts at `p=none`** (monitor only — cannot bounce mail). Tighten later.
- If cPanel's DKIM field length errors on #4, split the value into quoted strings per cPanel's prompt — the record value is identical once joined.

Save zone. Then in Admin console (Step 1.4) click **"Start authentication"** to activate DKIM signing.

---

## POST-VALIDATION (gate — ALL must pass before Domain 2 starts)

Allow up to ~1h propagation (TTL 3600), then:

```bash
d=jamesrickstinson.com
dig @8.8.8.8 +short MX  $d                       # → 1 smtp.google.com.
dig @8.8.8.8 +short TXT $d                        # → includes v=spf1 include:_spf.google.com ~all
dig @8.8.8.8 +short TXT google._domainkey.$d      # → v=DKIM1; k=rsa; p=...
dig @8.8.8.8 +short TXT _dmarc.$d                 # → v=DMARC1; p=none; ...
```

Then functional:
1. **Inbound:** from an external address, email `james@jamesrickstinson.com` → confirm it lands in the `james@fullpotential.ai` / canonical Gmail inbox.
2. **Outbound send-as:** Gmail → Settings → Accounts → "Send mail as" → add `james@jamesrickstinson.com` (verify). Send a test to **check-auth@verifier.port25.com** or **mail-tester.com** → require **SPF pass · DKIM pass · DMARC pass · score ≥ 9/10**.
3. **Reply-from-alias:** reply to the Step-1 inbound test → confirm From auto-sets to `james@jamesrickstinson.com`.
4. **DMARC reports:** confirm `rua` reports begin arriving at dmarc@fullpotential.com over the next days; all `pass`.

Only after 1–4 pass **AND the 48-hour observation gate below** → proceed to Domain 2 (inbounders.com). After 1–2 weeks of clean `rua`, tighten DMARC `p=none` → `quarantine`.

### 48-HOUR OBSERVATION GATE (before Domain 2)

Validation passing immediately is necessary but not sufficient. **Wait 48h before touching the next domain**, watching for:
- delayed / intermittent delivery (queued, greylisted, retried)
- first DMARC `rua` reports arriving (24h+ lag typical) — confirm all `pass`
- forwarding loops, bounces, or NDRs
- any deliverability drift (re-run mail-tester after 24h and 48h)

Domain 1 is dormant, so this window mostly validates the *mechanism* cleanly before it matters on live-traffic domains. Clean 48h → green-light Domain 2.

---

## ROLLBACK (rehearsed, trivial here)

Baseline was empty, so rollback is clean and lossless:
1. cPanel DNS Zone Editor → **delete records #1–#5**.
2. Admin console → **Account → Domains → remove `jamesrickstinson.com`** alias.
3. Confirm: `dig @8.8.8.8 +short MX jamesrickstinson.com` → empty (back to dormant).

No data loss: canonical Gmail inbox is untouched; only inbound routing for a dormant domain is affected during the window.

---

## Event-stream note

Once inbound validates, this is the **first channel** feeding the immutable Event stream (§5a). Inbound mail → Gmail adapter → `email.received` Event (`source: "gmail"`, `sender_identity: "jamesrickstinson.com"`). The domain proves the loop end-to-end at the lowest possible risk.
