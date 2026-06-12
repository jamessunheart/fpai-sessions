# SPEC: Financial Hub Rung 4

**Created:** 2026-06-12
**Status:** Draft
**Scope:** One secret-free money pane plus anomaly alerts
**Security posture:** Read-only by structure

---

## 1. Purpose

Financial Hub Rung 4 gives the cockpit a single trusted money pane that answers:

- How much liquidity do we have?
- What is current burn and runway?
- Are any leveraged positions close to liquidation?
- Are money snapshots stale?
- Are infrastructure/API costs approaching the $20/day cap?

The hub is observational only. It must never initiate trades, rebalance, move funds, alter treasury source files, store credentials, or expose secrets.

## 2. Rung 4 Definition

Rung 4 is the first operationally useful financial surface:

- One visible pane for liquidity, burn, runway, P&L, liquidation distance, and daily cost.
- Alert cards for the four required anomaly families.
- Source freshness and confidence shown beside every metric group.
- Derived snapshots persisted for dashboard speed and auditability.
- No secret ingestion, no privileged write path, no transaction path.

Rung 4 does not optimize the treasury. It makes the current financial state visible enough that a human can decide what to do next.

## 3. Non-Goals

- No trading, rebalancing, swaps, staking, withdrawals, deposits, or automated account actions.
- No private keys, wallet seed phrases, exchange credentials, bank credentials, Stripe secrets, OAuth tokens, or paid API keys.
- No financial advice language or "recommended trade" generation.
- No mutation of `core/STATE/TREASURY.json`, `treasury_data.json`, service registries, or trading-system state.
- No agent autonomy beyond emitting alerts and status.

## 4. Users

- Founder/operator: needs a quick, honest financial cockpit.
- Builder agents: need a read-only health signal before making cost- or infra-heavy choices.
- Review/audit agents: need source freshness, derivation notes, and clear alert evidence.

## 5. Read-Only By Structure

The implementation must enforce read-only behavior at multiple layers.

### 5.1 Process Permissions

- Run the collector/dashboard under a service user with read access to source paths and write access only to its own derived cache directory.
- The derived cache directory should be isolated, for example:
  - `var/financial-hub/snapshots/`
  - `var/financial-hub/alerts/`
- Source files and upstream service state must not be writable by this process.

### 5.2 API Surface

Allowed external methods:

- `GET /health`
- `GET /capabilities`
- `GET /state`
- `GET /api/v1/money-pane`
- `GET /api/v1/alerts`
- `GET /api/v1/sources`

Forbidden methods:

- Any endpoint that accepts wallet, exchange, bank, or payment credentials.
- Any endpoint named or behaving like `trade`, `rebalance`, `execute`, `approve`, `withdraw`, `deposit`, `transfer`, `swap`, `go-live`, or `credentials`.
- Any dashboard control that writes to upstream sources.

### 5.3 Adapter Contract

Every source adapter must implement only:

```python
class ReadOnlyFinancialSource:
    source_id: str
    source_type: str

    def read_snapshot(self) -> dict:
        ...

    def health(self) -> dict:
        ...
```

Adapters must not expose generic HTTP clients, shell execution, write handles, mutation methods, or credential setters.

### 5.4 Secret-Free Rules

- Do not read `.env` files.
- Do not display environment variables.
- Do not persist request headers, auth tokens, cookies, wallet addresses marked private, account numbers, or full transaction identifiers.
- If a source contains sensitive identifiers, show a short label and a fingerprint only, for example `wallet:trust-wallet`, `account:stripe-pending`, or `tx:abcd...1234`.
- If a metric requires a secret-bearing source, show the metric as unavailable with remediation text: `connect a redacted/read-only exporter`.

## 6. Inputs

Rung 4 should prefer local, already-redacted sources before external APIs.

### 6.1 Primary Local Sources

- `var/financial-hub/manual_financial_inputs.json`
  - Expected fields: `schema`, `updated_at`, `updated_by`, `cash_on_hand_usd`, `monthly_burn_usd`, `notes`.
  - Used for: canonical redacted cash and burn inputs when no safe automated exporter exists.
  - Rules: human-maintained, non-secret, read-only to the service; no account numbers, credentials, payment tokens, wallet secrets, or private identifiers.
- `core/STATE/TREASURY.json`
  - Expected fields: `last_updated`, `cash_on_hand`, `stripe_balance`, `monthly_burn`, `currency`, `health`.
  - Used for: liquidity, burn, runway, stale treasury state.
- `treasury_data.json` when present.
  - Expected fields: `timestamp`, `summary`, `spot_positions`, `leveraged_positions`, `liquidation_report`.
  - Used for: capital, P&L, liquidation distance, margin at risk.
- WhaleTrack/treasury service read endpoint when available:
  - `GET /api/treasury/snapshot`
  - Used for: portfolio snapshot and freshness.
- Service/catalog cost sources when present:
  - API gateway usage/cost files.
  - service registry metadata.
  - known per-service cost estimates.

### 6.2 Optional External Sources

Optional external sources must be disabled by default unless a source-specific read-only exporter exists.

- Stripe balance exporter, redacted and read-only.
- Cloud provider cost exporter, redacted and read-only.
- Exchange portfolio exporter, redacted and read-only.

The hub may read their redacted outputs. It must not hold their API keys.

## 7. Normalized Snapshot Model

`GET /api/v1/money-pane` returns one normalized object:

```json
{
  "generated_at": "2026-06-12T18:00:00Z",
  "currency": "USD",
  "summary": {
    "liquidity_usd": 0,
    "portfolio_value_usd": 0,
    "total_capital_usd": 0,
    "monthly_burn_usd": 0,
    "daily_burn_usd": 0,
    "runway_days": null,
    "pnl_usd": 0,
    "pnl_percent": 0,
    "daily_cost_usd": 0,
    "daily_cost_cap_usd": 20
  },
  "risk": {
    "nearest_liquidation": {
      "asset": null,
      "distance_percent": null,
      "distance_usd": null,
      "liquidation_price": null,
      "margin_at_risk_usd": null,
      "severity": "none"
    },
    "open_leveraged_positions": 0
  },
  "alerts": [],
  "sources": []
}
```

Each `sources[]` item:

```json
{
  "source_id": "core-state-treasury",
  "label": "Core Treasury State",
  "path_or_url": "core/STATE/TREASURY.json",
  "last_observed_at": "2026-06-12T17:55:00Z",
  "freshness_seconds": 300,
  "status": "fresh",
  "confidence": "medium",
  "notes": "Manual cash source; no bank credentials connected."
}
```

## 8. Required Alert Families

Alerts share this shape:

```json
{
  "id": "alert-20260612-cost-cap",
  "type": "cost_cap",
  "severity": "warning",
  "title": "Daily cost is near the cap",
  "message": "Estimated cost is $16.20 of the $20.00 daily cap.",
  "observed_value": 16.2,
  "threshold": 20,
  "source_ids": ["api-gateway-usage"],
  "detected_at": "2026-06-12T18:00:00Z",
  "read_only": true
}
```

### 8.1 Burn Spike

Purpose: detect sudden burn-rate jumps.

Inputs:

- Current `monthly_burn` from treasury state.
- Previous derived snapshots from Financial Hub cache.

Rules:

- `info`: current monthly burn exists but no 7-day baseline exists.
- `warning`: monthly burn is at least 25% above 7-day median and increase is at least $100/month.
- `critical`: monthly burn is at least 50% above 7-day median and increase is at least $500/month.

If only daily cost is available, project monthly burn as `daily_cost_usd * 30.4375` and mark confidence `low`.

### 8.2 Liquidation Distance

Purpose: surface leveraged position danger without taking action.

Inputs:

- `liquidation_report[]` from `treasury_data.json` or equivalent read endpoint.

Rules:

- `info`: leveraged positions exist and nearest distance is above 30%.
- `warning`: nearest liquidation distance is below 30%.
- `critical`: nearest liquidation distance is below 15%.

Nearest liquidation should be the minimum positive `distance_percent`. If a source reports a negative distance, emit `critical` and label it `past_liquidation_or_bad_source`; do not suppress it.

### 8.3 Stale Snapshot

Purpose: prevent calm-looking dashboards from hiding dead data.

Inputs:

- `last_updated`, `timestamp`, endpoint freshness, file mtimes.

Rules:

- `info`: snapshot age between 30 and 60 minutes.
- `warning`: snapshot age above 60 minutes.
- `critical`: snapshot age above 6 hours for any source used in top-line money metrics.

Every top-line number must display the source age.

### 8.4 $20/Day Cost Cap

Purpose: keep infra/API spend visible and bounded.

Inputs:

- Derived service cost estimates.
- API usage/cost data where available.
- Manual override file if present.

Rules:

- `info`: estimated daily cost is below $12.
- `warning`: estimated daily cost is at least $16, or 80% of the $20/day cap.
- `critical`: estimated daily cost is at least $20.

Behavior at critical:

- Emit alert.
- Freeze optional paid external polling.
- Continue local file and local service reads.
- Do not kill services automatically in Rung 4.

## 9. Dashboard Requirements

The dashboard should be one work surface, not a landing page.

### 9.1 Layout

Top row:

- Liquidity
- Monthly burn
- Runway
- Daily cost versus $20 cap

Second row:

- Portfolio value
- P&L
- Nearest liquidation distance
- Source freshness

Main body:

- Alert list grouped by severity.
- Source table with freshness, confidence, and last observed time.
- Compact position risk table for leveraged positions only.

### 9.2 UI Constraints

- Use neutral financial dashboard language.
- Do not include action buttons for trade, transfer, rebalance, approve, go-live, or credential setup.
- Alert cards may include links to source views, but links must be read-only.
- Every metric must show its source and age on hover or adjacent small text.
- Show unavailable metrics explicitly instead of inventing values.

## 10. Service API

### 10.1 Health

`GET /health`

```json
{
  "status": "healthy",
  "service": "financial-hub",
  "version": "0.4.0",
  "read_only": true,
  "timestamp": "2026-06-12T18:00:00Z"
}
```

### 10.2 Capabilities

`GET /capabilities`

```json
{
  "service": "financial-hub",
  "rung": 4,
  "capabilities": [
    "money_pane",
    "burn_spike_alerts",
    "liquidation_distance_alerts",
    "stale_snapshot_alerts",
    "daily_cost_cap_alerts",
    "source_freshness"
  ],
  "forbidden_capabilities": [
    "trading",
    "rebalancing",
    "credential_storage",
    "fund_transfer",
    "upstream_mutation"
  ]
}
```

### 10.3 State

`GET /state`

```json
{
  "status": "active",
  "mode": "read_only",
  "last_snapshot_at": "2026-06-12T18:00:00Z",
  "active_alerts": 0,
  "daily_cost_usd": 0,
  "daily_cost_cap_usd": 20,
  "paid_polling_frozen": false
}
```

### 10.4 Money Pane

`GET /api/v1/money-pane`

Returns the normalized snapshot model from section 7.

### 10.5 Alerts

`GET /api/v1/alerts?severity=warning`

Returns active alerts plus the latest resolved alerts if `include_resolved=true`.

### 10.6 Sources

`GET /api/v1/sources`

Returns source status, freshness, adapter type, confidence, and redaction status.

## 11. Persistence

Allowed writes:

- Derived normalized snapshots.
- Derived alert events.
- Derived source-health records.
- Local dashboard cache.

Forbidden writes:

- Source treasury files.
- Wallet, exchange, bank, or payment-provider state.
- Service registries unless a separate deploy task explicitly owns registration.
- Credentials or secret-bearing request/response bodies.

Suggested derived files:

```text
var/financial-hub/snapshots/latest.json
var/financial-hub/snapshots/YYYY-MM-DD.jsonl
var/financial-hub/alerts/active.json
var/financial-hub/alerts/history.jsonl
```

## 12. Cost Guardrails

- Default daily cap: `$20`.
- Cap is configurable only through a local non-secret config value, not a dashboard field.
- All optional paid pollers must declare estimated cost per call.
- The collector must maintain `estimated_cost_usd` per source per day.
- At 80% cap, reduce optional polling frequency to no more than once per hour.
- At 100% cap, disable optional paid polling until the next UTC day.
- Local files and already-running local service reads are allowed after cap breach.

### 8.5 Manual Financial Input

Purpose: keep runway truth available without storing credentials.

Inputs:

- `var/financial-hub/manual_financial_inputs.json`

Rules:

- `warning`: `monthly_burn_usd` is missing and no other burn source is available.
- `warning`: manual input file is older than 7 days.
- `critical`: manual input file is older than 30 days.

Manual inputs should override lower-confidence local estimates for `cash_on_hand_usd` and `monthly_burn_usd`.

Helper command:

```bash
python3 SERVICES/unified-financial-dashboard/scripts/manual_inputs.py --validate
python3 SERVICES/unified-financial-dashboard/scripts/manual_inputs.py --cash-on-hand-usd 120000 --monthly-burn-usd 30000 --updated-by human --notes "Redacted operating estimate."
```

The helper validates numeric fields and rejects secret-like keys or values before writing the ignored local file.

## 13. Implementation Notes

### 13.1 Collector Cadence

- Local source scan: every 60 seconds.
- Local service endpoint scan: every 2 minutes.
- Optional paid exporter scan: every 15 minutes until 80% cap, then hourly, then disabled at cap.
- Derived snapshot compaction: daily.

### 13.2 Confidence

Use confidence labels instead of false precision:

- `high`: direct current source with known freshness and no parse errors.
- `medium`: manual/local file source under 60 minutes old.
- `low`: projected or stale source, or source missing a baseline.
- `unavailable`: metric cannot be derived.

### 13.3 Currency

- Rung 4 uses USD only.
- If a source reports non-USD values, the adapter must either provide a redacted conversion source or mark the metric unavailable.

## 14. Acceptance Criteria

- A single dashboard pane renders with liquidity, burn, runway, daily cost cap, P&L, nearest liquidation distance, alerts, and source freshness.
- The service starts with no secrets configured.
- The service can run when optional external exporters are absent.
- No endpoint accepts credentials or mutation payloads.
- Attempts to call forbidden mutation endpoints return 404 or 405.
- The process cannot write to primary treasury source files under normal deployment permissions.
- Burn spike alert fires against a synthetic 7-day baseline.
- Liquidation warning fires when distance is below 30%; critical fires below 15%.
- Stale snapshot warning fires above 60 minutes; critical fires above 6 hours.
- Cost-cap warning fires at `$16/day`; critical fires at `$20/day` and freezes optional paid polling.
- Every top-line metric displays source age and confidence.
- Secret scanner over derived cache finds no tokens, keys, private keys, seed phrases, cookies, or auth headers.

## 15. Verification Commands

These are target commands for the implementation task:

```bash
pytest SERVICES/financial-hub/tests
curl http://localhost:8100/health
curl http://localhost:8100/api/v1/money-pane
curl http://localhost:8100/api/v1/alerts
curl http://localhost:8100/api/v1/sources
```

Expected manual check:

- Dashboard contains no trade/transfer/rebalance/credential controls.
- Dashboard still renders if only `core/STATE/TREASURY.json` exists.
- Alerts remain explanatory and do not claim to have taken action.

## 16. Open Questions

- Should Financial Hub live at the already-proposed unified financial dashboard port `8100`, or behind API Gateway routing only?
- What is the canonical redacted cost source for Claude/API usage?
- Should alert events be broadcast to the coordination mesh in Rung 4, or wait until Rung 5?
- What is the minimum source set required before the dashboard should be considered `healthy` rather than `degraded`?
