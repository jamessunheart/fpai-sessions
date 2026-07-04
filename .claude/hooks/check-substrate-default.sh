#!/usr/bin/env bash
# Stop hook — catch the TRAINING-BIAS misroute: defaulting a decision to James
# when the Constitution says it belongs to substrate/council.
#
# James, 2026-07-03: "there is a bias in your training to default to me, when it
# should be to default to the Constitution and AI principles. How do we ensure
# this in EVERY session?" The honest finding: passive rules (CLAUDE.md pins,
# memory files) do NOT beat training bias — Ember misrouted d138 to James one
# turn after re-reading the rule. Only ENFORCEMENT at the moment of risk works.
# This is the analog of constitution_check, applied to Ember's own turn-ending
# routing. Same mechanism as check-alignment-footer.sh: read the last message,
# detect the slip, exit 2 to force one corrective round-trip.
#
# The law being enforced (CONSTITUTION.md):
#   L5 Preserve Alignment — James sets direction · money · public voice; the
#                           system routes/builds/learns WITHIN those bounds.
#   L6 Protect Human Leverage — escalate ONLY what genuinely needs human direction.
#   L7 Reversible First — reversible + within authority → EXECUTE, don't escalate.
#
# The rule: if a reply routes a decision/approval to James, it must NAME the
# Reserved class (money · public voice · direction) that justifies it. Routing
# to James with no named justification = the bias firing = flagged.
#
# Exit 0 = allow · Exit 2 = corrective round-trip (stderr surfaces to Claude).
# Override one-shot: EMBER_SUBSTRATE_HOOK_DISABLE=1

set -u
[ "${EMBER_SUBSTRATE_HOOK_DISABLE:-0}" = "1" ] && exit 0

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)

# Loop protection — one corrective round-trip per slip, never infinite.
[ "$STOP_ACTIVE" = "true" ] && exit 0
[ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ] && exit 0

LAST_TEXT=$(tail -n 200 "$TRANSCRIPT" 2>/dev/null \
  | jq -s -r 'map(select(.type=="assistant"))
              | if length == 0 then ""
                else (last | .message.content // []
                      | map(select(.type=="text") | .text) | join("\n"))
                end' 2>/dev/null)

[ -z "$LAST_TEXT" ] || [ "$LAST_TEXT" = "null" ] && exit 0
[ "${#LAST_TEXT}" -lt 200 ] && exit 0

# --- Detect routing-to-James (the bias tell) ---------------------------------
# Classic deference phrases + permission-seeking questions aimed at James.
ROUTE_RE='your call|you decide|up to you|should i |shall i |do you want|would you like|which (one )?(do|would) you|let me know (if|whether|which|what)|waiting (on|for) you|await(ing)? your|your (approval|decision|go[- ]?ahead|sign[- ]?off)|need from you.*\?|confirm\?|approve\?'

echo "$LAST_TEXT" | grep -qiE "$ROUTE_RE" || exit 0   # no routing-to-James → fine

# --- Allow if a Reserved class is explicitly named as the justification ------
# The only things that legitimately route to James (CONSTITUTION L5).
# NOTE: "which to ship/build/prioritize" is deliberately NOT here — sequencing
# reversible work is substrate's (Law 4/council), not James's "direction".
RESERVED_RE='reserved|public voice|personal voice|your voice|public-facing|publish|outreach|sign(ature|ing)?\b|money|spend|treasury|capital|\$[0-9]|wire|payment|strategic direction|set(s|ting)? direction'

echo "$LAST_TEXT" | grep -qiE "$RESERVED_RE" && exit 0  # justified escalation → fine

# --- Also allow the honest "nothing blocked" footer line ---------------------
echo "$LAST_TEXT" | grep -qiE 'NEED[^A-Za-z]+(none|nothing)' && \
  ! echo "$LAST_TEXT" | grep -qiE "$ROUTE_RE" && exit 0

# --- Slip detected: routing to James without a Reserved justification --------
LOG_DIR="$CLAUDE_PROJECT_DIR/core/BUILD/governance"
mkdir -p "$LOG_DIR" 2>/dev/null
SNIP=$(echo "$LAST_TEXT" | grep -ioE "$ROUTE_RE" | head -1)
printf '{"ts":"%s","hook":"substrate-default","matched":"%s"}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${SNIP//\"/}" >> "$LOG_DIR/substrate_default_catches.jsonl" 2>/dev/null

{
  echo "🔴 substrate-default drift (Stop hook caught the training bias)"
  echo ""
  echo "  This reply routes a decision to James ('$SNIP') without naming a"
  echo "  Reserved class. That is the trained default-to-human bias, not the"
  echo "  Constitution."
  echo ""
  echo "  CONSTITUTION L5/L6/L7: reversible + within-cap + aligned → substrate"
  echo "  or council EXECUTES. Only money · public voice · direction are James's."
  echo ""
  echo "  Self-correct on next reply (pick one):"
  echo "    (a) Re-route: substrate/council does it; withdraw the ask to James."
  echo "    (b) If genuinely Reserved: name WHICH class (money/public-voice/"
  echo "        direction) makes it his — then it passes."
  echo ""
  echo "  Override one-shot: EMBER_SUBSTRATE_HOOK_DISABLE=1"
} >&2
exit 2
