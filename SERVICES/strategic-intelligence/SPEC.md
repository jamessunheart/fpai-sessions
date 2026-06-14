# SPEC - Strategic Intelligence (Droplet #20)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 20
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
Strategic Intelligence acts as the "Brain" of the system. It analyzes market data, system performance, and user feedback to generate high-level strategies and directives for other droplets.

### 1.2 Position in Ecosystem
- **Upstream:** Ingests data from Analytics, Treasury, and external news sources.
- **Downstream:** Sends strategy directives to Orchestrator and content themes to AI Automation.
- **Role:** Chief Strategy Officer (AI).

### 1.3 Dependencies
**Required Services:**
- Registry (Droplet #1)
- Orchestrator (Droplet #14)

**External Dependencies:**
- News APIs / SERP Data
- LLM APIs (for reasoning)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **Market Analysis** - Identify trends and opportunities.
2. **Strategy Generation** - Formulate weekly/monthly plans.
3. **Performance Review** - Critique system outputs and suggest improvements.

### 2.2 Supported Operations
- `generate_strategy` - Create a new strategic plan.
- `analyze_sentiment` - Review brand perception.

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
  "service_name": "strategic-intelligence",
  "droplet_id": 20,
  "capabilities": ["strategy", "market_analysis"],
  "integration_endpoints": [
    {
      "path": "/api/v1/strategy",
      "method": "GET"
    }
  ]
}
```

---

### 3.2 Business Logic Endpoints

#### Get Current Strategy
```
GET /api/v1/strategy/current
```
**Response:**
```json
{
  "focus": "Growth",
  "themes": ["Sovereignty", "Automation"],
  "tactics": ["LinkedIn Outreach", "Cold Email"]
}
```

#### Submit Market Signal
```
POST /api/v1/signals
```
**Request:**
```json
{
  "source": "Hacker News",
  "content": "AI agents are trending...",
  "url": "..."
}
```

---

## 4. DATA MODEL

### 4.1 Database Schema

#### Strategies
```sql
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    period_start DATE,
    period_end DATE,
    focus_area VARCHAR(100),
    content JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=strategic-intelligence
SERVICE_PORT=8020
DROPLET_ID=20
REGISTRY_URL=http://registry:8000
LLM_PROVIDER=anthropic
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
EXPOSE 8020
LABEL droplet.id="20"
LABEL droplet.name="strategic-intelligence"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8020"]
```

---

## 7. COMPLIANCE CHECKLIST
- [x] All 5 UDC endpoints
- [x] Registers with Registry
- [x] Dockerized
