# UDC v1.0

# Droplet #2: Airtable Connector

**Repo:** droplet-2  
**Purpose:** Airtable integration service for the Full Potential mesh network, providing CRUD operations for sprints, cells, proof submissions, and heartbeat data.

---

## 1. IDENTITY & STATUS

- **Droplet ID:** #2
- **Function:** Provides Airtable integration for sprint management, proof submissions, cell tracking, and heartbeat monitoring.
- **Steward:** @haythemtimoumi
- **Status:** OPERATIONAL
- **Live Endpoint:** https://drop2.fullpotential.ai
- **Healthcheck:** https://drop2.fullpotential.ai/health

---

## 2. SYSTEM CONTEXT

- **Upstream Dependencies:** 
  - #18 Registry (JWT authentication, droplet discovery)
  - #10 Orchestrator (heartbeat reporting, task coordination)
  - Airtable API (data storage and retrieval)

- **Downstream Outputs:** 
  - Provides sprint data to Dashboard (#5)
  - Stores proof submissions for verification
  - Tracks cell activities and heartbeats
  - Manages sprint lifecycle data

- **Related Droplets:** 
  - #5 Dashboard (consumes sprint and proof data)
  - #10 Orchestrator (receives heartbeat data)
  - #18 Registry (authentication and discovery)

---

## 3. ASSEMBLY LINE SPRINT (Current Work)

- **Current Sprint:** Modular Architecture Migration & Port Configuration Fix
- **Spec:** UDC_COMPLIANCE.md, Modular codebase restructure
- **Apprentice:** @haythemtimoumi
- **Verifier:** Amazon Q Developer
- **PR / Branch:** main
- **Cost / Time (Reported):** 4 h (Architecture migration), 1 h (Port fix)

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
│   └── routes/
│       ├── airtable.py        # Airtable CRUD operations
│       ├── emergency.py       # Emergency endpoints
│       ├── health.py          # UDC health endpoints
│       ├── management.py      # Config management
│       └── message.py         # UDC messaging
├── models/
│   ├── domain.py              # Business models
│   └── udc.py                 # UDC protocol models
├── services/
│   ├── airtable_service.py    # Airtable integration
│   ├── auth_manager.py        # JWT authentication
│   ├── heartbeat.py           # Orchestrator heartbeat
│   ├── message_handler.py     # Message processing
│   ├── orchestrator.py        # Orchestrator client
│   ├── orchestrator_client.py # Token generation
│   ├── registry.py            # Registry client
│   ├── token_manager.py       # JWT token management
│   └── private_key.pem        # RSA private key
├── utils/
│   ├── auth.py                # Auth utilities
│   ├── logging.py             # Logging setup
│   └── metrics.py             # Performance metrics
├── config.py                  # Configuration
└── main.py                    # FastAPI app

/tests/
├── test_health.py
└── __init__.py

/.env.example
/.dockerignore
/airtable-server.service
/deploy.sh
/docker-compose.yml
/Dockerfile
/install.sh
/main.py
/monitor.sh
/README.md
/requirements.txt
```

### C. AI Context

- **Primary Model:** Amazon Q Developer
- **Foundation Files Used:** 5 (UDC_COMPLIANCE, TECH_STACK, SECURITY_REQUIREMENTS, CODE_STANDARDS, INTEGRATION_GUIDE)
- **AI Prompts Stored:** Yes (in .amazonq/rules/)

### D. Setup & Run

#### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/fullpotential-ai/droplet-2.git
   cd droplet-2
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Copy the environment template**
   ```bash
   cp .env.example .env
   ```

4. **Fill in credentials in .env**
   ```env
   DROPLET_ID=2
   DROPLET_REGISTRY_ID=drop2.fullpotential.ai
   DROPLET_NAME=Airtable Connector
   DROPLET_STEWARD=Haythem
   DROPLET_URL=https://drop2.fullpotential.ai
   REGISTRY_URL=https://drop18.fullpotential.ai
   ORCHESTRATOR_URL=https://drop10.fullpotential.ai
   AIRTABLE_API_KEY=<your_airtable_api_key>
   BASE_ID=<your_base_id>
   PORT=8000
   ```

5. **Run locally**
   ```bash
   python main.py
   ```
   Access at: http://localhost:8000

#### Production Deployment

1. **On the server, navigate to directory**
   ```bash
   cd /root/airtable-server
   ```

2. **Pull latest code**
   ```bash
   git pull
   ```

3. **Deploy with Docker**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

4. **Or use docker-compose**
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

5. **View logs**
   ```bash
   docker-compose logs -f
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
| 2025-11-19 | Amazon Q Developer | main | PASS | Migrated to modular architecture from droplet_0 codebase. |
| 2025-11-19 | Amazon Q Developer | main | PASS | Fixed hardcoded localhost:8001 to use DROPLET_URL from env. |
| 2025-11-19 | Amazon Q Developer | main | PASS | Fixed port configuration from 8003 to 8000 for nginx compatibility. |
| 2025-11-19 | Amazon Q Developer | main | PASS | Registry and Orchestrator integration working with auto-generated JWT tokens. |
| 2025-11-19 | Amazon Q Developer | main | PASS | All UDC endpoints verified and operational. |

---

## 7. NOTES & IMPROVEMENTS

- **[Architecture Migration 2025-11-19]:** Successfully migrated from monolithic structure to modular architecture with separate api/models/services/utils layers. Improved code organization and maintainability.

- **[Bug Fix 2025-11-19]:** Fixed hardcoded `localhost:8001` in auth_manager.py to use `DROPLET_URL` from environment configuration. Registry now correctly shows `https://drop2.fullpotential.ai` as host.

- **[Port Configuration 2025-11-19]:** Changed default port from 8003 to 8000 to match docker-compose port mapping (80→8000, 443→8000). Removed complex port-finding logic in favor of simple environment variable.

- **[System Note]:** Airtable Connector integrates with Registry (#18) for JWT authentication and Orchestrator (#10) for heartbeat coordination. Auto-registration and token refresh implemented.

- **[External Services 2025-11-19]:** Registry v2 integration working with RS256 JWT tokens. Orchestrator heartbeat sending every 60 seconds. Registry heartbeat every 30 seconds. All authentication automated.

- **[Deployment 2025-11-19]:** Production deployment scripts (deploy.sh, install.sh, monitor.sh) configured for /root/airtable-server directory. Docker Compose setup with health checks and auto-restart.

---

## 8. TECH STACK

- **Framework:** FastAPI 0.104.1
- **Language:** Python 3.11+
- **HTTP Server:** Uvicorn
- **HTTP Client:** httpx (async)
- **Data Validation:** Pydantic v2
- **Authentication:** RS256 JWT (Registry v2 + Orchestrator)
- **Token Generation:** PyJWT + cryptography
- **System Metrics:** psutil
- **Environment:** python-dotenv
- **External API:** Airtable (pyairtable)
- **Deployment:** Docker + Docker Compose
- **Process Management:** systemd service

---

## 9. FEATURES

- 📊 **UDC Compliance** - Full implementation of Universal Droplet Contract v1.0
- 🗄️ **Airtable Integration** - Complete CRUD operations for Sprints, Cells, Proof, Heartbeats
- 🔐 **JWT Authentication** - Automated token generation and refresh with RS256
- 💓 **Dual Heartbeats** - Registry (30s) and Orchestrator (60s) health reporting
- 🔄 **Auto-Registration** - Automatic registration with Registry and Orchestrator on startup
- 📡 **UDC Messaging** - Send and receive messages via UDC protocol
- 🏥 **Health Monitoring** - Real-time CPU, memory, and performance metrics
- ⚙️ **Config Management** - Hot reload configuration without restart
- 🚨 **Emergency Controls** - Graceful shutdown and emergency stop endpoints
- 📝 **Structured Logging** - Comprehensive logging with log levels
- 🐳 **Docker Ready** - Full containerization with health checks
- 🔧 **Modular Architecture** - Clean separation of concerns (api/models/services/utils)

---

## 10. RELATED DOCS

- [UDC_COMPLIANCE.md](./1-UDC_COMPLIANCE.md) - Universal Droplet Contract specification
- [TECH_STACK.md](./2-TECH_STACK.md) - Technology standards and guidelines
- [INTEGRATION_GUIDE.md](./3-INTEGRATION_GUIDE.md) - Droplet integration patterns
- [CODE_STANDARDS.md](./4-CODE_STANDARDS.md) - Coding standards and best practices
- [SECURITY_REQUIREMENTS.md](./5-SECURITY_REQUIREMENTS.md) - Security guidelines
- [INTEGRATION_STATUS.md](./INTEGRATION_STATUS.md) - Current integration status
- [ORCHESTRATOR_API_GUIDE.md](./ORCHESTRATOR_API_GUIDE.md) - Orchestrator API documentation

---

**Last Updated:** 2025-11-19  
**UDC Version:** 1.0  
**Droplet Status:** OPERATIONAL ✅NTS.md) - Security guidelines
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
