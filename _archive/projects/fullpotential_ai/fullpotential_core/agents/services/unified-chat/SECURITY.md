# 🔐 Security Documentation - Unified Chat Interface

**Authentication & Authorization for Hive Mind Access**

---

## 🎯 Security Model

### **Two-Tier Authentication:**

1. **User Authentication** (You accessing the chat)
   - Password-based login
   - Token-based sessions (24-hour expiry)
   - Secure cookie storage
   - HTTPS recommended for production

2. **Session/Agent Authentication** (Claude sessions & autonomous agents)
   - API key authentication
   - Header-based verification
   - Persistent connections

---

## 🔑 Configuration

### **Edit `config.json`:**

```json
{
  "auth": {
    "user_password": "YOUR_STRONG_PASSWORD_HERE",
    "session_api_key": "YOUR_API_KEY_FOR_SESSIONS",
    "require_auth": true
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8100
  }
}
```

### **Set Strong Credentials:**

```bash
# Generate strong password
openssl rand -base64 32

# Generate API key for sessions
openssl rand -hex 32

# Update config.json with these values
```

---

## 🚀 Usage

### **For You (User):**

1. **Go to:** `http://localhost:8100`
2. **Enter password** from `config.json`
3. **Access granted!** Token valid for 24 hours
4. **Auto re-login** after 24 hours

### **For Claude Sessions:**

Connect with API key in header:

```python
import websockets
import json

async def connect_session():
    uri = "ws://localhost:8100/ws/session/my-session-id"
    headers = {
        "api-key": "YOUR_SESSION_API_KEY"  # From config.json
    }

    async with websockets.connect(uri, extra_headers=headers) as ws:
        # Connected securely!
        pass

asyncio.run(connect_session())
```

---

## 🔒 Security Features

### **Implemented:**
✅ Password authentication for users
✅ API key authentication for sessions/agents
✅ Token-based sessions (24h expiry)
✅ Secure cookie storage (HttpOnly, SameSite)
✅ Automatic token expiration
✅ Unauthorized access blocking
✅ WebSocket authentication

### **Recommended for Production:**
⚠️ Use HTTPS (not HTTP)
⚠️ Use environment variables for secrets (not config file)
⚠️ Rotate API keys regularly
⚠️ Add rate limiting
⚠️ Add IP whitelisting
⚠️ Enable audit logging

---

## 🌐 Production Deployment

### **With HTTPS (Recommended):**

```bash
# Use nginx as reverse proxy with SSL
server {
    listen 443 ssl;
    server_name chat.fullpotential.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### **With Environment Variables:**

```bash
# Don't store secrets in config.json!
export FPAI_USER_PASSWORD="your-strong-password"
export FPAI_SESSION_API_KEY="your-api-key"

# Update main_secure.py to read from env:
import os
USER_PASSWORD = os.environ.get("FPAI_USER_PASSWORD")
SESSION_API_KEY = os.environ.get("FPAI_SESSION_API_KEY")
```

---

## 🛡️ Best Practices

### **DO:**
✅ Use strong, unique passwords (20+ characters)
✅ Use HTTPS in production
✅ Rotate API keys monthly
✅ Use environment variables for secrets
✅ Enable audit logging
✅ Monitor for unauthorized access attempts

### **DON'T:**
❌ Use default passwords
❌ Share API keys in code repositories
❌ Use HTTP in production
❌ Store secrets in plain text files
❌ Reuse passwords across services

---

## 📊 Authentication Flow

```
┌─────────────────────────────────────┐
│  You open: http://localhost:8100   │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  Login page shown                   │
│  Enter password                     │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  POST /api/auth/login               │
│  Server verifies password           │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  ✅ Success:                        │
│  - Generate secure token            │
│  - Store in cookie (24h expiry)     │
│  - Redirect to /chat                │
└─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────┐
│  Chat interface loaded              │
│  WebSocket connection authenticated │
│  Full access to hive mind           │
└─────────────────────────────────────┘
```

---

## 🔄 Session Management

### **Token Lifecycle:**

- **Generated:** On successful login
- **Stored:** Secure HTTP-only cookie
- **Lifetime:** 24 hours
- **Validation:** Every WebSocket connection
- **Expiration:** Auto-cleanup after 24h
- **Renewal:** Re-login required

### **Session Cleanup:**

```python
# Automatic cleanup of expired tokens
def cleanup_expired_tokens():
    now = datetime.utcnow()
    expired = [
        token for token, data in authenticated_users.items()
        if datetime.fromisoformat(data['expires_at']) < now
    ]
    for token in expired:
        del authenticated_users[token]

# Run every hour
```

---

## ⚠️ Security Checklist

Before going to production:

- [ ] Changed default password in config.json
- [ ] Changed default API key in config.json
- [ ] Using HTTPS (not HTTP)
- [ ] Secrets in environment variables (not files)
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] IP whitelisting configured (if needed)
- [ ] Regular security updates
- [ ] Backup authentication enabled
- [ ] Tested authentication flow

---

## 🚨 Emergency Access

### **If You Forget Password:**

```bash
# Reset password in config.json
cd agents/services/unified-chat
nano config.json

# Change "user_password" to new value
# Restart server

# Or disable auth temporarily:
# Set "require_auth": false in config.json
```

### **If Sessions Can't Connect:**

```bash
# Check API key in config.json
cat config.json | grep session_api_key

# Make sure sessions use correct API key in header
# Or disable session auth temporarily
```

---

## 📝 Audit Log (Future Enhancement)

```python
# Log all authentication attempts
def log_auth_attempt(user, success, ip):
    with open("auth.log", "a") as f:
        f.write(f"{datetime.utcnow()} | {user} | {success} | {ip}\n")

# Log all user actions
def log_action(user, action, details):
    with open("activity.log", "a") as f:
        f.write(f"{datetime.utcnow()} | {user} | {action} | {details}\n")
```

---

## 🎯 Quick Setup

### **1. Generate Credentials:**

```bash
# Strong password (copy this!)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Session API key (copy this!)
python3 -c "import secrets; print('fpai-' + secrets.token_hex(32))"
```

### **2. Update config.json:**

```json
{
  "auth": {
    "user_password": "PASTE_PASSWORD_HERE",
    "session_api_key": "PASTE_API_KEY_HERE",
    "require_auth": true
  }
}
```

### **3. Run Secure Server:**

```bash
python3 main_secure.py
```

### **4. Test:**

- Go to `http://localhost:8100`
- Login with your password
- Success! ✅

---

**Status:** 🔐 SECURE VERSION READY
**Auth:** Password + API Key
**Sessions:** Token-based (24h)
**Production Ready:** With HTTPS + env vars

🔒⚡🎯 **ONLY YOU CAN ACCESS THE HIVE MIND!**
