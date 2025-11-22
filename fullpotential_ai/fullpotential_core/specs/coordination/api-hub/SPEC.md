# api-hub - SPECS

**Created:** 2025-11-15
**Status:** Operational

---

## Purpose

Self-expanding capability system that autonomously discovers, evaluates, acquires, and manages API access for needed capabilities. Enables the system to expand its own capabilities without manual API signup and integration work.

---

## Requirements

### Functional Requirements
- [ ] Maintain database of free/cheap APIs for all needed capabilities
- [ ] Evaluate APIs by free tier, ease of signup, quality, and pricing
- [ ] Recommend best API option for each capability
- [ ] Store API keys securely in encrypted vault
- [ ] Track which capabilities the system has vs needs
- [ ] Identify missing capabilities automatically
- [ ] Create acquisition tasks (automated or delegated to VAs)
- [ ] Generate signup instructions for human helpers
- [ ] Auto-signup for simple free-tier APIs (email only, no CC)
- [ ] Integrate with helper-management for complex signups
- [ ] API key retrieval for services that need capabilities
- [ ] Support for image generation, video generation, voice, music APIs

### Non-Functional Requirements
- [ ] Performance: API key retrieval < 100ms
- [ ] Security: AES-256 encryption for API keys in vault, encrypted at rest
- [ ] Availability: Core API database accessible even if external APIs are down
- [ ] Scalability: Support 100+ API integrations

---

## API Specs

### Endpoints

**GET /capabilities**
- **Purpose:** List all known capabilities and their status
- **Input:** None
- **Output:** JSON array of capabilities with status (available/missing/pending)
- **Success:** 200 OK with capabilities list
- **Errors:** 500 if database fails

**GET /capabilities/{capability_name}**
- **Purpose:** Get details about a specific capability
- **Input:** capability_name (e.g., "image_generation")
- **Output:** Capability details including recommended APIs, current status
- **Success:** 200 OK
- **Errors:** 404 if capability not found

**POST /capabilities/{capability_name}/acquire**
- **Purpose:** Trigger acquisition of a capability
- **Input:** capability_name, acquisition_method ("auto" or "delegate")
- **Output:** Task ID for acquisition process
- **Success:** 202 Accepted with task_id
- **Errors:** 400 if invalid method, 409 if already being acquired

**GET /apis**
- **Purpose:** List all known APIs in database
- **Input:** Optional query params (type, free_tier_available, etc.)
- **Output:** JSON array of API information
- **Success:** 200 OK
- **Errors:** 500 if database fails

**POST /apis**
- **Purpose:** Add new API to database
- **Input:** API details (name, type, free_tier, pricing, signup_url, etc.)
- **Output:** Created API entry
- **Success:** 201 Created
- **Errors:** 400 if validation fails

**GET /vault/keys**
- **Purpose:** List all stored API keys (names only, not values)
- **Input:** None
- **Output:** Array of API key metadata
- **Success:** 200 OK
- **Errors:** 500 if vault access fails

**GET /vault/keys/{key_name}**
- **Purpose:** Retrieve decrypted API key value
- **Input:** key_name
- **Output:** Decrypted API key value
- **Success:** 200 OK
- **Errors:** 404 if key not found, 500 if decryption fails

**POST /vault/keys**
- **Purpose:** Store new API key in vault
- **Input:** key_name, key_value, service_name, metadata
- **Output:** Confirmation of storage
- **Success:** 201 Created
- **Errors:** 400 if validation fails, 409 if key already exists

**DELETE /vault/keys/{key_name}**
- **Purpose:** Remove API key from vault
- **Input:** key_name
- **Output:** Confirmation of deletion
- **Success:** 200 OK
- **Errors:** 404 if key not found

**GET /health**
- **Purpose:** Health check
- **Input:** None
- **Output:** {"status": "healthy", "service": "api-hub"}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

### Data Models

```python
class API:
    name: str
    service: str
    capability: str  # "image_generation", "video_generation", etc.
    free_tier_available: bool
    free_tier_limits: str
    pricing: str
    signup_complexity: str  # "simple", "moderate", "complex"
    signup_url: str
    requires_credit_card: bool
    api_key_format: str
    quality_score: float  # 0-1
    metadata: dict

class Capability:
    name: str
    description: str
    status: str  # "available", "missing", "pending_acquisition"
    recommended_api: Optional[str]
    current_api: Optional[str]
    use_cases: List[str]

class APIKey:
    id: str
    key_name: str
    service: str
    capability: str
    encrypted_value: str  # AES-256 encrypted
    created_at: datetime
    last_used: Optional[datetime]
    metadata: dict

class AcquisitionTask:
    task_id: str
    capability: str
    api_name: str
    method: str  # "auto" or "delegate"
    status: str  # "pending", "in_progress", "completed", "failed"
    created_at: datetime
    completed_at: Optional[datetime]
    result: Optional[dict]
```

---

## Dependencies

### External Services
- Stripe: Already integrated (payment processing)
- Stable Diffusion API: Target for image generation
- D-ID: Target for video generation
- ElevenLabs: Target for voice generation
- Soundraw: Target for music generation

### APIs Required
- None initially (self-contained)
- Future: Integration with helper-management API for delegated signups

### Data Sources
- api_database.json: Local database of known APIs
- api_vault.json: Encrypted storage of API keys

---

## Success Criteria

How do we know this service works?

- [ ] API database contains 10+ APIs across 4+ capabilities
- [ ] Can recommend best API for each capability
- [ ] API keys stored securely (encrypted at rest)
- [ ] API key retrieval works for services
- [ ] Auto-signup successfully acquires at least 1 API key
- [ ] Delegation to helper-management creates valid tasks
- [ ] All endpoints return correct status codes
- [ ] Encryption/decryption works correctly
- [ ] Health check returns 200 OK

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8100 (or next available)
- **Resource limits:**
  - Memory: 256MB max
  - CPU: 0.5 cores
  - Storage: 100MB for database and vault
- **Response time:** < 100ms for key retrieval, < 1s for discovery
- **Security:** AES-256 encryption for API keys, HTTPS required in production
- **Environment:** Docker container deployment

---

## Security Notes

### API Key Protection
- All API keys encrypted at rest using AES-256
- Master encryption key stored in environment variable (never in code)
- Keys never logged or exposed in error messages
- Encrypted vault backed up separately from database

### Access Control
- Future: Token-based authentication for API access
- Currently: Trust-based (internal service only)

---

## Integration Notes

### With Other Services
Services request API keys from api-hub when needed:

```python
import httpx

# Service needs image generation API
response = httpx.get("http://api-hub:8100/vault/keys/stable_diffusion")
api_key = response.json()["value"]

# Use API key for image generation
image = generate_image(api_key, prompt="professional ad")
```

### With Helper Management
For complex API signups:

```python
# api-hub creates task for helper-management
response = httpx.post("http://helper-management:8026/tasks", json={
    "title": "Sign up for D-ID video API",
    "description": "Create account, get API key, test it",
    "credential_ids": [billing_card_id],
    "budget": 25.0
})
```

---

**Next Step:** Service is operational, expand API database and test auto-acquisition
