"""v8 ZV Value-Exchange Agreement mechanics — Dual-Ledger Architecture.

Two currencies, cleanly separated:
  * Zen Village Work Credits (ZWC) — hourly labor, invoice settlement only,
    approved-volunteer only. Internal storage names kept as `work_credits` /
    `wc_*` to minimize diff churn; user-facing label is "ZWC".
  * CORA Credits — merit/performance/content, open ecosystem, anyone.

Aligned to v8 specs 2026-05-20 (supersedes v6).

v6 → v8 changes (this canonical):
  * Tiers: 3 -> 2. The "communal" tier ($440) is REMOVED. Shared/Glamping
    becomes a single tier at $400 (was $530). Private remains $600.
  * Explicit per-tier "floor" is gone — gap coverage is now cash OR CORA OR
    discretionary ZWC bonus from ZV at Sunday Seal. We retain `floor=0` in
    the data shape for backward-compat; calling code that asks about floor
    should call `has_explicit_floor()` instead.
  * Tier assignment: ASSIGNED BY ZV, not volunteer-chosen. The data model
    gains `tier_assigned_by` (steward name or 'system') — see DB migration.
  * Meals included: 2 daily (breakfast + lunch · sometimes carries to
    dinner). Reflected in the bundled retail value table.
  * Bundled retail value is surfaced explicitly: $485/wk Shared, $685/wk
    Private — showing the $85/wk bundled discount built into the price.
  * Bonus form: at Sunday Seal, witness/ZV picks ONE form per award —
    ZWC bonus (closes invoice gap · typical for Private Room) OR CORA bonus
    (premium · typical for Shared). New `award_bonus()` helper makes the
    bookkeeping explicit.

Unchanged through v8 (carried forward from v6):
  * Hourly rate: $20/hr ZWC
  * Hard weekly cap: 20 hrs × $20 = $400 ZWC max per week
  * Cross-conversion dilution: 0.75 in BOTH directions
  * Service-to-paying-guest split: 70/15/5
  * Sauna add-on: 8 CORA / 2-wk
  * House-wide good standing: 10-15 CORA per housemate
  * Trust curve: W1=50%, W2=75%, W3+=100% (now interpreted as % of value
    stack reducible by ZWC, since there is no explicit floor in v8)

Cross-conversion gates:
  * ZWC -> CORA: 1 ZWC = 0.75 CORA (dilution); requires WC surplus beyond
    current week's invoice need; volunteer status (only approved volunteers
    can hold ZWC at all)
  * CORA -> ZWC: 1 CORA = 0.75 ZWC (dilution); requires approved-volunteer
  * cash -> CORA: 1:1, anyone
  * cash -> ZWC: NEVER (protects work-for-value spirit)

All amounts in ZWC/CORA are integer units (1 unit = $1 of nominal value).
Invoice / floor / dollar amounts are stored as integer cents.

Source-of-truth docs:
  docs/zen-village/agreements/zv-value-exchange-quickstart.md (v8)
  docs/zen-village/agreements/zv-value-exchange-agreement-v8.md (v8)
"""
from __future__ import annotations

from typing import Literal

# v8: 2 tiers only — `communal` (was $440) is REMOVED. Shared = Shared/Glamping.
Tier = Literal["private", "shared"]

# v8: bundled membership price by tier; floor concept retired (kept as 0 for
# back-compat data shape — call `has_explicit_floor()` for new logic).
TIER_VALUES: dict[Tier, dict[str, int]] = {
    "private": {"value_stack": 60000, "floor": 0},  # $600/wk · floor retired
    "shared":  {"value_stack": 40000, "floor": 0},  # $400/wk · was $530 in v6
}

# v8: explicit bundled retail value (the "you save $X" reveal).
# Difference between retail subtotal and bundled membership price.
BUNDLED_DISCOUNT = 8500              # $85/wk · same for both tiers
RETAIL_SUBTOTAL_SHARED = 48500       # $485/wk retail · bundled at $400
RETAIL_SUBTOTAL_PRIVATE = 68500      # $685/wk retail · bundled at $600


def has_explicit_floor(tier: Tier) -> bool:
    """v8: the explicit floor concept is retired.

    In v6 each tier had a minimum cash-or-ZWC component ($50/$75/$100).
    In v8, gap-coverage is handled flexibly at Sunday Seal — witness/ZV
    decides whether to award a ZWC bonus (closing gap) or a CORA bonus
    (premium credit) per actor's week-context. The remainder, if any, is
    covered by cash OR CORA from the volunteer's wallet.
    """
    return False


# ---------------------------------------------------------------------------
# ZWC (Zen Village Work Credits) — labor ledger
# ---------------------------------------------------------------------------

WC_RATE_PER_HOUR = 20            # $20/hr (carried from v6)
WC_WEEKLY_CAP_HOURS = 20         # hard cap on credited hours/week
WC_WEEKLY_CAP_AMOUNT = 400       # 20 hrs × $20 = $400 ZWC max/week

# Back-compat aliases (deprecated · kept so legacy callers / tests don't break)
WC_PER_HOUR = WC_RATE_PER_HOUR
HOURLY_CREDIT_CENTS = WC_RATE_PER_HOUR * 100

# ---------------------------------------------------------------------------
# Cross-conversion dilution (carried from v6)
# ---------------------------------------------------------------------------

WC_TO_CORA_DILUTION = 0.75       # 1 ZWC -> 0.75 CORA
CORA_TO_WC_DILUTION = 0.75       # 1 CORA -> 0.75 ZWC

# ---------------------------------------------------------------------------
# CORA earning tables (carried from v6 · unchanged in v8)
# ---------------------------------------------------------------------------

# Priority bonus table (CORA) — used in v6 worked examples; v8 keeps the
# concept but emphasizes witness/ZV discretion over fixed payouts.
CORA_PRIORITY_BONUSES = {"p1": 100, "p2": 75, "p3": 50}

# Content output bonus table (CORA per output) — unchanged through v8
CORA_CONTENT_BONUSES = {
    "show_reel":       200,
    "polished_video":  100,
    "podcast_episode": 150,
    "instagram_post":   10,
    "raw_footage_hr":   25,
    "short_clip":       40,
    "photo_essay":      50,
    "blog_post":        75,
}

# Excellence bonus bounds (carried from v6: bounded 25-100)
CORA_EXCELLENCE_MIN = 25
CORA_EXCELLENCE_MAX = 100

# House-wide good standing — per housemate, awarded at Sunday Seal
CORA_HOUSE_STANDING_MIN = 10
CORA_HOUSE_STANDING_MAX = 15

# Service to paying guest split (70/15/5 · carried from v6)
SERVICE_SPLIT_PROVIDER = 0.70
SERVICE_SPLIT_ZV       = 0.15
SERVICE_SPLIT_COMMUNITY = 0.05

# Weekly CORA earning cap from bonuses
WEEKLY_CORA_CAP = 250

# Future venture donation — earned when a guest's venture donates back
# to Community Fund; 1:1 with $ donated.
VENTURE_DONATION_CORA_PER_DOLLAR = 1.0

# Peer service redemption catalog (CORA-denominated) — v8 carries v6 calibration
# Split into hard-cost (real cash outflow) vs soft-cost (no outflow).
REDEMPTIONS_SOFT_COST: dict[str, dict] = {
    "sauna_session":   {"cost":   8, "cadence": "weekly",    "cap": 2},
    "stay_night":      {"cost":  75, "cadence": "yearly",    "cap": 7},
    "sparking":        {"cost": 150, "cadence": "quarterly", "cap": 1},
    "cohort_discount": {"cost": 400, "cadence": "per_cohort","cap": 1},
}

REDEMPTIONS_HARD_COST: dict[str, dict] = {
    "coconut":            {"cost":  5,  "cadence": "daily",   "cap": 1,
                           "weekly_cap": 7},
    "smoothie":           {"cost": 10,  "cadence": "daily",   "cap": 1},
    "juice":              {"cost": 10,  "cadence": "daily",   "cap": 1},
    "massage_external":   {"cost": 100, "cadence": "monthly", "cap": 2},
    "premium_food":       {"cost": None, "cadence": "weekly", "cap": 50,
                           "note": "varies; $50 worth/week max"},
    "car_self_drive":     {"cost_min":  8, "cost_max":  50,
                           "cadence": "weekly", "cap": 1},
    "car_steward_driven": {"cost_min": 12, "cost_max":  90,
                           "cadence": "weekly", "cap": 1},
    "thrift":             {"cost_min":  5, "cost_max":  30,
                           "cadence": "reasonable", "cap": None},
}

# Legacy flat catalog (kept for back-compat with v0.1/v0.2 callers)
REDEMPTIONS: dict[str, dict] = {
    **{k: v for k, v in REDEMPTIONS_HARD_COST.items() if "cost" in v},
    **REDEMPTIONS_SOFT_COST,
}


# ---------------------------------------------------------------------------
# Trust curve (unchanged from v6; v8 §9 Onboarding Curve)
# ---------------------------------------------------------------------------

def trust_curve_pct(week_number: int) -> int:
    """v8 §9: W1=50% W2=75% W3+=100%.

    Caps how much ZWC can be applied to the current week's invoice. Does NOT
    cap ZWC earning (you still earn ZWC for all approved hours up to the
    20-hr/$400 weekly cap) or CORA earning.
    """
    if week_number <= 1:
        return 50
    if week_number == 2:
        return 75
    return 100


def max_invoice_reduction_cents(tier: Tier, week_number: int) -> int:
    """Max ZWC-denominated amount applicable to invoice (capped by trust curve).

    v8: no explicit floor — the full value stack is reducible at week 3+.
    """
    tv = TIER_VALUES[tier]
    headroom = tv["value_stack"] - tv["floor"]  # floor=0 in v8 → full stack
    pct = trust_curve_pct(week_number)
    return int(headroom * pct / 100)


# ---------------------------------------------------------------------------
# Currency 1 — ZWC (Zen Village Work Credits), hour-based labor ledger
# ---------------------------------------------------------------------------

def compute_work_credits(
    hours_logged: int,
    overage_hours: int = 0,
    enforce_cap: bool = True,
) -> int:
    """Hour-based ZWC earning. Returns total ZWC earned this week.

    v8 §4: 1 approved hour = $20 ZWC, hard cap at 20 hrs/wk ($400 max).
    Hours beyond 20 do not earn additional ZWC; per v8, discretionary
    overage may be available at steward discretion for surge needs.

    `enforce_cap=False` is reserved for steward pre-approved overage events.
    When the steward has explicitly pre-approved overage hours, pass them as
    `overage_hours` AND set `enforce_cap=False`. Without that flag the cap
    is hard.
    """
    if hours_logged < 0 or overage_hours < 0:
        raise ValueError("hours cannot be negative")
    raw = (hours_logged + overage_hours) * WC_RATE_PER_HOUR
    if not enforce_cap:
        return raw
    capped = min(raw, WC_WEEKLY_CAP_AMOUNT)
    return capped


def compute_work_credits_with_clamp_info(
    hours_logged: int,
    overage_hours: int = 0,
    enforce_cap: bool = True,
) -> dict:
    """Same as compute_work_credits but returns clamp diagnostic info.

    Useful for the group_observer + UI so we can warn when a witness tries
    to approve hours beyond the cap. The cap is hard at the application
    layer per v8 §4 unless steward pre-approval is recorded out-of-band.
    """
    if hours_logged < 0 or overage_hours < 0:
        raise ValueError("hours cannot be negative")
    raw_amount = (hours_logged + overage_hours) * WC_RATE_PER_HOUR
    if enforce_cap and raw_amount > WC_WEEKLY_CAP_AMOUNT:
        return {
            "wc_earned": WC_WEEKLY_CAP_AMOUNT,
            "wc_raw": raw_amount,
            "clamped": True,
            "clamp_message": (
                f"hours exceed weekly cap · earned capped at "
                f"${WC_WEEKLY_CAP_AMOUNT} ZWC ({WC_WEEKLY_CAP_HOURS}hr × "
                f"${WC_RATE_PER_HOUR}/hr); overage hours help complete "
                f"priorities (CORA) but earn no additional ZWC"
            ),
        }
    return {
        "wc_earned": raw_amount,
        "wc_raw": raw_amount,
        "clamped": False,
        "clamp_message": None,
    }


# ---------------------------------------------------------------------------
# Floor-payment eligibility (v8: floor concept retired, but the helper stays
# as a back-compat shim for any caller asking the question).
# ---------------------------------------------------------------------------

def can_pay_floor(currency: str) -> bool:
    """v8: there is no explicit floor anymore — every dollar of the invoice
    can be covered by any mix of ZWC + ZV-discretion bonus + cash + CORA.

    The helper returns True for cash/ZWC (matching v6 semantics) for any
    legacy callers that still ask "can this pay floor?" — the answer is
    effectively "yes, any currency works above whatever ZWC covered" in v8.
    Kept False for CORA only because v6 callers used this to gate CORA-only
    floor payment; v8 still settles cash/ZWC first, then CORA, but the
    explicit-floor gate isn't a thing.
    """
    return currency.lower() in {"cash", "zwc", "wc", "work_credits"}


# ---------------------------------------------------------------------------
# v8 NEW: award_bonus — witness/ZV picks ZWC bonus OR CORA bonus at Sunday Seal
# ---------------------------------------------------------------------------

BonusForm = Literal["zwc", "cora"]


def award_bonus(
    actor_id: str,
    week_id: str,
    form: BonusForm,
    amount: int,
    reason: str,
    witness_id: str | None = None,
) -> dict:
    """v8 §4: at Sunday Seal, witness/ZV awards a discretionary bonus in one
    form per award — ZWC (to close invoice gap · typical Private Room) OR
    CORA (premium credit · typical Shared).

    Returns a structured transaction record. Persistence is the caller's
    responsibility (write to work_credits_ledger or cora_ledger based on
    `form`).

    Args:
        actor_id: phone / jid of the volunteer receiving the bonus
        week_id: which week this bonus is being sealed for (e.g. "2026-W21")
        form: "zwc" or "cora"
        amount: integer units (1 unit = $1 nominal)
        reason: free-text reason ("P1 delivered with strong proof", etc.)
        witness_id: optional witness/steward who approved the award

    Raises ValueError if form is not "zwc"/"cora" or amount is non-positive.
    """
    if form not in ("zwc", "cora"):
        raise ValueError(f"bonus form must be 'zwc' or 'cora', got: {form!r}")
    if amount <= 0:
        raise ValueError(f"bonus amount must be positive, got: {amount}")
    if not actor_id:
        raise ValueError("actor_id required")
    return {
        "actor_id":   actor_id,
        "week_id":    week_id,
        "form":       form,
        "amount":     amount,
        "reason":     reason,
        "witness_id": witness_id,
        # Caller writes this to the appropriate ledger:
        #   form='zwc'  -> work_credits_ledger (reason='bonus_zwc')
        #   form='cora' -> cora_ledger          (reason='bonus_cora')
        "target_ledger": "work_credits_ledger" if form == "zwc" else "cora_ledger",
    }


# ---------------------------------------------------------------------------
# Currency 2 — CORA Credits, output/merit ledger
# ---------------------------------------------------------------------------

def compute_cora_bonus(
    p1_status: str = "none",     # 'full' | 'partial' | 'none'
    p2_status: str = "none",
    p3_status: str = "none",
    content_outputs: dict[str, int] | None = None,
    tier_surplus_cora: int = 0,
    witness_excellence_cora: int = 0,
    peer_service_cora: int = 0,
    house_standing_cora: int = 0,
    venture_donation_dollars: float = 0,
) -> dict:
    """Output/merit-based CORA earning. Returns dict with raw, capped, honor entries.

    Per v8 §5 / §7 / §11:
      * Priority completion bonuses (full = 100/75/50, partial = half)
      * Content output bonuses (per CORA_CONTENT_BONUSES — count-multiplied)
      * Tier surplus (auto-converted when humbler tier than booked)
      * Witness-discretion excellence (bounded 25-100)
      * Peer-service-offered (negotiated, ZV records)
      * House-wide good standing (10-15 CORA per housemate)
      * Future venture donation (1:1 with $ donated)

    Cap at 250 CORA/week from bonuses. Above-cap amount becomes honor entries
    on the public roster.

    v8 note: priority delivery → CORA via this function represents the CORA
    side of the witness's Sunday-Seal decision. When the witness picks ZWC
    bonus instead (typical Private Room gap-close), call `award_bonus` with
    form='zwc' and skip the CORA bonus on that line.
    """
    content_outputs = content_outputs or {}

    # Priority bonuses
    priority_bonuses = 0
    for prio_key, status in (("p1", p1_status), ("p2", p2_status), ("p3", p3_status)):
        base = CORA_PRIORITY_BONUSES[prio_key]
        if status == "full":
            priority_bonuses += base
        elif status == "partial":
            priority_bonuses += base // 2

    # Content output bonuses (count × per-output rate)
    content_bonuses = 0
    for output_key, count in content_outputs.items():
        if output_key not in CORA_CONTENT_BONUSES:
            raise ValueError(f"unknown content output type: {output_key}")
        if count < 0:
            raise ValueError(f"negative count for {output_key}")
        content_bonuses += CORA_CONTENT_BONUSES[output_key] * count

    # Bound excellence to v8 range when nonzero
    excellence = witness_excellence_cora
    if excellence > 0:
        if excellence < CORA_EXCELLENCE_MIN:
            excellence = CORA_EXCELLENCE_MIN
        elif excellence > CORA_EXCELLENCE_MAX:
            excellence = CORA_EXCELLENCE_MAX

    # Future venture donation (1:1)
    venture_cora = int(round(venture_donation_dollars * VENTURE_DONATION_CORA_PER_DOLLAR))

    cora_raw = (
        priority_bonuses
        + content_bonuses
        + tier_surplus_cora
        + excellence
        + peer_service_cora
        + house_standing_cora
        + venture_cora
    )
    cora_earned = min(cora_raw, WEEKLY_CORA_CAP)
    honor_entries = max(cora_raw - WEEKLY_CORA_CAP, 0)

    return {
        "cora_priority_bonuses": priority_bonuses,
        "cora_content_bonuses":  content_bonuses,
        "cora_tier_surplus":     tier_surplus_cora,
        "cora_excellence":       excellence,
        "cora_peer_service":     peer_service_cora,
        "cora_house_standing":   house_standing_cora,
        "cora_venture_donation": venture_cora,
        "cora_raw":              cora_raw,
        "cora_earned":           cora_earned,
        "honor_entries":         honor_entries,
    }


# ---------------------------------------------------------------------------
# Service-to-paying-guest split (70/15/5 · carried from v6)
# ---------------------------------------------------------------------------

def compute_service_split(fee_dollars: float) -> dict:
    """v8 §10: paying-guest service fee splits 70% provider / 15% ZV / 5% Community.

    Note: 70 + 15 + 5 = 90; the remaining 10% covers payment processing,
    facilitation overhead, and rounding reserve at the ZV operator's
    discretion.
    """
    return {
        "provider":  round(fee_dollars * SERVICE_SPLIT_PROVIDER, 2),
        "zv":        round(fee_dollars * SERVICE_SPLIT_ZV, 2),
        "community": round(fee_dollars * SERVICE_SPLIT_COMMUNITY, 2),
        "residual":  round(
            fee_dollars * (1 - SERVICE_SPLIT_PROVIDER
                              - SERVICE_SPLIT_ZV
                              - SERVICE_SPLIT_COMMUNITY), 2),
    }


# ---------------------------------------------------------------------------
# Cross-conversion helpers — 0.75 dilution (carried from v6)
# ---------------------------------------------------------------------------

def convert_wc_to_cora(amount: int, has_surplus: bool) -> dict:
    """Convert ZWC -> CORA with 0.75 dilution. Gate: ZWC surplus beyond
    current week's invoice need.

    Returns {"ok": bool, "wc_out": int, "cora_in": int, "reason": str}.

    Dilution is intentional: the right earning path is more valuable than
    gaming the conversion. Right way to get CORA = perform excellently.
    """
    if amount <= 0:
        return {"ok": False, "wc_out": 0, "cora_in": 0,
                "reason": "amount must be positive"}
    if not has_surplus:
        return {"ok": False, "wc_out": 0, "cora_in": 0,
                "reason": "no ZWC surplus beyond current week's invoice need"}
    cora_in = int(amount * WC_TO_CORA_DILUTION)  # floor to integer CORA
    return {
        "ok":      True,
        "wc_out":  amount,
        "cora_in": cora_in,
        "rate":    WC_TO_CORA_DILUTION,
        "reason":  "ok",
    }


def convert_cora_to_wc(amount: int, is_approved_volunteer: bool) -> dict:
    """Convert CORA -> ZWC with 0.75 dilution. Gate: must be approved volunteer.

    Returns {"ok": bool, "cora_out": int, "wc_in": int, "reason": str}.

    The CORA->ZWC gate is the architectural genius: paying guests and
    supporters can earn/hold/spend CORA but cannot convert it to invoice
    settlement, preserving the volunteer-system character.
    """
    if amount <= 0:
        return {"ok": False, "cora_out": 0, "wc_in": 0,
                "reason": "amount must be positive"}
    if not is_approved_volunteer:
        return {"ok": False, "cora_out": 0, "wc_in": 0,
                "reason": "CORA->ZWC conversion requires approved-volunteer status"}
    wc_in = int(amount * CORA_TO_WC_DILUTION)  # floor to integer ZWC
    return {
        "ok":       True,
        "cora_out": amount,
        "wc_in":    wc_in,
        "rate":     CORA_TO_WC_DILUTION,
        "reason":   "ok",
    }


# ---------------------------------------------------------------------------
# Sealed-week record (v8 dual-ledger)
# ---------------------------------------------------------------------------

def compute_seal(
    tier: Tier,
    week_number: int,
    hours_logged: int,
    p1_status: str,    # 'full' | 'partial' | 'none'
    p2_status: str,
    p3_status: str,
    overage_hours: int = 0,
    witness_excellence_cora: int = 0,
    tier_surplus_cora: int = 0,
    content_outputs: dict[str, int] | None = None,
    peer_service_cora: int = 0,
    house_standing_cora: int = 0,
    venture_donation_dollars: float = 0,
    extra_wc_applied: int = 0,   # ZWC drawn from prior balance / cora_to_wc conversion
    steward_preapproved_overage: bool = False,
    zwc_bonus_awarded: int = 0,  # v8 NEW: explicit ZWC bonus from witness (closes gap)
) -> dict:
    """Returns the sealed week record per v8 §4 dual-ledger formula.

    ZWC ledger:
        zwc_earned         = min((hours_logged + overage_hours) × 20, 400)
                             unless steward_preapproved_overage=True
        zwc_pool           = zwc_earned + extra_wc_applied + zwc_bonus_awarded
        max_invoice_offset = value_stack × trust_curve_pct  (no floor in v8)
        zwc_applied        = MIN(zwc_pool, max_invoice_offset)
        final_due_cents    = value_stack_cents − zwc_applied × 100 (floored at 0)

    CORA ledger:
        cora_raw = priority + content + tier_surplus + excellence +
                   peer_service + house_standing + venture_donation
        cora_earned   = MIN(cora_raw, 250)
        honor_entries = MAX(cora_raw − 250, 0)

    v8 NEW: `zwc_bonus_awarded` is the discretionary ZWC bonus witness/ZV
    decides to grant at Sunday Seal (typical for Private Room: e.g. $200 to
    close the gap). It adds to the ZWC pool BEFORE invoice application.
    When the witness opts for a CORA bonus instead, set `zwc_bonus_awarded=0`
    and pass the CORA amount through `witness_excellence_cora` or
    `peer_service_cora`.

    Backward-compat fields (`invoice_reduction_cents`, etc.) are emitted so
    v0.1 / v0.2 callers continue to work while the wallet migrates.
    """
    tv = TIER_VALUES[tier]
    value_stack_cents = tv["value_stack"]
    floor_cents = tv["floor"]   # v8: 0

    # --- ZWC side ---
    wc_info = compute_work_credits_with_clamp_info(
        hours_logged, overage_hours,
        enforce_cap=not steward_preapproved_overage,
    )
    wc_earned = wc_info["wc_earned"]
    wc_pool = wc_earned + extra_wc_applied + zwc_bonus_awarded
    max_reduction_cents = max_invoice_reduction_cents(tier, week_number)
    # ZWC is denominated in $1 units; max_reduction is in cents.
    wc_applied = min(wc_pool, max_reduction_cents // 100)
    invoice_reduction_cents = wc_applied * 100
    final_due_cents = max(value_stack_cents - invoice_reduction_cents, floor_cents)

    # --- CORA side ---
    cora = compute_cora_bonus(
        p1_status=p1_status,
        p2_status=p2_status,
        p3_status=p3_status,
        content_outputs=content_outputs,
        tier_surplus_cora=tier_surplus_cora,
        witness_excellence_cora=witness_excellence_cora,
        peer_service_cora=peer_service_cora,
        house_standing_cora=house_standing_cora,
        venture_donation_dollars=venture_donation_dollars,
    )

    return {
        # Tier / context
        "tier":                  tier,
        "value_stack_cents":     value_stack_cents,
        "floor_cents":           floor_cents,
        "trust_curve_pct":       trust_curve_pct(week_number),

        # ZWC ledger
        "wc_earned":             wc_earned,
        "wc_raw":                wc_info["wc_raw"],
        "wc_clamped":            wc_info["clamped"],
        "wc_clamp_message":      wc_info["clamp_message"],
        "wc_bonus_awarded":      zwc_bonus_awarded,
        "wc_pool":               wc_pool,
        "wc_applied":            wc_applied,
        "wc_remaining":          wc_pool - wc_applied,
        "max_reduction_cents":   max_reduction_cents,

        # CORA ledger
        "cora_priority_bonuses": cora["cora_priority_bonuses"],
        "cora_content_bonuses":  cora["cora_content_bonuses"],
        "cora_tier_surplus":     cora["cora_tier_surplus"],
        "cora_excellence":       cora["cora_excellence"],
        "cora_peer_service":     cora["cora_peer_service"],
        "cora_house_standing":   cora["cora_house_standing"],
        "cora_venture_donation": cora["cora_venture_donation"],
        "cora_raw":              cora["cora_raw"],
        "cora_earned":           cora["cora_earned"],
        "honor_entries":         cora["honor_entries"],

        # Backward-compat (v0.1 / v0.2 callers)
        "hourly_credit_cents":   wc_earned * 100,
        "invoice_reduction_cents": invoice_reduction_cents,
        "final_due_cents":       final_due_cents,
        "cora_overage":          0,
    }


def proof_to_cora(priority: str | None, status: str) -> int:
    """CORA awarded for a single approved proof, per priority + status."""
    if priority not in CORA_PRIORITY_BONUSES:
        return 0
    base = CORA_PRIORITY_BONUSES[priority]
    if status == "approved":
        return base
    if status == "partial":
        return base // 2
    return 0


def format_dollars(cents: int) -> str:
    return f"${cents / 100:.2f}"


# ---------------------------------------------------------------------------
# Self-test / worked examples — re-aligned to v8
# Run with: python -m app.mechanics
# ---------------------------------------------------------------------------

def _run_worked_examples() -> None:
    print("=== v8 Worked Examples ===\n")

    # --- Example A: Shared volunteer, strong delivery week ---
    # v8 §5 Example #1: Shared $400 invoice. 20 hrs × $20 = $400 ZWC → full
    # coverage. Priorities delivered → ZV awards CORA bonus (pure CORA since
    # invoice is already settled). +15 CORA house-wide good standing.
    # Witness elects CORA-form bonus (typical for Shared); the priority CORA
    # represents that bonus form.
    a = compute_seal(
        tier="shared", week_number=3, hours_logged=20,
        p1_status="full", p2_status="full", p3_status="full",
        house_standing_cora=15,
    )
    assert a["wc_earned"] == 400, f"Example A wc_earned={a['wc_earned']}"
    # priority bonuses 100+75+50 = 225, +15 house = 240 CORA raw
    assert a["cora_raw"] == 225 + 15, f"Example A cora_raw={a['cora_raw']}"
    assert a["cora_earned"] == 240, f"Example A cora_earned={a['cora_earned']}"
    assert a["honor_entries"] == 0, f"Example A honor_entries={a['honor_entries']}"
    # Shared $400 - $400 ZWC = $0 owed
    assert a["final_due_cents"] == 0, f"Example A final_due={a['final_due_cents']}"
    print(f"A) Shared strong delivery: ZWC {a['wc_earned']}, CORA {a['cora_earned']}, "
          f"owe {format_dollars(a['final_due_cents'])} (v8 §5 #1) OK")

    # --- Example B: Private volunteer, strong delivery week ---
    # v8 §5 Example #2: Private $600 invoice. 20 hrs × $20 = $400 ZWC.
    # Gap = $200. Witness elects ZWC-form bonus of $200 → closes gap. +50
    # CORA banked for premium.
    b = compute_seal(
        tier="private", week_number=3, hours_logged=20,
        p1_status="none", p2_status="none", p3_status="none",
        zwc_bonus_awarded=200,  # v8 NEW: witness closes gap with ZWC bonus
        witness_excellence_cora=50,  # then +50 CORA on top for premium
    )
    assert b["wc_earned"] == 400, f"Example B wc_earned={b['wc_earned']}"
    assert b["wc_bonus_awarded"] == 200
    assert b["wc_pool"] == 600, f"Example B wc_pool={b['wc_pool']}"
    assert b["wc_applied"] == 600
    assert b["final_due_cents"] == 0, f"Example B final_due={b['final_due_cents']}"
    # excellence clamped into [25, 100] range → 50 valid
    assert b["cora_excellence"] == 50
    assert b["cora_earned"] == 50, f"Example B cora_earned={b['cora_earned']}"
    print(f"B) Private strong delivery: ZWC pool {b['wc_pool']} "
          f"(400 earned + 200 bonus), CORA {b['cora_earned']} banked, "
          f"owe {format_dollars(b['final_due_cents'])} (v8 §5 #2) OK")

    # --- Example C: Private volunteer, average week ---
    # v8 §5 Example #3: Private $600. 18 hrs × $20 = $360 ZWC. P1 full,
    # P2 partial, P3 none → witness awards $100 ZWC + 25 CORA. Gap = $140.
    c = compute_seal(
        tier="private", week_number=3, hours_logged=18,
        p1_status="none", p2_status="none", p3_status="none",
        zwc_bonus_awarded=100,
        witness_excellence_cora=25,
    )
    assert c["wc_earned"] == 360, f"Example C wc_earned={c['wc_earned']}"
    assert c["wc_pool"] == 460
    assert c["wc_applied"] == 460
    assert c["final_due_cents"] == 14000, f"Example C final_due={c['final_due_cents']}"
    assert c["cora_excellence"] == 25
    print(f"C) Private average week: ZWC pool {c['wc_pool']} "
          f"(360 earned + 100 bonus), CORA {c['cora_earned']}, "
          f"owe {format_dollars(c['final_due_cents'])} (v8 §5 #3) OK")

    # --- Example D: Shared volunteer, weak week ---
    # v8 §5 Example #4: Shared $400. 14 hrs × $20 = $280 ZWC. No priorities
    # delivered → no bonus. Gap = $120.
    d = compute_seal(
        tier="shared", week_number=3, hours_logged=14,
        p1_status="none", p2_status="none", p3_status="none",
    )
    assert d["wc_earned"] == 280
    assert d["wc_pool"] == 280
    assert d["final_due_cents"] == 12000, f"Example D final_due={d['final_due_cents']}"
    assert d["cora_earned"] == 0
    print(f"D) Shared weak week: ZWC {d['wc_earned']}, "
          f"owe {format_dollars(d['final_due_cents'])} (v8 §5 #4) OK")

    # --- Example E: ZWC -> CORA conversion gate + dilution (carried from v6) ---
    e1 = convert_wc_to_cora(100, has_surplus=True)
    e2 = convert_wc_to_cora(100, has_surplus=False)
    assert e1["ok"] and e1["cora_in"] == 75, f"E1 cora_in={e1['cora_in']}"
    assert not e2["ok"] and "surplus" in e2["reason"]
    print(f"E) ZWC->CORA: 100 ZWC -> {e1['cora_in']} CORA (0.75 dilution); "
          f"no-surplus rejected OK")

    # --- Example F: paying guest tries CORA -> ZWC ---
    f_conv = convert_cora_to_wc(500, is_approved_volunteer=False)
    assert not f_conv["ok"]
    assert "approved-volunteer status" in f_conv["reason"]
    print(f"F) paying guest CORA->ZWC rejected: '{f_conv['reason']}' OK")

    # --- Example G: 25 hrs logged · hard cap clamp (carried from v6) ---
    g_info = compute_work_credits_with_clamp_info(hours_logged=25)
    assert g_info["clamped"]
    assert g_info["wc_earned"] == WC_WEEKLY_CAP_AMOUNT
    assert g_info["wc_raw"] == 25 * WC_RATE_PER_HOUR
    print(f"G) 25-hr clamp: raw {g_info['wc_raw']} ZWC, "
          f"earned {g_info['wc_earned']} ZWC (capped) OK")

    # --- Example H: floor concept retired in v8 ---
    # v8 has no explicit floor — but the back-compat helper still answers
    # the legacy question.
    assert can_pay_floor("cash"), "cash should still be eligible"
    assert can_pay_floor("ZWC"), "ZWC should still be eligible"
    assert not can_pay_floor("cora"), "CORA stays non-floor by back-compat"
    assert not has_explicit_floor("shared")
    assert not has_explicit_floor("private")
    print(f"H) v8 floor concept retired · has_explicit_floor() = False OK")

    # --- Example I: service split (70/15/5 · carried from v6) ---
    split = compute_service_split(100.0)
    assert split["provider"] == 70.0
    assert split["zv"] == 15.0
    assert split["community"] == 5.0
    assert split["residual"] == 10.0
    print(f"I) service split on $100: provider {split['provider']}, "
          f"ZV {split['zv']}, community {split['community']}, "
          f"residual {split['residual']} OK")

    # --- Example J: house-wide good standing aggregate (carried from v6) ---
    j = compute_cora_bonus(house_standing_cora=72)
    assert j["cora_house_standing"] == 72
    assert j["cora_earned"] == 72
    print(f"J) house-wide good standing (6 mates × 12 CORA): "
          f"CORA {j['cora_earned']} OK")

    # --- Example K: trust curve at week 1 (Shared tier) ---
    # v8: no floor → full $400 reducible at 50% → max $200 applies
    k = compute_seal(
        tier="shared", week_number=1, hours_logged=20,
        p1_status="full", p2_status="full", p3_status="full",
    )
    assert k["trust_curve_pct"] == 50
    assert k["max_reduction_cents"] == 20000  # $400 × 50% = $200
    assert k["wc_earned"] == 400
    assert k["wc_applied"] == 200  # capped by trust curve
    # $400 invoice - $200 applied = $200 owed (no explicit floor in v8)
    assert k["final_due_cents"] == 20000
    print(f"K) Shared week 1 trust curve (50%): "
          f"ZWC applied {k['wc_applied']}, "
          f"owe {format_dollars(k['final_due_cents'])} OK")

    # --- Example L: excellence bound (25-100 · carried from v6) ---
    l_low = compute_cora_bonus(witness_excellence_cora=10)
    l_high = compute_cora_bonus(witness_excellence_cora=500)
    assert l_low["cora_excellence"] == CORA_EXCELLENCE_MIN
    assert l_high["cora_excellence"] == CORA_EXCELLENCE_MAX
    print(f"L) excellence bounded [25, 100]: low→{l_low['cora_excellence']}, "
          f"high→{l_high['cora_excellence']} OK")

    # --- Example M: v8 NEW · award_bonus helper ---
    m_zwc = award_bonus(
        actor_id="alice@example",
        week_id="2026-W21",
        form="zwc",
        amount=200,
        reason="P1 delivered with strong proof · closes Private gap",
        witness_id="james@example",
    )
    assert m_zwc["form"] == "zwc"
    assert m_zwc["amount"] == 200
    assert m_zwc["target_ledger"] == "work_credits_ledger"
    m_cora = award_bonus(
        actor_id="alice@example",
        week_id="2026-W21",
        form="cora",
        amount=50,
        reason="excellence beyond P1",
    )
    assert m_cora["target_ledger"] == "cora_ledger"
    # Invalid form raises
    try:
        award_bonus("a", "w", "btc", 10, "nope")  # type: ignore[arg-type]
        raise AssertionError("award_bonus should reject invalid form")
    except ValueError:
        pass
    print(f"M) award_bonus: ZWC bonus 200 → work_credits_ledger, "
          f"CORA bonus 50 → cora_ledger, invalid form rejected OK")

    # --- Example N: v8 NEW · 2-tier enum (communal removed) ---
    assert set(TIER_VALUES.keys()) == {"private", "shared"}, \
        f"v8: TIER_VALUES must be exactly private/shared, got {TIER_VALUES.keys()}"
    assert TIER_VALUES["shared"]["value_stack"] == 40000, \
        "v8 Shared = $400 (was $530 in v6)"
    assert TIER_VALUES["private"]["value_stack"] == 60000, \
        "v8 Private = $600 (unchanged)"
    print(f"N) v8 2-tier enum: Shared $400, Private $600, communal removed OK")

    # --- Example O: bundled retail value disclosure ---
    assert RETAIL_SUBTOTAL_SHARED == 48500, "Shared retail = $485/wk"
    assert RETAIL_SUBTOTAL_PRIVATE == 68500, "Private retail = $685/wk"
    assert BUNDLED_DISCOUNT == 8500, "Both tiers built-in $85/wk discount"
    # Sanity: retail - bundled price = discount
    assert RETAIL_SUBTOTAL_SHARED - TIER_VALUES["shared"]["value_stack"] == BUNDLED_DISCOUNT
    assert RETAIL_SUBTOTAL_PRIVATE - TIER_VALUES["private"]["value_stack"] == BUNDLED_DISCOUNT
    print(f"O) Bundled disclosure: Shared ${RETAIL_SUBTOTAL_SHARED//100} retail → "
          f"${TIER_VALUES['shared']['value_stack']//100} bundled "
          f"(saves ${BUNDLED_DISCOUNT//100}/wk) OK")

    print("\nAll v8 worked examples passed.")


if __name__ == "__main__":
    _run_worked_examples()
