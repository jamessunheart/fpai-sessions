# 🎯 Apprentice Submission Guide
**Full Potential OS - Code Harvest Protocol**

## Overview

This guide explains how to submit code to the Full Potential OS ecosystem as an apprentice developer. We use an automated "harvest" system that pulls your code from Git repositories, verifies it, and integrates it into the main system.

---

## 🚀 Quick Start for Apprentices

### 1. Prepare Your Code

Before submitting, ensure your repository includes:

- ✅ **Tests** - In a `tests/` directory or as `test_*.py` files
- ✅ **README.md** - Setup instructions, usage examples, API documentation
- ✅ **Dependencies** - `requirements.txt` (Python) or `package.json` (Node.js)
- ✅ **Clean code** - No hardcoded secrets, API keys, or passwords
- ✅ **Working tests** - All tests must pass locally

### 2. Run Pre-Flight Check

Run this command in your repository to validate submission requirements:

```bash
curl -sSL https://raw.githubusercontent.com/fullpotential/fpai-cockpit/main/_scripts/apprentice-preflight-check.sh | bash
```

Or if you have the repo:

```bash
cd /path/to/FPAI_Cockpit
./_scripts/apprentice-preflight-check.sh
```

Fix any errors before proceeding.

### 3. Push to GitHub

```bash
git add .
git commit -m "feat: Ready for submission"
git push origin main
```

### 4. Submit Your Repository URL

Share your repository URL with the system administrator or autonomous agent:
- `https://github.com/yourname/your-service`

That's it! The system will automatically:
1. Clone your code to a staging area
2. Run verification tests
3. Calculate a quality score
4. Auto-merge if score ≥90%, or provide feedback for improvements

---

## 📋 Submission Requirements

### Minimum Requirements (MUST HAVE)

1. **Tests**
   - Unit tests for core functionality
   - Integration tests for APIs/endpoints
   - All tests must pass
   - Minimum: 60% code coverage (recommended: 80%+)

2. **Documentation**
   - README.md with:
     - Project description
     - Setup/installation instructions
     - Usage examples
     - API documentation (if applicable)
   - Inline code comments for complex logic
   - Docstrings for functions/classes

3. **Dependencies**
   - `requirements.txt` with pinned versions (Python)
   - `package.json` with dependencies (Node.js)
   - No missing dependencies

4. **Security**
   - No hardcoded API keys, passwords, or secrets
   - Use environment variables (`.env` file pattern)
   - `.gitignore` excludes sensitive files

### Best Practices (SHOULD HAVE)

- 🎯 **Clear project structure** - Organized directories
- 📝 **Type hints** - For Python code (PEP 484)
- 🔒 **Input validation** - Sanitize user inputs
- 🧪 **Test fixtures** - Reusable test data
- 📊 **Logging** - Use proper logging instead of print statements
- 🚀 **Performance** - Reasonable response times
- 🎨 **Code style** - Follow language conventions (PEP 8, ESLint)

---

## 🛠️ Pre-Flight Checklist

Run through this checklist before submitting:

```
□ All tests pass locally
□ README.md is complete and accurate
□ No hardcoded secrets or API keys
□ Dependencies are specified and pinned
□ .gitignore excludes venv/, node_modules/, .env
□ Git history is clean (no sensitive commits)
□ Code follows style guidelines
□ No large files (>10MB) committed
□ All features documented
□ Pre-flight check script passes
```

---

## 🎭 Submission Modes

The system supports two harvesting modes:

### Mode 1: Gatekeeper (Default - Recommended)

**Best for:** New apprentices, experimental features

- ✅ Full verification workflow
- ✅ Staged in quarantine first
- ✅ Automated quality scoring
- ✅ Automatic fixes dispatched if needed
- ✅ Safe rollback on failures

**Process:**
```
Your Repo → STAGING/ → Verification → SERVICES/ (if ≥90%)
                                    → Fix Intent (if <90%)
```

### Mode 2: Direct (Trusted Only)

**Best for:** Proven apprentices, urgent hotfixes

- ⚡ Fast-track integration
- ⚡ Direct merge via git subtree
- ⚡ Basic verification only
- ⚠️  Requires approval from maintainer

**Process:**
```
Your Repo → Merge to SERVICES/ → Basic Tests → Commit
```

---

## 📊 Quality Scoring

Your submission receives a quality score based on:

| Check | Weight | Description |
|-------|--------|-------------|
| Tests Exist | 20% | Tests directory or test files found |
| Tests Pass | 30% | All tests execute successfully |
| Documentation | 20% | README.md with meaningful content |
| Dependencies | 15% | requirements.txt or package.json present |
| Security | 15% | No hardcoded secrets detected |

**Score Thresholds:**
- **90-100%**: ✅ Auto-approved - Instant merge to production
- **80-89%**: ⚠️ Approved with warnings - Manual review recommended
- **60-79%**: ⚠️ Needs improvement - Fix recommended issues
- **<60%**: ❌ Rejected - Major issues must be fixed

---

## 🔧 For System Administrators

### Harvesting an Apprentice Submission

```bash
# Navigate to the main repository
cd /path/to/FPAI_Cockpit

# Harvest with verification (safe mode)
./_scripts/harvest-apprentice.py AliceSmith https://github.com/alice/api-service

# Harvest from trusted apprentice (skip verification)
./_scripts/harvest-apprentice.py BobVeteran https://github.com/bob/core-lib --trusted

# Custom service name and branch
./_scripts/harvest-apprentice.py Charlie https://github.com/charlie/app \
  --service charlie-analytics \
  --branch develop

# List recent submissions
./_scripts/harvest-apprentice.py --list
```

### Manual Verification

If automated checks are insufficient:

```bash
# Navigate to harvested code
cd STAGING/incoming/service-name/

# Run tests manually
pytest -v

# Check code quality
flake8 .
pylint *.py

# Review security
bandit -r .

# If satisfied, promote manually
cd /path/to/FPAI_Cockpit
git add SERVICES/service-name/
git commit -m "feat: Manual promotion of service-name (verified)"
git push origin main
```

### Troubleshooting Failed Harvests

```bash
# View recent submissions and their status
./_scripts/harvest-apprentice.py --list

# Check logs
tail -f docs/coordination/apprentice-submissions.log

# View detailed error
cat docs/coordination/apprentice-submissions.json | jq '.submissions[-1]'

# Rollback if needed
git log --oneline | head
git revert HEAD  # Revert last harvest
```

---

## 🎓 Common Issues & Solutions

### "Tests Not Found"

**Problem:** No tests directory or test files detected

**Solution:**
```bash
mkdir tests
touch tests/__init__.py
touch tests/test_main.py
```

Add actual tests:
```python
# tests/test_main.py
def test_basic():
    assert 1 + 1 == 2

def test_your_function():
    from your_module import your_function
    result = your_function("test")
    assert result == expected_value
```

### "Tests Failed"

**Problem:** Tests exist but don't pass

**Solution:**
```bash
# Run tests locally to see failures
pytest -v

# Fix the failing tests or code
# Re-run until all pass
pytest -v
```

### "No README"

**Problem:** Missing documentation

**Solution:**
```bash
# Create README.md with template
cat > README.md << 'EOF'
# Project Name

## Description
Brief description of what this service does.

## Setup
```bash
pip install -r requirements.txt
```

## Usage
```python
from your_module import main
main()
```

## API
- `GET /endpoint` - Description
- `POST /endpoint` - Description

## Testing
```bash
pytest tests/
```
EOF
```

### "Hardcoded Secrets"

**Problem:** API keys or passwords in code

**Solution:**
```python
# ❌ BAD - Hardcoded
API_KEY = "sk_live_abc123..."

# ✅ GOOD - Environment variable
import os
API_KEY = os.getenv("API_KEY")

# Use .env file for local development
# Add .env to .gitignore!
```

---

## 📞 Getting Help

- 📧 Email: apprentice-support@fullpotential.ai
- 💬 Discord: #apprentice-submissions
- 📚 Docs: https://docs.fullpotential.ai
- 🐛 Issues: https://github.com/fullpotential/fpai-cockpit/issues

---

## 🎉 Success Stories

> "The pre-flight check caught my hardcoded API key before I submitted. Saved me from a security incident!" - Alice, Backend Apprentice

> "Got 95% on my first submission. The automated feedback was incredibly helpful." - Bob, Full-Stack Apprentice

> "From submission to production in 3 minutes. The harvest system is amazing!" - Charlie, ML Apprentice

---

**Ready to submit? Run the pre-flight check and share your repo URL!** 🚀

