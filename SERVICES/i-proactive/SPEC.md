# SPEC - I-Proactive (Droplet #6)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 6
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
I-Proactive is an autonomous outreach engine that identifies and engages potential partners or leads before they even realize they have a need. It shifts from reactive waiting to proactive connection.

### 1.2 Position in Ecosystem
- **Upstream:** Receives target criteria from Strategic Intelligence.
- **Downstream:** Feeds warm leads to I-Match or AI Automation for follow-up.
- **Role:** The Hunter / Scout.

### 1.3 Dependencies
**Required Services:**
- Registry (Droplet #1)
- Strategic Intelligence (Droplet #20) - Targeting logic

**External Dependencies:**
- LinkedIn API / Sales Navigator
- Twitter/X API
- Apollo.io / ZoomInfo (Data enrichment)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **Signal Detection** - Monitor social feeds/news for "intent signals" (e.g., "looking for X").
2. **Lead Enrichment** - Gather contact info and context on identified targets.
3. **Initial Outreach** - Send the first "icebreaker" message or connection request.

### 2.2 Supported Operations
- `scan_for_leads` - Run a search based on keywords/criteria.
- `enrich_profile` - Get email/phone for a social profile.
- `send_icebreaker` - Initiate contact.

---

## 3. API SPECIFICATION

### 3.1 UDC Endpoints (Required)

#### Health Check
```
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### Capabilities
```
GET /capabilities
```
**Response:**
```json
{
  "service_name": "i-proactive",
  "droplet_id": 6,
  "capabilities": ["lead_scouting", "outreach"],
  "integration_endpoints": [
    {
      "path": "/api/v1/leads",
      "method": "POST"
    }
  ]
}
```

---

### 3.2 Business Logic Endpoints

#### Submit Lead Criteria
```
POST /api/v1/scout
```
**Request:**
```json
{
  "keywords": ["hiring AI engineers", "building autonomous agents"],
  "platform": "linkedin",
  "max_results": 50
}
```
**Response:**
```json
{
  "job_id": "scout-123",
  "status": "queued"
}
```

#### Get Identified Leads
```
GET /api/v1/leads?job_id=scout-123
```
**Response:**
```json
{
  "leads": [
    {"name": "Jane Doe", "profile_url": "...", "signal": "Tweeted about needing AI help"}
  ]
}
```

---

## 4. DATA MODEL

### 4.1 Database Schema

#### Leads
```sql
CREATE TABLE leads (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    profile_url VARCHAR(500) UNIQUE,
    platform VARCHAR(50),
    status VARCHAR(50), -- 'new', 'contacted', 'responded'
    enrichment_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=i-proactive
SERVICE_PORT=8006
DROPLET_ID=6
REGISTRY_URL=http://registry:8000
LINKEDIN_COOKIE=...
```

---

## 6. DEPLOYMENT

### 6.1 Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8006
LABEL droplet.id="6"
LABEL droplet.name="i-proactive"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]
```

---

## 7. COMPLIANCE CHECKLIST
- [x] All 5 UDC endpoints
- [x] Registers with Registry
- [x] Dockerized
