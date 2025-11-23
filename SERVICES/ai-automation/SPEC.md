# SPEC - AI Marketing Engine (Droplet #11)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 11
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
The AI Marketing Engine automates the outreach and engagement process for Full Potential AI. It leverages the multi-agent system to conduct market research, engage with prospects via email and social channels, and qualify leads for the onboarding funnel.

### 1.2 Position in Ecosystem
This service sits in the **Revenue Layer**, downstream of the Registry and Orchestrator, and upstream of the Dashboard. It interacts with external APIs (Apollo, SendGrid/Brevo, Reddit) and feeds data into the central CRM (via I-Match or direct integration).

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Authentication & service discovery
- Orchestrator (droplet #10) - Task coordination and scheduling
- Credentials Manager (droplet #20) - Secure API key access

**Optional Services:**
- I-Match (droplet #7) - Lead handoff for matching
- Content Generation Engine (droplet #18) - Dynamic content for emails

**External Dependencies:**
- Apollo API (Prospecting)
- Brevo/SendGrid API (Email)
- Reddit API (Social Engagement)
- OpenAI/Anthropic API (LLM Intelligence)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[Prospect Discovery]** - Finds high-fit leads based on ideal customer profiles (ICP).
2. **[Autonomous Outreach]** - Sends personalized emails and messages at scale.
3. **[Engagement Tracking]** - Monitors opens, clicks, replies, and sentiment.

### 2.2 Supported Operations
- `find_prospects` - Search for new leads matching criteria.
- `send_campaign` - Execute an email sequence to a prospect list.
- `check_replies` - Scan for and analyze incoming responses.
- `qualify_lead` - Score a lead based on engagement and fit.

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
  "timestamp": "2025-11-23T12:00:00Z",
  "uptime_seconds": 86400,
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
  "service_name": "ai-automation",
  "droplet_id": 11,
  "capabilities": ["prospect_discovery", "autonomous_outreach", "engagement_tracking"],
  "supported_operations": ["find_prospects", "send_campaign", "check_replies"],
  "integration_endpoints": [
    {
      "path": "/api/v1/campaigns",
      "method": "POST",
      "description": "Start a new campaign"
    }
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
  "mode": "production",
  "active_campaigns": 3,
  "metrics": {
    "emails_sent_today": 150,
    "prospects_found_today": 50
  }
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
    {
      "name": "registry",
      "type": "service",
      "status": "connected",
      "host": "registry:8000"
    }
  ],
  "optional_services": [],
  "external_apis": [
    {
        "name": "apollo",
        "status": "connected"
    },
    {
        "name": "brevo",
        "status": "connected"
    }
  ]
}
```

#### Message
```
POST /message
```
**Request:**
```json
{
  "from_service": "orchestrator",
  "message_type": "task_assignment",
  "payload": {
      "action": "start_outreach",
      "target_segment": "saas_founders"
  },
  "reply_to": "http://orchestrator:8001/callback"
}
```

---

### 3.2 Business Logic Endpoints

#### Trigger Outreach
```
POST /api/v1/outreach/trigger
```
**Purpose:** Manually trigger an outreach run for a specific segment.

**Request:**
```json
{
  "segment": "tech_startups",
  "limit": 50
}
```

**Response (200 OK):**
```json
{
  "data": {
    "job_id": "job-123",
    "status": "queued"
  },
  "meta": {
    "timestamp": "2025-11-23T12:00:00Z"
  }
}
```

---

## 4. DATA MODEL

### 4.1 Database Schema (Conceptual)

#### `prospects`
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary Key |
| email | String | Unique email |
| status | Enum | new, contacted, replied, qualified |
| score | Int | Lead score (0-100) |
| last_contacted | Timestamp | Last engagement time |

#### `campaigns`
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary Key |
| name | String | Campaign Name |
| status | Enum | active, paused, completed |
| metrics | JSON | Open/Click/Reply stats |

---

## 5. BUSINESS LOGIC

### 5.1 Core Workflows

#### Outreach Cycle
**Trigger:** Scheduled Cron or API Call
**Steps:**
1. Fetch new prospects from Apollo API based on ICP.
2. Filter duplicates and validate emails.
3. Generate personalized email content using LLM.
4. Send via Brevo/SendGrid.
5. Log event to `campaigns` table.

**Result:** Emails sent, database updated.

### 5.2 Integration Patterns
- **Registry:** Registers as "ai-automation" on port 8700.
- **Orchestrator:** Listens for "marketing_sprint" tasks.

---

## 6. CONFIGURATION

### 6.1 Environment Variables
```bash
SERVICE_NAME=ai-automation
SERVICE_PORT=8700
DROPLET_ID=11
REGISTRY_URL=http://registry:8000
APOLLO_API_KEY=sk_...
BREVO_API_KEY=xkeysib-...
OPENAI_API_KEY=sk-...
```

---

## 7. DEPLOYMENT

### 7.1 Docker Configuration
**Dockerfile:** Standard Python 3.11-slim image exposing port 8700.
**Labels:** `droplet.id="11"`, `droplet.name="ai-automation"`, `droplet.udc_compliant="true"`.

---

## 8. TESTING
- `pytest` suite covering /health and outreach logic.
- Mock external APIs for reliable CI execution.

---

## 9. SECURITY
- API Keys stored in Vault (Credentials Manager), injected at runtime.
- Rate limiting on external API calls to prevent bans.

---

## 10. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] Registers with Registry
- [x] Environment variables standardized
- [ ] Tests fully implemented (In Progress)

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎

