-- ZV Wallet v0.1 -> v8 Schema Migration (PENDING — not applied)
--
-- NOTE: Originally drafted as v6 migration; v8 addendum at bottom of file
-- captures the v6 → v8 deltas (tier enum shrinks 3→2 · floor concept retired
-- · members.tier_assigned_by + members.weeks_at_zv + transactions.
-- bonus_award_type added · 'communal' tier members migrated to 'shared').
--
-- This migration introduces the dual-ledger architecture per v8 agreement:
--   * Zen Village Work Credits (ZWC) — labor ledger, per-node, closed-loop,
--     $20/hr, hard weekly cap of 20 hrs / $400. Internal table/column names
--     kept as `work_credits_*` to minimize diff churn; UI surfaces "ZWC".
--   * CORA Credits — merit ledger, ecosystem-wide, open
--
-- v6 changes vs the prior v0.2 draft of this file:
--   * Rate $25/hr -> $20/hr (application-layer constant; no DB change)
--   * Weekly cap added (application-layer enforcement in
--     `app.group_observer._week_to_date_wc`; no DB CHECK constraint because
--     witness preapproval can lift the cap at the steward's discretion and
--     a hard CHECK would block that path).
--   * Cross-conversion dilution 1:1 -> 0.75 (application-layer in
--     `app.mechanics.convert_wc_to_cora` / `convert_cora_to_wc`).
--   * Conversion-event table records the post-dilution `amount` field
--     plus a new `rate` column so audit can reproduce the math.
--   * Floor-payment eligibility (`approved_volunteer` flag) unchanged.
--
-- Status: DRAFT — do NOT execute against production. The v0.1 schema (CORA-only)
-- continues running until v4.2 docs are signed by James and the migration
-- script is rehearsed against a snapshot.
--
-- Apply order:
--   1. Snapshot prod DB.
--   2. BEGIN TRANSACTION; run statements below; verify counts; COMMIT.
--   3. Update mechanics.compute_seal callers in commands.py to pass the new
--      `extra_wc_applied` parameter.
--   4. Update dashboard PWA to show two-balance display.
--
-- ---------------------------------------------------------------------------
-- 1. Add WC balance column to users-equivalent table.
--    NOTE: in v0.1 schema, balances live in a dedicated `cora_balances` table
--    rather than on `users`. We add a parallel `work_credits_balances` table
--    so the WC ledger is a sibling structure, mirroring CORA exactly.

CREATE TABLE IF NOT EXISTS work_credits_balances (
  phone            TEXT PRIMARY KEY,
  balance          INTEGER NOT NULL DEFAULT 0,
  lifetime_earned  INTEGER NOT NULL DEFAULT 0,
  lifetime_spent   INTEGER NOT NULL DEFAULT 0,
  lifetime_to_cora INTEGER NOT NULL DEFAULT 0,  -- WC converted out to CORA
  lifetime_from_cora INTEGER NOT NULL DEFAULT 0, -- CORA converted in (approved-vol gate)
  updated_at       TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- 2. WC ledger (mirrors cora_ledger).

CREATE TABLE IF NOT EXISTS work_credits_ledger (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  phone          TEXT NOT NULL,
  delta          INTEGER NOT NULL,            -- +earn / -spend / +/- convert
  reason         TEXT NOT NULL,               -- 'hours_sealed' | 'invoice_offset' | 'convert_from_cora' | 'convert_to_cora' | 'forfeit_on_exit'
  ref_id         INTEGER,                     -- FK to invoice / seal / conversion record
  balance_after  INTEGER NOT NULL,
  ts             TEXT NOT NULL,
  classification TEXT DEFAULT 'PRIVATE'
);

CREATE INDEX IF NOT EXISTS idx_wc_ledger_phone ON work_credits_ledger(phone, ts);

-- ---------------------------------------------------------------------------
-- 3. Tag existing transactions with currency_type for unified queries.
--    cora_ledger is the existing v0.1 ledger; we backfill its currency_type.

ALTER TABLE cora_ledger ADD COLUMN currency_type TEXT NOT NULL DEFAULT 'CORA'
  CHECK (currency_type IN ('WC', 'CORA'));

-- (work_credits_ledger does not need this column; type is implicit by table.)

-- ---------------------------------------------------------------------------
-- 4. Conversion-event audit table (records cross-bridge swaps).

CREATE TABLE IF NOT EXISTS currency_conversions (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  phone            TEXT NOT NULL,
  direction        TEXT NOT NULL CHECK (direction IN ('wc_to_cora', 'cora_to_wc')),
  amount_in        INTEGER NOT NULL,          -- units of source currency consumed
  amount_out       INTEGER NOT NULL,          -- units of target currency credited (after dilution)
  rate             REAL NOT NULL DEFAULT 0.75, -- v6 dilution rate (1 unit src -> rate units tgt)
  gate_satisfied   INTEGER NOT NULL,          -- 1 if approved (logged either way for audit)
  gate_reason      TEXT,                      -- which gate was checked
  approved_by      TEXT,                      -- witness or steward phone
  ts               TEXT NOT NULL,
  wc_ledger_id     INTEGER,                   -- FK to work_credits_ledger entry
  cora_ledger_id   INTEGER                    -- FK to cora_ledger entry
);

CREATE INDEX IF NOT EXISTS idx_conv_phone ON currency_conversions(phone, ts);

-- ---------------------------------------------------------------------------
-- 5. Augment weekly_seals to record WC accounting explicitly.

ALTER TABLE weekly_seals ADD COLUMN wc_earned INTEGER DEFAULT 0;
ALTER TABLE weekly_seals ADD COLUMN wc_applied INTEGER DEFAULT 0;
ALTER TABLE weekly_seals ADD COLUMN wc_carried_forward INTEGER DEFAULT 0;
ALTER TABLE weekly_seals ADD COLUMN extra_wc_from_cora_conversion INTEGER DEFAULT 0;

-- ---------------------------------------------------------------------------
-- 6. Augment users with approved-volunteer flag (required for CORA->WC gate).
--    Defaults TRUE for all existing rows (assumed approved under v0.1; review
--    operationally and flip any guest accounts to FALSE before opening CORA
--    purchase to non-volunteers).

ALTER TABLE users ADD COLUMN approved_volunteer INTEGER NOT NULL DEFAULT 1;

-- ---------------------------------------------------------------------------
-- 7. Backfill: existing CORA balances stay where they are. WC balances start
--    at 0 (we did not separately track hours-vs-priorities before — v0.1
--    bundled everything in CORA, so historical WC is irrecoverable).
--
--    Operational note: communicate to current volunteers that WC starts fresh
--    on v4.2 cutover; existing CORA balances are preserved.

INSERT OR IGNORE INTO work_credits_balances (phone, balance, lifetime_earned, lifetime_spent, updated_at)
SELECT phone, 0, 0, 0, datetime('now') FROM cora_balances;

-- ---------------------------------------------------------------------------
-- End of pending migration. Verify with:
--   SELECT COUNT(*) FROM work_credits_balances;       -- should match users count
--   SELECT COUNT(*) FROM work_credits_ledger;          -- should be 0 at cutover
--   SELECT DISTINCT currency_type FROM cora_ledger;    -- should return only 'CORA'

-- ===========================================================================
-- v6 ADDENDUM (May 20 2026) — application-layer enforcements
-- ===========================================================================
-- The following v6 rules are enforced in the Python application layer rather
-- than at the DB level. Reasons:
--   * The weekly $400 cap can be lifted by steward preapproval (rare event,
--     not common-path) — a hard SQL CHECK would block that legitimate path.
--   * The 0.75 dilution math is best kept as a single constant in
--     `app.mechanics` (WC_TO_CORA_DILUTION / CORA_TO_WC_DILUTION) so it
--     stays consistent across reads, writes, and UI display.
--   * The floor-rule (cash/ZWC only) is enforced at the commands.py /
--     invoice-settlement boundary, not at row-insert time.
--
-- Application-layer reference points:
--   * mechanics.WC_RATE_PER_HOUR         = 20    (was 25)
--   * mechanics.WC_WEEKLY_CAP_HOURS      = 20
--   * mechanics.WC_WEEKLY_CAP_AMOUNT     = 400
--   * mechanics.WC_TO_CORA_DILUTION      = 0.75
--   * mechanics.CORA_TO_WC_DILUTION      = 0.75
--   * mechanics.can_pay_floor(currency)  — gate for floor settlement
--   * group_observer._week_to_date_wc()  — caps witness approvals to $400/wk
--
-- Future schema work (deferred):
--   * Camp Zen track flag on users: ENUM('guest','supporter','partial_vol','venture_donor')
--     — currently inferred from approved_volunteer + member_roles + transaction history.
--   * House-wide good standing audit table (currently flows through cora_ledger
--     with reason='house_standing').
--   * Personal car use bookings (currently out-of-band; CORA charge logged
--     with reason='car_self_drive' or 'car_steward_driven').

-- ===========================================================================
-- v8 ADDENDUM (May 20 2026) — tier collapse + ZV-assigned tier + bonus form
-- ===========================================================================
-- v6 → v8 deltas:
--   1. Tiers: 3 -> 2. Drop 'communal' ($440). Shared/Glamping is one tier at
--      $400 (was $530). Private stays at $600.
--   2. Floor concept retired — application-layer `has_explicit_floor()`
--      returns False in v8. The data shape keeps floor=0 for back-compat.
--      Gap coverage is now flexible (cash OR CORA OR discretionary ZV bonus).
--   3. Tier assignment: ZV-assigned, not volunteer-chosen. New column
--      `members.tier_assigned_by` (steward name or 'system') is added so
--      provenance is auditable.
--   4. Weeks at ZV: tracked explicitly for Trust Curve calc (v8 §9).
--   5. Bonus form: witness/ZV elects ZWC bonus OR CORA bonus at Sunday Seal.
--      New `transactions.bonus_award_type` captures the chosen form.
--
-- The DDL below is DRAFT — do NOT execute yet. Live wallet stays on v6
-- schema until the snapshot + rehearsal happens. v0.1 production has no
-- live users yet so live impact is minimal, but we still gate behind a
-- separate apply-the-migration dispatch.
--
-- ---------------------------------------------------------------------------
-- v8-1. Tier enum collapse — migrate any 'communal' rows to 'shared' first,
--       then add CHECK constraint excluding 'communal'.
-- ---------------------------------------------------------------------------

-- Migrate existing communal-tier users to shared (preserve audit trail in
-- the notes column). v0.1 schema stores tier on `users.tier` not `members`,
-- so the rename "members" here is forward-looking — adapt to actual table
-- name at apply-time.
UPDATE users
   SET tier = 'shared',
       notes = COALESCE(notes, '') || ' [v8-migration: communal -> shared]'
 WHERE tier = 'communal';

-- SQLite cannot ALTER COLUMN to add CHECK directly; the apply-time script
-- should re-create the users table with the new CHECK or use a trigger.
-- Sketched as a trigger here so we don't break running v0.1:
DROP TRIGGER IF EXISTS users_tier_v8_check;
CREATE TRIGGER users_tier_v8_check
BEFORE INSERT ON users
WHEN NEW.tier IS NOT NULL AND NEW.tier NOT IN ('private', 'shared')
BEGIN
  SELECT RAISE(ABORT, 'v8: tier must be private or shared (communal removed)');
END;
-- Mirror for UPDATE:
DROP TRIGGER IF EXISTS users_tier_v8_check_update;
CREATE TRIGGER users_tier_v8_check_update
BEFORE UPDATE OF tier ON users
WHEN NEW.tier IS NOT NULL AND NEW.tier NOT IN ('private', 'shared')
BEGIN
  SELECT RAISE(ABORT, 'v8: tier must be private or shared (communal removed)');
END;

-- ---------------------------------------------------------------------------
-- v8-2. Tier provenance + weeks-at-ZV columns
-- ---------------------------------------------------------------------------

-- Who assigned this tier (steward name or 'system'). Defaults NULL for
-- pre-v8 rows; backfill operationally as stewards confirm assignments.
ALTER TABLE users ADD COLUMN tier_assigned_by TEXT;

-- Weeks at ZV — for Trust Curve calc. Defaults 0; backfill from
-- onboarded_at when convenient.
ALTER TABLE users ADD COLUMN weeks_at_zv INTEGER NOT NULL DEFAULT 0;

-- ---------------------------------------------------------------------------
-- v8-3. Bonus award type — which form did the discretionary bonus take?
-- ---------------------------------------------------------------------------

-- v0.1 has no `transactions` table; in this codebase the analog is
-- cora_ledger + work_credits_ledger. The bonus_award_type column lives on
-- whichever ledger received the bonus, so we add it to both for symmetry.
-- (Apply-time script may consolidate.)

ALTER TABLE cora_ledger ADD COLUMN bonus_award_type TEXT
  CHECK (bonus_award_type IS NULL OR bonus_award_type IN ('zwc', 'cora'));

-- For work_credits_ledger (created in §2 above):
-- ALTER TABLE work_credits_ledger ADD COLUMN bonus_award_type TEXT
--   CHECK (bonus_award_type IS NULL OR bonus_award_type IN ('zwc', 'cora'));
-- (Already-applied? guard with a SELECT FROM pragma_table_info at apply-time.)

-- ---------------------------------------------------------------------------
-- v8-4. Verification queries (run after BEGIN/COMMIT block)
-- ---------------------------------------------------------------------------
--   SELECT COUNT(*) FROM users WHERE tier = 'communal';
--     -> should be 0
--   SELECT tier, COUNT(*) FROM users GROUP BY tier;
--     -> should show only 'private' and 'shared' (and NULL for guests)
--   SELECT name FROM sqlite_master WHERE type='trigger'
--     AND name IN ('users_tier_v8_check', 'users_tier_v8_check_update');
--     -> should return both triggers
--   PRAGMA table_info(users);
--     -> should include tier_assigned_by, weeks_at_zv
--   PRAGMA table_info(cora_ledger);
--     -> should include bonus_award_type
--
-- Application-layer reference points (v8):
--   * mechanics.TIER_VALUES.keys() == {'private', 'shared'}
--   * mechanics.has_explicit_floor(tier) -> False (always, v8)
--   * mechanics.BUNDLED_DISCOUNT == 8500   ($85/wk shown to volunteers)
--   * mechanics.RETAIL_SUBTOTAL_SHARED == 48500  ($485/wk retail)
--   * mechanics.RETAIL_SUBTOTAL_PRIVATE == 68500 ($685/wk retail)
--   * mechanics.award_bonus(actor, week, form, amount, reason) — witness
--     elects 'zwc' or 'cora' form at Sunday Seal.
--   * mechanics.compute_seal(..., zwc_bonus_awarded=N) — passes the ZWC
--     bonus form through to invoice settlement.
