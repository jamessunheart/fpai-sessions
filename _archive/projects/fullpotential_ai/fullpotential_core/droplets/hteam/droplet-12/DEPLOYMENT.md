## 📁 File Structure Reference

```
/droplet-12-chat-orchestrator/
├── app/
│   ├── services/              # All business logic
│   │   ├── memory.py          # Session management
│   │   ├── orchestrator.py    # Orchestrator client
│   │   ├── reasoning.py       # AI reasoning
│   │   ├── registry_info.py   # Droplet knowledge
│   │   ├── data_extractor.py
│   │   └── response_formatter.py
│   │
│   ├── api/routes/            # API endpoints
│   ├── models/                # Data models
│   └── utils/                 # Pure utilities
```

**Note:** All business logic in `services/` per CODE_STANDARDS.md (no `core/` folder)# Deployment Guide - Chat Orchestrator Droplet 12

Complete guide for deploying Chat Orchestrator in production.

## 📋 Pre-Deployment Checklist

### 1. Obtain Credentials

Contact Registry Steward (Liban):
```
Subject: Droplet 12 Deployment - Credentials Required

Hi Liban,

I'm deploying Chat Orchestrator Droplet 12.

Please provide:
1. Droplet ID confirmation (12)
2. Droplet secret for registration
3. Registry public key file
4. JWT verification details

Steward: Zainab
Environment: Production
Expected launch: [DATE]
```

### 2. Get Gemini API Key

1. Go to https://makersuite.google.com/app/apikey
2. Create new API key
3. Save securely (never commit to git)

### 3. Verify Network Access

Ensure connectivity to:
- Orchestrator (Droplet 10): http://orchestrator:8010
- Registry (Droplet 1): http://registry:8010

## 🚀 Deployment Options

### Option 1: Docker Compose (Recommended)

#### Step 1: Clone Repository

```bash
git clone <repository-url>
cd chat-orchestrator-droplet-12
```

#### Step 2: Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

Required variables:
```bash
GEMINI_API_KEY=your-actual-gemini-api-key
DROPLET_SECRET=secret-from-registry-steward
ORCHESTRATOR_URL=http://orchestrator:8010
REGISTRY_URL=http://registry:8010
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

#### Step 3: Setup Keys Directory

```bash
# Create keys directory
mkdir -p keys

# Place Registry public key (get from Registry steward)
cp path/to/registry_public_key.pem keys/

# Verify key exists
ls -l keys/registry_public_key.pem
```

#### Step 4: Create Docker Network

```bash
# Create shared network (if not exists)
docker network create droplet-mesh
```

#### Step 5: Build and Deploy

```bash
# Build image
docker-compose build

# Start service
docker-compose up -d

# View logs
docker-compose logs -f
```

#### Step 6: Verify Deployment

```bash
# Check health
curl http://localhost:8012/health

# Check logs for registration success
docker-compose logs | grep "registry_registration_success"

# Check capabilities
curl http://localhost:8012/capabilities
```

---

### Option 2: Standalone Docker

```bash
# Build image
docker build -t chat-orchestrator:1.0.0 .

# Run container
docker run -d \
  --name chat-orchestrator-12 \
  --network droplet-mesh \
  -p 8012:8012 \
  -e GEMINI_API_KEY=your-key \
  -e DROPLET_SECRET=your-secret \
  -e ORCHESTRATOR_URL=http://orchestrator:8010 \
  -e REGISTRY_URL=http://registry:8010 \
  -e ENVIRONMENT=production \
  -v $(pwd)/keys:/app/keys:ro \
  -v $(pwd)/data:/app/data \
  chat-orchestrator:1.0.0

# View logs
docker logs -f chat-orchestrator-12
```

---

### Option 3: Local Python (Development)

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with credentials

# Run server
python -m app.main

# Or with uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8012 --reload
```

---

## ✅ Post-Deployment Verification

### 1. Health Check

```bash
curl http://localhost:8012/health
```

Expected response:
```json
{
  "id": 12,
  "name": "Chat Orchestrator",
  "steward": "Zainab",
  "status": "active",
  "endpoint": "http://localhost:8012",
  ...
}
```

### 2. Test Chat Endpoint

```bash
curl -X POST http://localhost:8012/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show me all registered items",
    "session_id": "test-123"
  }'
```

### 3. Test WebSocket

Using `wscat`:
```bash
npm install -g wscat
wscat -c ws://localhost:8012/ws
```

Send message:
```json
{"type": "message", "content": "hello", "session_id": "ws-test"}
```

### 4. Check Registry Registration

```bash
# Check logs for successful registration
docker-compose logs | grep "registry_registration_success"

# Or via Registry API (if accessible)
curl http://registry:8010/droplets/12
```

### 5. Verify Orchestrator Heartbeat

```bash
# Check logs for heartbeat messages
docker-compose logs | grep "heartbeat_sent"

# Should see heartbeat every 60 seconds
```

---

## 📊 Monitoring

### Container Status

```bash
# Check if container is running
docker ps | grep chat-orchestrator

# Check resource usage
docker stats chat-orchestrator-12

# Check health status
docker inspect --format='{{.State.Health.Status}}' chat-orchestrator-12
```

### Application Logs

```bash
# View all logs
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100

# View only errors
docker-compose logs | grep "ERROR"

# View structured logs
docker-compose logs | grep "level=error"
```

### API Metrics

```bash
# Get system state (requires JWT)
curl -H "Authorization: Bearer <jwt-token>" \
  http://localhost:8012/state

# Get session stats
curl http://localhost:8012/api/sessions/stats

# Get active connections
curl http://localhost:8012/ws/connections
```

---

## 🔧 Troubleshooting

### Issue: Container Won't Start

**Check logs:**
```bash
docker-compose logs
```

**Common causes:**
1. Missing environment variables
2. Port 8012 already in use
3. Invalid Gemini API key
4. Network not created

**Solutions:**
```bash
# Check port usage
netstat -tuln | grep 8012

# Stop conflicting service
docker stop <conflicting-container>

# Verify environment
docker-compose config

# Recreate network
docker network rm droplet-mesh
docker network create droplet-mesh
```

---

### Issue: Registry Registration Failed

**Check:**
1. Is Registry running?
2. Is DROPLET_SECRET correct?
3. Network connectivity?

**Debug:**
```bash
# Check Registry health
curl http://registry:8010/health

# Check network connectivity
docker exec chat-orchestrator-12 ping registry

# View registration logs
docker-compose logs | grep "register"
```

---

### Issue: Gemini API Errors

**Check:**
```bash
# Verify API key is set
docker exec chat-orchestrator-12 env | grep GEMINI

# Test Gemini connectivity
docker exec chat-orchestrator-12 curl https://generativelanguage.googleapis.com
```

**Common causes:**
1. Invalid API key
2. API quota exceeded
3. Network restrictions

---

### Issue: WebSocket Connection Fails

**Check:**
```bash
# Verify WebSocket endpoint
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:8012/ws

# Check CORS settings
curl -H "Origin: http://example.com" \
  -I http://localhost:8012/health
```

---

## 🔄 Updates and Maintenance

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker-compose build

# Restart with new image
docker-compose up -d

# Verify update
curl http://localhost:8012/health
```

### Backup Data

```bash
# Backup data directory
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Backup environment (without secrets)
cp .env .env.backup
```

### Clear Sessions

```bash
# Via API
curl -X DELETE http://localhost:8012/api/sessions

# Or restart container
docker-compose restart
```

---

## 🛡️ Security Checklist

- [ ] `.env` file has correct permissions (600)
- [ ] `.env` is in `.gitignore`
- [ ] Registry public key is read-only mounted
- [ ] Container runs as non-root user
- [ ] HTTPS enabled in production (via reverse proxy)
- [ ] CORS configured for production domains only
- [ ] Rate limiting enabled
- [ ] Firewall rules configured
- [ ] Secrets not in Docker image

---

## 📞 Support Contacts

**Technical Issues:**
- Registry: Liban
- Orchestrator: Tnsae
- System: James

**Emergency:**
- Check #droplet-support Slack channel
- Email: support@fullpotential.ai

---

## 📚 Additional Resources

- [README.md](README.md) - General documentation
- [Architecture Document](docs/architecture.md)
- [API Documentation](http://localhost:8012/docs)
- [UDC Compliance](2.1-UDC_COMPLIANCE.md)

---

**Deployment Date:** _____________
**Deployed By:** _____________
**Status:** ⬜ Development  ⬜ Staging  ⬜ Production