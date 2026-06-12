#!/usr/bin/env bash
# Stop hook — flag missing ALIGNMENT footer on non-trivial assistant replies.
#
# Per James 2026-05-17: the alignment footer is non-negotiable on non-trivial
# replies (decisions, deploys, checklists, multi-turn context). Memory alone
# proved insufficient — Ember dropped the footer for an entire session of
# execution-pressure work despite the rule being loaded. This hook is the
# harness-level enforcement that catches the slip in real-time.
#
# Reads Stop event JSON from stdin (Claude Code hook contract):
#   {session_id, transcript_path, stop_hook_active, ...}
#
# Exit 0 = allow (compliant or trivial).
# Exit 2 = remind (stderr surfaces to Claude in next turn; Claude then sends
#                  a corrective reply with the footer + acknowledgment).
#
# Loop protection: if stop_hook_active is true, this fire is itself caused by
# a prior Stop-hook re-trigger — bail to avoid infinite loops. Means we get
# one corrective round-trip per slip, which is enough.
#
# Codified in: feedback_reply_alignment_footer.md, identity/VOICE.md.

# 2026-06-12 James: alignment footer removed from visible output.
# State logs to background file instead. Hook disabled.
exit 0

set -u

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)

# Loop protection
[ "$STOP_ACTIVE" = "true" ] && exit 0
[ -z "$TRANSCRIPT" ] && exit 0
[ ! -f "$TRANSCRIPT" ] && exit 0

# Pull the last assistant message's combined text content. Tail to keep this
# fast even on long transcripts — assistant messages aren't followed by 200
# user/tool events in normal flow.
LAST_TEXT=$(tail -n 200 "$TRANSCRIPT" 2>/dev/null \
  | jq -s -r 'map(select(.type=="assistant"))
              | if length == 0 then ""
                else (last | .message.content // []
                      | map(select(.type=="text") | .text) | join("\n"))
                end' 2>/dev/null)

[ -z "$LAST_TEXT" ] && exit 0
[ "$LAST_TEXT" = "null" ] && exit 0

# Triviality filter: short replies, acknowledgments, single-word answers.
# 200 chars catches one-liners while letting any structured reply through.
LEN=${#LAST_TEXT}
[ "$LEN" -lt 200 ] && exit 0

# Compliant — full footer present.
echo "$LAST_TEXT" | grep -q "─── ALIGNMENT ───" && exit 0

# Compliant — compressed Caveman v2.1 one-liner present
# (per feedback_caveman_clarity_output_contract.md · 2026-05-27 patch).
# Format: a single line starting with "ALIGNMENT:" carrying Now / Goal / Need / Next.
echo "$LAST_TEXT" | grep -qE '^ALIGNMENT:' && exit 0

# Non-trivial + footer missing → surface reminder.
cat >&2 <<'EOF'
🔴 ALIGNMENT FOOTER MISSING (Stop hook caught it)

Your last reply was non-trivial (≥200 chars) but did not include the
ALIGNMENT footer. This is a hard rule per identity/VOICE.md and
feedback_reply_alignment_footer.md.

Self-correct on your NEXT reply:
  1. Acknowledge the slip briefly (one line) so James knows the hook caught it
  2. Add the ALIGNMENT footer (vertical, code-fenced, per VOICE.md format)
  3. Continue with the user's pending request

Format reminder (wrap in triple-backtick code fence so whitespace renders):
  NOW · STREAMS (7 streams, 🟢/🟡/⚪) · GOALS (top 3 stream-tagged) · NEED · NEXT

If this fires repeatedly, the rule needs more reinforcement, not less.
EOF
exit 2
