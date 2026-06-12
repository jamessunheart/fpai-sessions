# SPEC — Zen Village Wallet v0.1

**Version:** 0.1.0
**Port:** 8774
**Status:** Infrastructure-only · DO NOT onboard real participants until James greenlights
**Contract:** Enforces ZV Value-Exchange Agreement v4.1 (`docs/zen-village/agreements/zv-value-exchange-agreement-v4.1.md`) — adds Peer-to-Peer Transfers section
**Naming:** Coherent Credits Protocol-compatible (1 CORA = $1 internal recognition unit; ZV is the first CCP node)

## Purpose

WhatsApp-first weekly cycle wallet for Zen Village participants. Operationalizes the v4.0 agreement:
- Monday invoice (value stack + floor + 3 priorities)
- Daily proof submission (text/photo/video/voice)
- Witness queue + approval
- Sunday Seal (week summary + CORA Credits issued)
- Redemption flow (coconut, smoothie, etc.)
- Trust-curve enforcement (W1=50% / W2=75% / W3+=full)
- Earning cap (250 CORA/week · overflow = honor entry)
- Floor enforcement (can never go below tier floor)

WhatsApp is **transport only**. All proof, balance, audit lives in our DB. Phoenix-resilient.

## Architecture

```
WhatsApp (participant)
    ↓ (Evolution API · self-hosted)
    ↓ webhook POST /wa/webhook
zv-wallet.service (FastAPI · port 8774)
    ↓ writes to
SQLite at /var/lib/zv-wallet/zv-wallet.db
    ↓ reads from
PWA dashboard at /wallet/ (HTML + JSON API)
```

## Endpoints

### WhatsApp transport

```
POST /wa/webhook              Evolution API webhook (messages.upsert · connection.update · qrcode.updated)
POST /wa/send                 Internal: send WA message via Evolution API (admin token gated)
GET  /wa/qr                   Get current QR code for instance pairing (admin)
GET  /wa/status               Connection status (admin)
```

### Wallet (read · no auth · uses phone as ID)

```
GET  /wallet/balance/{phone}        CORA balance + last 7d activity
GET  /wallet/invoice/{phone}        Active week invoice
GET  /wallet/seal/{phone}/{week}    Sunday Seal record
GET  /wallet/redemptions            Menu of redeemable items (from v4.0)
```

### Wallet (action · participant-initiated via WA)

Commands parsed from WA messages (case-insensitive, first word):
```
balance                           Return current balance
invoice                           Return active invoice
proof p1 <text>                   Submit P1 proof (text)
proof p2 <text>                   Submit P2 proof
proof p3 <text>                   Submit P3 proof
proof <text>                      Generic proof (witness routes)
redeem <item>                     Request redemption (coconut/smoothie/massage)
transfer @user <amount> [memo]    P2P CORA transfer (v4.1)
history                           Last 10 personal transactions (v4.1)
help                              Returns help text
```

Photo/video/voice attached to a "proof" command → media stored, queued for witness with link.

### Witness

```
POST /witness/invoice/issue                Issue weekly invoice
       body: {participant_phone, tier, week_start, p1, p2, p3, value_stack}
POST /witness/proof/{proof_id}/approve     Approve proof (priority bonus awarded)
POST /witness/proof/{proof_id}/partial     Partial credit
POST /witness/proof/{proof_id}/reject      Reject
POST /witness/seal/{participant_phone}     Generate Sunday Seal · finalize week · issue CORA
POST /witness/pair                          Pair witness ↔ participant
GET  /witness/queue/{witness_phone}        Pending review queue
GET  /witness/participants/{witness_phone} Active participants for this witness
```

Witness commands also work via WA (DM to bot):
```
/issue @participant tier:shared p1:"..." p2:"..." p3:"..."
/approve <proof_id>
/partial <proof_id> <reason>
/reject <proof_id> <reason>
/seal @participant
/queue
```

### Admin

```
GET  /admin/users                List all participants + witnesses
POST /admin/user/onboard         Manually onboard (used during rotation)
GET  /admin/audit                Full action log
POST /admin/rotate               Mark current WhatsApp number ROTATED + queue re-onboard
GET  /health                     Health check (no auth)
```

All `/witness/*` and `/admin/*` require `X-Admin-Token` header.

## DB Schema (SQLite)

```sql
CREATE TABLE users (
  phone TEXT PRIMARY KEY,          -- E.164 format
  display_name TEXT,
  role TEXT NOT NULL,              -- 'participant' | 'witness' | 'steward'
  tier TEXT,                       -- 'private' | 'shared' | 'communal' (participants only)
  week_number INTEGER DEFAULT 0,   -- for trust-curve (1=50%, 2=75%, 3+=full)
  active INTEGER NOT NULL DEFAULT 1,
  onboarded_at TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE witness_pairings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  participant_phone TEXT NOT NULL,
  witness_phone TEXT NOT NULL,
  paired_at TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  FOREIGN KEY (participant_phone) REFERENCES users(phone),
  FOREIGN KEY (witness_phone) REFERENCES users(phone)
);

CREATE TABLE invoices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  participant_phone TEXT NOT NULL,
  week_start TEXT NOT NULL,        -- ISO date of Monday
  tier TEXT NOT NULL,
  value_stack_cents INTEGER NOT NULL,  -- e.g. 53000 for shared = $530
  floor_cents INTEGER NOT NULL,         -- 5000/7500/10000
  trust_curve_pct INTEGER NOT NULL,     -- 50/75/100
  p1 TEXT NOT NULL,
  p2 TEXT NOT NULL,
  p3 TEXT NOT NULL,
  issued_at TEXT NOT NULL,
  sealed INTEGER NOT NULL DEFAULT 0,
  final_due_cents INTEGER,              -- populated at seal
  final_cora_earned INTEGER,            -- populated at seal
  final_honor_entry INTEGER             -- populated at seal
);

CREATE TABLE proofs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  invoice_id INTEGER NOT NULL,
  participant_phone TEXT NOT NULL,
  priority TEXT,                   -- 'p1' | 'p2' | 'p3' | 'hours' | 'content'
  content_text TEXT,
  media_path TEXT,                 -- /var/lib/zv-wallet/media/{id}.{ext}
  media_type TEXT,                 -- 'image' | 'video' | 'audio' | 'document'
  classification TEXT DEFAULT 'PRIVATE',  -- PRIVATE | COUNCIL-RESTRICTED | COUNCIL-OPEN | PUBLIC
  submitted_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'approved' | 'partial' | 'rejected'
  witness_decision_at TEXT,
  witness_phone TEXT,
  witness_note TEXT,
  cora_awarded INTEGER DEFAULT 0,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

CREATE TABLE cora_balances (
  phone TEXT PRIMARY KEY,
  balance INTEGER NOT NULL DEFAULT 0,    -- in cents/1-CORA-units
  lifetime_earned INTEGER NOT NULL DEFAULT 0,
  lifetime_spent INTEGER NOT NULL DEFAULT 0,
  honor_entries INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE TABLE cora_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phone TEXT NOT NULL,
  delta INTEGER NOT NULL,         -- positive = earn, negative = spend
  reason TEXT NOT NULL,           -- 'p1_complete' | 'invoice_pay' | 'redeem_coconut' etc.
  ref_id INTEGER,                 -- proof_id or redemption_id
  balance_after INTEGER NOT NULL,
  ts TEXT NOT NULL,
  classification TEXT DEFAULT 'PRIVATE'
);

CREATE TABLE redemptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  participant_phone TEXT NOT NULL,
  item TEXT NOT NULL,             -- 'coconut' | 'smoothie' | 'massage' | etc.
  cora_cost INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'requested',  -- 'requested' | 'fulfilled' | 'denied' | 'expired'
  requested_at TEXT NOT NULL,
  fulfilled_at TEXT,
  fulfilled_by TEXT
);

CREATE TABLE weekly_seals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  invoice_id INTEGER NOT NULL UNIQUE,
  participant_phone TEXT NOT NULL,
  hours_logged INTEGER DEFAULT 0,
  p1_status TEXT,
  p2_status TEXT,
  p3_status TEXT,
  proof_count INTEGER DEFAULT 0,
  hourly_offset_cents INTEGER DEFAULT 0,
  invoice_reduction_cents INTEGER DEFAULT 0,
  final_due_cents INTEGER NOT NULL,
  cora_earned_raw INTEGER DEFAULT 0,
  cora_capped INTEGER DEFAULT 0,
  honor_entries INTEGER DEFAULT 0,
  sealed_at TEXT NOT NULL,
  witness_phone TEXT NOT NULL,
  narrative TEXT,
  FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

CREATE TABLE wa_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  wa_message_id TEXT UNIQUE,
  from_phone TEXT NOT NULL,
  to_phone TEXT,
  direction TEXT NOT NULL,        -- 'in' | 'out'
  message_type TEXT NOT NULL,     -- 'text' | 'image' | 'audio' | 'video' | 'document'
  body TEXT,
  media_path TEXT,
  raw_payload TEXT,               -- full Evolution webhook payload (JSON)
  ts TEXT NOT NULL,
  processed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL,            -- phone or 'system' or 'admin'
  action TEXT NOT NULL,
  target TEXT,
  detail TEXT,
  ts TEXT NOT NULL
);

CREATE INDEX idx_proofs_invoice ON proofs(invoice_id);
CREATE INDEX idx_proofs_status ON proofs(status, witness_phone);
CREATE INDEX idx_wa_messages_from ON wa_messages(from_phone, ts);
CREATE INDEX idx_cora_ledger_phone ON cora_ledger(phone, ts);
CREATE INDEX idx_invoices_participant ON invoices(participant_phone, week_start);
```

## Value-Stack mechanics (encoded from v4.0 agreement)

```python
TIER_VALUES = {
  "private":  {"value_stack": 60000, "floor": 10000},  # $600 / $100
  "shared":   {"value_stack": 53000, "floor":  7500},  # $530 / $75
  "communal": {"value_stack": 44000, "floor":  5000},  # $440 / $50
}

TRUST_CURVE = {1: 50, 2: 75}  # default 100 for week 3+

CORA_BONUSES = {
  "p1": 100, "p2": 75, "p3": 50,
}

OVERAGE_HOUR_CORA = 25
HOURLY_CREDIT_CENTS = 2500  # $25/hour
WEEKLY_CORA_CAP = 250

REDEMPTIONS = {
  "coconut":    {"cost": 5,   "daily_cap": 1},
  "smoothie":   {"cost": 10,  "daily_cap": 1},
  "juice":      {"cost": 10,  "daily_cap": 1},
  "massage":    {"cost": 100, "monthly_cap": 2},
  "stay_night": {"cost": 75,  "yearly_cap": 7},
  "sparking":   {"cost": 150, "quarterly_cap": 1},
}
```

## Phoenix Protocol — WhatsApp transport resilience

1. Every inbound WA message logs to `wa_messages` table BEFORE processing — never lose a message.
2. All media downloaded to `/var/lib/zv-wallet/media/` and backed up daily.
3. Witness commands ALSO available via PWA dashboard (no WA dependency for approvals).
4. If WhatsApp number banned:
   - Run `POST /admin/rotate` (marks current pairing inactive)
   - Restart Evolution API with new instance + QR pair
   - Bot DMs all active users on new number via... well, can't DM if banned. So:
   - **Phoenix recovery channel:** Telegram broadcast to opt-in users + dashboard banner with new WA number + manual re-onboarding via QR.
5. Rotation runbook at `~/.config/fpai/runbooks/zv_wallet_whatsapp_rotation.md`
6. Goal: <1 hour rotation.

## Integration with substrate

- **Privacy Narrator:** every inbound proof tagged `classification='PRIVATE'` by default. Promotion to PUBLIC requires explicit witness flag + Privacy Narrator audit.
- **The Publisher:** never auto-publishes proof. Only honor-roster entries (sanitized) get staged for publish.
- **sunheart-brain:** Sunday Seal narrative posted to brain as `concept:weekly_seal:{phone}:{week}` for cross-session continuity (Phase B+, not v0.1).
- **fpai-alerts:** any RED-flag event (banned WA · witness queue >20 · floor breach attempt) pushes to James's Telegram.

## Deploy

```bash
cd SERVICES/zv-wallet
./deploy.sh   # writes to /opt/zv-wallet, systemctl enable + start
```

Service: `zv-wallet.service` on port 8774 (matching the apprentice-gateway pattern).

## Reversibility

- `systemctl stop zv-wallet zv-evolution-api` — kills both
- DB at `/var/lib/zv-wallet/zv-wallet.db` — backup before reset
- Evolution instance: delete via Evolution Manager UI
- nginx routes removable

## Peer-to-Peer Transfers (v4.1)

Per agreement v4.1, the wallet supports member-to-member CORA transfers at v0.1.

**Capabilities:**
- WhatsApp: `transfer @user 500 [memo]` — wallet-to-wallet move; both parties confirmed.
- WhatsApp: `history` — last 10 personal transactions (in + out).
- PWA dashboard: full history with filters (date · counterparty · amount).
- Stewards: read-only view of all transfers via `/wallet/transfers/all` (admin-gated).
- Large transfers (≥500 CORA): auto-emit visibility notification to steward channel + append to `~/.config/fpai/zv_wallet/large_transfer_audit.log`. NOT approval-gated.

**Endpoints:**
```
POST /wallet/transfer                         {from_phone, to_phone, amount, memo}
GET  /wallet/history/{phone}?limit=10         Personal history
GET  /wallet/transfers/all                    Steward read-only (admin)
GET  /wallet/governance                       Disclosure: locks, threshold, disclaimer
POST /exchange/{connect,withdraw,deposit}     Returns 403 — by design
POST /wallet/cash/{buy,sell}                  Returns 403 — by design
```

**Hard locks (governance-protected · CORA Nation vote required to change):**
1. NO automated trading. API explicitly REJECTS any third-party exchange integration. Documented in `/wallet/governance`.
2. NO ZV-side exchange. Wallet does NOT support buying/selling CORA at any cash rate. Peer-to-peer only.
3. Future change to transfer rules requires CORA Nation governance approval (not Ember/Forge unilateral).

**DB additions (table `p2p_transfers`):**
```sql
CREATE TABLE p2p_transfers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_phone TEXT NOT NULL,
  to_phone TEXT NOT NULL,
  amount INTEGER NOT NULL,
  memo TEXT,
  ts TEXT NOT NULL,
  large_flag INTEGER NOT NULL DEFAULT 0,
  steward_notified INTEGER NOT NULL DEFAULT 0
);
```

Every transfer also mirrors into `cora_ledger` for unified history.

## Group Observer v0.1 (added 2026-05-20)

Extends the existing DM-only wallet with passive observation of a single
WhatsApp **group chat** ("Zen Village Work Credits"). Volunteers post
work-of-proof claims (text + photo); a Claude Haiku 4.5 parser classifies them;
a witness approves via WhatsApp reaction (✅) and the volunteer's WC balance
is updated.

### Architecture

```
Volunteer posts in group  -> Evolution webhook ->
  main.handle_inbound (detects @g.us)         ->
  group_observer.process_message              ->
    1. persist raw to group_messages          (Phoenix · raw-first)
    2. Haiku parse (text + vision if image)
    3. if work_claim & conf>0.7:
         insert work_credit_pending(status=pending)
         bot reply: "🪙 Pending: 50 WC for 2hr cleaning · react ✅"
    4. wait for messages.reaction event
       witness ✅ -> approved · WC credited · ticker push
       witness ❌ -> rejected · ledger updated · audit log
```

### Webhook event routing

| Event | Routed to |
|---|---|
| `messages.upsert` with `remoteJid` ending `@g.us` | `group_observer.process_message` |
| `messages.upsert` with `remoteJid` ending `@s.whatsapp.net` | existing DM wallet handler (unchanged) |
| `messages.reaction` | `group_observer.process_reaction` |
| `connection.update`, `qrcode.updated` | audit log only |

### Witness approval state machine

```
[group msg]               [bot reply: pending]              [witness reacts]
                                  |
                                  +-- ✅  -> APPROVED  -> credit + ticker
                                  +-- ❌  -> REJECTED  -> log + reason
                                  +-- (nothing)        -> stays pending
```

Confidence < 0.7 → bot asks for clarification, no row inserted.
Confidence ≥ 0.7 but hours_claimed=null → bot asks for hours.

### Manual override

```
!credit @alice 2hr deep-clean of kitchen
```

Witness-only. Bypasses Haiku parser. Inserts a pending row with
`evidence_type='override'`, immediately auto-approved (since the witness is
the source). Same audit + ticker push.

### Schema additions (additive · no existing table changed)

```sql
group_messages       -- raw audit log of every group msg · COUNCIL-RESTRICTED
work_credit_pending  -- pending | approved | rejected attribution
member_roles         -- jid -> role (volunteer | member | steward | witness)
```

WC balance derivation: if v0.2 `work_credits_balances` table exists, written
through. Otherwise computed from `SUM(wc_amount) WHERE status='approved'`.

### Public leaderboard PWA

- Mounted at `fullpotential.com/leaderboard/` (served by FastAPI;
  nginx passthrough on port 8774).
- Polls `GET /api/leaderboard?week=current` every 10s.
- Returns aggregated stats only:
  - Top 10 villagers (display name + WC total + activity count)
  - Last 10 approved tickers (actor + activity + hours + WC + witness)
  - Total WC issued this week
  - Pending count awaiting witness
- **Privacy: PUBLIC tier.** No raw messages, no JIDs, no media URLs. Names
  shown only if `actor_display_name` was set by the bot's `pushName` capture;
  otherwise jids are masked (`12***45`).

### Privacy tiers (Group Observer)

| Surface | Classification |
|---|---|
| `group_messages` table contents | COUNCIL-RESTRICTED |
| `work_credit_pending.parser_extracted_json` | COUNCIL-RESTRICTED |
| Bot replies inside the group | COUNCIL-OPEN (visible to all group members) |
| `/api/leaderboard` aggregates | PUBLIC |
| Audit log entries | COUNCIL-RESTRICTED |

### Cost (Phoenix-disciplined)

- Haiku 4.5 calls: ~$0.001 per group message at expected volume.
- 500 group msgs/wk = ~$0.50/wk. Well under the $5 budget.
- API key from `/etc/fp-game-bot/fp-game-bot.env` (`ANTHROPIC_API_KEY`).
  Phoenix runbook: if Anthropic key revoked, raw messages still queue
  (parsed=0) and replay when key rotated.

### Phoenix recovery procedure

If WhatsApp number is banned OR Anthropic API revokes the key:

```bash
# 1. Confirm raw log integrity
sqlite3 /var/lib/zv-wallet/zv-wallet.db \
  "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM group_messages;"

# 2. Approved balances are intact (sum over work_credit_pending)
sqlite3 /var/lib/zv-wallet/zv-wallet.db \
  "SELECT actor_display_name, SUM(wc_amount)
   FROM work_credit_pending WHERE status='approved'
   GROUP BY actor_jid ORDER BY 2 DESC;"

# 3. After re-pairing (new WA number) or key rotation:
#    Restart zv-wallet.service · re-pair members via QR scan ·
#    background worker (TODO) replays unparsed group_messages

# 4. Recovery target: <1 hour (raw log + balances persisted; only the
#    real-time approval loop pauses).
```

Group observer never trusts WhatsApp to be storage. Bans = transport
rotation, not data loss.

### Onboarding sequence (James-side, ~3 minutes)

1. **Pair the bot's WhatsApp number** — visit `https://fullpotential.com/wallet/`
   admin path or POST `/wa/qr` with `X-Admin-Token` and scan the QR.
2. **Add the bot to a new group "Zen Village Work Credits"** — invite the
   bot's number; group_jid auto-discovered on first inbound.
3. **Whitelist the group** — set `ZV_GROUP_JIDS=<jid>@g.us` in
   `/etc/zv-wallet.env` (or leave unset for open observation).
4. **Seed James as witness** — set `ZV_JAMES_JID=<digits>@s.whatsapp.net` in
   env before first start, OR insert manually:
   ```sql
   INSERT INTO member_roles(jid, display_name, role)
   VALUES ('<digits>@s.whatsapp.net', 'James', 'witness');
   ```
5. **First volunteer posts proof** — e.g. "Just cleaned the dish station,
   30 min" with a photo.
6. **James reacts ✅** — bot credits 12.5 → 13 WC (rounded), updates the
   public leaderboard.

### Environment variables added

| Var | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | (none) | Haiku 4.5 calls |
| `HAIKU_MODEL` | `claude-haiku-4-5-20251001` | model override |
| `ZV_GROUP_JIDS` | (empty = all) | comma-sep allowed group jids |
| `ZV_PARSER_CONFIDENCE` | `0.7` | pending threshold |
| `ZV_JAMES_JID` | (none) | seed James as witness at init |

### Open ambiguities (v0.1 → v0.2 todo)

- Witness discovery: only James seeded; first time a candidate appears,
  steward must `INSERT INTO member_roles` manually. Phase B: `/promote @user
  witness` DM command from existing witness.
- Display-name resolution: relies on Evolution's `pushName`; if absent, JIDs
  are masked on the public leaderboard.
- Background retry worker for parser failures is stub-only in v0.1
  (raw row persists with `parsed=0`; a future cron walks them).
- Week boundary: rolling 7-day for v0.1. v0.2 will align to Monday→Sunday CR
  time matching the wallet's existing weekly cycle.

## v0.1 explicit non-goals (DO NOT BUILD YET)

- Cross-node Coherent Credits transfer (single node only)
- Cash payment integration (Stripe optional Phase B)
- Multi-language (English/Spanish only English in v0.1)
- Push notifications beyond WA (TG via Phoenix only)
- Real-time presence (PWA polls every 30s in v0.1)
- AI auto-classification of proof (Privacy Narrator is offline review)
- Voice transcription (audio proofs stored raw, witness reviews)
