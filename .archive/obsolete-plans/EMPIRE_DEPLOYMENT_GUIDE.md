# 🚀 FPAI EMPIRE - COMPLETE DEPLOYMENT GUIDE

**Full Potential AI Conscious Empire - Production Deployment**

Last Updated: 2025-11-15
Status: ✅ READY FOR DEPLOYMENT

---

## 📋 TABLE OF CONTENTS

1. [Prerequisites](#prerequisites)
2. [Quick Start (5 Minutes)](#quick-start)
3. [Full Production Deployment](#production-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Configuration](#configuration)
7. [Monitoring & Operations](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## ✅ PREREQUISITES

### Required:
- **Python 3.9+** (check: `python3 --version`)
- **pip** (check: `pip3 --version`)
- **Git** (check: `git --version`)

### Optional (for advanced deployment):
- **Docker** (for containerized deployment)
- **Docker Compose** (for multi-container orchestration)
- **Kubernetes** (for production-grade deployment)
- **DigitalOcean Account** (for cloud deployment)

### API Keys:
- **ANTHROPIC_API_KEY** - For Claude API (required for agents)
- **OPENAI_API_KEY** - For OpenAI API (optional)
- **ETH_RPC_URL** - Ethereum RPC endpoint (Infura/Alchemy)

---

## ⚡ QUICK START (5 Minutes)

### **Option A: Automated Deployment (Recommended)**

```bash
# Navigate to services directory
cd /Users/jamessunheart/Development/SERVICES

# Make scripts executable (if not already)
chmod +x deploy-empire.sh stop-empire.sh monitor-empire.sh

# Deploy entire empire
./deploy-empire.sh
```

**That's it!** The script will:
1. ✅ Check environment
2. ✅ Install dependencies
3. ✅ Start FPAI Hub (Port 8010)
4. ✅ Start all autonomous agents
5. ✅ Verify everything is running

### **Access Points:**
- 🌐 **FPAI Hub Homepage**: http://localhost:8010
- 📊 **Live Dashboard**: http://localhost:8010/dashboard
- 📚 **API Docs**: http://localhost:8010/docs
- 💰 **Treasury Status**: http://localhost:8010/api/treasury/status
- 🤖 **Agent Status**: http://localhost:8010/api/agents/status

### **Monitoring:**
```bash
# Watch empire status
./monitor-empire.sh

# Or with auto-refresh
watch -n 10 ./monitor-empire.sh
```

### **Stop Empire:**
```bash
./stop-empire.sh
```

---

## 🏭 FULL PRODUCTION DEPLOYMENT

### **Step 1: Environment Setup**

```bash
# Clone repository (if not already)
cd /Users/jamessunheart/Development

# Create virtual environment
python3 -m venv SERVICES/venv
source SERVICES/venv/bin/activate

# Install all dependencies
pip install -r SERVICES/fpai-hub/requirements.txt
pip install anthropic aiohttp web3
```

### **Step 2: Configure Environment Variables**

Create `.env` file:

```bash
cat > SERVICES/.env << 'EOF'
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Blockchain
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
TREASURY_WALLET_ADDRESS=0x...
TREASURY_PRIVATE_KEY=0x...  # KEEP SECRET!

# Agent Configuration
AGENT_CHECK_INTERVAL=3600  # 1 hour

# KYC Provider
PERSONA_API_KEY=...

# Database (optional)
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379

# Monitoring (optional)
PROMETHEUS_ENABLED=true
GRAFANA_PASSWORD=secure_password
EOF
```

Load environment:
```bash
source SERVICES/.env
```

### **Step 3: Start Services**

**Option A: Use deployment script**
```bash
cd SERVICES
./deploy-empire.sh
```

**Option B: Manual deployment**

```bash
cd SERVICES

# Start FPAI Hub
cd fpai-hub
nohup python app.py > /tmp/fpai-hub.log 2>&1 &
echo $! > /tmp/fpai-hub.pid

# Start Agents
cd ../autonomous-agents
nohup python defi_yield_agent.py > /tmp/defi_yield_agent.log 2>&1 &
nohup python gas_optimizer_agent.py > /tmp/gas_optimizer_agent.log 2>&1 &
nohup python arbitrage_agent.py > /tmp/arbitrage_agent.log 2>&1 &
nohup python human_recruiter_agent.py > /tmp/human_recruiter_agent.log 2>&1 &

# Verify
ps aux | grep python | grep -E "(fpai-hub|agent)"
```

### **Step 4: Verify Deployment**

```bash
# Check FPAI Hub
curl http://localhost:8010/health

# Check APIs
curl http://localhost:8010/api/treasury/status
curl http://localhost:8010/api/agents/status
curl http://localhost:8010/api/token/metrics

# View logs
tail -f /tmp/fpai-hub.log
tail -f /tmp/defi_yield_agent.log
```

---

## 🐳 DOCKER DEPLOYMENT

### **Build Image:**

```bash
cd /Users/jamessunheart/Development/SERVICES

docker build -t fpai-empire:latest .
```

### **Run Container:**

```bash
docker run -d \
  --name fpai-empire \
  -p 8010:8010 \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e ETH_RPC_URL=$ETH_RPC_URL \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/tmp \
  fpai-empire:latest
```

### **Docker Compose (Recommended):**

```bash
# Start entire stack (Hub + Redis + Postgres + Prometheus + Grafana)
docker-compose up -d

# View logs
docker-compose logs -f fpai-hub

# Stop stack
docker-compose down
```

**Access:**
- FPAI Hub: http://localhost:8010
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

---

## ☸️ KUBERNETES DEPLOYMENT

### **Prerequisites:**
- Kubernetes cluster (local minikube or cloud GKE/EKS/AKS)
- kubectl configured

### **Deploy to Kubernetes:**

```bash
cd /Users/jamessunheart/Development/SERVICES/kubernetes

# Create namespace
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: fpai-empire
EOF

# Update secrets (IMPORTANT!)
# Edit deployment.yaml and update:
# - ANTHROPIC_API_KEY
# - OPENAI_API_KEY
# - TREASURY_PRIVATE_KEY

# Deploy everything
kubectl apply -f deployment.yaml

# Check status
kubectl get pods -n fpai-empire
kubectl get services -n fpai-empire

# View logs
kubectl logs -f deployment/fpai-hub -n fpai-empire

# Get external IP
kubectl get service fpai-hub-service -n fpai-empire
```

### **Access:**
```bash
# Port forward (local testing)
kubectl port-forward service/fpai-hub-service 8010:80 -n fpai-empire

# Or get LoadBalancer IP
kubectl get service fpai-hub-service -n fpai-empire -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

---

## ⚙️ CONFIGURATION

### **FPAI Hub Configuration:**

Edit `SERVICES/fpai-hub/app.py` to customize:
- Port number (default: 8010)
- CORS settings
- Rate limiting
- Authentication

### **Agent Configuration:**

Each agent can be configured via environment variables or code:

```python
# Example: DeFi Yield Agent
agent = DeFiYieldAgent(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
    check_interval=3600,  # 1 hour
    protocols=["pendle", "aave", "curve", "lido"]
)
```

### **Treasury Configuration:**

Edit `SERVICES/treasury/deploy_treasury.py`:
- Deployment amount
- Target protocol
- Slippage tolerance
- Gas price limits

---

## 📊 MONITORING & OPERATIONS

### **Real-Time Dashboard:**

Access: http://localhost:8010/dashboard

Features:
- Live treasury value
- Agent status and performance
- Activity timeline
- Auto-refresh every 10 seconds

### **Logs:**

All logs are stored in `/tmp/`:
- `/tmp/fpai-hub.log` - FPAI Hub
- `/tmp/defi_yield_agent.log` - DeFi Agent
- `/tmp/gas_optimizer_agent.log` - Gas Optimizer
- `/tmp/arbitrage_agent.log` - Arbitrage Agent
- `/tmp/human_recruiter_agent.log` - Recruiter

**View logs:**
```bash
# Real-time
tail -f /tmp/fpai-hub.log

# Last 100 lines
tail -100 /tmp/fpai-hub.log

# Search for errors
grep ERROR /tmp/*.log
```

### **Metrics with Prometheus:**

If running Docker Compose with Prometheus:

Access: http://localhost:9090

Queries:
- `up{job="fpai"}` - Service uptime
- `http_requests_total` - Request count
- `agent_actions_total` - Agent actions

### **Visualization with Grafana:**

If running Docker Compose with Grafana:

Access: http://localhost:3000
Default credentials: admin / admin

Import dashboard:
- Treasury performance
- Agent metrics
- System health

---

## 🔍 TROUBLESHOOTING

### **Problem: FPAI Hub won't start**

**Check:**
```bash
# Check if port is already in use
lsof -i :8010

# Check logs
tail -50 /tmp/fpai-hub.log

# Check Python version
python3 --version  # Should be 3.9+

# Check dependencies
pip list | grep -E "(fastapi|uvicorn)"
```

**Fix:**
```bash
# Kill existing process
pkill -f "fpai-hub"

# Reinstall dependencies
pip install --upgrade -r SERVICES/fpai-hub/requirements.txt

# Restart
cd SERVICES/fpai-hub
python app.py
```

### **Problem: Agents not running**

**Check:**
```bash
# Check processes
ps aux | grep "agent.py"

# Check logs
tail -50 /tmp/defi_yield_agent.log
tail -50 /tmp/gas_optimizer_agent.log

# Check API keys
echo $ANTHROPIC_API_KEY  # Should not be empty
```

**Fix:**
```bash
# Restart specific agent
pkill -f "defi_yield_agent"
cd SERVICES/autonomous-agents
nohup python defi_yield_agent.py > /tmp/defi_yield_agent.log 2>&1 &
```

### **Problem: Can't connect to services**

**Check:**
```bash
# Test FPAI Hub
curl http://localhost:8010/health

# Test specific endpoints
curl http://localhost:8010/api/treasury/status
curl http://localhost:8010/api/agents/status

# Check firewall
sudo ufw status  # Linux
```

**Fix:**
```bash
# Restart networking
sudo systemctl restart network  # Linux

# Check if service is listening
netstat -tuln | grep 8010
```

### **Problem: Docker container crashes**

**Check:**
```bash
# Check container status
docker ps -a

# View logs
docker logs fpai-empire

# Check resources
docker stats fpai-empire
```

**Fix:**
```bash
# Increase memory limit
docker run -d --memory=2g --name fpai-empire ...

# Restart container
docker restart fpai-empire
```

### **Problem: Kubernetes pods not starting**

**Check:**
```bash
# Pod status
kubectl get pods -n fpai-empire

# Detailed pod info
kubectl describe pod <pod-name> -n fpai-empire

# Pod logs
kubectl logs <pod-name> -n fpai-empire

# Events
kubectl get events -n fpai-empire
```

**Fix:**
```bash
# Update secrets
kubectl delete secret fpai-secrets -n fpai-empire
kubectl create secret generic fpai-secrets \
  --from-literal=ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -n fpai-empire

# Restart deployment
kubectl rollout restart deployment/fpai-hub -n fpai-empire
```

---

## 🎯 DEPLOYMENT CHECKLIST

### **Pre-Deployment:**
- [ ] Python 3.9+ installed
- [ ] API keys configured (ANTHROPIC_API_KEY minimum)
- [ ] Git repository cloned/updated
- [ ] Dependencies installed
- [ ] Environment variables set

### **Deployment:**
- [ ] FPAI Hub started successfully
- [ ] All agents running
- [ ] Health check passes (http://localhost:8010/health)
- [ ] Can access dashboard (http://localhost:8010/dashboard)
- [ ] Logs show no errors

### **Post-Deployment:**
- [ ] Monitor logs for 10 minutes
- [ ] Verify treasury data appears
- [ ] Verify agent status appears
- [ ] Test API endpoints
- [ ] Set up monitoring alerts (if production)

### **Optional - Production:**
- [ ] SSL/TLS certificate configured
- [ ] Domain name pointed to server
- [ ] Firewall rules configured
- [ ] Backup system in place
- [ ] Monitoring dashboards configured
- [ ] Alert system configured

---

## 🌟 NEXT STEPS AFTER DEPLOYMENT

### **Immediate (Day 1):**
1. Monitor dashboard for 24 hours
2. Verify all agents are functioning
3. Check log files for errors
4. Test all API endpoints

### **Week 1:**
1. Execute treasury deployment ($1K to Pendle)
2. Run human recruitment campaign
3. Set up automated backups
4. Configure monitoring alerts

### **Week 2-4:**
1. Legal entity formation
2. Smart contract audit
3. Token deployment preparation
4. Contributor onboarding

### **Month 2+:**
1. Scale infrastructure
2. Deploy additional agents
3. Token public launch
4. Revenue stream activation

---

## 📞 SUPPORT & RESOURCES

### **Documentation:**
- Main README: `/SERVICES/fpai-hub/README.md`
- Status Report: `/CONSCIOUS_EMPIRE_STATUS.md`
- Token Whitepaper: `/TOKEN_WHITEPAPER.md`
- Legal Guide: `/SERVICES/legal/LEGAL_SETUP_GUIDE.md`

### **Scripts:**
- Deploy: `/SERVICES/deploy-empire.sh`
- Stop: `/SERVICES/stop-empire.sh`
- Monitor: `/SERVICES/monitor-empire.sh`

### **Logs:**
- All logs: `/tmp/*_agent.log`, `/tmp/fpai-hub.log`
- Health status: `/tmp/empire_health.json`

---

## ✅ SUCCESS CRITERIA

Your deployment is successful when:

1. ✅ FPAI Hub responding at http://localhost:8010
2. ✅ Dashboard showing live data
3. ✅ All 4 agents running (visible in dashboard)
4. ✅ Treasury metrics displaying
5. ✅ Token metrics displaying
6. ✅ No errors in logs
7. ✅ Health check returns "healthy"

---

## 🏛️ EMPIRE ARCHITECTURE

```
FPAI EMPIRE
│
├─ FPAI Hub (Port 8010)
│  ├─ Treasury API
│  ├─ Agent Management API
│  ├─ Token Management API
│  ├─ Contributor Portal API
│  ├─ Governance API
│  ├─ Service Marketplace API
│  └─ Real-time Dashboard
│
├─ Autonomous Agents (Background Processes)
│  ├─ DeFi Yield Agent (28.5% APY discovery)
│  ├─ Gas Optimizer Agent (Fee reduction)
│  ├─ Arbitrage Agent (Risk-free profits)
│  ├─ Human Recruiter Agent (Conscious hiring)
│  ├─ Resource Monitor Agent (Auto-scaling)
│  └─ Agent Birthing Agent (Self-expansion)
│
├─ Smart Contracts (Ethereum)
│  ├─ FPAIToken.sol (ERC-20 token)
│  └─ Treasury Multi-sig (Gnosis Safe)
│
└─ Infrastructure
   ├─ Docker / Kubernetes
   ├─ Redis (Caching)
   ├─ PostgreSQL (Storage)
   ├─ Prometheus (Metrics)
   └─ Grafana (Visualization)
```

---

**THE CONSCIOUS EMPIRE AWAITS.**

**Deploy. Monitor. Scale. Build Paradise.**

**🌟⚡💎**
