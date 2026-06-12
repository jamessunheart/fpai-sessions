#!/usr/bin/env bash
# status.sh — show cohort funnel state by reading the cohort memory file
# and cross-referencing live champion data from fullpotential.com/api.
#
# Cohort memory file is at:
#   ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/project_first_cohort.md
# It must contain a markdown table with columns: name | phone | path | invited_at.
#
# Live API: https://fullpotential.com/api/champion/list

set -euo pipefail

COHORT_MD="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/project_first_cohort.md"
API="https://fullpotential.com/api/champion/list"

if [[ ! -f "$COHORT_MD" ]]; then
  echo "status: cohort file not found at $COHORT_MD" >&2
  exit 1
fi

CHAMPIONS_JSON=$(curl -sS --max-time 10 "$API" || echo '{}')

python3 - "$COHORT_MD" <<PY
import sys, re, json, os, urllib.request

cohort_path = sys.argv[1]
src = open(cohort_path).read()
champions = json.loads(os.environ.get("CHAMPIONS_JSON", "{}")).get("champions", [])

# Parse the cohort table — first markdown table with a "name" header column.
rows = []
in_table = False
headers = []
for line in src.splitlines():
    line = line.rstrip()
    if line.startswith("|") and "name" in line.lower() and "phone" in line.lower():
        in_table = True
        headers = [c.strip().lower() for c in line.strip("|").split("|")]
        continue
    if in_table:
        if not line.startswith("|"):
            in_table = False
            continue
        if set(line.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))

# Build a name -> champion lookup (case-insensitive on first name).
champ_by_first = {}
for c in champions:
    first = (c.get("name") or "").split()[0].lower()
    if first:
        champ_by_first[first] = c

print(f"\\n  COHORT STATUS  ·  {len(rows)} invitees  ·  {len(champions)} signed Champions live\\n")
print(f"  {'NAME':<12} {'PATH':<14} {'INVITED':<12} {'SIGNED':<10} {'CARD':<6} {'PROOFS':<8}")
print(f"  {'-'*12} {'-'*14} {'-'*12} {'-'*10} {'-'*6} {'-'*8}")

for r in rows:
    name = r.get("name", "?")
    first = re.sub(r'[^A-Za-zÀ-ÿ]', '', name.split()[0]).lower() if name else ""
    path = r.get("path", "?")[:14]
    invited = (r.get("invited_at", "") or "—")[:12]
    champ = champ_by_first.get(first)
    if champ:
        signed = (champ.get("date_signed", "") or "yes")[:10]
        card = "✓" if champ.get("card_filed") else "—"
        proofs = str(champ.get("proof_count", "?"))
    else:
        signed, card, proofs = "—", "—", "—"
    print(f"  {name[:12]:<12} {path:<14} {invited:<12} {signed:<10} {card:<6} {proofs:<8}")

print()
PY
