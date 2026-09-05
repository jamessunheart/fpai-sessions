#!/usr/bin/env bash
# ONE command = every open James-tap fires at once. Frictionless by design.
# 1) Deploys the FPI fix to 198 (auto-backup, rollback line printed)
# 2) Puts a fresh WhatsApp pairing QR on screen (auto-refreshing, 50 min)
# 3) Copies the marketplace submission text to your clipboard + opens the form
# You: scan the QR when you see it, and paste (Cmd-V) into the form. Done.
set -uo pipefail
R=/Users/jamessunheart/FullPotentialOS

echo "── 0/3 Push one-tap recruiting commit (D4) ──"
(cd "$R/_staged_repos/super-agents-pack" && rm -f .git/HEAD.lock .git/objects/maintenance.lock && git push origin master) || echo "  (push failed — run: gh auth login, then re-run)"

echo "── 1/3 FPI deploy ──"
bash "$R/infra/scripts/deploy_fpi_fix.sh" || echo "  (FPI deploy failed — logged, continue)"

echo "── 2/3 WhatsApp QR (auto-refreshing page opening) ──"
nohup bash "$R/infra/scripts/super_vendor_qr_watch.sh" >/tmp/qr_watch.log 2>&1 &
sleep 2; open "$HOME/Desktop/super-vendor-qr.html" 2>/dev/null || true

echo "── 3/3 Marketplace submission ──"
cat <<'EOF' | pbcopy
Plugin name: super-agents
One-line: Turn any outcome into an accountable, transferable Build Card — three sub-agents that serve, disclose AI, and hand every close to a human.
Description:
super-agents is a Claude Code plugin of three cooperating sub-agents. super-build converts a plain-language outcome ("find me a reliable produce supplier") into a structured Build Card with a max-loss bound and a nine-point "more alive" check. super-vendor-agent runs provider outreach over WhatsApp Business, always discloses it is an AI, logs every message verbatim, and classifies replies. super-steward tracks release conditions and state across sessions. Design law: the agent never releases funds, books, pays, or speaks as the human — every close is handed up. The deliverable is the unedited ledger; transfer of the whole system to the user is the promise on day one. MIT. Ethic: rich serving, never sovereign.
Repo: https://github.com/jamessunheart/super-agents-pack
EOF
open "https://platform.claude.com/plugins/submit" 2>/dev/null || true
echo "Submission text is in your clipboard — paste into the form that just opened."
echo ""
echo "ALL SET. Remaining decisions are one-word replies to Ember:"
echo "  redemption: 'same-day' or '7-days' (before Saturday's message 2)"
