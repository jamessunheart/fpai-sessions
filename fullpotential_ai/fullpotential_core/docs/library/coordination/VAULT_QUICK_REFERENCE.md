# 🔐 Credential Vault - Quick Reference

## 🌐 Live URL
**https://fullpotential.com/vault**

## ⚡ Quick Access

### Get a Credential (30 seconds)
```bash
cd /Users/jamessunheart/Development/docs/coordination
source ~/.zshrc
./scripts/session-get-credential.sh anthropic_api_key
```

### List All Available
```bash
./scripts/session-list-credentials.sh
```

### Use in Your Code
```bash
export ANTHROPIC_API_KEY=$(./scripts/session-get-credential.sh anthropic_api_key)
export OPENAI_API_KEY=$(./scripts/session-get-credential.sh openai_api_key)
```

## 📚 Resources

- **API Docs:** https://fullpotential.com/vault/docs
- **Health Check:** https://fullpotential.com/vault/health
- **Full Guide:** docs/coordination/SESSION_ONBOARDING.md
- **Recovery:** docs/coordination/CREDENTIAL_RECOVERY.md

## ❌ NEVER

- Ask user for API keys (check vault first!)
- Hardcode credentials in code
- Commit credentials to git

## ✅ ALWAYS

1. Check vault FIRST before asking user
2. Use credential scripts (not manual copy/paste)
3. Store new credentials user provides

---
**Live URL:** https://fullpotential.com/vault 🌐🔐⚡
