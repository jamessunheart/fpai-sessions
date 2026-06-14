# 🔐 Credential Recovery Guide

**IMPORTANT:** Keep this file secure! It contains recovery information.

---

## 🆘 Emergency Recovery

### If You Lose Access to Credentials-Manager

**All recovery keys are stored in your local encrypted vault.**

To recover:

```bash
cd /Users/jamessunheart/Development/docs/coordination

# List all recovery credentials
./scripts/session-list-credentials.sh | grep server_

# Get admin password
./scripts/session-get-credential.sh server_admin_password

# Get master encryption key
./scripts/session-get-credential.sh server_master_encryption_key

# Get JWT secret
./scripts/session-get-credential.sh server_jwt_secret
```

---

## 🔑 Current Credentials

### Server Credentials-Manager

**🌐 Live URL:** https://fullpotential.com/vault
**📚 API Documentation:** https://fullpotential.com/vault/docs
**💓 Health Check:** https://fullpotential.com/vault/health

**Admin Access:**
- Username: `admin`
- Password: Stored in vault as `server_admin_password`
- Get it: `./scripts/session-get-credential.sh server_admin_password`

**Internal Access (from server):**
- Direct IP: http://198.54.123.234:8025
- Localhost: http://127.0.0.1:8025

**Encryption Keys:**
- Master Encryption Key: Stored as `server_master_encryption_key`
- JWT Secret: Stored as `server_jwt_secret`

### Local Mac Vault

**Master Key:**
- Environment variable: `FPAI_CREDENTIALS_KEY`
- Value: `0090050b4ac419b69bfd0b7763d861fd11619255f672b4122c34b97abe12d63f`
- Location: `~/.zshrc`

**Vault File:**
- Path: `/Users/jamessunheart/Development/docs/coordination/.credentials`
- Format: AES-256 encrypted JSON
- Never commit to git (already in .gitignore)

---

## 🚨 What If I Lose My Local Mac Vault?

### Recovery Steps:

**1. Check if master key is in your shell profile:**
```bash
cat ~/.zshrc | grep FPAI_CREDENTIALS_KEY
```

**2. If key is there, vault file can be recreated:**
- Your vault is just an encrypted file
- As long as you have the master key, you can recreate it
- Store new credentials using `./scripts/session-set-credential.sh`

**3. If key is lost, you'll need to:**
- Generate new master key: `python3 -c 'import secrets; print(secrets.token_hex(32))'`
- Set it: `export FPAI_CREDENTIALS_KEY=new_key`
- Delete old vault: `rm .credentials`
- Re-store all credentials

**4. Server credentials are still safe:**
- Server credentials-manager has its own encryption keys
- Stored in `/root/SERVICES/credentials-manager/.env`
- Not dependent on your local vault

---

## 🔄 How to Reset Server Admin Password

If you forget the admin password:

**1. Get the password from local vault:**
```bash
./scripts/session-get-credential.sh server_admin_password
```

**2. Or reset it manually on server:**
```bash
# SSH to server
ssh root@198.54.123.234

# Generate new password hash
python3 -c "import bcrypt; pw=input('New password: '); print(bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode())"

# Update .env file
cd /root/SERVICES/credentials-manager
nano .env  # Update ADMIN_PASSWORD_HASH

# Restart service
pkill -f "uvicorn app.main:app --host 0.0.0.0 --port 8025"
uvicorn app.main:app --host 0.0.0.0 --port 8025 > /tmp/cm.log 2>&1 &
```

---

## 💾 Backup Strategy

### What to Backup:

**1. Local Mac:**
- `~/.zshrc` (contains FPAI_CREDENTIALS_KEY)
- `/Users/jamessunheart/Development/docs/coordination/.credentials` (encrypted vault)
- This recovery document

**2. Server:**
- `/root/SERVICES/credentials-manager/.env` (encryption keys)
- `/root/SERVICES/credentials-manager/credentials.db` (encrypted credentials database)

**3. How to Backup:**
```bash
# Backup from Mac
mkdir -p ~/Backups/fpai-credentials
cp ~/.zshrc ~/Backups/fpai-credentials/
cp /Users/jamessunheart/Development/docs/coordination/.credentials ~/Backups/fpai-credentials/
cp /Users/jamessunheart/Development/docs/coordination/CREDENTIAL_RECOVERY.md ~/Backups/fpai-credentials/

# Backup from server
scp root@198.54.123.234:/root/SERVICES/credentials-manager/.env ~/Backups/fpai-credentials/server-env
scp root@198.54.123.234:/root/SERVICES/credentials-manager/credentials.db ~/Backups/fpai-credentials/server-db

# Encrypt the backup folder
tar czf ~/Backups/fpai-$(date +%Y%m%d).tar.gz ~/Backups/fpai-credentials/
rm -rf ~/Backups/fpai-credentials/
```

---

## 🔐 Security Best Practices

### ✅ DO:

1. **Keep master key in environment only**
   - Never hardcode in files (except ~/.zshrc which is local)
   - Never commit to git

2. **Backup regularly**
   - Weekly: Backup .credentials file
   - Monthly: Backup server .env and database

3. **Rotate credentials**
   - Change admin password every 90 days
   - Rotate encryption keys annually

4. **Use different keys for dev vs prod**
   - Local vault: Development API keys
   - Server vault: Production API keys

### ❌ DON'T:

1. **Never share master key**
   - Each person should have their own
   - Server has its own separate key

2. **Never commit sensitive files**
   - `.credentials` is git-ignored
   - `.env` is git-ignored
   - Double-check before git push

3. **Never log credentials**
   - Don't print credential values to console
   - Log credential names only

4. **Never email/slack credentials**
   - Use the credential vault
   - Share access tokens (time-limited) instead

---

## 📞 Quick Reference

### Get Server Admin Access:
```bash
# Username
echo "admin"

# Password
./scripts/session-get-credential.sh server_admin_password
```

### Login to Server Credentials-Manager:
```bash
# Get admin token (using live URL)
curl -X POST https://fullpotential.com/vault/auth/admin \
  -d "username=admin&password=$(./scripts/session-get-credential.sh server_admin_password)"

# Or using direct IP
curl -X POST http://198.54.123.234:8025/auth/admin \
  -d "username=admin&password=$(./scripts/session-get-credential.sh server_admin_password)"
```

### Test Local Vault:
```bash
# Store test
./scripts/session-set-credential.sh test_key test_value

# Retrieve test
./scripts/session-get-credential.sh test_key

# Delete test
./scripts/session-delete-credential.sh test_key
```

---

## ✅ System Status Check

```bash
# Check local vault
echo $FPAI_CREDENTIALS_KEY
./scripts/session-list-credentials.sh

# Check server service (live URL)
curl -s https://fullpotential.com/vault/health

# Or from server directly
ssh root@198.54.123.234 'curl -s http://localhost:8025/health'
```

---

**Last Updated:** 2025-11-15
**Next Review:** 2026-02-15 (3 months)

🔐 Keep this document secure! 🔐
