# SPEC - Phase 1 Execution Engine (Droplet #15)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 15
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
A focused automation engine dedicated to the "Phase 1" launch strategy (Reddit Outreach -> I-Match). It orchestrates specific, tactical scripts to execute the initial go-to-market plan without the overhead of the full Autonomous Executor.

### 1.2 Position in Ecosystem
This service sits in the **Execution Layer** (Tactical). It is a temporary or specialized droplet designed to "bootstrap" the ecosystem's first revenue.

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Service discovery
- I-Match (droplet #7) - Destination for leads

**External Dependencies:**
- Reddit API (PRAW)
- Selenium/Playwright (Browser automation if needed)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[Reddit Automation]** - Scans subreddits for keywords, identifying high-intent leads.
2. **[Outreach Sequencing]** - Manages the initial "Hello" -> "Value Add" -> "Link" sequence.
3. **[Handoff Logic]** - Pushes qualified leads into the I-Match funnel.

### 2.2 Supported Operations
- `run_campaign` - Execute specific outreach plan.
- `status_report` - Summary of engagement metrics.

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
  "version": "1.0.0",
  "timestamp": "2025-11-23T12:00:00Z"
}
```

#### Capabilities
```
GET /capabilities
```
**Response:**
```json
{
  "service_name": "phase1-execution-engine",
  "droplet_id": 15,
  "capabilities": ["reddit_automation", "outreach"],
  "supported_operations": ["run_campaign"],
  "integration_endpoints": [
    { "path": "/api/v1/run", "method": "POST" }
  ]
}
```

#### State
```
GET /state
```
**Response:**
```json
{
  "status": "active",
  "campaign_progress": 0.65
}
```

#### Dependencies
```
GET /dependencies
```
**Response:**
```json
{
  "required_services": [
    { "name": "registry", "status": "connected" }
  ],
  "external_apis": [
    { "name": "reddit", "status": "connected" }
  ]
}
```

#### Message
```
POST /message
```
**Response:**
```json
{
  "received": true,
  "status": "processed"
}
```

---

### 3.2 Business Logic Endpoints

#### Run Campaign
```
POST /api/v1/run
```
**Request:**
```json
{
  "target_subreddit": "saas",
  "keywords": ["deployment", "DevOps"]
}
```
**Response:**
```json
{
  "job_id": "run-555",
  "status": "started"
}
```

---

## 4. DATA MODEL

### 4.1 Campaign State
Stores transient state of ongoing outreach.

#### `leads`
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Lead ID |
| source | String | "reddit/r/saas" |
| status | Enum | new, contacted, replied |

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=phase1-execution-engine
SERVICE_PORT=8015
DROPLET_ID=15
REGISTRY_URL=http://registry:8000
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
```

---

## 6. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] Registers with Registry
- [ ] Tests implemented

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎

