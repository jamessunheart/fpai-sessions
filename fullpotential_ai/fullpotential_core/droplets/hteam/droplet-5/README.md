# UDC v1.0

# Droplet #5: Full Potential Dashboard

**Repo:** droplet-5  
**Purpose:** Real-time monitoring and visualization dashboard for the Full Potential mesh network, providing system health, sprint management, and infrastructure oversight.

---

## 1. IDENTITY & STATUS

- **Droplet ID:** #5
- **Function:** Provides real-time visualization and monitoring interface for all droplets, sprints, and system metrics in the Full Potential mesh network.
- **Steward:** @haythemtimoumi
- **Status:** OPERATIONAL
- **Live Endpoint:** https://dashboard.fullpotential.ai
- **Healthcheck:** https://dashboard.fullpotential.ai/health

---

## 2. SYSTEM CONTEXT

- **Upstream Dependencies:** 
  - #18 Registry (JWT authentication, droplet discovery)
  - #10 Orchestrator (heartbeat reporting, task coordination)
  - #2 Airtable Connector (sprint data, proof submissions)
  - #4 Multi-Cloud Manager (infrastructure metrics)

- **Downstream Outputs:** 
  - Provides visualization for all droplets in the mesh
  - Displays system-wide health and performance metrics
  - Sprint management interface for coordinators

- **Related Droplets:** 
  - #12 Chat Orchestrator (chat interface integration)
  - #13 Nexus (intelligence coordination display)

---

## 3. ASSEMBLY LINE SPRINT (Current Work)

- **Current Sprint:** Infrastructure Health Monitoring & UX Enhancement
- **Spec:** UDC_COMPLIANCE.md, Infrastructure UI/UX improvements
- **Apprentice:** @haythemtimoumi
- **Verifier:** Amazon Q Developer
- **PR / Branch:** main
- **Cost / Time (Reported):** 3 h (Health monitoring), 2 h (UI/UX enhancements)

---

## 4. TECHNICAL SSOT (How to Run)

### A. Core Foundation Files

Built against and must adhere to:
- `1-UDC_COMPLIANCE.md`
- `2-TECH_STACK.md`
- `5-SECURITY_REQUIREMENTS.md`
- `4-CODE_STANDARDS.md`
- `3-INTEGRATION_GUIDE.md`

### B. Repository Map

```
/app/
├── api/
│   ├── health/
│   ├── health-check/          # Health proxy for CORS
│   ├── capabilities/
│   ├── state/
│   ├── dependencies/
│   ├── message/
│   ├── send/
│   ├── version/
│   ├── shutdown/
│   ├── reload-config/
│   ├── emergency-stop/
│   └── proxy/
├── components/
│   ├── Sidebar.tsx
│   ├── SprintTable.tsx
│   ├── StatsCard.tsx
│   └── VoiceRecorder.tsx
├── features/
│   ├── analytics/
│   ├── dashboard/
│   ├── infrastructure/
│   └── sprints/
├── lib/
│   ├── api.ts
│   ├── udc.ts
│   ├── startup.ts
│   ├── registry-client.ts
│   └── heartbeat.ts
├── shared/
│   ├── components/
│   ├── contexts/
│   ├── hooks/
│   ├── styles/
│   └── utils/
├── types/
│   └── index.ts
├── globals.css
├── layout.tsx
└── page.tsx

/.env.example
/Dockerfile
/docker-compose.yml
/next.config.js
/package.json
/README.md
/udc_config.json
/tsconfig.json
```

### C. AI Context

- **Primary Model:** Amazon Q Developer  Claude 4.5 Sonnet
- **Foundation Files Used:** 5 (UDC_COMPLIANCE, TECH_STACK, SECURITY_REQUIREMENTS, CODE_STANDARDS, INTEGRATION_GUIDE)
- **AI Prompts Stored:** Yes (in documentation files)

### D. Setup & Run

1. **Clone the repository**
   ```bash
   git clone https://github.com/fullpotential/droplet-5.git
   cd droplet-5
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Copy the environment template**
   ```bash
   cp .env.example .env
   ```

4. **Generate Orchestrator JWT Token**
   ```bash
   pip install PyJWT cryptography
   python test.py
   ```
   Copy the generated token for the next step.

5. **Fill in credentials in .env**
   ```env
   NEXT_PUBLIC_API_URL=https://drop2.fullpotential.ai
   REGISTRY_URL=https://drop18.fullpotential.ai
   REGISTRY_API_KEY=a5447df6e4fe34df8c4d0c671ad98ce78de9e55cf152e5d07e5bf221769e31dc
   ORCHESTRATOR_URL=https://drop10.fullpotential.ai
   ORCHESTRATOR_JWT=<paste_generated_token_here>
   DROPLET_ID=drop5.fullpotential.ai
   ```
   
   **Note:** The Orchestrator JWT token expires after 24 hours. Regenerate using `python test.py` and update .env when needed.

6. **Run locally**
   ```bash
   npm run dev
   ```
   Access at: http://localhost:3000

7. **Build for production**
   ```bash
   npm run build
   npm start
   ```

8. **Run with Docker**
   ```bash
   docker-compose up -d
   ```

---

## 5. UDC COMPLIANCE STATUS

### Core Endpoints (6/6) ✅
- ✅ `GET /health` - Droplet status and health
- ✅ `GET /capabilities` - Feature declarations (includes udc_version: "1.0")
- ✅ `GET /state` - Resource usage and performance metrics
- ✅ `GET /dependencies` - Connected droplets
- ✅ `POST /message` - Receive UDC messages
- ✅ `POST /send` - Send messages to other droplets

### Extended Endpoints (4/4) ✅
- ✅ `GET /version` - Build and deployment info
- ✅ `POST /shutdown` - Graceful shutdown
- ✅ `POST /reload-config` - Hot config reload
- ✅ `POST /emergency-stop` - Emergency shutdown

### Integration (6/6) ✅
- ✅ Auto-registers with Registry on startup
- ✅ Sends heartbeat to Registry every 30s
- ✅ Auto-registers with Orchestrator on startup
- ✅ Sends heartbeat to Orchestrator every 60s
- ✅ Graceful shutdown handlers (SIGTERM/SIGINT)
- ✅ udc_config.json configured

### Response Standards ✅
- ✅ Success responses use UDC format with timestamps
- ✅ Error responses use standard error codes
- ✅ All responses include timestamps

**Compliance Score:** 100% ✅

---

## 6. VERIFICATION HISTORY

| Date | Verifier | Branch/PR | Result | Notes |
|------|----------|-----------|--------|-------|
| 2025-01-15 | Amazon Q Developer | main | PASS | Full UDC compliance verified. All 10 endpoints implemented correctly. |
| 2025-01-15 | Amazon Q Developer | main | PASS | Registry fix applied (both id and droplet_id fields). |
| 2025-01-15 | Amazon Q Developer | main | PASS | Registry v2 integration working with valid API key. |
| 2025-11-16 | Amazon Q Developer | main | PASS | Orchestrator integration complete. Registration and heartbeat working with RS256 JWT tokens. |
| 2025-11-16 | Amazon Q Developer | main | PASS | Infrastructure health monitoring implemented. Real-time status indicators with UDC compliance. |
| 2025-01-18 | Amazon Q Developer | main | PASS | Fixed Droplet #5 health check to use dashboard.fullpotential.ai instead of drop5.fullpotential.ai. |

---

## 7. NOTES & IMPROVEMENTS

- **[Apprentice Note 2025-01-15]:** Successfully implemented all UDC core and extended endpoints. Dashboard is fully compliant with UDC v1.0 specification.

- **[Verifier Note 2025-01-15]:** All endpoints verified and working. Registry integration includes fix from Droplet #6 (both id and droplet_id fields in payloads).

- **[System Note]:** Dashboard integrates with Registry (#18) for authentication and Orchestrator (#10) for coordination. Auto-registration and heartbeat services implemented.

- **[External Services 2025-11-16]:** Registry v2 integration working. Orchestrator integration complete with RS256 JWT authentication. Both registration and heartbeat endpoints operational.

- **[Infrastructure Enhancement 2025-11-16]:** Real-time health monitoring implemented with UDC-compliant status indicators (active/inactive/error). CORS proxy added for cross-origin health checks. Manual refresh with 5-second cooldown to prevent rate limiting.

- **[Bug Fix 2025-01-18]:** Fixed infrastructure page to use dashboard.fullpotential.ai for Droplet #5's health checks instead of drop5.fullpotential.ai, ensuring correct state monitoring.

---

## 8. TECH STACK

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript (strict mode)
- **Styling:** Tailwind CSS
- **UI Components:** Shadcn/ui
- **Charts:** Recharts
- **Icons:** Lucide Icons
- **State Management:** React Context + Zustand
- **HTTP Client:** Fetch API
- **Authentication:** RS256 JWT (Registry v2 + Orchestrator)
- **Token Generation:** Python (PyJWT + cryptography)
- **Deployment:** Docker + Docker Compose

---

## 9. FEATURES

- 📊 **Real-time Monitoring** - Live droplet health and status with UDC compliance
- 🎯 **Sprint Management** - View and manage all sprints
- 💻 **System Health** - Monitor infrastructure and performance
- 📈 **Analytics** - Daily digest and performance metrics
- 💬 **Chat Interface** - System communication
- 🎨 **Dark/Light Mode** - Theme switching support with full readability
- 🔄 **Manual Refresh** - On-demand health data updates with rate limiting
- 🔐 **JWT Authentication** - Secure droplet communication
- 🟢 **Status Indicators** - Color-coded health status (Active/Inactive/Error/Offline)
- 🚀 **Premium UI** - Enhanced modal design with smooth animations
- 🔍 **Advanced Search** - Filter droplets by ID, name, host, or role
- ⚡ **Performance Optimized** - React.memo for efficient rendering

---

## 10. RELATED DOCS

- [UDC_COMPLIANCE.md](./1-UDC_COMPLIANCE.md) - Universal Droplet Contract specification
- [TECH_STACK.md](./2-TECH_STACK.md) - Technology standards and guidelines
- [INTEGRATION_GUIDE.md](./3-INTEGRATION_GUIDE.md) - Droplet integration patterns
- [CODE_STANDARDS.md](./4-CODE_STANDARDS.md) - Coding standards and best practices
- [SECURITY_REQUIREMENTS.md](./5-SECURITY_REQUIREMENTS.md) - Security guidelines
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Quick reference guide
- [test.py](./test.py) - Orchestrator JWT token generator

---

**Last Updated:** 2025-01-18  
**UDC Version:** 1.0  
**Droplet Status:** OPERATIONAL ✅

---

## 11. ORCHESTRATOR AUTHENTICATION

### Token Generation

The Orchestrator uses RS256 JWT tokens for authentication. Tokens are generated using a shared private key and expire after 24 hours.

**Generate a new token:**
```bash
python test.py
```

**Token payload:**
```json
{
  "droplet_id": 5,
  "steward": "Haythem",
  "permissions": ["read", "write"],
  "iat": <current_timestamp>,
  "exp": <timestamp_24h_later>
}
```

### Token Refresh

Tokens expire after 24 hours. To refresh:

1. Run `python test.py` to generate a new token
2. Update `ORCHESTRATOR_JWT` in `.env`
3. Restart the application

### Files

- `private_key.pem` - RSA private key for signing tokens (shared across droplets)
- `test.py` - Token generation script
- `generate_keys.py` - Key pair generation (if needed)
