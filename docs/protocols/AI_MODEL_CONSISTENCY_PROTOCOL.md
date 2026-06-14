# AI Model Consistency Protocol v2.0 🔒 LOCKED

**Last Updated:** December 1, 2025  
**Lock Version:** 1.0.0  
**Purpose:** Ensure all FPAI services use the LATEST AI models - enforced automatically

---

## 🔒 LOCKED CONFIGURATION

This protocol is now **LOCKED** with automatic enforcement:
- **23 outdated models are BLOCKED**
- **Model Enforcer Daemon** runs every 5 minutes
- **Auto-upgrade** any blocked model to latest version

---

## The Problem (SOLVED)

~~Different services were using different (often outdated) model versions~~
~~Model names were hardcoded in multiple files~~
~~No single source of truth for model versions~~

**NOW:** All services use a locked, centralized configuration with automatic enforcement.

---

## The Solution

### 🛡️ Centralized LOCKED Configuration

**Location:** `/opt/fpai/shared/ai_models_config.py`

This file exists on ALL servers:
- Main Server (198.54.123.234): `/opt/fpai/shared/ai_models_config.py`
- AI Server (162.0.208.88): `/opt/fpai/shared/ai_models_config.py`

### 🚀 How to Use (with Auto-Enforcement)

```python
import sys
sys.path.insert(0, "/opt/fpai/shared")

from ai_models_config import (
    # Get models with enforcement
    get_model,             # get_model("anthropic", "primary") -> latest
    enforce_latest,        # enforce_latest("gpt-4") -> "gpt-5.1"
    validate_model,        # Check if model is blocked
    
    # Direct access
    ANTHROPIC_MODELS,      # {"primary": "claude-opus-4-5-20251101", ...}
    OPENAI_MODELS,         # {"primary": "gpt-5.1", ...}
    GOOGLE_MODELS,         # {"primary": "gemini-3-pro", ...}
    
    # Blocked models list
    BLOCKED_MODELS,        # {"gpt-4": "gpt-5.1", "gemini-2.5-pro": "gemini-3-pro", ...}
    
    # Lock info
    get_lock_info          # Returns lock version, date, blocked count
)
```

### 🔥 Current LATEST Models (December 2025)

| Provider | Model ID | Display Name | Released |
|----------|----------|--------------|----------|
| **Anthropic** | `claude-opus-4-5-20251101` | Claude Opus 4.5 🔒 | Nov 1, 2025 |
| **OpenAI** | `gpt-5.1` | GPT-5.1 🔒 | Nov 13, 2025 |
| **Google** | `gemini-3-pro` | Gemini 3 Pro 🔒 | Nov 18, 2025 |
| **xAI** | `grok-4-fast-reasoning` | Grok 4 🔒 | Latest |
| **Meta** | `llama-3.3-70b` | Llama 3.3 70B 🔒 | Latest |

### 🚫 BLOCKED Outdated Models (23 total)

| Blocked Model | Auto-Upgraded To |
|---------------|------------------|
| `gpt-4`, `gpt-4-turbo`, `gpt-4.1` | `gpt-5.1` |
| `claude-3-opus-*`, `claude-3-sonnet-*` | `claude-opus-4-5-20251101` |
| `gemini-pro`, `gemini-1.5-pro`, `gemini-2.5-pro` | `gemini-3-pro` |
| `llama-2-*`, `llama-3-*`, `llama-3.1-*` | `llama-3.3-70b` |

---

## 🛡️ Model Enforcer Daemon

A background service continuously monitors all services for model drift:

**Service:** `model-enforcer.service`  
**Location:** `/opt/fpai/shared/model_enforcer.py`  
**Check Interval:** Every 5 minutes

### Check Status Manually
```bash
# Run one-time check
python3 /opt/fpai/shared/model_enforcer.py --once

# View service logs
journalctl -u model-enforcer -f

# Check status file
cat /opt/fpai/shared/model_status.json
```

### API Endpoint
```bash
# Check model compliance via API
curl -s http://localhost:8600/api/models/status | jq
```

---

## Updating Models (When New Versions Release)

### Step 1: Update the LOCKED config
```bash
ssh root@198.54.123.234
nano /opt/fpai/shared/ai_models_config.py

# Update these sections:
# 1. Add new model to appropriate *_MODELS dict
# 2. Add OLD model to BLOCKED_MODELS with upgrade path
# 3. Update LOCK_VERSION and LOCK_DATE
```

### Step 2: Sync to all servers
```bash
scp /opt/fpai/shared/ai_models_config.py root@162.0.208.88:/opt/fpai/shared/
```

### Step 3: Restart services
```bash
# Main Server
systemctl restart whaletrack-magnet
systemctl restart model-enforcer

# AI Server
ssh root@162.0.208.88 "systemctl restart ai-brain"
```

### Step 4: Verify
```bash
curl -s http://localhost:8600/api/models/status | jq '.lock_info'
```

---

## Services Using This Config

| Service | Location | Import Method |
|---------|----------|---------------|
| WhaleTrack | `/opt/fpai/services/whaletrack-magnet/` | `ai_chat.py`, `chat_endpoints.py`, `main.py` |
| AI Brain | `/opt/fpai/ai-brain/` | `main.py` |
| Intelligence Core | `/opt/fpai/ai-brain/` | `intelligence_core.py` |
| Model Enforcer | `/opt/fpai/shared/` | `model_enforcer.py` |

---

## 📊 Monitoring Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/models/status` | Full compliance status |
| `GET /api/chat/models` | WhaleTrack model info |
| `GET http://162.0.208.88:8101/` | AI Brain model info |

### Quick Health Check
```bash
# All-in-one status
curl -s http://localhost:8600/api/models/status | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Lock: v{d[\"lock_info\"][\"lock_version\"]}')
print(f'Blocked: {d[\"blocked_models_count\"]} models')
print(f'Status: {d[\"status\"]}')"
```

---

## 💰 Cost Considerations

| Model | Input Cost | Output Cost | Use For |
|-------|------------|-------------|---------|
| Claude Opus 4.5 | $15/M | $75/M | Critical intelligence |
| GPT-5.1 | $10/M | $30/M | Complex reasoning |
| Gemini 3 Pro | $7/M | $21/M | Multimodal tasks |
| Claude Sonnet 4 | $3/M | $15/M | Standard tasks |
| GPT-4o Mini | $0.15/M | $0.60/M | High volume |

**Rule:** Use the LATEST models. Intelligence is only as good as its models!

---

## 🚨 Emergency Fallback Chain

1. **Anthropic** - Claude Opus 4.5 (Primary)
2. **OpenAI** - GPT-5.1
3. **Google** - Gemini 3 Pro
4. **xAI** - Grok 4
5. **Together** - Llama 3.3 70B
6. **Local Ollama** - Llama 3.2 (Offline fallback)

---

## ⚠️ NEVER Do This

❌ Use a model from the BLOCKED_MODELS list  
❌ Hardcode model names in service files  
❌ Skip the `enforce_latest()` wrapper  
❌ Ignore Model Enforcer warnings  

## ✅ ALWAYS Do This

✅ Import from `/opt/fpai/shared/ai_models_config.py`  
✅ Use `enforce_latest(model)` before API calls  
✅ Check `/api/models/status` after deployments  
✅ Update BLOCKED_MODELS when new versions release  

---

**🔒 LOCKED:** Intelligence is only as smart as its latest models. No exceptions!
