# Message for Team - Droplet 2 API Details

---

**Hey team! 👋**

**Droplet #2 (Dashboard) is ready for integration.**

## 📡 Main Endpoint for Metrics Sync

**For Suresh (Nexus #13) and other droplets to push metrics:**

### Endpoint
```
POST https://drop2.fullpotential.ai/heartbeats
```

### JSON Schema
```json
{
  "Cell_ID": "droplet_13",
  "CPU_Usage": 45.2,
  "RAM_Usage": 512,
  "Status": "active",
  "Timestamp": "2025-01-15T10:30:00Z"
}
```

### Field Details
- **Cell_ID** (string): Your droplet identifier (e.g., "droplet_13", "droplet_10")
- **CPU_Usage** (number): CPU percentage 0-100
- **RAM_Usage** (number): Memory in MB
- **Status** (string): "active" | "inactive" | "error"
- **Timestamp** (string): ISO 8601 format (UTC)

### Example Response
```json
{
  "id": "rec123abc",
  "createdTime": "2025-01-15T10:30:00.000Z",
  "fields": {
    "Cell_ID": "droplet_13",
    "CPU_Usage": 45.2,
    "RAM_Usage": 512,
    "Status": "active",
    "Timestamp": "2025-01-15T10:30:00Z"
  }
}
```

---

## 📚 Full API Documentation

See **DROPLET2_API_DOCUMENTATION.md** for complete endpoint list including:
- GET/POST /heartbeats
- GET/POST/PUT/DELETE /sprints
- GET /cells
- GET /proof
- POST /daily-digest

All endpoints include Postman setup instructions.

---

## ✅ Ready for Testing

You can test immediately with:
```bash
curl -X POST https://drop2.fullpotential.ai/heartbeats \
  -H "Content-Type: application/json" \
  -d '{
    "Cell_ID": "droplet_13",
    "CPU_Usage": 45.2,
    "RAM_Usage": 512,
    "Status": "active",
    "Timestamp": "2025-01-15T10:30:00Z"
  }'
```

Or use Postman with the examples in the documentation.

---

**Haythem**  
Droplet #2 - Dashboard  
Status: ✅ Active
