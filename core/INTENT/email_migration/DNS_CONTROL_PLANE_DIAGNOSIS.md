# DNS Control-Plane Diagnosis + Domain Safety Matrix

_2026-07-10 · Ember · all read-only (whois · dig · WHM dumpzone/listaccts, root@209.74.93.72). No mutation. No delegation change._

## 🔴 Headline finding — cPanel is NOT the authoritative DNS control plane for most domains

The earlier assumption ("edit the cPanel DNS zone to migrate") is **false for most domains.** cPanel on 209.74.93.72 holds zone *files*, but public DNS is served elsewhere per-domain:

| Domain | Registrar-delegated NS | Actual control plane | Public A | Resolves? |
|--------|------------------------|----------------------|----------|-----------|
| fullpotential.com | dns1/2.registrar-servers.com | **Namecheap BasicDNS** | 198.54.123.234 | ✅ |
| jamesrick.com | dns1/2.registrar-servers.com | **Namecheap BasicDNS** | 209.74.93.72 | ✅ |
| outbounders.com | ns1/2.outbounders.com | **cPanel (209)** | 209.74.93.72 | ✅ |
| expresspayfranchise.com | ns05/06.domaincontrol.com | **GoDaddy** | 162.0.234.58 | ✅ |
| **jamesrickstinson.com** | ns1/2.fullpotential.com | **⛔ none serving** | NONE | ❌ |

**Implication:** to migrate any domain you must first identify *its* control plane (Namecheap / GoDaddy / cPanel) — editing the cPanel zone changes nothing for a domain whose registrar delegates to Namecheap or GoDaddy. **The `domain1_jamesrickstinson.md` cPanel runbook is marked NON-EXECUTABLE** until per-domain control plane is confirmed.

## C. jamesrickstinson.com delegation fault (precise)

- **Registrar (Namecheap) delegates to:** ns1/ns2.fullpotential.com → both → 198.54.123.234, where **named is inactive (port 53 refused).**
- **cPanel zone** (209.74.93.72) is fully populated (website, mail, DKIM, SPF, subdomains) and self-declares NS ns1/ns2.outbounders.com — but the registrar does not point there.
- **Where the cPanel zone affects public DNS:** nowhere. Nothing on the public internet is delegated to the NS that serve it.
- **Split/stale zones:** yes — an orphaned live cPanel zone + a dead delegation target.
- **User-visible impact today:** the domain resolves to **nothing** publicly — no website, no mail in/out. Effectively offline.
- **Is anything broken today?** Only if someone expects jamesrickstinson.com to work publicly. No active service depends on it (0 recent exim activity). Low urgency.
- **Safest correction (NOT executing):** at Namecheap, repoint delegation from ns1/2.fullpotential.com → the intended plane. If cPanel should serve it: ns1/2.outbounders.com. If Namecheap DNS should serve it (like fullpotential.com): switch to BasicDNS + set records there. Decide the target plane first.
- **Rollback:** revert Namecheap NS to the prior value (single field; instant).
- **Consequence of leaving unchanged:** none operationally — domain stays dark. Only blocks using this domain until fixed.

## B. Domain safety matrix (migration-proof candidate search)

Read-only per candidate: cPanel mailboxes, forwarders, recent exim mail, website index, control plane.

| Domain | Mailboxes | Fwd | Recent mail | Web index | Control plane | Verdict |
|--------|-----------|-----|-------------|-----------|---------------|---------|
| jamesrick.com | 2 | 21 | — | real (YES) | Namecheap | ❌ live (21 forwarders) |
| globalsky.com | 5 | 0 | — | real (YES) | ? | ❌ 5 mailboxes |
| maschristo.com | 1 | 0 | 0 lines | 405B parking | whois blank | 🟡 dormant-ish, plane unclear |
| **expresspayfranchise.com** | 1 | 0 | 0 lines | 405B parking | **GoDaddy (clear)** | 🟢 **lowest risk** |
| one-bpo.com | 1 | 0 | 0 lines | empty (0B) | ? | 🟡 brand-adjacent (ownership-sensitive) |
| obpo.co | 1 | 0 | 0 lines | 405B parking | ? | 🟡 dormant-ish, plane unclear |

Notes: `index_bytes=405` = default cPanel parking page (not a real site). The single mailbox on each is the default cPanel account. **No managed domain is 100% provably dormant**, but four have zero recent mail + only a parking page.

**Recommendation:** **expresspayfranchise.com** — zero recent mail, parking page only, and the **only candidate with a clear, resolvable, single control plane (GoDaddy)**. That makes its migration and rollback authority unambiguous. Risk remaining: confirm (a) we hold the GoDaddy login, (b) the business is truly dead.

**Alternative if GoDaddy access is unavailable:** register a brand-new throwaway domain with zero history — cleanest possible migration proof, no legacy to preserve.

## What James uniquely decides

Only the **business meaning + registrar access**: "Is expresspayfranchise.com business-safe to repoint, and do we hold its GoDaddy login?" — OR "use a fresh throwaway domain instead." Everything else (baseline capture, control-plane confirmation, additive records, validation, soak) I execute.
