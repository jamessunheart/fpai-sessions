# SPEC - AI Automation (Droplet #11)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 11
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
The AI Automation Service is the execution engine for automated marketing, outreach, and content generation. It translates high-level intent into concrete actions (emails, posts, messages) using LLMs.

### 1.2 Position in Ecosystem
- **Upstream:** Receives tasks from Orchestrator (Droplet #14) and content from Strategic Intelligence (Droplet #20).
- **Downstream:** Pushes content to social platforms (via specialized tools) and email gateways.
- **Role:** "The Hands" of the autonomous system.

### 1.3 Dependencies
**Required Services:**
- Registry (Droplet #1) - Discovery & Auth
- Orchestrator (Droplet #14) - Task assignment
- Strategic Intelligence (Droplet #20) - Content strategy source

**External Dependencies:**
- Anthropic API (Claude) - Content generation
- OpenAI API (GPT-4) - Alternative generation
- SendGrid/Mailgun - Email delivery

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **Content Generation** - Create high-quality marketing copy, emails, and social posts.
2. **Campaign Execution** - Run multi-step outreach sequences.
3. **Personalization** - Adapt content based on recipient data.

### 2.2 Supported Operations
- `generate_content` - Produce text based on prompt/context.
- `execute_campaign` - Trigger a defined outreach sequence.
- `optimize_copy` - Refine existing text for better conversion.

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
  "capabilities": ["content_generation", "campaign_execution"],
  "supported_operations": ["generate_content", "execute_campaign"],
  "integration_endpoints": [
    {
      "path": "/api/v1/generate",
      "method": "POST",
      "description": "Generate content"
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
    "requests_per_minute": 12.5,
    "average_response_time_ms": 1500
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
  "external_apis": [
    {
      "name": "anthropic",
      "status": "connected"
    }
  ]
}
```

#### Message
```
POST /message
```
Standard UDC message handling for async tasks.

---

### 3.2 Business Logic Endpoints

#### Generate Content
```
POST /api/v1/generate
```
**Request:**
```json
{
  "prompt": "Write a welcome email for new subscribers",
  "context": {"audience": "tech founders"},
  "model": "claude-3-opus"
}
```
**Response:**
```json
{
  "content": "Welcome to the future...",
  "metadata": {"tokens_used": 450}
}
```

#### Execute Campaign
```
POST /api/v1/campaigns/execute
```
**Request:**
```json
{
  "campaign_id": "camp-123",
  "target_segment": "new-leads"
}
```

---

## 4. DATA MODEL

### 4.1 Database Schema

#### Campaigns
```sql
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    config JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Generations
```sql
CREATE TABLE generations (
    id SERIAL PRIMARY KEY,
    prompt TEXT,
    output TEXT,
    model VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=ai-automation
SERVICE_PORT=8011
DROPLET_ID=11
REGISTRY_URL=http://registry:8000
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...
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
EXPOSE 8011
LABEL droplet.id="11"
LABEL droplet.name="ai-automation"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]
```

---

## 7. COMPLIANCE CHECKLIST
- [x] All 5 UDC endpoints
- [x] Registers with Registry
- [x] Sends Heartbeats
- [x] JWT Auth
- [x] Dockerized
