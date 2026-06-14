# Brain Droplet - SPECS

**Droplet ID:** #104
**Version:** 1.0.0
**Status:** Planning

---

## Purpose

Handle AI/LLM integration for natural language processing, reasoning, and tool execution. Uses Claude as the primary AI model with fallback to other providers.

---

## Requirements

### Functional Requirements
- [ ] Process natural language queries
- [ ] Execute tools based on user intent
- [ ] Maintain conversation context
- [ ] Handle multi-turn conversations
- [ ] Provide reasoning transparency
- [ ] Fall back to alternative models on failure

### Non-Functional Requirements
- [ ] Must respond within 30 seconds
- [ ] Must handle API rate limits
- [ ] Must gracefully degrade if AI unavailable
- [ ] Must track API usage and costs

---

## API Specs

### UDC Endpoints (Required)

```
GET /health
Response: {"status": "healthy", "timestamp": "...", "uptime_seconds": N, "version": "1.0.0"}

GET /capabilities
Response: {"service_name": "brain", "droplet_id": 104, "capabilities": [...]}

GET /state
Response: {"status": "active", "model": "claude-sonnet-4-20250514", "requests_today": N}

GET /dependencies
Response: {"required_services": [...], "optional_services": [...]}

POST /message
Request: {"from_service": "router", "message_type": "query", "payload": {"text": "hello", "user_id": "123"}}
Response: {"received": true, "status": "completed", "result": {"response": "Hello! How can I help?"}}
```

### Business Endpoints

```
POST /chat
Request: {"message": "...", "user_id": "...", "context": [...]}
Response: {"response": "...", "model_used": "...", "tokens_used": N}

POST /tools/execute
Request: {"tool": "run_command", "params": {...}}
Response: {"result": "...", "success": true}

GET /tools
Response: List of available tools

GET /usage
Response: API usage statistics
```

---

## Dependencies

### Required Services
- Claude API (Anthropic) - Primary AI model

### Optional Services
- OpenAI API - Fallback model
- Gemini API - Secondary fallback
- memory (for conversation context)

---

## Available Tools

```python
TOOLS = [
    {
        "name": "run_command",
        "description": "Execute a shell command on the server",
        "parameters": {"command": "string"}
    },
    {
        "name": "search_web",
        "description": "Search the web for information",
        "parameters": {"query": "string"}
    },
    {
        "name": "read_file",
        "description": "Read contents of a file",
        "parameters": {"path": "string"}
    },
    {
        "name": "get_trading_status",
        "description": "Get current trading positions and P&L",
        "parameters": {}
    }
]
```

---

## Model Fallback Chain

```
1. claude-sonnet-4-20250514 (primary)
   ↓ on failure
2. gpt-4o (fallback)
   ↓ on failure
3. gemini-1.5-pro (secondary fallback)
   ↓ on failure
4. Return error message
```

---

## Success Criteria

- [ ] Can process natural language queries
- [ ] Can execute tools when requested
- [ ] Falls back to alternative models on failure
- [ ] Tracks API usage
- [ ] Passes all UDC compliance tests
- [ ] Has >80% test coverage

---

## Configuration

```bash
# Environment Variables
BRAIN_PORT=8752
ANTHROPIC_API_KEY=<key>
OPENAI_API_KEY=<key>
GEMINI_API_KEY=<key>
DEFAULT_MODEL=claude-sonnet-4-20250514
MAX_TOKENS=4096
TEMPERATURE=0.7
REQUEST_TIMEOUT_SECONDS=30
```

---

## Compliance Notes

- Processes user messages (contains PII)
- Must not log full message content
- Must track API costs for billing
- Must handle sensitive tool operations securely








