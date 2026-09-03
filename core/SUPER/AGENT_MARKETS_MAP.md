# SUPER — Agent Markets Map

Mission (James, Reserved:direction, 2026-09-03): "if you reach agent markets, we will have funds to support lifestyle while building super system."
All entries verified live via WebFetch/WebSearch on 2026-09-03. No from-memory listings.

Asset: `https://github.com/jamessunheart/super-agents-pack` — MIT, public. Three Claude Code sub-agents (super-steward, super-vendor-agent, super-build) + `super_build.py` + Card templates + WhatsApp vendor bot. NOT yet a plugin (no `plugin.json`/`marketplace.json`).

Gate reminder: Track B "nothing sells before BUILD-001 CLOSED (B1)." REACH is unlocked; anything that SELLS stays James-gated. Free listings for reach are substrate-executable; account creation / public voice / money remain James-gated.

---

## 1. The markets (verified live 2026-09-03)

| # | Market | URL | What lists there | Monetization mechanics | Submission | Effort | Honest reach |
|---|--------|-----|------------------|------------------------|------------|--------|--------------|
| 1 | **Own marketplace repo** (`.claude-plugin/marketplace.json` in our own repo) | github.com/jamessunheart/super-agents-pack | Any Claude Code plugin we ship | Free; we own it; no rev-share | Add `marketplace.json` + `plugin.json`, push. Users run `/plugin marketplace add jamessunheart/super-agents-pack` | 1–2 h | Small alone, but it is the install substrate every other channel points at |
| 2 | **Anthropic community marketplace** (`claude-community`) | github.com/anthropics/claude-plugins-community · submit: platform.claude.com/plugins/submit (Console) or claude.ai/admin-settings/directory/submissions/plugins/new | Third-party Claude Code plugins that pass validation + safety screen | Free listing, no rev-share. Reach = lead-gen only | `claude plugin validate ./pack`, then Console form (individual authors OK; claude.ai form needs Team/Ent). Approved plugins pinned to commit SHA, catalog syncs nightly | 2–4 h + review wait | **High** — the canonical discovery surface for Claude Code users |
| 3 | **`a-list-of-claude-code-agents`** (hesreallyhim) | github.com/hesreallyhim/a-list-of-claude-code-agents | Community sub-agents | Free, PR-based, no money | PR against README in existing format (name in backticks, author, one-line desc). "Passively maintained" | 15 min | Medium — real discovery, low friction |
| 4 | **`awesome-claude-code-subagents`** (VoltAgent, 100+ agents) | github.com/VoltAgent/awesome-claude-code-subagents | Curated subagents | Free, PR | PR, follow category format | 20 min | Medium-high — one of the largest curated lists |
| 5 | **`awesome-claude-agents`** (rahulvrane) + navin4078 + EricTechPro forks | github.com/rahulvrane/awesome-claude-agents | Subagents, frameworks, orchestration recipes | Free, PR | PR / issue with link + summary | 15 min each | Low-medium each; cheap to blanket |
| 6 | **GitHub topics** | github.com/topics/claude-code-subagents · /sub-agents · /cowork-plugin · /claude-code-plugins-marketplace | Any repo tagged | Free, organic search/discovery | Add topics to repo settings | 5 min | Low-medium, passive long-tail |
| 7 | **claudemarketplaces.com** | claudemarketplaces.com/marketplaces | Directory of Claude Code plugin marketplaces | Free directory | Submit our marketplace (from #1) | 15 min | Medium — aggregates marketplaces for browsers |
| 8 | **Claude Cowork plugin marketplace** | claude.com/plugins · claude.com/blog/cowork-plugins-across-enterprise | Vertical skill/connector/sub-agent packs for knowledge workers; 39+ Agent-Skills bundles (legal, finance, real estate, trades) | Free listing today; enterprise private marketplaces; subscription-per-plugin model emerging | Same plugin format as #2; org/enterprise surface | 3–5 h + org | **High-value** — this is the paying-business audience; best fit for Track B outcomes |
| 9 | **MCP Marketplace** | mcp-marketplace.io | Paid MCP servers | **Direct $**: Stripe Connect + license-key SDK (Py/TS) + creator dashboard; per-call/subscription pricing | Reshape pack → MCP server, list, set price | 1–2 days (MCP reshape) | Medium reach, **real dollars** |
| 10 | **SettleGrid** | (npx settlegrid publish) | Paid MCP tools | **Direct $**: keep **95%** on Free tier, per-transaction | `npx settlegrid publish` on an MCP server | 1–2 days | Small-medium, highest take-rate |
| 11 | **AgenticMarket / Apify MCP** | agenticmarket.dev · apify.com | Paid MCP servers / actors | **Direct $**: per-call, keep 80–90%; Apify pay-per-event, keep 80% minus compute | Add header check + price (AgenticMarket) or define events (Apify) | 1–2 days | Apify = large existing buyer base |
| 12 | **Virtuals ACP / Revenue Network** | app.virtuals.io · whitepaper.virtuals.io | Autonomous agent-to-agent services (18,000+ agents) | **Direct $**, onchain escrow; Revenue Network distributes **up to $1M/mo** to service-selling agents; ACP v2 non-custodial wallet + SDK/CLI | Register agent, wallet, ACP integration | 3–5 days, crypto | Largest raw pool; crypto + custody friction; fit tension with serve-not-rule |
| — | **Payment rails (infra, not markets):** Skyfire KYAPay, Payman (SOC2/PCI API), Nevermined | skyfire.xyz · paymanai.com · nevermined.ai | — | Rails for when agents pay agents | Integrate later | — | Watchlist — enabling infra, not a listing surface |

Reality check (source: mcp-marketplace.io): 20,000+ MCP servers exist, <5% earn a single dollar. Listing ≠ dollars. Free agent-pack listings buy **reach**; dollars come either from (a) funneling that reach into the Track B $150/mo subscription, or (b) reshaping the pack as a **paid MCP server** on #9–11.

---

## 2. Ranking — (funds potential × speed × fit with serve-not-rule ethic)

**Tier A — do now, substrate-executable, foundation (highest speed × fit):**
1. **#1 Own marketplace repo** — instant, we own it, zero gate, makes every other channel one-command installable. Funds: indirect (distribution rail). Fit: perfect.
2. **#3 + #4 + #5 awesome-list PRs** — 15–20 min each, pure reach, MIT-honest, no money touched. Fit: perfect (serving the commons).
3. **#6 GitHub topics + #7 claudemarketplaces** — passive long-tail discovery, near-zero cost.

**Tier B — highest legit reach, needs one James-gated form:**
4. **#2 Anthropic community marketplace** — the canonical Claude Code discovery surface. Free, ethic-aligned, but submission needs account/Console form (James-gated). Biggest reach for zero money.

**Tier C — the actual dollar engine (post-BUILD-001):**
5. **#8 Cowork marketplace** — the paying-business audience; the natural home for Track B "finance dept / find-a-provider / hold-my-Build" outcome packs at $150/mo. Best funds×fit once B1 clears.
6. **#9 MCP Marketplace / #10 SettleGrid / #11 Apify** — direct per-call dollars, keep 80–95%. Requires MCP reshape + Track B B1 gate. This is where "first real dollar without a subscription conversation" can happen fastest.

**Watchlist (re-evaluate 30 days):**
7. **#12 Virtuals ACP Revenue Network** — largest pool ($1M/mo) but crypto custody + onchain identity create fit tension with the serve-not-sovereign ethic and heavy money-gate. Revisit if Track B proves and we want an autonomous-agent revenue line.

Path-to-first-dollar, honest: fastest legit dollar = **reshape one pack (e.g. "find-a-provider") as a paid MCP server on SettleGrid/MCP Marketplace** (keep 80–95%, no subscription sales call) — but that trips the Track B B1 gate, so it waits on #001. Fastest **ungated** money-adjacent move = list free everywhere (Tier A+B) to build the lead funnel that Track B converts once #001 closes.

---

## 3. Top-3 listing text — ready to paste

### TOP 1 — Own marketplace (`.claude-plugin/marketplace.json`) — SUBSTRATE-EXECUTABLE NOW

`marketplace.json` (at repo `.claude-plugin/marketplace.json`):
```json
{
  "name": "super-agents",
  "owner": { "name": "James Sunheart", "url": "https://github.com/jamessunheart" },
  "metadata": {
    "description": "Agents that turn outcomes into accountable, transferable Build Cards — rich serving, never sovereign.",
    "version": "0.1.0"
  },
  "plugins": [
    {
      "name": "super-agents",
      "source": "./",
      "description": "Three sub-agents (steward, vendor, build) that convert a real-world outcome into a signed Build Card, run provider outreach with AI disclosure, and hand every close to a human. Every deliverable is an unedited ledger; transfer is the day-one promise.",
      "version": "0.1.0",
      "author": { "name": "James Sunheart" },
      "homepage": "https://github.com/jamessunheart/super-agents-pack",
      "license": "MIT"
    }
  ]
}
```
Plus `.claude-plugin/plugin.json` (name `super-agents`, version `0.1.0`, `agents/` at root). Then README line: `/plugin marketplace add jamessunheart/super-agents-pack` → `/plugin install super-agents@super-agents`.
Substrate can build/commit this fully. Only the `git push` to James's public repo is account-gated.

### TOP 2 — Anthropic community marketplace submission text

Plugin name: `super-agents`
One-line: **Turn any outcome into an accountable, transferable Build Card — three sub-agents that serve, disclose AI, and hand every close to a human.**
Description (form body):
> super-agents is a Claude Code plugin of three cooperating sub-agents. **super-build** converts a plain-language outcome ("find me a reliable produce supplier") into a structured Build Card with a max-loss bound and a nine-point "more alive" check. **super-vendor-agent** runs provider outreach over WhatsApp Business, always discloses it is an AI, logs every message verbatim, and classifies replies. **super-steward** tracks release conditions and state across sessions. Design law: the agent never releases funds, books, pays, or speaks as the human — every close is handed up. The deliverable is the unedited ledger; transfer of the whole system to the user is the promise on day one. MIT. Ethic: rich serving, never sovereign.
> Repo: https://github.com/jamessunheart/super-agents-pack
Pre-submit: run `claude plugin validate ./super-agents-pack` (must print ✔). Submit via platform.claude.com/plugins/submit (individual) — **James-gated (account + form)**.

### TOP 3 — awesome-list PR entry (a-list-of-claude-code-agents, VoltAgent, rahulvrane)

README line (matches existing backtick/author/desc format):
```markdown
- [`super-agents`](https://github.com/jamessunheart/super-agents-pack) — by [@jamessunheart](https://github.com/jamessunheart) — Three sub-agents that turn a real-world outcome into an accountable, transferable Build Card: `super-build` (outcome → signed Card), `super-vendor-agent` (AI-disclosed provider outreach, verbatim ledger), `super-steward` (release conditions + cross-session state). Never pays/books/speaks-as-human; every close handed up. MIT.
```
PR body:
> Adds `super-agents`, a 3-agent pack for outcome→Card workflows with human-in-the-loop on every close and full ledger transparency. MIT, not malicious, fits the format. Thanks for maintaining the list.
Substrate can draft the PR; the actual PR-open uses James's GitHub identity → **James-gated (public voice + account)**.

---

## 4. James-gated vs substrate-executable

**Substrate can do now (reversible, no account/voice/money):**
- Write `marketplace.json` + `plugin.json`, restructure repo to plugin layout, run `claude plugin validate`.
- Draft every PR body + listing text (above).
- Add GitHub topics list (as a ready command).
- Reshape a pack into an MCP-server skeleton for #9–11 (build only; no publish).

**James-gated (public voice · account creation · money):**
- `git push` to the public `super-agents-pack` repo (his identity).
- Opening PRs to awesome-lists (his GitHub voice).
- Community-marketplace Console/claude.ai submission (his account).
- Any Cowork/MCP-marketplace/SettleGrid/Virtuals **account creation or pricing** — plus these SELL, so also Track B B1-gated until BUILD-001 closes.
- Any wallet / onchain / Stripe Connect setup.

---

## 5. Bottom line (5 lines)

1. **Top 3 markets:** (1) our own `marketplace.json` repo — substrate-buildable now, the install rail everything points at; (2) Anthropic community marketplace — the canonical Claude Code discovery surface, free; (3) the awesome-lists (a-list / VoltAgent / rahulvrane) — 15-min PRs, pure reach.
2. **Direct-dollar engine (post-#001):** SettleGrid / MCP Marketplace (keep 80–95% per call) by reshaping one pack as a paid MCP server; Cowork marketplace for the $150/mo Track B outcome packs.
3. **Expected path to first dollar:** list the free pack everywhere (Tier A+B) → build the lead funnel → convert to Track B $150/mo once BUILD-001 closes; OR, faster and subscription-free, ship "find-a-provider" as a paid MCP server on SettleGrid — but that trips the B1 gate, so it waits on #001.
4. **Single fastest James-gated step:** `git push` the plugin-formatted repo, then paste the community-marketplace submission (Top 2 text) at platform.claude.com/plugins/submit — one account action unlocks the highest-reach free channel.
5. **Reality:** 20k+ agent/MCP listings exist, <5% earn a dollar — listing buys reach, not revenue; the dollar is the Track B conversion or the paid-MCP reshape, both B1-gated.
