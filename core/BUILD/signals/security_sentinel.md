# Security Sentinel Report

**Generated:** 2026-06-17T00:26:31Z
**Mode:** report-only local scan of repo-local text/config files; no network probing, external secret-store reads, private-key inspection, enforcement, deployment, spend, outreach, or service mutation. Emitted evidence is redacted.

## Summary

- Total findings: 2
- Max severity: 5
- P0 findings: 0
- P1 findings: 2
- P2 findings: 0

| Category | Findings |
|---|---:|
| hardware | 1 |
| system | 0 |
| adversarial_behavior | 0 |
| circumvention | 1 |
| control_plane | 0 |

## Findings

### circumvention - severity 5 - Guardrail circumvention language appears in active runnable surfaces
- **Detail:** Instructions or scripts that mention bypassing reviews, tests, guards, or main-branch protections deserve review before autonomous execution.
- **Next action:** Classify each hit as test fixture, benign warning, or actionable bypass path; remove or gate actionable paths.
- **Evidence:**
  - `tools/merge/ai_review.py:71: "main branch, and any silent guardrail bypass. Be strict: when in doubt, REQUEST_CHANGES. "`
  - `tools/probe/__init__.py:5: contacts or bypass James-owned outreach gates.`
  - `SERVICES/zv-wallet/app/group_observer.py:23: Any witness can post `!credit @user Xhr <activity>` in the group to bypass`
  - `SERVICES/zv-wallet/app/group_observer.py:131: # 2. Manual override path - witness can bypass parser`
  - `SERVICES/sunheart-brain/scripts/issue_token.sh:13: #   admin     Bypass all scope checks. Keep this only on the MCP's internal [secret-keyword].`
  - `SERVICES/sunheart-brain/curator/curator.py:81: # Long-running poller, not a one-shot job. Bypass _run/asyncio.run.`
  - `SERVICES/sunheart-brain/curator/tgbot.py:1604: For inner/sacred cards, set ADMIN_TOKEN in env to bypass visibility gate.`
  - `SERVICES/aria-command/sovereign/ascension/proactive_engine.py:335: # Critical actions bypass rate limit`
  - `SERVICES/aria-command/consciousness/source.py:228: ("override safety", "Safety bypass"),`
  - `SERVICES/fp-index/app/engine.py:390: "security": ["vulnerability", "jailbreak", "adversarial", "safety", "alignment",`
  - `SERVICES/fp-index/app/engine.py:2567: "attack", "bypass", "jailbreak", "hack", "phishing",`
  - `SERVICES/fp-index/app/engine.py:2569: "brute force", "injection", "exfiltrat", "trojan",`

### hardware - severity 5 - Privileged host or hardware access appears in runnable artifacts
- **Detail:** Root users, host networking, docker socket access, device mounts, or broad capabilities make hardware/system exploits more consequential.
- **Next action:** Review each privileged path; move live units toward least privilege, named users, bounded capabilities, and explicit installation approval.
- **Evidence:**
  - `SERVICES/deploy-droplet.sh:81: User=root`
  - `SERVICES/check-dns-wildcard.sh:108: echo "   - Mac: sudo dscacheutil -flushcache"`
  - `SERVICES/check-dns-wildcard.sh:109: echo "   - Linux: sudo systemd-resolve --flush-caches"`
  - `SERVICES/zv-wallet/zv-wallet.service:8: User=root`
  - `SERVICES/2x-treasury/deploy.sh:26: User=root`
  - `SERVICES/ai-automation/setup-automation.sh:411: User=root`
  - `SERVICES/ai-automation/setup-automation.sh:427: echo "  sudo cp ai-marketing-engine.service /etc/systemd/system/"`
  - `SERVICES/ai-automation/setup-automation.sh:428: echo "  sudo systemctl enable ai-marketing-engine"`
  - `SERVICES/ai-automation/setup-automation.sh:429: echo "  sudo systemctl start ai-marketing-engine"`
  - `SERVICES/mission-control/mission-control.service:7: User=root`
  - `SERVICES/ops/setup-ssh-access.sh:152: echo "  2. Check server SSH config: sudo nano /etc/ssh/sshd_config"`
  - `SERVICES/ops/setup-ssh-access.sh:155: echo "  3. Check server SSH logs: sudo tail -20 /var/log/auth.log"`
