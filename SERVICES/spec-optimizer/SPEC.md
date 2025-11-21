# SPEC Optimizer Service

**Service Name:** spec-optimizer
**Port:** 8206
**Version:** 1.0.0
**TIER:** 0 (Infrastructure Quality Assurance)

## Purpose

AI-powered SPEC optimization service that uses Claude API to intelligently improve SPEC files for completeness, clarity, and UDC compliance. Acts as an enhancement layer between spec-verifier and spec-builder to ensure maximum quality specs before droplet builds.

## Core Capabilities

### 1. AI-Powered SPEC Enhancement
- Uses Claude Sonnet 4.5 to analyze and improve specs
- Understands UDC standard requirements
- Learns from reference specs (TIER 0+1)
- Maintains original intent while improving structure

### 2. Multi-Pass Optimization
- **Pass 1: Structure** - Ensures all required sections present
- **Pass 2: Clarity** - Improves descriptions and examples
- **Pass 3: UDC Compliance** - Adds/fixes endpoint documentation
- **Pass 4: Best Practices** - Applies patterns from reference specs

### 3. Intelligent Gap Filling
- Identifies missing sections from spec-verifier feedback
- Generates missing content based on service purpose
- Adds code examples for endpoints
- Suggests optimization opportunities

### 4. Quality Verification Loop
- Runs spec-verifier before optimization
- Re-verifies after optimization
- Ensures score improvement
- Provides before/after comparison

### 5. Preservation of Intent
- Never removes existing content
- Enhances rather than replaces
- Maintains technical accuracy
- Preserves custom sections

## UDC Endpoints (5/5)

### 1. GET /health
**Returns:** Service health status
```json
{
  "status": "active|inactive|error",
  "service": "spec-optimizer",
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
    "ai_powered_optimization",
    "multi_pass_enhancement",
    "gap_filling",
    "quality_verification_loop",
    "intent_preservation"
  ],
  "dependencies": ["claude_api", "spec_verifier", "registry"],
  "udc_version": "1.0",
  "metadata": {
    "claude_model": "claude-sonnet-4-5-20250929",
    "optimization_passes": 4,
    "average_score_improvement": 35.5
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
  "specs_optimized_total": 42,
  "average_score_before": 65.3,
  "average_score_after": 87.8,
  "average_improvement": 22.5,
  "active_optimizations": 2
}
```

### 4. GET /dependencies
**Returns:** Service dependencies
```json
{
  "required": [
    {"name": "claude_api", "status": "available", "version": "2024-01-01"},
    {"name": "spec_verifier", "status": "available", "url": "http://localhost:8205"},
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
  "target": "spec-optimizer",
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

### POST /optimize
**Purpose:** Optimize a SPEC file using AI
**Input:**
```json
{
  "spec_content": "markdown content",
  "spec_path": "/path/to/SPEC.md",
  "optimization_level": "basic|standard|aggressive",
  "preserve_sections": ["Custom Section"],
  "target_score": 90
}
```

**Output:**
```json
{
  "success": true,
  "original_spec": "...",
  "optimized_spec": "...",
  "verification_before": {
    "score": {"overall": 65.0},
    "errors": [...],
    "warnings": [...]
  },
  "verification_after": {
    "score": {"overall": 92.0},
    "errors": [],
    "warnings": []
  },
  "improvements": [
    "Added UDC Endpoints section with all 5 endpoints",
    "Enhanced Purpose section with clearer description",
    "Added Tech Stack section",
    "Added 10 code examples",
    "Filled optimization opportunities"
  ],
  "score_improvement": 27.0,
  "claude_cost_usd": 0.03
}
```

### POST /optimize-file
**Purpose:** Optimize a SPEC file by path
**Input:**
```json
{
  "file_path": "/Users/jamessunheart/Development/SERVICES/jobs/SPEC.md",
  "optimization_level": "standard",
  "save_backup": true,
  "overwrite": false
}
```

**Output:** Same as /optimize, plus:
```json
{
  "backup_path": "/Users/jamessunheart/Development/SERVICES/jobs/SPEC.md.backup",
  "output_path": "/Users/jamessunheart/Development/SERVICES/jobs/SPEC.optimized.md"
}
```

### POST /batch-optimize
**Purpose:** Optimize multiple SPEC files
**Input:**
```json
{
  "file_paths": [
    "/path/to/spec1.md",
    "/path/to/spec2.md"
  ],
  "optimization_level": "standard"
}
```

**Output:**
```json
{
  "results": [
    {"file": "spec1.md", "success": true, "score_improvement": 25.0},
    {"file": "spec2.md", "success": true, "score_improvement": 18.5}
  ],
  "total_improved": 2,
  "total_failed": 0,
  "average_improvement": 21.75
}
```

### GET /optimization-strategies
**Purpose:** Get available optimization strategies
**Output:**
```json
{
  "levels": {
    "basic": {
      "description": "Fix critical errors only",
      "passes": 1,
      "cost_range": "$0.01-$0.02"
    },
    "standard": {
      "description": "Fix errors + improve quality",
      "passes": 2,
      "cost_range": "$0.02-$0.04"
    },
    "aggressive": {
      "description": "Maximum quality enhancement",
      "passes": 4,
      "cost_range": "$0.04-$0.08"
    }
  }
}
```

## Optimization Strategy

### Level: Basic (1 Pass)
1. Fix critical errors from spec-verifier
2. Add missing required sections
3. Ensure UDC compliance

**Target:** 75+ score
**Cost:** ~$0.01-0.02 per spec

### Level: Standard (2 Passes)
1. All Basic optimizations
2. Enhance clarity and descriptions
3. Add code examples
4. Improve completeness

**Target:** 85+ score
**Cost:** ~$0.02-0.04 per spec

### Level: Aggressive (4 Passes)
1. All Standard optimizations
2. Apply best practices from references
3. Add optimization opportunities
4. Maximize build-readiness

**Target:** 90+ score
**Cost:** ~$0.04-0.08 per spec

## Claude Prompt Template

```
You are a SPEC optimization expert for the FPAI droplet mesh. Your task is to improve the following SPEC file while preserving its original intent.

**Original SPEC:**
{spec_content}

**Verification Report:**
Score: {score}/100
Errors: {errors}
Warnings: {warnings}
Missing Sections: {missing}

**Reference Specs (Best Practices):**
{reference_patterns}

**Requirements:**
1. Maintain all existing content (enhance, don't replace)
2. Add missing UDC endpoints (all 5 required)
3. Improve clarity and add examples
4. Follow best practices from references
5. Output ONLY the complete optimized SPEC in markdown

**Optimization Level:** {level}
**Target Score:** {target_score}+

Generate the optimized SPEC now:
```

## Dependencies

### Required
- **Claude API** - Anthropic API for AI optimization
- **spec-verifier** (port 8205) - SPEC validation and scoring
- **Registry** (port 8000) - Service registration and discovery

### Optional
- **spec-builder** (future) - For generating initial specs

## Auto-Registration

Service auto-registers with Registry on startup:
```python
@app.on_event("startup")
async def register_with_registry():
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8000/register",
            json={
                "name": "spec-optimizer",
                "id": 8,
                "url": "http://localhost:8206",
                "version": "1.0.0",
                "metadata": {
                    "tier": 0,
                    "category": "quality_assurance",
                    "purpose": "AI-powered SPEC optimization"
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
- **Cost Tracking**: Built-in token/cost estimation

## File Structure

```
spec-optimizer/
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
    │   └── optimization_models.py
    └── services/
        ├── __init__.py
        ├── claude_client.py
        ├── optimization_engine.py
        └── verification_client.py
```

## Optimization Opportunities

1. **Parallel Optimization**: Process multiple specs simultaneously
2. **Caching**: Cache reference spec patterns to reduce API calls
3. **Streaming**: Stream optimization progress via WebSocket
4. **Learning**: Track successful patterns and apply automatically
5. **Templates**: Pre-built optimization templates for common service types
6. **Diff View**: Show visual diff of changes made
7. **Rollback**: Keep version history for rollback
8. **Auto-Tuning**: Adjust optimization level based on initial score

## Example Usage

### Optimize a SPEC file
```bash
curl -X POST http://localhost:8206/optimize-file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/Users/jamessunheart/Development/SERVICES/jobs/SPEC.md",
    "optimization_level": "standard",
    "save_backup": true
  }'
```

### Batch optimize all TIER 1 specs
```bash
curl -X POST http://localhost:8206/batch-optimize \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": [
      "/Users/jamessunheart/Development/SERVICES/autonomous-executor/SPEC.md",
      "/Users/jamessunheart/Development/SERVICES/jobs/SPEC.md"
    ],
    "optimization_level": "aggressive"
  }'
```

## Success Criteria

- ✅ All 5 UDC endpoints implemented and tested
- ✅ Optimizes specs with 20+ point score improvement average
- ✅ Preserves original intent (no content removal)
- ✅ Integrates with spec-verifier for before/after validation
- ✅ Auto-registers with Registry
- ✅ Processes optimization in <30 seconds
- ✅ Claude API costs <$0.10 per spec
- ✅ Zero false improvements (score never decreases)

## Cost Analysis

**Per SPEC Optimization:**
- Input tokens: ~2,000 (SPEC + context)
- Output tokens: ~3,000 (optimized SPEC)
- Cost per optimization: ~$0.02-0.08 (depending on level)

**Monthly Estimate (100 specs):**
- Basic: $1-2
- Standard: $2-4
- Aggressive: $4-8

**ROI:**
- Time saved per spec: 30-60 minutes (manual optimization)
- Human cost avoided: $25-50 per spec
- ROI: 500-2500x

---

**Build Priority:** TIER 0 - Critical quality enhancement for all future builds
**Build Method:** Sacred Loop via autonomous-executor
**Estimated Build Time:** 1-2 hours
