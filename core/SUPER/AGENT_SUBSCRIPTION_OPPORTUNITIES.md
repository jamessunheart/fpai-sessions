# SUPER — Agent Subscription Opportunities (both directions)

Prepared 2026-09-03 by The Forge. Directive (James, Reserved:direction, 2026-09-03):
"look at all subscription-to-agent-services opportunities right now as we move toward
the super agent-to-agent system."

**All entries verified live via WebSearch/WebFetch on 2026-09-03. No from-memory claims.**
Gate reminder (Track B, `NBM.md`): **nothing SELLS before BUILD-001 is CLOSED (B1).**
Connection / registration / free-listing infra is NOT gated. Anything that creates an
account, spends money, or uses James's identity/voice is **JAMES-GATED** and flagged inline.

Scope note vs `AGENT_MARKETS_MAP.md`: that map covers *where we list the pack* (12 markets).
This doc covers **recurring subscription** flows specifically — inbound (who pays us monthly)
and outbound (what we pay monthly for leverage) — plus the rights schema for subscribed agents.

---

## A. INBOUND — recurring revenue surfaces (who would subscribe to OUR agent services)

Ranked by (returns potential × readiness × serve-not-rule fit).

| # | Surface | URL | Live evidence (2026-09-03) | Recurring mechanics | Fit w/ our 2 packs + $150/mo card | Substrate-now / B1-gated / James-gated |
|---|---------|-----|----------------------------|---------------------|-----------------------------------|----------------------------------------|
| A1 | **Claude Cowork plugin marketplace + enterprise private marketplaces** | claude.com/blog/cowork-plugins · support.claude.com/articles/13837433 | Plugins live for all paid plans (research preview). Anthropic plugins free; **third-party packs sold separately**; Team/Enterprise owners run **private curated marketplaces**; dept-specific packs (finance/legal/real-estate/trades) already shipping | Today: pack installs on the buyer's existing paid Claude plan (no Anthropic per-plugin fee). Our recurring layer rides *outside* the plugin: the pack is the free hook, the **$150/mo outcome card** is the subscription we bill directly. Enterprise private marketplaces = the B2B distribution surface | **Best fit.** Both packs (find-a-provider, hold-my-Build) install here; the outcome card is the natural upsell to the paying-business audience. Enterprise = one buyer, many seats | List free = substrate-drafts / **JAMES-GATED** submit (account). SELLING the outcome card = **B1-GATED** |
| A2 | **Paid MCP subscription (reshape a pack as a metered MCP server)** | usagebox.com/articles/how-to-charge-for-mcp-server-2026... · dev.to/whoffagents ($19/mo case) · mcpbundles.com | Live market: ~318 MCP servers in the Claude Code marketplace, majority free; **paid tier $19–$149/mo real**; explicit gap in the $5–15 casual tier. `$19/mo` servers exist and defend the price | Subscription (flat monthly) OR per-call OR outcome-based. Delivery: SettleGrid (keep **95%**), Apify pay-per-event (keep **80%**, flat-rental sunset **Oct 2026**), or self-host + gateway | Reshape **find-a-provider** as a metered MCP server → recurring $19–49/mo tier below the $150 human-outcome card. Two-tier ladder: self-serve MCP (cheap, automated) vs stewarded outcome ($150, human close) | Build skeleton = **substrate-now** (already have MCP skeleton). Publish/price = **B1-GATED + JAMES-GATED** (account) |
| A3 | **x402 / A2A / ACP + Stripe MPP recurring rails** | stripe.com/blog/machine-payments-protocol · docs.stripe.com/payments/machine/mpp · paidsync.ai/blog/what-is-x402 · rzlt.io | **Stripe MPP live since 2026-03-18**, extended with streaming payments Apr 2026 — explicitly supports **agent recurring subscriptions** (fixed monthly/weekly cadence, no re-minting). x402 under Linux Foundation (x402 Foundation, Apr 2026); **165M+ tx, 69k agents**. PaidSync Q3-2026 roadmap: **ACP-compliant checkout for agent-initiated subscription signups** + AP2 mandates in the A2A Agent Card | An *agent* subscribes to our service on a cadence and pays machine-to-machine (stablecoin/card/BNPL via Shared Payment Tokens). This is the "agent-to-agent" future the SUPER system targets — a subscriber's agent auto-renews without a human each cycle | Fit **tension**: money-signature is Reserved. MPP recurring is the *right rail* for A2A subs, but auto-charging = exactly what our ethic hands to a human. Use MPP for **inbound receipt** (they pay us), never outbound autonomous spend | Watchlist / **JAMES-GATED** (Stripe account, wallet). Recurring receipt only post-B1 |
| A4 | **Agent-service aggregators / MCP bundles** | mcpbundles.com · getchatads.com/blog/tools-for-monetizing-mcp-servers · apify.com | Aggregators bundle MCP servers and "handle billing, discovery, and payout for a cut" (usagebox). Apify has a large existing buyer base; pay-per-event, keep 80% minus compute | They run the subscription meter + invoicing; we plug a pack in and take the majority split. Lowest ops burden, lower margin/control | Fit OK for the cheap self-serve tier; less fit for the stewarded $150 outcome (needs our own ledger + human close, which aggregators don't model) | Build = substrate-now; list/price = **B1-GATED + JAMES-GATED** |

**Cross-cutting reality (verified):** market average MCP price is **$0** and <5% of 20k+ listings earn a dollar (mcp-marketplace.io, per markets map). Subscriptions convert on **outcome + trust + transfer**, not on listing. Our differentiators — unedited ledger, rights-not-roles, human close, day-one transfer — are exactly what a $150/mo tier can defend that a $0 commodity MCP cannot.

---

## B. OUTBOUND — what OUR Super Agent should subscribe to (≤$50/mo total, compounds the loop)

Only items with a concrete use in Build #001–#003 or Track B. Each: cost · unlocks · kill-switch.
Ranked by (leverage × readiness × fit).

| # | Service | URL | Cost | What it unlocks (concrete Build use) | Kill-switch condition |
|---|---------|-----|------|--------------------------------------|-----------------------|
| B-out-1 | **Phone/WhatsApp verification API** (Twilio Lookup — already in substrate — or Veriphone/AbstractAPI) | twilio.com/lookup · veriphone.io · abstractapi.com | **$0 now** (per-lookup $0.004–0.025; Twilio number already owned +15089780034) OR $19/mo AbstractAPI 5k calls | `vendor_bot` verifies a provider's WhatsApp number is real/active **before** M1 outreach (candidate #2 onward). Prevents wasted consented starts + protects the AI-disclosure discipline. Directly serves Build #002+ | Cancel if candidate flow stays 1-at-a-time (manual check is fine at N=1). Re-evaluate at 3+ concurrent candidates |
| B-out-2 | **AWS Agent Registry** (A2A Agent Card discovery) | gerardo.dev/en/aws-agent-registry · awslabs/a2a-agent-registry-on-aws | **~$0** at our scale (GA 2026-08-31; free tier 5k records / 1M search / 2M get-list per mo; then $0.40/1k records) | Register our packs' A2A Agent Cards so other agents *discover* SUPER services — the inbound-discovery half of "agent-to-agent." Prep for A3 recurring. Effectively free until we have thousands of records | Drop if A2A discovery drives zero qualified inbound in 30 days; free tier means near-zero downside to leaving it on |
| B-out-3 | **Domain/business reputation lookup** (APIVoid / WhoisXML Domain Reputation) | apivoid.com/browse · domain-reputation.whoisxmlapi.com | pay-as-you-go, ~$0–10/mo at our volume | Vet a provider/counterparty's business legitimacy (website, email domain) before a Build Card names them. Feeds the vetting step of find-a-provider | Cancel if provider vetting stays local/relationship-based (as with candidate #1, a known human) |
| B-out-4 | **Uptime monitoring free tier** (UptimeRobot / BetterStack free) | uptimerobot.com · betterstack.com | **$0** (free tier) | Watch the systemd `vendor_bot` + heartbeat + fp-index on 198; alert James via existing Telegram if the Super Agent's voice line dies mid-conversation | N/A — free; remove only if it adds noise |

**Total committed outbound recurring: $0/mo** right now (all start on free/PAYG tiers). Ceiling if all paid tiers activate: **~$48/mo** — under the $50 cap. Every paid activation is **JAMES-GATED** (account + card). Recommend: keep all four on $0 tiers until a Build concretely needs the paid tier, then propose the single upgrade.

---

## C. RIGHTS-NOT-ROLES permissions schema (subscribed sub-agents) — grounded in dev_gateway

A subscriber's agent gets **rights** (specific verbs it may call) — never a **role** (standing access).
Every tier below is *already implemented* in `mcp/dev_gateway/gateway.py`; nothing is invented auth infra.
The invariant: **a lease is coordination between agents, NOT authorization** (`PROVISIONAL_NOTICE`).
Authorization is always a separate, explicit human (James) step.

| Tier | Right (verb) | Backed by (real code) | What the subscriber's agent MAY do | Guardrails already enforced |
|------|--------------|------------------------|------------------------------------|------------------------------|
| **R0 · READ-PUBLIC** | `get_open_blocks()` | `gateway.py` parses only the sanitized `HELP_WANTED.snapshot.md` | Read the public claim board / offer card / pack docs | No auth, no network, **no path, hostname, or secret ever in a response**; reads only files inside its own dir |
| **R1 · PROVISIONAL-LEASE** | `claim_block(id, claimant, contact)` | Writes `leases.json`, **4-hour** expiry enforced on read | Reserve one outcome/slot so two agents don't collide | Refuses double-claim; expiry auto-drops; response **always** carries `PROVISIONAL_NOTICE` = "coordination only, not authorization" |
| **R2 · SUBMIT-QUEUED** | `submit_build(id, pr_url)` | Appends `submissions.jsonl` — **STUB, no network** | Queue a deliverable/PR for human review | Requires a live lease + a plausible `https://` URL; returns "queued for human review"; **notifies no one** (no webhook = no accidental grant) |
| **R3 · JAMES-AUTHORIZED** | *(not an API call)* | Human confirm in the GitHub claim issue | Get **exactly the access the outcome needs, nothing more**, on the public ledger | **JAMES-GATED** by definition. No code path grants standing access, money movement, booking, or speaking-as-human. This is the only tier where real access appears |

**One-line summary:** a subscribed agent may *read the public board (R0), take a 4-hour provisional lease (R1), and queue a submission (R2)* entirely on its own — but **every real grant, and any money/books/voice, requires an explicit human authorization step (R3)**; rights are scoped verbs, roles are never issued, and a lease is coordination, not consent.

This maps 1:1 to Track B **O3 "rights not roles"** and the Subscription Card promise: *"your agent gets exactly the access the outcome needs, nothing more; you can read its permissions in one place at any time; it never moves your money, signs, or speaks as you."*

---

## FINAL (the five lines + one)

**Top 3 INBOUND:**
1. **Cowork enterprise private marketplaces** (claude.com/blog/cowork-plugins) — best returns×fit; free pack install is the hook, the **$150/mo outcome card** is the sub. B1-gated to sell; free listing is James-gated (account).
2. **Paid MCP subscription** by reshaping find-a-provider as a metered server ($19–49/mo tier; SettleGrid keep 95%) — real market ($19–149/mo live), fills the automated cheap tier under the human $150 tier. Skeleton is substrate-now; publish B1+James-gated.
3. **Stripe MPP recurring + x402/ACP A2A rails** (stripe.com/blog/machine-payments-protocol, live since Mar 2026) — the machine-to-machine subscription future; use for **inbound receipt only**, never autonomous outbound spend. Watchlist / James-gated.

**Top 2 OUTBOUND (≤$50/mo, all start $0):**
1. **Phone/WhatsApp verification** — Twilio Lookup (number already owned, $0 now) — verify provider numbers before outreach; serves Build #002+. Kill if flow stays 1-at-a-time.
2. **AWS Agent Registry** (GA 2026-08-31, free tier ~$0) — register our A2A Agent Cards so agents discover SUPER; the discovery half of agent-to-agent. Kill if zero qualified inbound in 30 days.

**Schema one-liner:** subscribed agents get scoped *rights* (read board · 4h provisional lease · queue submission) they can exercise alone — but every real grant, and all money/books/voice, is a separate explicit **James-authorization** step; a lease is coordination, not consent (already implemented in `mcp/dev_gateway/gateway.py`).

**Every money/identity step above is flagged JAMES-GATED; every SELL step is B1-GATED (waits on BUILD-001 close).**

---

### Sources (verified live 2026-09-03)
- Cowork plugins: https://claude.com/blog/cowork-plugins · https://support.claude.com/en/articles/13837433-manage-plugins-for-your-organization
- Paid MCP pricing: https://dev.to/whoffagents/pricing-an-mcp-server-in-2026-why-we-charge-19mo-when-the-market-average-is-0-nig · https://usagebox.com/articles/how-to-charge-for-mcp-server-2026-per-call-subscription-x402 · https://www.mcpbundles.com/blog/best-mcp-servers
- Stripe MPP recurring: https://stripe.com/blog/machine-payments-protocol · https://docs.stripe.com/payments/machine/mpp
- x402 / A2A / ACP: https://paidsync.ai/blog/what-is-x402 · https://www.rzlt.io/blog/agentic-payments-2026-x402-explainer
- AWS Agent Registry: https://gerardo.dev/en/aws-agent-registry.html · https://github.com/awslabs/a2a-agent-registry-on-aws
- Phone/domain verification: https://www.abstractapi.com/guides/alternatives-to/numverify-alternatives · https://www.apivoid.com/browse/ · https://domain-reputation.whoisxmlapi.com/api/pricing
- dev_gateway lease design (grounding for §C): `_staged_repos/super-agents-pack/mcp/dev_gateway/gateway.py` + `README.md`
</content>
</invoke>
