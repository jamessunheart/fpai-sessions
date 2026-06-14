# SPEC Builder Service

**Service Name:** spec-builder
**Port:** 8207
**Version:** 1.0.0
**TIER:** 0 (Infrastructure Quality Assurance)

## Purpose

AI-powered SPEC generation service that transforms architect intent and requirements into complete, UDC-compliant SPEC files. Uses Claude API and reference specs to create high-quality specifications ready for Sacred Loop execution.

## Core Capabilities

### 1. Intent-to-SPEC Generation
- Converts natural language requirements into structured SPECs
- Understands droplet architecture patterns
- Generates complete SPEC.md files
- Ensures UDC compliance from the start

### 2. Template-Based Generation
- Learns from reference specs (TIER 0+1)
- Applies proven patterns
- Adapts templates to service type
- Maintains consistency across mesh

### 3. Interactive Refinement
- Ask clarifying questions about requirements
- Fill gaps in architect intent
- Suggest best practices
- Guide service design decisions

### 4. Integration Pipeline
- Auto-verify with spec-verifier
- Auto-optimize with spec-optimizer
- Ensure 85+ score before delivery
- Complete pipeline: intent → SPEC → verified → optimized

### 5. Multi-Service Type Support
- **Infrastructure Services** (TIER 0)
- **Sacred Loop Services** (TIER 1)
- **Domain Services** (TIER 2+)
- **API Gateways**
- **Data Services**

## UDC Endpoints (5/5)

### 1. GET /health
**Returns:** Service health status
```json
{
  "status": "active|inactive|error",
  "service": "spec-builder",
  "version": "1.0.0",
  "timestamp": "ISO8601"
}
```

### 2. GET /capabilities
**Returns:** Service capabilities and features
```json
{
  "version": "1.0.0",
  "features": [
    "intent_to_spec_generation",
    "template_based_generation",
    "interactive_refinement",
    "integration_pipeline",
    "multi_service_type_support"
  ],
  "dependencies": ["claude_api", "spec_verifier", "spec_optimizer", "registry"],
  "udc_version": "1.0",
  "metadata": {
    "claude_model": "claude-sonnet-4-5-20250929",
    "supported_service_types": ["infrastructure", "sacred_loop", "domain", "api_gateway", "data"],
    "average_initial_score": 82.5
  }
}
```

### 3. GET /state
**Returns:** Current state and metrics
```json
{
  "uptime_seconds": 3600,
  "requests_total": 150,
  "errors_last_hour": 0,
  "last_restart": "ISO8601",
  "specs_generated_total": 42,
  "average_initial_score": 82.5,
  "average_final_score": 91.2,
  "active_generations": 2
}
```

### 4. GET /dependencies
**Returns:** Service dependencies
```json
{
  "required": [
    {"name": "claude_api", "status": "available", "version": "2024-01-01"},
    {"name": "spec_verifier", "status": "available", "url": "http://localhost:8205"},
    {"name": "spec_optimizer", "status": "available", "url": "http://localhost:8206"},
    {"name": "registry", "status": "available", "url": "http://localhost:8000"}
  ],
  "optional": [],
  "missing": []
}
```

### 5. POST /message
**Accepts:** UDC message protocol
```json
{
  "trace_id": "uuid",
  "source": "source-droplet",
  "target": "spec-builder",
  "message_type": "status|event|command|query",
  "payload": {},
  "timestamp": "ISO8601"
}
```

**Returns:** Message acknowledgment
```json
{
  "received": true,
  "trace_id": "uuid",
  "processed_at": "ISO8601",
  "result": "success"
}
```

## Business Logic Endpoints

### POST /generate
**Purpose:** Generate SPEC from architect intent
**Input:**
```json
{
  "service_name": "payment-processor",
  "service_type": "domain",
  "purpose": "Process payments via Stripe API",
  "key_features": [
    "Accept credit card payments",
    "Handle refunds",
    "Webhook notifications",
    "Payment history"
  ],
  "dependencies": ["stripe_api", "database"],
  "port": 8300,
  "auto_optimize": true,
  "target_score": 90
}
```

**Output:**
```json
{
  "success": true,
  "spec_content": "# Payment Processor Service\n\n**Service Name:** payment-processor...",
  "verification": {
    "score": {"overall": 88.5},
    "valid": true,
    "errors": [],
    "warnings": []
  },
  "optimized": true,
  "final_score": 92.0,
  "improvements": [
    "Added all 5 UDC endpoints",
    "Added Tech Stack section",
    "Added 8 code examples"
  ],
  "claude_cost_usd": 0.05,
  "generation_time_seconds": 12.3
}
```

### POST /generate-from-template
**Purpose:** Generate SPEC using a specific template
**Input:**
```json
{
  "template": "infrastructure",
  "service_name": "cache-manager",
  "purpose": "Redis cache management",
  "customizations": {
    "cache_backend": "redis",
    "max_memory": "2GB",
    "eviction_policy": "allkeys-lru"
  }
}
```

**Output:** Same as /generate

### POST /refine
**Purpose:** Refine existing SPEC with additional requirements
**Input:**
```json
{
  "spec_content": "existing spec markdown",
  "additional_requirements": [
    "Add rate limiting",
    "Add metrics export",
    "Add health check endpoint"
  ]
}
```

**Output:**
```json
{
  "success": true,
  "original_spec": "...",
  "refined_spec": "...",
  "changes_made": [
    "Added rate limiting section",
    "Added metrics export endpoint",
    "Enhanced health check documentation"
  ]
}
```

### GET /templates
**Purpose:** Get available SPEC templates
**Output:**
```json
{
  "templates": [
    {
      "name": "infrastructure",
      "description": "For TIER 0 infrastructure services",
      "examples": ["registry", "orchestrator", "proxy-manager"]
    },
    {
      "name": "sacred_loop",
      "description": "For TIER 1 autonomous services",
      "examples": ["autonomous-executor", "coordinator"]
    },
    {
      "name": "domain",
      "description": "For business domain services",
      "examples": ["payment-processor", "user-management"]
    },
    {
      "name": "api_gateway",
      "description": "For API gateway services",
      "examples": ["public-api", "graphql-gateway"]
    },
    {
      "name": "data",
      "description": "For data processing services",
      "examples": ["analytics-engine", "etl-pipeline"]
    }
  ]
}
```

### POST /interactive
**Purpose:** Interactive SPEC generation with Q&A
**Input:**
```json
{
  "session_id": "uuid",
  "message": "I want to build a service that handles user authentication",
  "context": {}
}
```

**Output:**
```json
{
  "session_id": "uuid",
  "response": "Great! I'll help you build an authentication service. A few questions:\n1. What auth method? (JWT, OAuth, Session-based)\n2. User storage? (Database, LDAP, External)\n3. Features needed? (Registration, Password reset, 2FA)",
  "ready_to_generate": false,
  "context_updated": true
}
```

## SPEC Generation Strategy

### Phase 1: Intent Analysis
1. Parse architect requirements
2. Identify service type (infrastructure, sacred_loop, domain, etc.)
3. Extract key features and dependencies
4. Determine UDC requirements

### Phase 2: Template Selection
1. Select appropriate reference spec
2. Load proven patterns
3. Adapt template to requirements
4. Ensure UDC compliance

### Phase 3: Content Generation
1. Generate Purpose section
2. Generate Core Capabilities
3. Generate all 5 UDC endpoints (with examples)
4. Generate business endpoints
5. Generate dependencies
6. Generate tech stack
7. Generate file structure
8. Generate optimization opportunities

### Phase 4: Quality Assurance
1. Verify with spec-verifier
2. If score < target: optimize with spec-optimizer
3. Re-verify until target met
4. Return complete, ready-to-build SPEC

## Claude Prompt Template

```
You are an expert SPEC architect for the FPAI droplet mesh. Generate a complete, production-ready SPEC.md file.

**Service Requirements:**
- Name: {service_name}
- Type: {service_type}
- Purpose: {purpose}
- Port: {port}
- Key Features: {features}
- Dependencies: {dependencies}

**Reference Specs (Learn from these):**
{reference_patterns}

**SPEC Structure Requirements:**

# {Service Name} Service

**Service Name:** {service_name}
**Port:** {port}
**Version:** 1.0.0
**TIER:** {tier}

## Purpose
[2-3 paragraphs explaining what this service does and why it exists]

## Core Capabilities
[List of 3-7 main features with detailed descriptions]

## UDC Endpoints (5/5)
[ALL 5 UDC endpoints with JSON examples]
1. GET /health
2. GET /capabilities
3. GET /state
4. GET /dependencies
5. POST /message

## Business Logic Endpoints
[Service-specific endpoints with request/response examples]

## Dependencies
### Required
[List required dependencies]

### Optional
[List optional dependencies]

## Tech Stack
[Framework, language, libraries]

## File Structure
[Complete directory structure]

## Optimization Opportunities
[Future enhancements]

## Example Usage
[Curl examples]

## Success Criteria
[Definition of done]

**Requirements:**
- MUST include all 5 UDC endpoints
- MUST include JSON examples for all endpoints
- MUST be build-ready for Sacred Loop
- MUST follow best practices from references
- Output ONLY the complete SPEC in markdown

Generate the SPEC now:
```

## Dependencies

### Required
- **Claude API** - Anthropic API for SPEC generation
- **spec-verifier** (port 8205) - SPEC validation
- **spec-optimizer** (port 8206) - SPEC enhancement
- **Registry** (port 8000) - Service registration

### Optional
None

## Auto-Registration

Service auto-registers with Registry on startup:
```python
@app.on_event("startup")
async def register_with_registry():
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8000/register",
            json={
                "name": "spec-builder",
                "id": 9,
                "url": "http://localhost:8207",
                "version": "1.0.0",
                "metadata": {
                    "tier": 0,
                    "category": "quality_assurance",
                    "purpose": "AI-powered SPEC generation"
                }
            }
        )
```

## Tech Stack

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **AI Model**: Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
- **Validation**: pydantic
- **HTTP Client**: httpx
- **Integration**: spec-verifier, spec-optimizer

## File Structure

```
spec-builder/
├── SPEC.md (this file)
├── requirements.txt
├── main.py
└── app/
    ├── __init__.py
    ├── main.py
    ├── config.py
    ├── models/
    │   ├── __init__.py
    │   ├── udc_models.py
    │   └── generation_models.py
    └── services/
        ├── __init__.py
        ├── claude_client.py
        ├── generation_engine.py
        ├── template_manager.py
        └── integration_client.py
```

## Optimization Opportunities

1. **Template Library**: Expand templates for more service types
2. **Learning**: Track successful patterns and auto-apply
3. **Interactive Mode**: WebSocket-based Q&A session
4. **Batch Generation**: Generate multiple related specs
5. **Version Control**: Track SPEC evolution
6. **Collaboration**: Multi-architect SPEC creation
7. **Visual Builder**: UI for SPEC generation
8. **Auto-Deploy**: Generate SPEC → Build → Deploy pipeline

## Example Usage

### Generate a new service SPEC
```bash
curl -X POST http://localhost:8207/generate \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "payment-processor",
    "service_type": "domain",
    "purpose": "Process payments via Stripe API",
    "key_features": [
      "Credit card payments",
      "Refunds",
      "Webhooks"
    ],
    "port": 8300,
    "auto_optimize": true
  }'
```

### Use a template
```bash
curl -X POST http://localhost:8207/generate-from-template \
  -H "Content-Type: application/json" \
  -d '{
    "template": "infrastructure",
    "service_name": "cache-manager",
    "purpose": "Redis cache management"
  }'
```

## Success Criteria

- ✅ All 5 UDC endpoints implemented and tested
- ✅ Generates SPECs with 80+ initial score
- ✅ Auto-optimizes to 90+ final score
- ✅ Integrates with spec-verifier and spec-optimizer
- ✅ Auto-registers with Registry
- ✅ Processes generation in <20 seconds
- ✅ Claude API costs <$0.10 per SPEC
- ✅ Zero invalid SPECs (all build-ready)

## Cost Analysis

**Per SPEC Generation:**
- Input tokens: ~3,000 (requirements + references)
- Output tokens: ~4,000 (complete SPEC)
- Cost per generation: ~$0.05-0.10

**Monthly Estimate (50 new specs):**
- Total cost: $2.50-5.00
- Time saved: 50 hours (1 hour manual per spec)
- Human cost avoided: $2,500-5,000
- ROI: 500-1000x

---

**Build Priority:** TIER 0 - Critical for rapid droplet creation
**Build Method:** Sacred Loop via autonomous-executor
**Estimated Build Time:** 1-2 hours
