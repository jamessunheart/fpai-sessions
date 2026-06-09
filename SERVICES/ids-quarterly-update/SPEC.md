# SPEC — IDS Quarterly Update Service (design stub)

**Status:** DESIGN ONLY · not yet built · queued for future Forge dispatch
**Created:** 2026-05-19 (per Counsel review v0.1 Forge Notes #3)
**Purpose:** automate the quarterly refresh of the Income Disclosure Statement per IDS methodology paragraph commitment

---

## Why this exists

The IDS v0.2 commits to quarterly refresh on the 15th of Jan/Apr/Jul/Oct. The methodology paragraph specifies:

- Population: all active apprentices with referral compensation enabled in the period
- Weighting: by active days
- Exclusions: refunded subscriptions, canceled >30 days before report close
- Statistics: median, range (10th-90th), % earning zero

Doing this manually each quarter is JamesTime-leaking and error-prone. The service should auto-pull from Stripe + apprentice-gateway DB and draft the next IDS revision for review.

---

## Functional spec

### Inputs

```python
@dataclass
class QuarterlyParams:
    period_start: date          # e.g., 2026-04-01
    period_end: date            # e.g., 2026-06-30
    publication_date: date      # e.g., 2026-07-15
    prior_ids_version: str      # e.g., 'v0.2'
    next_ids_version: str       # e.g., 'v0.3'
```

### Process

1. **Pull from Stripe:**
   - List all customers with `apprentice_*` product subscriptions
   - For each customer: start date, end date (if any), refund history
   - For each: any affiliate-payout records (Stripe Connect or wherever payouts live)

2. **Cross-reference with apprentice-gateway DB:**
   - Active state at period start and period end
   - `provision_state == 'complete'` filter
   - Exclude apprentices canceled >30 days before period_end

3. **Compute statistics:**
   - Population N
   - Days-weighted active count
   - Earnings distribution: median, percentiles (10/25/50/75/90), % earning zero, mean
   - Top 10% mean (regulator-relevant)

4. **Draft IDS revision:**
   - Pull `ids_v0.2.md` template
   - Replace TBD table cells with computed figures
   - Update methodology block with actual N, dates
   - Bump version (`v0.2` → `v0.3`)
   - Save to `~/.config/fpai/apprentice_launch/ids_v0.3.md`

5. **AI Counsel pre-review:**
   - Dispatch AI Counsel for sanity check on the figures
   - Flag any unusual patterns (e.g., median jumped significantly — likely real-data event)

6. **Surface to James:**
   - TG notification: "IDS v0.3 ready for review · /apprentice/ids preview link · 30 days to publication"
   - Diff against prior version
   - Counsel sanity-check summary

7. **On approval:**
   - Archive prior version to `~/.config/fpai/apprentice_launch/archive/ids_v0.2_archived.md`
   - Deploy new version to `static/ids.html` (or markdown→HTML pipeline)
   - Update apprentice-gateway DB column `ids_version` for new signups

### Outputs

- `~/.config/fpai/apprentice_launch/ids_v{N+1}.md` — drafted IDS
- `~/.config/fpai/apprentice_launch/quarterly_data/{period}.json` — raw computed data
- TG notification to James
- Optional: AI Counsel pre-review log

### Scheduling

Cron-fired on the 1st of Jan/Apr/Jul/Oct (gives 15 days for review before scheduled publication).

```
0 9 1 1,4,7,10 * /usr/local/bin/run_ids_quarterly_update.sh
```

---

## Implementation notes

- **Language:** Python (matches apprentice-gateway stack)
- **Dependencies:** stripe SDK, sqlite3, existing AI Counsel dispatch utility
- **Storage:** read-only on Stripe + apprentice-gateway DB; writes only to `~/.config/fpai/apprentice_launch/`
- **Security:** no public endpoints; runs as cron user with read-only DB access
- **Reversibility:** all outputs are drafts; no auto-publish without James approval
- **Cost:** AI Counsel call ~$0.50 per quarterly run; negligible

---

## Phase plan

**Phase 0 (current):** SPEC committed. No code.

**Phase 1 (built when triggered):** when v0.2 affiliate layer activates (the first quarter with real earnings data is the trigger). Builds the data-pull + statistics. Drafts a markdown.

**Phase 2 (after 2-3 successful runs):** add AI Counsel pre-review automation.

**Phase 3 (after 1 year stable):** add public dashboard at /apprentice/ids-archive showing historical IDS versions.

---

## Dependencies

- Apprentice Gateway v0.2 (affiliate layer must be active for there to be earnings data to disclose)
- Stripe Connect (payout records source-of-truth)
- AI Counsel dispatch wrapper (exists as agent invocation pattern)

---

## Trigger to build

Build when: (a) v0.2 affiliate layer ships AND (b) first quarter of post-activation data approaches close.

Until then: this SPEC remains as design reference. Ember references it when planning v0.2 work.

---

*Designed by The Forge · 2026-05-19 · per Counsel review v0.1 Forge Notes #3*
