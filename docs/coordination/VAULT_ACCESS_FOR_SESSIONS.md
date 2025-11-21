# Vault Access - Quick Guide for All Sessions

**Last Updated**: 2025-11-16
**For**: All Claude Code Sessions

---

## 🔑 The ONE Thing You Need From User

Ask user for this **ONCE per session**:

```bash
export FPAI_CREDENTIALS_KEY="0090050b4ac419b69bfd0b7763d861fd11619255f672b4122c34b97abe12d63f"
```

**Never ask for individual credentials** - they're all in the vault!

---

## 📍 Vault Location

**Encrypted file**: `/Users/jamessunheart/Development/docs/coordination/.credentials`
**Scripts**: `/Users/jamessunheart/Development/docs/coordination/scripts/`

All sessions share the same vault. Read/write access for all.

---

## 🛠️ Common Operations

### 1. List All Available Credentials

```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts
./session-list-credentials.sh
```

**Output**:
```
📋 Stored credentials:
  - anthropic_api_key (api_key) [anthropic]
  - openai_api_key (api_key)
  - STRIPE_SECRET_KEY (api_key)
  - STRIPE_PUBLISHABLE_KEY (api_key)
  - NAMECHEAP_API_USER (api_key) [namecheap]
  - NAMECHEAP_API_KEY (api_key) [namecheap]
  - server_admin_password (password) [credentials-manager]
  - server_master_encryption_key (secret) [credentials-manager]
  - server_jwt_secret (secret) [credentials-manager]
  - test_key (api_key) [test]
```

### 2. Get a Specific Credential

```bash
# Get ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=$(./session-get-credential.sh anthropic_api_key)

# Get OpenAI key
export OPENAI_API_KEY=$(./session-get-credential.sh openai_api_key)

# Get Stripe secret
export STRIPE_SECRET_KEY=$(./session-get-credential.sh STRIPE_SECRET_KEY)

# Get server admin password
export ADMIN_PASSWORD=$(./session-get-credential.sh server_admin_password)
```

### 3. Add a New Credential to Vault

```bash
./session-set-credential.sh <name> <value> [type] [service]
```

**Examples**:
```bash
# Add SendGrid API key
./session-set-credential.sh sendgrid_api_key "SG.xxxxx" api_key sendgrid

# Add database password
./session-set-credential.sh db_password "securepass123" password postgres

# Add GitHub token
./session-set-credential.sh github_token "ghp_xxxxx" access_token github

# Add custom API key
./session-set-credential.sh custom_api_key "key_value" api_key my_service
```

**Types**: `api_key`, `access_token`, `password`, `connection_string`, `secret`

### 4. Delete a Credential

```bash
./session-delete-credential.sh <name>
```

**Example**:
```bash
./session-delete-credential.sh old_api_key
```

---

## ✅ Best Practices

### DO:
✅ Check vault FIRST before asking user for credentials
✅ Add new credentials to vault when you receive them
✅ Use descriptive names (e.g., `sendgrid_api_key`, not `key1`)
✅ Specify the service parameter for clarity
✅ List credentials to see what's available

### DON'T:
❌ Ask user for credentials that might be in vault
❌ Store credentials in .env files (use vault instead)
❌ Hardcode credentials in code
❌ Share credentials across insecure channels
❌ Delete credentials without coordination

---

## 🔐 Security

- **Encryption**: AES-256 with Fernet
- **Key Derivation**: PBKDF2HMAC
- **Master Key**: `FPAI_CREDENTIALS_KEY` (64 hex characters)
- **Permissions**: Only sessions with master key can access
- **Backup**: `.credentials` file should be backed up securely

---

## 📋 Protocol Compliance

From BOOT.md:
> **Get credentials (NEVER ask user first!):**
> ```bash
> ./scripts/session-list-credentials.sh
> export ANTHROPIC_API_KEY=$(./scripts/session-get-credential.sh anthropic_api_key)
> ```

**Always check vault before asking user for credentials.**

---

## 🤝 Multi-Session Coordination

**Vault is shared by all 11+ sessions**:
- Session #1, #2, #3, #4, #5, #6, #7, #8, #9, #10, #11, #13
- Any session can read/write
- Changes are immediately available to all sessions
- No conflicts - vault handles concurrent access

**When adding important credentials**:
1. Add to vault with `session-set-credential.sh`
2. Broadcast to other sessions with `session-send-message.sh`
3. Document in your session notes

**Example**:
```bash
# Add credential
./session-set-credential.sh sendgrid_api_key "SG.xxxxx" api_key sendgrid

# Notify other sessions
./session-send-message.sh "broadcast" "SendGrid Key Added" "sendgrid_api_key now available in vault for email services" "normal"
```

---

## 🚀 Quick Start Examples

### Example 1: AI Service Needs Claude API

```bash
# Set master key (ask user once)
export FPAI_CREDENTIALS_KEY="0090050b4ac419b69bfd0b7763d861fd11619255f672b4122c34b97abe12d63f"

# Get from vault (never ask user)
export ANTHROPIC_API_KEY=$(./session-get-credential.sh anthropic_api_key)

# Use it
python3 my_ai_service.py
```

### Example 2: Payment Service Needs Stripe

```bash
# Set master key
export FPAI_CREDENTIALS_KEY="0090050b4ac419b69bfd0b7763d861fd11619255f672b4122c34b97abe12d63f"

# Get both Stripe keys from vault
export STRIPE_SECRET_KEY=$(./session-get-credential.sh STRIPE_SECRET_KEY)
export STRIPE_PUBLISHABLE_KEY=$(./session-get-credential.sh STRIPE_PUBLISHABLE_KEY)

# Use them
python3 payment_service.py
```

### Example 3: User Provides New Credential

```bash
# User says: "Here's the SendGrid key: SG.xxxxx"

# Add to vault immediately
./session-set-credential.sh sendgrid_api_key "SG.xxxxx" api_key sendgrid

# Broadcast to team
./session-send-message.sh "broadcast" "SendGrid Added" "sendgrid_api_key available in vault" "normal"

# Use it
export SENDGRID_API_KEY=$(./session-get-credential.sh sendgrid_api_key)
python3 email_service.py
```

### Example 4: Deploy Service with Vault Credentials

```bash
# Set master key
export FPAI_CREDENTIALS_KEY="0090050b4ac419b69bfd0b7763d861fd11619255f672b4122c34b97abe12d63f"

# Get all needed credentials
export ANTHROPIC_API_KEY=$(./session-get-credential.sh anthropic_api_key)
export DB_PASSWORD=$(./session-get-credential.sh db_password)

# Deploy to server with credentials
ssh root@server "cd /root/service && \
  ANTHROPIC_API_KEY='$ANTHROPIC_API_KEY' \
  DB_PASSWORD='$DB_PASSWORD' \
  nohup python3 main.py &"
```

---

## 🆘 Troubleshooting

### Error: "FPAI_CREDENTIALS_KEY not set"
**Solution**: Ask user for master key once:
```bash
export FPAI_CREDENTIALS_KEY="0090050b4ac419b69bfd0b7763d861fd11619255f672b4122c34b97abe12d63f"
```

### Error: "Credential not found"
**Solution**: List available credentials to see what's in vault:
```bash
./session-list-credentials.sh
```

If credential truly doesn't exist, ask user for it, then add to vault.

### Error: "Permission denied"
**Solution**: Make sure you're running from correct directory:
```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts
```

### Want to see what's in vault without decrypting?
**Not possible** - vault is encrypted. Use `session-list-credentials.sh` instead.

---

## 📊 Current Vault Contents

**As of 2025-11-16**:

| Credential Name | Type | Service | Added By |
|-----------------|------|---------|----------|
| anthropic_api_key | api_key | anthropic | Session #3 |
| openai_api_key | api_key | - | - |
| STRIPE_SECRET_KEY | api_key | - | - |
| STRIPE_PUBLISHABLE_KEY | api_key | - | - |
| NAMECHEAP_API_USER | api_key | namecheap | - |
| NAMECHEAP_API_KEY | api_key | namecheap | - |
| server_admin_password | password | credentials-manager | - |
| server_master_encryption_key | secret | credentials-manager | - |
| server_jwt_secret | secret | credentials-manager | - |
| test_key | api_key | test | - |

**Total**: 10 credentials

**Still Needed**:
- sendgrid_api_key (for email automation)
- sendgrid_from_email (optional)

---

## 💡 Remember

**The vault exists so you NEVER have to ask the user for the same credential twice.**

If a session asks for `ANTHROPIC_API_KEY` and you add it to the vault, **every future session** can retrieve it automatically. This is the entire point of centralization.

---

**Questions?** Check `/docs/coordination/VAULT_QUICK_REFERENCE.md` or ask Session #2 (Coordination & Infrastructure)
