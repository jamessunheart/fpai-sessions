# 🎯 Harvest System - Quick Reference

## For Apprentices (Submitting Code)

### Step 1: Validate Your Code
```bash
# In your repository
curl -sSL https://raw.githubusercontent.com/fullpotential/fpai-cockpit/main/_scripts/apprentice-preflight-check.sh | bash
```

### Step 2: Push to GitHub
```bash
git push origin main
```

### Step 3: Share Repository URL
Send your repo URL to the system administrator:
```
https://github.com/yourname/your-service
```

---

## For System Admins (Harvesting Code)

### Quick Harvest (Safe Mode - Default)
```bash
cd /path/to/FPAI_Cockpit
./_scripts/harvest-apprentice.py ApprenticeNameHere https://github.com/user/repo
```

### Trusted Apprentice (Skip Verification)
```bash
./_scripts/harvest-apprentice.py TrustedName https://github.com/user/repo --trusted
```

### Custom Options
```bash
# Custom service name
./_scripts/harvest-apprentice.py John https://github.com/john/repo --service custom-name

# Different branch
./_scripts/harvest-apprentice.py Jane https://github.com/jane/repo --branch develop

# All options together
./_scripts/harvest-apprentice.py Bob https://github.com/bob/repo \
  --service bob-api \
  --branch feature/v2 \
  --trusted
```

### View Recent Submissions
```bash
./_scripts/harvest-apprentice.py --list
```

---

## Quality Scoring

| Score | Result | Action |
|-------|--------|--------|
| 90-100% | ✅ Auto-approved | Instant merge to SERVICES/ |
| 80-89% | ⚠️ Approved | Merged with improvement notes |
| 60-79% | ⚠️ Needs work | Feedback provided, resubmit |
| <60% | ❌ Rejected | Major fixes required |

---

## File Locations

```
FPAI_Cockpit/
├── _scripts/
│   ├── harvest-apprentice.py          # Main harvester (USE THIS)
│   ├── apprentice-preflight-check.sh   # Pre-submission validation
│   └── HARVEST_QUICKSTART.md           # This file
│
├── fullpotential_ai/orchestration/tools/
│   └── harvest_repo.py                 # Direct harvester (legacy)
│
├── orchestration/tools/
│   └── gatekeeper.py                   # Gatekeeper system
│
├── docs/coordination/
│   ├── apprentice-submissions.json    # Submission tracking
│   └── apprentice-submissions.log     # Audit log
│
├── STAGING/incoming/                  # Quarantine area
└── SERVICES/                          # Production services
```

---

## Troubleshooting

### "Command not found"
```bash
# Make scripts executable
chmod +x /path/to/FPAI_Cockpit/_scripts/*.py
chmod +x /path/to/FPAI_Cockpit/_scripts/*.sh
```

### "Gatekeeper not found"
```bash
# Use direct mode (less safe)
./_scripts/harvest-apprentice.py Name https://github.com/user/repo --trusted
```

### "Tests failed"
```bash
# View detailed logs
tail -f docs/coordination/apprentice-submissions.log

# Check submission details
cat docs/coordination/apprentice-submissions.json | jq '.submissions[-1]'
```

### "Need to rollback"
```bash
git log --oneline | head -5
git revert <commit-hash>
git push origin main
```

---

## Examples

### Example 1: First-time Apprentice
```bash
# Admin receives: "Hi, here's my API service: https://github.com/alice/api-v1"

cd /Users/jamessunheart/FPAI_Cockpit
./_scripts/harvest-apprentice.py Alice https://github.com/alice/api-v1

# Output:
# 🛡️ Using GATEKEEPER mode
# 📊 Quality Score: 95%
# ✅ SUCCESS: api-v1 harvested successfully!
# 📂 Location: SERVICES/api-v1
```

### Example 2: Trusted Veteran
```bash
# Bob has submitted 20+ times, all high quality

./_scripts/harvest-apprentice.py Bob https://github.com/bob/hotfix --trusted

# Output:
# ⚡ Using DIRECT mode (Trusted)
# ✅ SUCCESS: hotfix harvested successfully!
```

### Example 3: Custom Configuration
```bash
# Charlie's repo is called "project-x" but we want it as "charlie-analytics"

./_scripts/harvest-apprentice.py Charlie https://github.com/charlie/project-x \
  --service charlie-analytics \
  --branch production

# Output:
# 🏷️  Auto-detected service name: project-x
# 🏷️  Overriding with: charlie-analytics
# ✅ SUCCESS: charlie-analytics harvested successfully!
```

---

## Best Practices

1. **Always use safe mode** for new apprentices
2. **Review logs** after each harvest
3. **Test manually** for critical services
4. **Track submissions** with `--list` regularly
5. **Keep scripts updated** with `git pull`

---

## Support

- Full Guide: `_guides/operations/APPRENTICE_SUBMISSION_GUIDE.md`
- Issues: Open GitHub issue with `[harvest]` tag
- Emergency: Rollback immediately, ask questions later

