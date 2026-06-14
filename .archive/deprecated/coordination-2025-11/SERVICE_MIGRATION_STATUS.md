# Service Migration Status - December 13, 2025

## 🚨 ACTION REQUIRED: Update Your Service Endpoints

The following services have been **migrated to the secondary server**. They are currently running on BOTH servers for redundancy. Update your code to use the new endpoints before we shut down the primary copies.

---

## 📍 Endpoint Changes

### Services That Moved to Secondary (162.0.208.88)

| Service | OLD Endpoint | NEW Endpoint | Status |
|---------|--------------|--------------|--------|
| **Aria AI** | `http://198.54.123.234:8710` | `http://162.0.208.88:8710` | ✅ Both running |
| **Sparket Engine** | `http://198.54.123.234:8711` | `http://162.0.208.88:8711` | ✅ Both running |
| **AI Automation** | `http://198.54.123.234:8715` | `http://162.0.208.88:8715` | ✅ Both running |
| **AI Gateway** | `http://198.54.123.234:8104` | `http://162.0.208.88:8104` | ✅ Both running |

---

## 📋 Complete Service Map

### 🔴 PRIMARY SERVER (198.54.123.234)

**KEEP ON PRIMARY - Do Not Change:**

| Service | Port | Purpose |
|---------|------|---------|
| whaletrack-magnet | 8600 | Trading engine |
| whaletrack-live | 8601 | Live trading |
| whaletrack-bridge-btc | - | BTC price bridge |
| whaletrack-bridge-eth | - | ETH price bridge |
| whaletrack-bridge-sol | - | SOL price bridge |
| fpai-data-service | 8125 | Memory system, data |
| fpai-nerve-center | 8120 | Integration hub |
| fpai-credits-gateway | 8765 | Credits API |
| godmode | 8120 | Dashboard |
| fpai-orchestrator | 8001 | Task routing |
| nginx | 80/443 | Web routing |
| postgresql | 5432 | Database |

**WILL BE STOPPED (after migration confirmed):**

| Service | Port | New Location |
|---------|------|--------------|
| fpai-aria | 8710 | → 162.0.208.88:8710 |
| fpai-sparket-engine | 8711 | → 162.0.208.88:8711 |
| fpai-ai-automation | 8715 | → 162.0.208.88:8715 |

---

### 🔵 SECONDARY SERVER (162.0.208.88)

**AI & INFERENCE:**

| Service | Port | Purpose |
|---------|------|---------|
| ai-brain | 8101 | Main AI inference |
| ollama | 11434 | Local LLM |
| fpai-ai-gateway | 8104 | AI access point |

**MIGRATED FROM PRIMARY (NEW HOME):**

| Service | Port | Purpose |
|---------|------|---------|
| fpai-aria | 8710 | Aria AI assistant |
| fpai-sparket-engine | 8711 | Marketing engine |
| fpai-ai-automation | 8715 | AI automation |

**CONSCIOUSNESS:**

| Service | Port | Purpose |
|---------|------|---------|
| fpai-consciousness_feeder | 8240 | Consciousness feeds |
| fpai-consciousness_verifier | 8230 | Verification |
| fpai-consciousness_dashboard | 8170 | Dashboard |

---

## 🔧 How to Update Your Code

### If you call Aria:

```python
# OLD
ARIA_URL = "http://198.54.123.234:8710"

# NEW
ARIA_URL = "http://162.0.208.88:8710"
```

### If you call Sparket Engine:

```python
# OLD
SPARKET_URL = "http://198.54.123.234:8711"

# NEW  
SPARKET_URL = "http://162.0.208.88:8711"
```

### If you call AI Automation:

```python
# OLD
AI_AUTOMATION_URL = "http://198.54.123.234:8715"

# NEW
AI_AUTOMATION_URL = "http://162.0.208.88:8715"
```

### Environment Variables to Update:

```bash
# Check your .env files for these patterns and update:
grep -r "198.54.123.234:871" /opt/fpai/SERVICES/
grep -r "198.54.123.234:8710" /opt/fpai/SERVICES/
```

---

## 📊 Memory Impact

| Server | Before Migration | After Migration |
|--------|------------------|-----------------|
| Primary | 6.2GB / 7.7GB (81%) | 5.8GB / 7.7GB (75%) |
| Secondary | 4.0GB / 31GB (13%) | 7.5GB / 31GB (24%) |

**Memory recovered on Primary:** ~217 MB

---

## ⏰ Timeline

| Date | Action |
|------|--------|
| Dec 13 | Services deployed redundantly on secondary |
| Dec 13-14 | **YOU:** Update service endpoints |
| Dec 15 | Stop services on primary (after confirmation) |
| Dec 16+ | Remove code from primary |

---

## ❓ Questions?

- **Which services call Aria?** Check: `grep -r "8710\|aria" /opt/fpai/`
- **Which services call Sparket?** Check: `grep -r "8711\|sparket" /opt/fpai/`
- **Test new endpoints:** `curl http://162.0.208.88:8710/health`

---

*Last Updated: December 13, 2025*





