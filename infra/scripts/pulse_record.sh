#!/bin/bash
# pulse_record.sh — append a James PULSE rating to the ledger
#
# Usage: pulse_record.sh <rating 1-5> [YYYY-MM-DD]
#   Date defaults to yesterday (matches what pulse_daily_prompt.sh asks about).
#
# Companion to pulse_daily_prompt.sh. Used by Ember (manually for now) when
# James replies to the daily TG prompt with a rating. Will be invoked
# automatically by the /pulse bot handler once it's deployed (follow-up).
#
# Idempotent: detects + replaces an existing line for the same date.
# Reversibility: edit ledger to revert; LEDGER_BACKUP_BEFORE saved on every run.

set -uo pipefail

LEDGER="${HOME}/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/reference_soul_time_ledger.md"
OUTDIR="${HOME}/.config/fpai/pulse_daily"
BACKUP_DIR="${OUTDIR}/ledger_backups"
TS_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

mkdir -p "$BACKUP_DIR"

RATING="${1:-}"
DATE="${2:-$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d 'yesterday' +%Y-%m-%d)}"

if [ -z "$RATING" ] || ! [[ "$RATING" =~ ^[1-5]$ ]]; then
  echo "usage: $0 <rating 1-5> [YYYY-MM-DD]" >&2
  echo "   rating must be 1, 2, 3, 4, or 5" >&2
  exit 1
fi

if [ ! -f "$LEDGER" ]; then
  echo "ERROR: ledger not found at $LEDGER" >&2
  exit 2
fi

# Backup
cp "$LEDGER" "${BACKUP_DIR}/$(basename "$LEDGER").${TS_UTC}.bak"

# The compact, machine-readable entry that grep-friendly tools can find:
ENTRY="- ${DATE} · James rated PULSE: ${RATING}/5  _(recorded ${TS_UTC})_"

# Find or create the "James ratings" section
if grep -q "^## James daily ratings$" "$LEDGER"; then
  # Section exists — check if we already have an entry for this date
  if grep -qE "^- ${DATE} · James rated PULSE:" "$LEDGER"; then
    # Replace existing line in place (BSD sed compatible)
    python3 - "$LEDGER" "$DATE" "$ENTRY" <<'PY'
import sys, re
path, date, new_line = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f: text = f.read()
pattern = re.compile(rf"^- {re.escape(date)} · James rated PULSE: \d/5.*$", re.MULTILINE)
text2, n = pattern.subn(new_line, text, count=1)
with open(path, 'w') as f: f.write(text2)
print(f"replaced {n} line(s) for {date}")
PY
  else
    # Append under the section header (after any existing entries for that section)
    python3 - "$LEDGER" "$ENTRY" <<'PY'
import sys, re
path, new_line = sys.argv[1], sys.argv[2]
with open(path) as f: lines = f.readlines()
out = []
inserted = False
i = 0
while i < len(lines):
    out.append(lines[i])
    if not inserted and lines[i].strip() == "## James daily ratings":
        # Walk forward past existing "- YYYY-MM-DD" entries and the blank line under header
        j = i + 1
        # Skip section-blank line(s)
        while j < len(lines) and lines[j].strip() == "":
            out.append(lines[j]); j += 1
        # Keep existing entries
        while j < len(lines) and lines[j].startswith("- ") and "James rated PULSE" in lines[j]:
            out.append(lines[j]); j += 1
        # Insert new entry here (keeps section sorted-ish by insertion order, newest at bottom)
        out.append(new_line + "\n")
        inserted = True
        i = j
        continue
    i += 1
with open(path, 'w') as f: f.writelines(out)
print("appended to existing section")
PY
  fi
else
  # No section yet — append at file end
  {
    echo ""
    echo "## James daily ratings"
    echo ""
    echo "$ENTRY"
  } >> "$LEDGER"
  echo "section created and entry appended"
fi

echo "✅ ledger updated: $DATE · PULSE=${RATING}/5"
echo "   backup: ${BACKUP_DIR}/$(basename "$LEDGER").${TS_UTC}.bak"
