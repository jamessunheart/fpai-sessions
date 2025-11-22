# 🔐 Master Control Dashboard - Architecture

## Vision
Single biometric-authenticated dashboard providing God-mode access to entire Full Potential AI ecosystem.

## Core Features

### 1. Biometric Authentication (Primary)
- **WebAuthn API** - Industry standard for biometrics
- **Face ID** - Mac/iPhone facial recognition
- **Touch ID** - Mac/iPhone fingerprint
- **Windows Hello** - Windows facial/fingerprint
- **Security Keys** - YubiKey as backup

### 2. Multi-Factor Recovery
- **Primary:** Face ID / Touch ID
- **Backup 1:** Registered security key (YubiKey)
- **Backup 2:** Recovery codes (encrypted in vault)
- **Backup 3:** Emergency email link (time-limited)
- **God Mode:** Master biometric + recovery code

### 3. Unified Access Points

**Services Dashboard:**
- Credential Vault (https://fullpotential.com/vault)
- Registry (port 8000)
- Orchestrator (port 8001)
- Dashboard (port 8002)
- I PROACTIVE (port 8400)
- I MATCH (port 8401)
- Church Guidance (fullpotential.com/church)
- All 13 Claude Code sessions

**System Controls:**
- Server health monitoring
- Service start/stop/restart
- Log viewing
- Credential management
- Session management
- Database access

**Financial Dashboard:**
- Revenue tracking
- Treasury management
- Subscription metrics
- Payment processing

### 4. God Mode Authority
- **Never Locked Out:** Multiple biometric fallbacks
- **Always Authority:** Bypass all permissions
- **Instant Recovery:** Biometric-based reset
- **Audit Trail:** All access logged but never blocked

## Technical Stack

### Frontend
- **Framework:** React + TypeScript
- **Auth:** @simplewebauthn/browser (WebAuthn)
- **UI:** Tailwind CSS + shadcn/ui
- **State:** Zustand
- **Charts:** Recharts

### Backend
- **Framework:** FastAPI (Python)
- **Auth:** @simplewebauthn/server equivalent (py_webauthn)
- **Database:** SQLite (biometric credentials)
- **Session:** JWT with biometric binding

### Security
- **Transport:** HTTPS only (TLS 1.3)
- **Storage:** Encrypted biometric challenge/response
- **Recovery:** AES-256 encrypted recovery codes
- **Audit:** Every access logged to audit.log

## URL Structure

**Primary:** https://fullpotential.com/master
**Alt:** https://admin.fullpotential.com (CNAME to master)
**Emergency:** https://fullpotential.com/emergency-recovery

## User Flow

1. Navigate to https://fullpotential.com/master
2. Click "Access with Biometrics"
3. Face ID / Touch ID prompt appears
4. Instant authentication → Master Dashboard
5. See all services, sessions, metrics
6. Click any service → instant authenticated access

## Recovery Flow

**If biometrics fail:**
1. "Biometric Failed" → Show recovery options
2. Option A: Security Key (YubiKey)
3. Option B: Recovery code from vault
4. Option C: Emergency email link (sent to james@fullpotential.ai)
5. All options → Full access restored

## Implementation Phases

**Phase 1 (Now - 30 min):**
- Basic FastAPI backend with WebAuthn
- Simple HTML/JS frontend with biometric button
- Registration flow for Face ID/Touch ID

**Phase 2 (1 hour):**
- Full dashboard UI with all services
- Live service status indicators
- Quick action buttons

**Phase 3 (2 hours):**
- Recovery system with multiple fallbacks
- Audit logging
- Emergency access

**Phase 4 (Deploy):**
- Deploy to https://fullpotential.com/master
- Register your biometrics
- Test recovery flows
