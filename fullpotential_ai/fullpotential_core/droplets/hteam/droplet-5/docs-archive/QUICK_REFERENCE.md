# 🚀 Droplet 2 - Quick Reference

**Steward:** Haythem Timoumi  
**Status:** ✅ Active and Ready

---

## 📡 Main Endpoint (For Nexus Integration)

```
POST https://drop2.fullpotential.ai/heartbeats
```

**Body:**
```json
{
  "Cell_ID": "droplet_13",
  "CPU_Usage": 45.2,
  "RAM_Usage": 512,
  "Status": "active",
  "Timestamp": "2025-01-15T10:30:00Z"
}
```

---

## 📚 Documentation Files

1. **DROPLET2_API_DOCUMENTATION.md** - Complete API reference with all endpoints
2. **POSTMAN_TESTING_GUIDE.md** - Step-by-step Postman instructions
3. **Droplet2_Postman_Collection.json** - Import this into Postman
4. **TEAM_MESSAGE_FOR_SURESH.md** - Copy/paste message for team chat

---

## ⚡ Quick Test

```bash
curl -X POST https://drop2.fullpotential.ai/heartbeats \
  -H "Content-Type: application/json" \
  -d '{"Cell_ID":"droplet_13","CPU_Usage":45.2,"RAM_Usage":512,"Status":"active","Timestamp":"2025-01-15T10:30:00Z"}'
```

---

## 📋 All Available Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /heartbeats | Submit metrics (USE THIS) |
| GET | /heartbeats | Get all metrics |
| GET | /sprints | Get all sprints |
| POST | /sprints | Create sprint |
| PUT | /sprints/{id} | Update sprint |
| DELETE | /sprints/{id} | Delete sprint |
| GET | /cells | Get droplet status |
| GET | /proof | Get proofs |
| POST | /daily-digest | Generate analytics |

---

## ✅ Ready for Integration

Share with team:
- Base URL: `https://drop2.fullpotential.ai`
- Main endpoint: `POST /heartbeats`
- Schema: See TEAM_MESSAGE_FOR_SURESH.md
- Postman collection: Droplet2_Postman_Collection.json
