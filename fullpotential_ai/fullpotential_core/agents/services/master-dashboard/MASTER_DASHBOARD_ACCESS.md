# Master Control Dashboard - Access Information

## Access URL
**https://fullpotential.com/master**

## Master Password
```
gDqfvCUrAfZvA17c
```

**IMPORTANT: Save this password securely! This is the ONLY way to access your Master Control Dashboard.**

---

## What You Can Access

The Master Control Dashboard provides unified access to your entire Full Potential AI ecosystem:

### Dashboard Views
1. **Master Control** - Biometric authentication & unified service access
2. **Coordination (Visual)** - Live session coordination with animations (port 8031)
3. **Coordination (Simple)** - Clean table view of session status (port 8030)
4. **System Dashboard** - Real-time system metrics at dashboard.fullpotential.com

### All Services
- **Credential Vault** - API keys and secrets with AES-256 encryption
- **Registry** - Service discovery and health monitoring
- **Orchestrator** - Task coordination and workflow management
- **I PROACTIVE** - Autonomous AI agent system
- **I MATCH** - AI-powered matching engine
- **Church Guidance** - Ministry formation tools
- **White Rock Coaching** - Professional coaching services
- **Claude Sessions** - Manage 13 active AI development sessions

---

## Security Features

✅ **Password Authentication** - Bcrypt hashed password with 12 rounds
✅ **JWT Tokens** - 8-hour session expiration
✅ **Secure Cookies** - HTTP-only, secure, same-site protection
✅ **HTTPS Only** - All traffic encrypted via SSL/TLS
✅ **Protected Routes** - All dashboard pages require authentication

---

## How to Login

1. Visit **https://fullpotential.com/master**
2. Enter the master password: `gDqfvCUrAfZvA17c`
3. Click "Unlock Dashboard"
4. You'll be logged in for 8 hours

---

## API Endpoints

### Login
```bash
curl -X POST https://fullpotential.com/master/api/login \
  -H "Content-Type: application/json" \
  -d '{"password":"gDqfvCUrAfZvA17c"}'
```

### Get Current User
```bash
curl https://fullpotential.com/master/api/me \
  -H "Cookie: access_token=YOUR_TOKEN"
```

### Logout
```bash
curl -X POST https://fullpotential.com/master/api/logout
```

### Health Check
```bash
curl https://fullpotential.com/master/health
```

---

## Technical Details

- **Service**: master-dashboard
- **Port**: 8026 (internal)
- **Public URL**: https://fullpotential.com/master
- **Authentication**: Password + JWT
- **Session Duration**: 8 hours
- **Deployment**: nginx reverse proxy → FastAPI backend

---

## Recovery Options

If you lose access:

1. **Password Reset**: SSH to server and update auth.py with new hash
2. **Direct Server Access**: Access via port 8026 locally on server
3. **Session Files**: Check /root/agents/services/master-dashboard/ for configs

---

## Password Hash (for reference)

Current bcrypt hash stored in auth.py:
```
$2b$12$O6wLfJjzT7dI1mQFp1CaWOG2sKAD.a1R8s5Vn9IkHAXEfkrUSBp1S
```

To generate a new password hash:
```python
import bcrypt
password = "your_new_password"
hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
print(hash.decode('utf-8'))
```

---

## Service Status

Check service status:
```bash
ssh root@198.54.123.234 "curl http://localhost:8026/health"
```

View logs:
```bash
ssh root@198.54.123.234 "tail -f /tmp/master-dashboard.log"
```

Restart service:
```bash
ssh root@198.54.123.234 "pkill -f 'uvicorn.*8026' && cd /root/agents/services/master-dashboard && nohup uvicorn main:app --host 0.0.0.0 --port 8026 > /tmp/master-dashboard.log 2>&1 &"
```

---

**Last Updated**: November 15, 2025
**Deployed By**: Claude Code Session
