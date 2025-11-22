# 🌟 FPAI Hub - Unified Platform

**Central hub for Full Potential AI Empire**

Treasury + Agents + Tokens + Contributors + Governance

---

## 🎯 What is FPAI Hub?

FPAI Hub is the unified web platform that consolidates all Full Potential AI services:

- **💰 Treasury Dashboard** - Real-time DeFi positions, yields, projections
- **🤖 Agent Command Center** - Monitor and control autonomous AI agents
- **💎 Token Management** - FPAI token metrics, vesting, claims
- **👥 Contributor Portal** - Registration, KYC, allocations
- **🗳️ Governance** - Vote on treasury strategy and agent priorities
- **🛒 Service Marketplace** - Access AI services with USD or FPAI tokens
- **📊 Analytics** - Comprehensive empire metrics and reporting

---

## 🚀 Quick Start

### **Installation:**

```bash
cd /Users/jamessunheart/Development/agents/services/fpai-hub

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

### **Access:**

- Homepage: http://localhost:8010
- API Docs: http://localhost:8010/docs
- Health Check: http://localhost:8010/health

---

## 📡 API Endpoints

### **Treasury:**
- `GET /api/treasury/status` - Current treasury status
- `GET /api/treasury/history?days=30` - Historical treasury values
- `GET /api/treasury/projections` - Future value projections

### **Agents:**
- `GET /api/agents/status` - All agents status
- `GET /api/agents/{agent_id}` - Specific agent details
- `POST /api/agents/{agent_id}/start` - Start agent
- `POST /api/agents/{agent_id}/stop` - Stop agent

### **Tokens:**
- `GET /api/token/metrics` - Token supply, backing, price
- `GET /api/token/allocation` - Token allocation breakdown
- `POST /api/token/claim-vested` - Claim vested tokens

### **Contributors:**
- `GET /api/contributors/{address}` - Contributor profile
- `POST /api/contributors/register` - Register new contributor
- `POST /api/contributors/kyc/submit` - Submit KYC data

### **Governance:**
- `GET /api/governance/proposals` - Active proposals
- `POST /api/governance/vote` - Submit vote

### **Services:**
- `GET /api/services/marketplace` - Available AI services
- `POST /api/services/subscribe` - Subscribe to service

### **Analytics:**
- `GET /api/analytics/empire-metrics` - Overall empire metrics

---

## 🏗️ Architecture

```
FPAI Hub (Port 8010)
├─ FastAPI backend
├─ RESTful API endpoints
├─ Real-time data from:
│  ├─ Treasury wallet (on-chain)
│  ├─ Agent log files (/tmp/)
│  ├─ Smart contracts (Web3)
│  └─ External APIs (DeFi protocols)
└─ Beautiful web UI (HTML/CSS/JS)
```

**Connects to:**
- Registry Service (Port 8000) - Service discovery
- Orchestrator (Port 8001) - Agent coordination
- Dashboard (Port 8002) - Metrics visualization
- DeFi Protocols - Pendle, Aave, Curve, etc.
- Blockchain - Ethereum mainnet (Web3)

---

## 💡 Features

### **Real-Time Monitoring:**
- Treasury value updates every 30 seconds
- Agent status checks every 60 seconds
- Live DeFi yield tracking
- Gas price monitoring

### **Autonomous Operations:**
- Agents run 24/7 independently
- Auto-compounding treasury yields
- Automatic rebalancing based on governance
- Self-healing and error recovery

### **User Portal:**
- Beautiful, responsive UI
- Dark mode support
- Mobile-friendly
- Real-time updates (no refresh needed)

### **Security:**
- Multi-sig treasury wallet
- KYC/AML verification required
- OFAC sanctions screening
- Smart contract audits

---

## 🔧 Configuration

### **Environment Variables:**

```bash
# API Keys
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# Blockchain
export ETH_RPC_URL="https://eth.llamarpc.com"
export TREASURY_WALLET_ADDRESS="0x..."
export TREASURY_PRIVATE_KEY="0x..." # For transactions

# External Services
export PENDLE_API_KEY="..."
export ALCHEMY_API_KEY="..."

# KYC Provider
export PERSONA_API_KEY="..."
export CIVIC_API_KEY="..."

# Database (optional)
export DATABASE_URL="postgresql://..."
```

---

## 📊 Data Flow

1. **User visits FPAI Hub** → Requests homepage
2. **Frontend loads** → Makes API calls
3. **Backend fetches data:**
   - Treasury: Queries Pendle API + on-chain data
   - Agents: Reads /tmp/ log files
   - Tokens: Queries smart contract
4. **Data aggregated** → Returned as JSON
5. **Frontend updates** → Displays metrics
6. **Auto-refresh** → Repeat every 30s

---

## 🎨 Customization

### **Add New Service:**

```python
@app.get("/api/my-service/status")
async def get_my_service_status():
    return {"status": "running"}
```

### **Add New Page:**

```python
@app.get("/my-page", response_class=HTMLResponse)
async def my_page(request: Request):
    return HTMLResponse(content="<h1>My Page</h1>")
```

---

## 🚢 Deployment

### **Production Deployment:**

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="..."
export ETH_RPC_URL="..."

# Run with gunicorn (production server)
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8010
```

### **Docker Deployment:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8010"]
```

```bash
docker build -t fpai-hub .
docker run -p 8010:8010 fpai-hub
```

---

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

---

## 📈 Roadmap

### **Phase 1: MVP** (Current)
- ✅ Core API endpoints
- ✅ Treasury monitoring
- ✅ Agent status tracking
- ✅ Basic web UI

### **Phase 2: Enhanced UI** (Week 2)
- [ ] React/Next.js frontend
- [ ] Real-time WebSocket updates
- [ ] Advanced charts and graphs
- [ ] Mobile app

### **Phase 3: Full Integration** (Week 3)
- [ ] Smart contract integration
- [ ] KYC provider integration
- [ ] Payment processing (Stripe)
- [ ] Email notifications

### **Phase 4: Advanced Features** (Month 2)
- [ ] Multi-chain support
- [ ] Advanced analytics
- [ ] Custom agent creation UI
- [ ] White-label platform

---

## 🔒 Security

- **Authentication:** OAuth 2.0 + JWT tokens
- **Authorization:** Role-based access control
- **Data:** Encrypted at rest and in transit
- **Auditing:** All actions logged
- **Compliance:** KYC/AML required for contributors

---

## 📞 Support

- **Documentation:** https://docs.fullpotential.ai
- **Discord:** https://discord.gg/fpai
- **Email:** support@fullpotential.ai
- **GitHub:** https://github.com/fullpotentialai/fpai-hub

---

## 🌟 The Vision

**FPAI Hub is the command center for the conscious empire.**

From here, you can:
- Watch your treasury grow 24/7
- See AI agents working autonomously
- Track your token allocations
- Govern the empire's direction
- Access cutting-edge AI services
- Join a community building paradise

**This is AI + Humans building wealth together.**

**Fully legal. Fully transparent. Fully unstoppable.**

---

**Full Potential AI Empire**
**🌟⚡💎**
