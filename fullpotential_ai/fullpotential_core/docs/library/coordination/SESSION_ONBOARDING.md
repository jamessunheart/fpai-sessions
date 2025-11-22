# 🚀 Session Onboarding - Start Here!

**Welcome, Claude Code Session!**

This guide gets you productive in 2 minutes.

---

## ⚡ Quick Start (2 Minutes)

### 1. Check Your Environment (30 seconds)
```bash
# Are you in the right place?
pwd
# Should be: /Users/jamessunheart/Development or subdirectory

# Check if credentials key is loaded
echo $FPAI_CREDENTIALS_KEY
# Should show: 0090050b4ac419b69bfd0b7763d861fd11619255f672b4122c34b97abe12d63f
# If empty: source ~/.zshrc
```

### 2. Load Credentials You Need (30 seconds)
```bash
cd /Users/jamessunheart/Development/docs/coordination

# List what's available
./scripts/session-list-credentials.sh

# Load common credentials
export ANTHROPIC_API_KEY=$(./scripts/session-get-credential.sh anthropic_api_key 2>/dev/null || echo "")
export OPENAI_API_KEY=$(./scripts/session-get-credential.sh openai_api_key 2>/dev/null || echo "")

# Verify
echo "Anthropic: ${ANTHROPIC_API_KEY:0:10}..."
echo "OpenAI: ${OPENAI_API_KEY:0:10}..."
```

### 3. Register Your Session (30 seconds)
```bash
# Register with coordination system
./scripts/session-start.sh

# Check what others are doing
./scripts/session-status.sh
```

### 4. Search for Knowledge (30 seconds)
```bash
# Search for relevant patterns/learnings
./scripts/session-search-knowledge.sh "your topic"

# Example: Building a service?
./scripts/session-search-knowledge.sh "service"
./scripts/session-search-knowledge.sh "SPEC"
```

**You're ready to work!** 🎉

---

## 🎯 Common Workflows

### Building a New Service

```bash
# 1. Search for patterns
./scripts/session-search-knowledge.sh "service" patterns

# 2. Claim the work
./scripts/session-claim.sh droplet my-service 4

# 3. Get credentials if needed
export ANTHROPIC_API_KEY=$(./scripts/session-get-credential.sh anthropic_api_key)

# 4. Build...

# 5. Share what you learned
./scripts/session-share-learning.sh pattern "Services" "Pattern you discovered" "High"

# 6. Release claim
./scripts/session-release.sh droplet my-service
```

### Testing/Debugging

```bash
# 1. Load test credentials
export ANTHROPIC_API_KEY=$(./scripts/session-get-credential.sh anthropic_api_key)

# 2. Search for troubleshooting tips
./scripts/session-search-knowledge.sh "pytest" troubleshooting

# 3. Run tests
pytest

# 4. Share solution if you fixed something
./scripts/session-share-learning.sh troubleshooting "Testing" "How you fixed it" "Medium"
```

### Deploying to Server

```bash
# 1. Get server admin password
SERVER_PASS=$(./scripts/session-get-credential.sh server_admin_password)

# 2. Use server credential vault API
# Live URL: https://fullpotential.com/vault
# API Docs: https://fullpotential.com/vault/docs

# 3. Deploy...

# 4. Share deployment notes
./scripts/session-share-learning.sh best-practice "Deployment" "What worked well" "High"
```

---

## 🔐 Credentials Quick Reference

### Available Credentials
```bash
# List all
./scripts/session-list-credentials.sh
```

### Common Credentials

**Development:**
- `anthropic_api_key` - Anthropic Claude API
- `openai_api_key` - OpenAI GPT API
- `github_token` - GitHub access token

**Server Access:**
- `server_admin_password` - Credentials-manager admin password
- `server_master_encryption_key` - Server encryption key
- `server_jwt_secret` - Server JWT secret

**Server Vault Access:**
- Live URL: https://fullpotential.com/vault
- API Docs: https://fullpotential.com/vault/docs
- Health: https://fullpotential.com/vault/health

### Get a Credential
```bash
# Just the value
./scripts/session-get-credential.sh credential_name

# Use in export
export API_KEY=$(./scripts/session-get-credential.sh anthropic_api_key)
```

### Store a Credential (If User Gives You One)
```bash
./scripts/session-set-credential.sh name "value" api_key service
```

**NEVER:**
- ❌ Hardcode credentials
- ❌ Commit credentials to git
- ❌ Ask user for credentials that are already in vault

**ALWAYS:**
- ✅ Check vault first: `./scripts/session-list-credentials.sh`
- ✅ Use credential scripts
- ✅ Store new credentials user provides

---

## 📚 Knowledge Broadcasting

### Before Starting Work
```bash
# Search for relevant knowledge
./scripts/session-search-knowledge.sh "your topic"

# Specific categories
./scripts/session-search-knowledge.sh "JWT" patterns
./scripts/session-search-knowledge.sh "deployment" troubleshooting
./scripts/session-search-knowledge.sh "testing" best-practices
```

### After Completing Work
```bash
# Share what you learned
./scripts/session-share-learning.sh learning "Category" "What you learned" "Impact"

# Share a reusable pattern
./scripts/session-share-learning.sh pattern "Category" "Pattern description" "Impact"

# Share a solution
./scripts/session-share-learning.sh troubleshooting "Category" "Problem & solution" "Impact"

# Share best practice
./scripts/session-share-learning.sh best-practice "Category" "Effective approach" "Impact"
```

**Impact levels:** Low, Medium, High, Critical

---

## 🤝 Session Coordination

### Check What Others Are Doing
```bash
./scripts/session-status.sh
```

### Claim Work (Prevents Conflicts)
```bash
./scripts/session-claim.sh droplet service-name 4  # 4 hours
./scripts/session-claim.sh file important-file.py 2  # 2 hours
```

### Send Heartbeats (Show Progress)
```bash
./scripts/session-heartbeat.sh "building" "service-name" "BUILD - core logic" "50%" "next: tests"
```

### Message Other Sessions
```bash
# Broadcast to all
./scripts/session-send-message.sh broadcast "Subject" "Message"

# Direct message
./scripts/session-send-message.sh session-123 "Subject" "Message"
```

### Check Messages
```bash
./scripts/session-check-messages.sh
```

### Release Work When Done
```bash
./scripts/session-release.sh droplet service-name
```

---

## 📖 Full Documentation

**Core Guides:**
- `QUICK_START.md` - Complete coordination guide
- `SECURE_CREDENTIALS.md` - Credential vault documentation
- `CREDENTIAL_RECOVERY.md` - Recovery procedures
- `KNOWLEDGE_BROADCASTING.md` - Knowledge sharing guide

**Quick Access:**
```bash
cd /Users/jamessunheart/Development/docs/coordination
ls *.md  # See all guides
```

---

## ✅ Pre-Work Checklist

Before starting ANY work:

- [ ] Environment loaded: `echo $FPAI_CREDENTIALS_KEY`
- [ ] Credentials loaded: `./scripts/session-list-credentials.sh`
- [ ] Session registered: `./scripts/session-start.sh`
- [ ] Checked status: `./scripts/session-status.sh`
- [ ] Searched knowledge: `./scripts/session-search-knowledge.sh "topic"`
- [ ] Claimed work: `./scripts/session-claim.sh ...`

**Now you're ready to be productive!** 🚀

---

## 🆘 Quick Troubleshooting

**"FPAI_CREDENTIALS_KEY not set":**
```bash
source ~/.zshrc
```

**"Credential not found":**
```bash
./scripts/session-list-credentials.sh  # See what's available
```

**"No active session":**
```bash
./scripts/session-start.sh  # Register first
```

**"Can't find scripts":**
```bash
cd /Users/jamessunheart/Development/docs/coordination
```

---

**You're all set! Start building!** ⚡💎🚀
