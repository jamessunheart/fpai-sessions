#!/usr/bin/env bash
# Regenerates the version history on /blueprints from git. Run from anywhere.
# The history is DERIVED, never hand-written: a hand-kept changelog drifts from
# what actually shipped, and a drifted log is worse than none. git cannot lie about
# what changed. If this script stops running, the page says so rather than going stale.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
STAMP="$(date -u +'%Y-%m-%d %H:%M UTC')"

ROWS=""
while IFS='|' read -r sha when subj; do
  [ -z "$sha" ] && continue
  esc=$(printf '%s' "$subj" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')
  ROWS="${ROWS}<tr><td class=\"sha\">${sha}</td><td class=\"when\">${when}</td><td>${esc}</td></tr>"
done < <(git log --date=short --pretty=format:'%h|%ad|%s' -- . 2>/dev/null | head -60)

if [ -z "$ROWS" ]; then
  ROWS='<tr><td colspan="3">No commits recorded yet for this directory.</td></tr>'
fi

python3 - "$STAMP" "$ROWS" <<'PY'
import sys, re, io
stamp, rows = sys.argv[1], sys.argv[2]
p = 'index.html'
s = io.open(p, encoding='utf-8').read()
s = re.sub(r'<!--HISTORY:START-->.*?<!--HISTORY:END-->',
           '<!--HISTORY:START-->' + rows + '<!--HISTORY:END-->', s, flags=re.S)
s = re.sub(r'<!--STAMP:START-->.*?<!--STAMP:END-->',
           '<!--STAMP:START-->' + stamp + '<!--STAMP:END-->', s, flags=re.S)
io.open(p, 'w', encoding='utf-8').write(s)
print('history regenerated:', stamp)
PY
