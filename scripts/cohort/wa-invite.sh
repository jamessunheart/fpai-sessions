#!/usr/bin/env bash
# wa-invite.sh — open WhatsApp.app with a prefilled cohort invite.
# Usage: wa-invite.sh "<Name>" "<phone>" [path]
#   path defaults to "game". Templates live in core/STATE/INVITE_TEMPLATES.md
#     (uses the {path}-wa-short heading; falls back to game-wa-short).
# Requires: macOS WhatsApp.app, python3.
#
# Side effects:
#   - Opens whatsapp://send?phone=...&text=... (you tap send)
#   - Appends a row to scripts/cohort/.invite-log.tsv

set -euo pipefail

NAME="${1:?usage: wa-invite.sh \"<Name>\" \"<phone>\" [path]}"
PHONE_RAW="${2:?usage: wa-invite.sh \"<Name>\" \"<phone>\" [path]}"
PATH_SLUG="${3:-game}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATES="$REPO_ROOT/core/STATE/INVITE_TEMPLATES.md"
# Log lives outside the repo — phone numbers shouldn't enter git history.
LOG="${FPAI_INVITE_LOG:-$HOME/.config/fpai/cohort-invite-log.tsv}"

# Normalize phone -> E.164 digits-only (strip +, spaces, parens, dashes).
PHONE_DIGITS=$(printf '%s' "$PHONE_RAW" | tr -cd '0-9')
if [[ ${#PHONE_DIGITS} -lt 10 || ${#PHONE_DIGITS} -gt 15 ]]; then
  echo "wa-invite: phone '$PHONE_RAW' normalized to '$PHONE_DIGITS' — expected 10-15 digits" >&2
  exit 2
fi
# Add US country code if 10 digits and looks like a NANP number.
if [[ ${#PHONE_DIGITS} -eq 10 ]]; then
  PHONE_DIGITS="1$PHONE_DIGITS"
fi
PHONE_E164="+$PHONE_DIGITS"

# Pull the per-path WhatsApp short template, fallback to game-wa-short.
extract_template() {
  local slug="$1"
  python3 - "$TEMPLATES" "$slug" <<'PY'
import sys, re
path, slug = sys.argv[1], sys.argv[2]
src = open(path).read()
# Match a "## <slug>-wa-short" section up to the next "## " or "---" line.
pat = re.compile(rf'^##\s+{re.escape(slug)}-wa-short\s*\n(.*?)(?=^---|\Z)', re.M | re.S)
m = pat.search(src)
print(m.group(1).strip() if m else "")
PY
}

TEMPLATE=$(extract_template "$PATH_SLUG")
if [[ -z "$TEMPLATE" ]]; then
  TEMPLATE=$(extract_template "game")
fi
if [[ -z "$TEMPLATE" ]]; then
  echo "wa-invite: no '$PATH_SLUG-wa-short' or 'game-wa-short' template in $TEMPLATES" >&2
  exit 3
fi

INVITER_NAME="James Sunheart"
INVITER_URL_PARAM=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" "$INVITER_NAME")
TRACKED_LINK="https://fullpotential.com/game/?inviter=$INVITER_URL_PARAM"
FIRST_NAME="${NAME%% *}"

MSG=$(printf '%s' "$TEMPLATE" \
  | sed "s|{NAME}|$FIRST_NAME|g" \
  | sed "s|{TRACKED_LINK}|$TRACKED_LINK|g")

# URL-encode the full message for the WhatsApp URL scheme.
ENCODED=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" "$MSG")
URL="whatsapp://send?phone=$PHONE_DIGITS&text=$ENCODED"

# Log invite (timestamp, name, phone, path, message).
mkdir -p "$(dirname "$LOG")"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
printf "%s\t%s\t%s\t%s\t%s\n" "$TS" "$NAME" "$PHONE_E164" "$PATH_SLUG" "${MSG//$'\n'/ ↵ }" >> "$LOG"

echo "─ to:    $NAME ($PHONE_E164)"
echo "─ path:  $PATH_SLUG"
echo "─ link:  $TRACKED_LINK"
echo
echo "$MSG"
echo
echo "─ opening WhatsApp.app …"
open "$URL"
