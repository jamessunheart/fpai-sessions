# SPEC - Church Guidance Ministry (Droplet #13)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 13
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
Educational ministry providing guidance and resources for individuals interested in forming 508(c)(1)(A) churches. Service focuses on education, documentation support via AI, and clear legal boundaries—**NOT** legal advice or formation services.

### 1.2 Position in Ecosystem
This service sits in the **Experience Layer** (public-facing ministry), downstream of the Registry and Orchestrator. It integrates with Stripe for donations/payments and email providers for delivering educational resources.

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Service discovery & auth
- Orchestrator (droplet #10) - Task scheduling
- Credentials Manager (droplet #20) - API key management

**External Dependencies:**
- Stripe API (Payments/Donations)
- Anthropic Claude API (Document drafting)
- SendGrid/Brevo (Email delivery)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[Educational Resources]** - Hosting content on 508(c)(1)(A) structures.
2. **[Document Generation]** - AI-assisted drafting of bylaws/articles based on user intake.
3. **[Compliance Guidance]** - Checklists and educational frameworks.

### 2.2 Supported Operations
- `submit_intake` - Collect user ministry details.
- `generate_docs` - Draft educational templates.
- `process_payment` - Handle guidance package fees.

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
  "service_name": "church-guidance-ministry",
  "droplet_id": 13,
  "capabilities": ["education", "doc_generation", "payment_processing"],
  "supported_operations": ["submit_intake", "generate_docs"],
  "integration_endpoints": [
    { "path": "/api/v1/intake", "method": "POST" }
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
  "metrics": {
    "intakes_today": 5,
    "docs_generated": 12
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
    { "name": "registry", "status": "connected" }
  ],
  "external_apis": [
    { "name": "stripe", "status": "connected" },
    { "name": "anthropic", "status": "connected" }
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
  "status": "processing"
}
```

---

### 3.2 Business Logic Endpoints

#### Submit Intake
```
POST /api/v1/intake
```
**Request:**
```json
{
  "name": "User Name",
  "email": "user@example.com",
  "ministry_name": "New Hope",
  "mission_statement": "To serve..."
}
```

#### Generate Documents
```
POST /api/v1/generate/{intake_id}
```
**Response:**
```json
{
  "status": "queued",
  "job_id": "gen-123"
}
```

---

## 4. DATA MODEL

### 4.1 Database Schema (Conceptual)

#### `intakes`
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary Key |
| email | String | User email |
| details | JSON | Ministry details |
| status | Enum | pending, paid, generated |
| created_at | Timestamp | Submission time |

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=church-guidance-ministry
SERVICE_PORT=8003
DROPLET_ID=13
REGISTRY_URL=http://registry:8000
STRIPE_SECRET_KEY=sk_...
ANTHROPIC_API_KEY=sk-...
```

---

## 6. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] Legal disclaimers on all outputs (NOT legal advice)
- [x] Registers with Registry
- [ ] Tests implemented

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎

