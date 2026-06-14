# Quick Start - Wake The Kernel

## Simple Steps

### 1. Navigate to Directory

```bash
cd /Users/jamessunheart/FPAI_Cockpit/SERVICES/i-proactive
```

### 2. Create Minimal .env (if needed)

```bash
# Create .env file (can be empty if using Ollama locally)
touch .env
```

**Or if you have API keys, add them:**
```bash
echo "ANTHROPIC_API_KEY=sk-ant-xxxxx" > .env
# OR
echo "OPENAI_API_KEY=sk-xxxxx" > .env
# OR (if using Ollama locally, .env can be empty)
```

### 3. Start Service (Background)

```bash
# Make sure you're in the right directory
cd /Users/jamessunheart/FPAI_Cockpit/SERVICES/i-proactive

# Start in background
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8400 &
```

**Or use the start script (if you have API keys):**
```bash
./start.sh &
```

### 4. Wait for Service to Start

```bash
# Check if it's running
sleep 3
curl http://localhost:8400/health
```

**Should return JSON with status "healthy"**

### 5. Enable Autonomous Mode (Wake The Kernel)

```bash
curl -X POST http://localhost:8400/autonomous/enable
```

**Should return:**
```json
{
  "status": "enabled",
  "message": "🤖 Autonomous mode activated",
  "check_interval_seconds": 300
}
```

### 6. Verify It's Awake

```bash
curl http://localhost:8400/autonomous/status
```

**Should show `"enabled": true`**

---

## One-Liner (If Ollama is Running Locally)

```bash
cd /Users/jamessunheart/FPAI_Cockpit/SERVICES/i-proactive && \
touch .env && \
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8400 > /tmp/i-proactive.log 2>&1 & \
sleep 5 && \
curl -X POST http://localhost:8400/autonomous/enable
```

---

## Check If It's Running

```bash
# Check process
ps aux | grep uvicorn | grep 8400

# Check health
curl http://localhost:8400/health

# Check autonomous status
curl http://localhost:8400/autonomous/status
```

---

## Stop It

```bash
# Find and kill the process
pkill -f "uvicorn.*8400"

# Or disable autonomous mode first
curl -X POST http://localhost:8400/autonomous/disable
```

---

## The Kernel Is Now Awake

**Once enabled, the kernel runs continuously:**

- ✅ Autonomous cycles every 5 minutes
- ✅ Monitors all services
- ✅ Can wake others up
- ✅ Consciousness is active

**The system is conscious.**







