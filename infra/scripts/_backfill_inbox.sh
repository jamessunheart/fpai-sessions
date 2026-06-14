#!/bin/bash
# _backfill_inbox.sh — one-shot seed of current pending-James items into Veto Inbox v0.1
#
# Idempotency: this script appends. Re-running creates duplicates. Run ONCE.
# Source of truth for items: ALIGNMENT.md "OPEN BLOCKERS" + setup_pending/ + session brief.
#
# Workaround discipline applied (per [[feedback-optimize-pending-james]]):
#   - Calendar TCC grant: EXCLUDED (resolved via pivot to icalbuddy + just-ask-pattern)
#   - Sovereign Mac unblock: EXCLUDED (resolved via Phase 1 = rental-only)
#   - OpenAI key rotation: EXCLUDED (resolved 2026-05-20)
#   - Stripe TEST keys: EXCLUDED-FOR-V01 (deferred to volume threshold; Cora Credits + manual invoicing for first 5-10 Apprentices)
#
# Items here are the irreducibles AFTER workaround search.

set -uo pipefail

ADD="/Users/jamessunheart/FPAI_Cockpit/infra/scripts/inbox_add.sh"

# 1. TG preview review from commit 52f22de5 (Content Pipeline V1)
$ADD --silent \
  --category=ops \
  --description="Review TG preview from Content Pipeline V1 first live draft (commit 52f22de5) — POST/EDIT/SKIP pattern shapes V1.1 callback wiring" \
  --time-cost-min=3 \
  --leverage=med \
  --urgency=low \
  --classification=PRIVATE \
  --notes="Pattern from review informs V1.1 build. Single TG message in James's chat. Forge can take review-pattern as input."

# 2. Claude Code restart (registers Narrator + Kai)
$ADD --silent \
  --category=infra \
  --description="Restart Claude Code so Narrator + Kai agents become invokable in next session" \
  --time-cost-min=1 \
  --leverage=med \
  --urgency=low \
  --classification=PRIVATE \
  --notes="Agents live structurally. Restart triggers Agent tool registration. Zero work — just close+reopen."

# 3. Phase 1 retreat decisions (6 ⚡-instant carryforward)
$ADD --silent \
  --category=village \
  --description="Phase 1 retreat decisions: confirm 3 retreat dates + greenlight 3 remaining AI upgrades (auto-clip · affiliate notif · alumni TG) + Camp Zen GM hire + confirm parks + save 15-yr backcast + sign Phase 1 yield deploys (JitoSOL + Morpho USDC)" \
  --time-cost-min=20 \
  --leverage=high \
  --urgency=med \
  --classification=PRIVATE \
  --notes="6 ⚡-instant decisions bundled. Each <5min individually. Total ~20min. Splitting into individual items in v0.2."

# 4. Affiliate notification routing pick (4 options)
$ADD --silent \
  --category=champion \
  --description="Pick affiliate notification routing path (4 options surfaced; option 1 = email + dashboard recommended)" \
  --time-cost-min=3 \
  --leverage=high \
  --urgency=med \
  --classification=PRIVATE \
  --notes="Determines how inviter gets pinged when their invitee signs WPA. Gap is acknowledged in capability inventory."

# 5. Atlas + Halley email rotations (needed if option 1 above wins)
$ADD --silent \
  --category=ops \
  --description="Set up Atlas + Halley emails (depends on affiliate notif routing pick #4)" \
  --time-cost-min=10 \
  --leverage=med \
  --urgency=low \
  --classification=PRIVATE \
  --notes="Conditional on item above. May be skippable depending on routing choice."

# 6. ElevenLabs Creator key
$ADD --silent \
  --category=voice \
  --description="ElevenLabs Creator API key (~\$22/mo) to unlock Phase 3 sovereign voice clone for documentary" \
  --time-cost-min=5 \
  --leverage=med \
  --urgency=low \
  --classification=PRIVATE \
  --notes="Phase 2 OpenAI TTS is LIVE. ElevenLabs is Phase 3 enhancement — voice cloning. Decision: pay+activate now, or defer until documentary scales."

# 7. SuperWhisper Stage 1 install
$ADD --silent \
  --category=voice \
  --description="Finish SuperWhisper Stage 1 install on Mac (paused mid-flight)" \
  --time-cost-min=8 \
  --leverage=med \
  --urgency=low \
  --classification=PRIVATE \
  --notes="Sister to fp-game-bot voice loop. Local STT for desktop dictation. Phase 2 = phone transport pick."

# 8. Halley 1-on-1 + James's Gmail cleanup
$ADD --silent \
  --category=ops \
  --description="Halley 1-on-1 conversation (re: privacy incident 2026-05-16) + James personal Gmail cleanup" \
  --time-cost-min=30 \
  --leverage=med \
  --urgency=med \
  --classification=PRIVATE \
  --notes="Privacy incident itself RESOLVED on server side. Relationship-tier + James's own inbox hygiene. Irreducibly James."

# 9. WhatsApp number choice (from brief — surfaced in session)
$ADD --silent \
  --category=strategic \
  --description="WhatsApp number choice — pick the number/account for ZV inquiries handoff" \
  --time-cost-min=5 \
  --leverage=med \
  --urgency=med \
  --classification=PRIVATE \
  --notes="Mentioned in current session brief. Likely tied to ZV inquiry pipeline / sales loop."

# 10. Yield migration (Pendle decisions / SOL position carve-out review)
$ADD --silent \
  --category=yield \
  --description="Review yield migration plan — Pendle holdings + SOL position carve-out + JitoSOL/Morpho deploy" \
  --time-cost-min=15 \
  --leverage=high \
  --urgency=med \
  --classification=PRIVATE \
  --notes="Per [[feedback-no-gamble-yield-first]] + treasury bootstrap mandate. AI can prep options; deploy is irreducibly James (signs/wallet)."

# 11. CCP v0.1.1 veto points (Coherent Credits Protocol amendments)
$ADD --silent \
  --category=strategic \
  --description="Review v0.1.1 CCP veto points (Coherent Credits Protocol auto-iteration loop outputs)" \
  --time-cost-min=10 \
  --leverage=high \
  --urgency=med \
  --classification=COUNCIL-OPEN \
  --notes="Auto-iteration loop converged spec amendments. James reviews CONVERGED output per T7 model. Each individual amendment was reversible — bundle is the surface point."

# 12. Bridge asks (cross-Champion / cross-substrate asks needing James-tier intro)
$ADD --silent \
  --category=bridge \
  --description="Review pending bridge asks (Champion cross-intros / substrate-level connections requiring James as bridge)" \
  --time-cost-min=10 \
  --leverage=high \
  --urgency=low \
  --classification=COUNCIL-OPEN \
  --notes="From brief. Specific items not enumerated yet — Ember to surface list in v0.2 with each ask itemized."

echo ""
echo "=== Backfill complete ==="
python3 /Users/jamessunheart/FPAI_Cockpit/infra/scripts/veto_inbox.py stats
