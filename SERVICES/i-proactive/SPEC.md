# SPEC - I-Proactive (Droplet #6)

**Version:** 1.0
**Created:** 2025-11-23
**Droplet ID:** 6
**Status:** Production

---

## 1. SERVICE OVERVIEW

### 1.1 Purpose
The intelligence engine that transforms static intents into proactive execution. It uses a multi-agent system (CrewAI) to parallelize tasks, learn from outcomes (Mem0), and optimize revenue strategies.

### 1.2 Position in Ecosystem
This service sits in the **Intelligence Layer**, acting as the "Strategy Brain" for the ecosystem. It directs I-Match (execution) and reports to Mission Control (visibility).

### 1.3 Dependencies
**Required Services:**
- Registry (droplet #1) - Service discovery
- Orchestrator (droplet #10) - Task assignment
- Credentials Manager (droplet #20) - Key access

**External Dependencies:**
- OpenAI/Anthropic/Gemini (LLM Intelligence)
- Mem0 (Long-term Memory)
- CrewAI (Agent Framework)

---

## 2. CAPABILITIES

### 2.1 Core Capabilities
1. **[Multi-Agent Execution]** - Parallel processing via specialized agents (Strategist, Builder, etc.).
2. **[Persistent Memory]** - Retains context across sessions to improve decision quality.
3. **[Model Routing]** - Dynamically selects the best LLM for each task (Cost vs. Capability).

### 2.2 Supported Operations
- `execute_plan` - Run a multi-step strategy.
- `store_memory` - Save key insights.
- `retrieve_context` - Get relevant history for a task.

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
  "service_name": "i-proactive",
  "droplet_id": 6,
  "capabilities": ["multi_agent", "memory", "model_routing"],
  "supported_operations": ["plan", "learn", "optimize"],
  "integration_endpoints": [
    { "path": "/api/v1/execute", "method": "POST" }
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
  "active_crews": 2,
  "memory_size_mb": 45.2
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
    { "name": "openai", "status": "connected" },
    { "name": "mem0", "status": "connected" }
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

#### Execute Strategy
```
POST /api/v1/execute
```
**Request:**
```json
{
  "goal": "Increase revenue by 10%",
  "constraints": ["budget < $100", "timeline < 7d"]
}
```
**Response:**
```json
{
  "plan_id": "plan-789",
  "agents_assigned": ["strategist", "analyst"]
}
```

---

## 4. DATA MODEL

### 4.1 Memory Store
Uses vector storage (Mem0) to index past decisions, outcomes, and user preferences.

#### `memories`
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Memory ID |
| vector | List[Float] | Embedding |
| content | Text | The insight |
| context | JSON | Metadata |

---

## 5. CONFIGURATION

### 5.1 Environment Variables
```bash
SERVICE_NAME=i-proactive
SERVICE_PORT=8400
DROPLET_ID=6
REGISTRY_URL=http://registry:8000
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
GEMINI_API_KEY=...
MEM0_API_KEY=...
```

---

## 6. COMPLIANCE CHECKLIST
- [x] UDC Endpoints defined
- [x] Registers with Registry
- [x] Persistent memory integration
- [ ] Tests implemented

---

**This SPEC is the contract. Build matches SPEC exactly.**
🌐⚡💎
