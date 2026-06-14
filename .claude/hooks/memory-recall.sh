#!/usr/bin/env bash
# UserPromptSubmit hook — AUTOMATIC memory recall on every prompt.
#
# The fix for "memories lost are our biggest cost" (James, 2026-06-12):
# retrieval was passive — the AI only saw memories it happened to grep.
# This hook makes recall STRUCTURAL: every prompt is keyword-matched against
# the complete MEMORY_MAP.md and the top hits are injected as context.
# The Camp Zen plan can never be invisible again.
#
# Kill switch:  EMBER_MEMORY_RECALL_DISABLE=1
# Self-maintaining: rebuilds the map if missing or older than 24h.
set -u
[ "${EMBER_MEMORY_RECALL_DISABLE:-0}" = "1" ] && exit 0

MEM_DIR="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory"
# Prefer the unified SYSTEM_MAP (memory+vault+repo+config+fleet, Cartographer v1);
# fall back to the memory-only map if the system map can't be built.
MAP="$MEM_DIR/SYSTEM_MAP.md"
FALLBACK_MAP="$MEM_DIR/MEMORY_MAP.md"
BUILDER="${CLAUDE_PROJECT_DIR:-$HOME/FPAI_Cockpit}/tools/memory/build_system_map.py"
FALLBACK_BUILDER="${CLAUDE_PROJECT_DIR:-$HOME/FPAI_Cockpit}/tools/memory/build_memory_map.py"

# Rebuild map if missing or stale (>24h) — self-maintaining, no cron needed.
if [ ! -f "$MAP" ] || [ -n "$(find "$MAP" -mtime +1 2>/dev/null)" ]; then
  command -v python3 >/dev/null 2>&1 && python3 "$BUILDER" >/dev/null 2>&1
fi
if [ ! -f "$MAP" ]; then
  [ -f "$FALLBACK_MAP" ] || { command -v python3 >/dev/null 2>&1 && python3 "$FALLBACK_BUILDER" >/dev/null 2>&1; }
  MAP="$FALLBACK_MAP"
fi
[ -f "$MAP" ] || exit 0

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
[ -z "$PROMPT" ] && exit 0
# Skip trivial prompts — nothing to recall against.
[ ${#PROMPT} -lt 12 ] && exit 0

# Extract keywords: words >=4 chars, lowercased, deduped, minus stopwords, cap 12.
KEYWORDS=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '\n' \
  | awk 'length($0) >= 4' \
  | grep -vxE 'what|when|where|which|that|this|with|from|have|will|would|could|should|please|about|there|here|they|them|then|than|some|like|just|been|being|over|into|also|need|want|make|made|done|okay|yeah|know|think|going|other|more|most|much|many|very|next|why|how|see|let|the|and|for|you|your|our|are|can|now|get|got|its|his|her|she|him|had|has|was|were|not|but|all|out|use|used|using|does|did|doing|say|said|tell|show|find|look|help|work|thing|things|something|anything|everything' \
  | sort -u | head -12)
[ -z "$KEYWORDS" ] && exit 0

# Score map lines by number of distinct keyword hits; emit top 12 with >=1 hit.
# Skip header/structural lines (only score "territory | name | desc | path" rows).
MATCHES=$(awk -v kws="$(echo "$KEYWORDS" | tr '\n' ' ')" '
  BEGIN { n = split(kws, K, " ") }
  /^[a-z]+ \|/ {
    line = tolower($0); score = 0
    for (i = 1; i <= n; i++) if (K[i] != "" && index(line, K[i]) > 0) score++
    if (score > 0) print score "\t" $0
  }
' "$MAP" | sort -t$'\t' -k1,1nr | cut -f2- \
  | awk '{t=$1; if (++c[t]<=4 && ++n<=12) print}')  # max 4/territory so memory cannot crowd out vault/fleet/repo

# Always surface stale-SSOT warnings if the map carries any.
STALE=$(sed -n '/^## ⚠ STALE SSOTs/,/^$/p' "$MAP" 2>/dev/null | grep '^- ' || true)

[ -z "$MATCHES" ] && [ -z "$STALE" ] && exit 0

cat <<EOF
<system-reminder>
AUTO-RECALL (memory-recall.sh) — resources matching this prompt, from the COMPLETE system map of $(grep -c '^[a-z]* |' "$MAP" 2>/dev/null || echo '?') resources (memory + vault + repo + config + fleet):

$MATCHES
${STALE:+
⚠ STALE SSOTs (verify before asserting):
$STALE}

Path roots: memory→~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/ · vault→~/Documents/FPOS/Full Potential OS/ · repo→~/FPAI_Cockpit/ · config→as shown · fleet→core/STATE/FLEET_SNAPSHOT.md. Read the full file(s) before answering if relevant. These are point-in-time observations; verify live state before asserting. SSOT rules: core/STATE/SSOT_REGISTRY.md. (Kill switch: EMBER_MEMORY_RECALL_DISABLE=1)
</system-reminder>
EOF
exit 0
