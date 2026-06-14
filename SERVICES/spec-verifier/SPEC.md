# SPEC Verifier Service

**Service Name:** spec-verifier
**Port:** 8205
**Version:** 1.0.0
**TIER:** 0 (Infrastructure Quality Assurance)

## Purpose

Validates SPEC files for completeness, quality, and UDC compliance BEFORE droplet builds. Acts as a quality gate ensuring all specs meet minimum standards for successful Sacred Loop execution.

## Core Capabilities

### 1. SPEC File Validation
- Parse and validate SPEC.md structure
- Check for required sections (Purpose, Capabilities, UDC Endpoints, Dependencies, etc.)
- Verify markdown formatting and readability
- Detect missing or incomplete sections

### 2. UDC Compliance Verification
- Verify all 5 UDC endpoints are documented
- Validate endpoint specifications match UDC standard
- Check message protocol documentation
- Verify dependency declarations

### 3. Quality Scoring
- Completeness score (0-100%)
- Clarity score (description quality)
- UDC compliance score
- Build-readiness score

### 4. Optimization Recommendations
- Identify missing sections
- Suggest improvements for clarity
- Recommend additional features
- Flag potential issues before build

### 5. SPEC Comparison
- Compare against reference specs (TIER 0+1)
- Identify best practices from existing services
- Suggest patterns from successful builds

## UDC Endpoints (5/5)

### 1. GET /health
**Returns:** Service health status
```json
{
  "status": "active|inactive|error",
  "service": "spec-verifier",
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
    "spec_validation",
    "udc_compliance_check",
    "quality_scoring",
    "optimization_recommendations",
    "spec_comparison"
  ],
  "dependencies": ["registry"],
  "udc_version": "1.0",
  "metadata": {
    "supported_spec_versions": ["1.0"],
    "validation_rules": 25,
    "reference_specs": 6
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
  "specs_verified_total": 42,
  "average_score": 87.5,
  "active_verifications": 2
}
```

### 4. GET /dependencies
**Returns:** Service dependencies
```json
{
  "required": [
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
  "target": "spec-verifier",
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

### POST /verify
**Purpose:** Verify a SPEC file
**Input:**
```json
{
  "spec_content": "markdown content",
  "spec_path": "/path/to/SPEC.md",
  "strict_mode": false
}
```

**Output:**
```json
{
  "valid": true,
  "score": {
    "completeness": 95,
    "clarity": 88,
    "udc_compliance": 100,
    "build_readiness": 92,
    "overall": 93.75
  },
  "sections": {
    "found": ["Purpose", "Capabilities", "UDC Endpoints", "Dependencies"],
    "missing": [],
    "incomplete": []
  },
  "udc_endpoints": {
    "documented": 5,
    "required": 5,
    "missing": [],
    "compliant": true
  },
  "recommendations": [
    "Consider adding optimization opportunities section",
    "Add example API usage for business endpoints"
  ],
  "errors": [],
  "warnings": [
    "Business endpoint /hire could benefit from more detailed error responses"
  ]
}
```

### POST /verify-file
**Purpose:** Verify a SPEC file by path
**Input:**
```json
{
  "file_path": "/Users/jamessunheart/Development/SERVICES/jobs/SPEC.md",
  "strict_mode": false
}
```

**Output:** Same as /verify

### GET /reference-specs
**Purpose:** Get list of reference specs for comparison
**Output:**
```json
{
  "count": 6,
  "specs": [
    {
      "name": "registry",
      "path": "/Users/jamessunheart/Development/SERVICES/registry/SPEC.md",
      "tier": 0,
      "score": 98
    },
    {
      "name": "orchestrator",
      "path": "/Users/jamessunheart/Development/SERVICES/orchestrator/SPEC.md",
      "tier": 0,
      "score": 96
    }
  ]
}
```

### POST /compare
**Purpose:** Compare spec against reference specs
**Input:**
```json
{
  "spec_content": "markdown content",
  "compare_with": ["registry", "orchestrator"]
}
```

**Output:**
```json
{
  "similarities": [
    "UDC endpoint documentation format matches best practices",
    "Dependency structure follows TIER 0 pattern"
  ],
  "differences": [
    "Missing optimization opportunities section (present in 5/6 references)",
    "Business endpoints lack detailed error responses (present in jobs, autonomous-executor)"
  ],
  "recommendations": [
    "Add optimization section like autonomous-executor",
    "Document error responses following jobs pattern"
  ]
}
```

## Validation Rules

### Required Sections
1. **Service Name** - Must be present in header
2. **Port** - Must be documented
3. **Purpose** - Clear description of service function
4. **Core Capabilities** - List of main features
5. **UDC Endpoints** - All 5 documented with request/response examples
6. **Business Logic Endpoints** - Service-specific endpoints
7. **Dependencies** - Required and optional dependencies

### UDC Compliance Checks
1. All 5 UDC endpoints documented
2. /health returns correct status format
3. /capabilities lists features and dependencies
4. /state includes uptime and metrics
5. /dependencies lists required/optional/missing
6. /message accepts UDC message protocol

### Quality Metrics
- **Completeness (40%)**: All required sections present
- **Clarity (30%)**: Clear descriptions, examples provided
- **UDC Compliance (20%)**: All endpoints documented correctly
- **Build-Readiness (10%)**: Dependencies clear, examples complete

### Scoring Thresholds
- **90-100%**: Excellent - Ready for build
- **75-89%**: Good - Minor improvements recommended
- **60-74%**: Fair - Significant improvements needed
- **Below 60%**: Poor - Not ready for build

## Dependencies

### Required
- **Registry** (port 8000) - Service registration and discovery

### Optional
- **Claude API** - For AI-powered spec analysis and recommendations (future)

## Auto-Registration

Service auto-registers with Registry on startup:
```python
@app.on_event("startup")
async def register_with_registry():
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8000/register",
            json={
                "name": "spec-verifier",
                "id": 7,
                "url": "http://localhost:8205",
                "version": "1.0.0",
                "metadata": {
                    "tier": 0,
                    "category": "quality_assurance"
                }
            }
        )
```

## Tech Stack

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Validation**: Pydantic
- **Markdown Parsing**: python-markdown, BeautifulSoup4
- **HTTP Client**: httpx

## File Structure

```
spec-verifier/
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
    │   └── verification_models.py
    └── services/
        ├── __init__.py
        ├── spec_parser.py
        ├── udc_validator.py
        ├── quality_scorer.py
        └── recommendation_engine.py
```

## Optimization Opportunities

1. **AI-Powered Analysis**: Use Claude API to analyze spec quality and suggest improvements
2. **SPEC Templates**: Generate starter templates for common service types
3. **Version Control**: Track spec changes over time
4. **Batch Verification**: Verify multiple specs simultaneously
5. **CI/CD Integration**: Block builds for specs below quality threshold
6. **Spec Diff**: Compare spec versions to track evolution
7. **Best Practice Library**: Build corpus of high-quality spec patterns

## Example Usage

### Verify a SPEC file
```bash
curl -X POST http://localhost:8205/verify \
  -H "Content-Type: application/json" \
  -d '{
    "spec_path": "/Users/jamessunheart/Development/SERVICES/jobs/SPEC.md"
  }'
```

### Compare against reference specs
```bash
curl -X POST http://localhost:8205/compare \
  -H "Content-Type: application/json" \
  -d '{
    "spec_path": "/Users/jamessunheart/Development/SERVICES/new-service/SPEC.md",
    "compare_with": ["registry", "orchestrator", "jobs"]
  }'
```

## Success Criteria

- ✅ All 5 UDC endpoints implemented and tested
- ✅ Validates SPEC files with 95%+ accuracy
- ✅ Provides actionable recommendations
- ✅ Scores align with human assessment
- ✅ Auto-registers with Registry
- ✅ Processes verification in <1 second
- ✅ Zero false positives on reference specs

---

**Build Priority:** TIER 0 - Critical quality gate for all future builds
**Build Method:** Sacred Loop via autonomous-executor
**Estimated Build Time:** 1-2 hours
