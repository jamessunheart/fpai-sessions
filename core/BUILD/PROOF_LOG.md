# PROOF LOG — autonomous actions (append-only)

Every autonomous action Ember/Codex takes on James's behalf lands here: what, why, and the
one-command reverse. James's standing condition for hands-off operation (2026-06-11):
*"keep running logs / proof log and ways to reverse it if it's not helpful."*

Newest first. Each entry: `[UTC] · STREAM · what · why · REVERSE: <command/steps>`.

---

## 2026-06-11

- **[setup] · Game · Proof-log + reversibility scaffold created.**
  Why: James authorized hands-off operation conditioned on logging + reversibility.
  REVERSE: `git -C ~/FPAI_Cockpit revert e80815b6` (build-loop) + delete `core/BUILD/`.

- **[setup] · Game · Build loop committed (`e80815b6`) — file-queue spec→build→review for Codex.**
  Runner now builds each spec in an isolated git worktree on branch `build/<id>` (James added).
  Why: seamless Codex builds on the ChatGPT Max plan (no API), James only blesses merges.
  REVERSE: `git -C ~/FPAI_Cockpit revert e80815b6`; remove worktrees: `git worktree prune`.

- **[install] · Game · Installed `codex` CLI v0.139 (npm -g @openai/codex). auth_mode=chatgpt.**
  Why: activate the build loop on James's plan.
  REVERSE: `npm rm -g @openai/codex`.

- **[diagnose · read-only] · Treasury · Whaletrack live audit.**
  Wallet $431.53 (above $425 start); 2 shorts (ETH/SOL) in +$36 profit but with ZERO resting
  stop orders; stop-fix present in code but never fires; host python env broken (typing backport
  + sitecustomize shadow stdlib). No state changed.
  REVERSE: n/a (read-only).

---

## How to halt everything fast

- **Whaletrack live trading:** `ssh root@198.54.123.234 "sed -i 's/SWEEP_LIVE=1/SWEEP_LIVE=0/' /etc/systemd/system/whaletrack-magnet.service.d/sweep-live.conf && systemctl daemon-reload && systemctl restart whaletrack-magnet"`
- **Build loop:** delete pending files in `core/BUILD/specs/`; nothing auto-deploys (worktree branches only).
- **Codex:** `npm rm -g @openai/codex` (auth stays in `~/.codex` for re-install).
- **Any commit:** `git -C ~/FPAI_Cockpit revert <sha>` — every change is a discrete, reversible commit.
