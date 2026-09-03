#!/usr/bin/env bash
# Open listing PRs for super-agents-pack on the three awesome-lists.
# James runs this (public voice = his). Requires: gh authenticated as jamessunheart.
set -uo pipefail
SCRATCH="${TMPDIR:-/tmp}/recruit_prs_$$"
mkdir -p "$SCRATCH"
ENTRY='- [`super-agents`](https://github.com/jamessunheart/super-agents-pack) — by [@jamessunheart](https://github.com/jamessunheart) — Three sub-agents that turn a real-world outcome into an accountable, transferable Build Card: `super-build` (outcome → signed Card), `super-vendor-agent` (AI-disclosed provider outreach, verbatim ledger), `super-steward` (release conditions + cross-session state). Never pays/books/speaks-as-human; every close handed up. MIT.'
BODY='Adds `super-agents`, a 3-agent pack for outcome→Card workflows with human-in-the-loop on every close and full ledger transparency. MIT, follows the list format. Thanks for maintaining the list.'

for REPO in hesreallyhim/a-list-of-claude-code-agents VoltAgent/awesome-claude-code-subagents rahulvrane/awesome-claude-agents; do
  NAME=${REPO#*/}
  echo "=== $REPO"
  gh repo fork "$REPO" --clone=false >/dev/null 2>&1
  git clone --depth 1 "https://github.com/jamessunheart/$NAME.git" "$SCRATCH/$NAME" >/dev/null 2>&1 || { echo "  clone failed, skipping"; continue; }
  cd "$SCRATCH/$NAME"
  git checkout -b add-super-agents >/dev/null 2>&1
  printf '\n%s\n' "$ENTRY" >> README.md
  git add README.md
  git commit -m "Add super-agents pack" >/dev/null
  git push -u origin add-super-agents >/dev/null 2>&1
  gh pr create --repo "$REPO" --title "Add super-agents" --body "$BODY" --head "jamessunheart:add-super-agents" 2>&1 | tail -1
  cd - >/dev/null
done
echo "NOTE: entry appended at README end — maintainers may ask to move it to a category; that is fine."
