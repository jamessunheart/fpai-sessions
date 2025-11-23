# SPEC - I-Match (Droplet #7)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 7
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
Professional matching platform connecting high-net-worth individuals with premium service providers. Acts as the "Tinder for Business," using AI scoring to facilitate connections and taking a 20% commission on successful engagements.

### 1.2 Position in Ecosystem
This service sits in the **Value Layer** (revenue generation), bridging demand (from Outreach) and supply (Provider Network). It feeds revenue data to the Treasury and Dashboard.

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Service discovery
- Orchestrator (droplet #10) - Task coordination
- I-Proactive (droplet #6) - Revenue tracking

**External Dependencies:**
- Stripe API (Subscriptions/Commissions)
- OpenAI/Anthropic API (Matching Logic)
- SendGrid (Notifications)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[AI Matching Engine]** - Scores compatibility between Needs and Offers (0-100%).
2. **[Marketplace Economy]** - Manages tiered subscriptions and transaction fees.
3. **[Referral Tracking]** - Credits contributors for successful introductions.

### 2.2 Supported Operations
- `submit_profile` - Create new user (Client/Provider).
- `find_matches` - Return ranked list of potential partners.
- `initiate_connection` - Start a conversation (deducts credits).

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
  "service_name": "i-match",
  "droplet_id": 7,
  "capabilities": ["matching", "marketplace", "subscriptions"],
  "supported_operations": ["match", "connect", "transact"],
  "integration_endpoints": [
    { "path": "/api/v1/matches", "method": "POST" }
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
    "active_users": 120,
    "matches_made": 45
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
    { "name": "registry", "status": "connected" },
    { "name": "i-proactive", "status": "connected" }
  ],
  "external_apis": [
    { "name": "stripe", "status": "connected" }
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

#### Find Matches
```
POST /api/v1/matches
```
**Request:**
```json
{
  "user_id": "user-123",
  "criteria": {
    "role": "developer",
    "budget_range": [5000, 10000]
  }
}
```
**Response:**
```json
{
  "matches": [
    { "id": "prov-456", "score": 0.95, "name": "Top Dev" }
  ]
}
```

---

## 4. DATA MODEL

### 4.1 Database Schema (Conceptual)

#### `users`
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary Key |
| type | Enum | client, provider |
| profile | JSON | Skills/Needs vector |
| subscription | String | free, basic, premium |

#### `connections`
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary Key |
| from_id | UUID | Initiator |
| to_id | UUID | Target |
| status | Enum | pending, accepted, paid |

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=i-match
SERVICE_PORT=8401
DROPLET_ID=7
REGISTRY_URL=http://registry:8000
STRIPE_SECRET_KEY=sk_...
OPENAI_API_KEY=sk-...
```

---

## 6. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] Registers with Registry
- [x] Tiered revenue model implemented
- [ ] Tests fully implemented

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎
