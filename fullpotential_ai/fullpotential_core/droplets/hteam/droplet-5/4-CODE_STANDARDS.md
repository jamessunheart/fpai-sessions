# CODE_STANDARDS.md
**Full Potential AI - Coding Standards**
**Version:** 1.0
**Last Updated:** November 2025

---

## 🎯 CORE PRINCIPLES

1. **Clarity over cleverness** - Code is read 10x more than written
2. **Explicit over implicit** - No magic, no surprises
3. **Simple over complex** - Solve simply first, optimize later
4. **Tested over perfect** - Working beats elegant
5. **Documented over obvious** - Future you needs context

---

## 📁 FILE STRUCTURE

### Backend (Python/FastAPI)

```
/droplet-name/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app initialization
│   ├── config.py               # Configuration management
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py       # UDC health endpoints
│   │       ├── message.py      # UDC messaging
│   │       └── custom.py       # Your specific endpoints
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── udc.py             # UDC standard models
│   │   └── domain.py          # Your domain models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── registry.py        # Registry communication
│   │   ├── orchestrator.py    # Orchestrator communication
│   │   └── business_logic.py  # Your core logic
│   │
│   └── utils/
│       ├── __init__.py
│       ├── auth.py            # JWT verification
│       ├── logging.py         # Structured logging
│       └── helpers.py         # Utility functions
│
├── tests/
│   ├── __init__.py
│   ├── test_health.py
│   ├── test_message.py
│   └── test_business_logic.py
│
├── .env.example               # Template for environment vars
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── udc_config.json           # UDC configuration
└── README.md
```

### Frontend (Next.js/TypeScript)

```
/app/
├── components/
│   ├── ui/                   # Reusable UI components
│   │   ├── Button.tsx
│   │   └── Card.tsx
│   └── features/             # Feature-specific components
│       └── DropletMonitor.tsx
│
├── lib/
│   ├── api.ts               # API client
│   ├── auth.ts              # Authentication
│   └── utils.ts             # Utilities
│
├── types/
│   └── index.ts             # TypeScript types
│
├── app/
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Home page
│   └── dashboard/
│       └── page.tsx         # Dashboard page
│
└── public/                  # Static assets
```

---

## 🐍 PYTHON STANDARDS

### Naming Conventions

```python
# Files: snake_case
# Good
health_checker.py
message_router.py

# Bad
healthChecker.py
MessageRouter.py

# Classes: PascalCase
class DropletStatus:
    pass

class MessageHandler:
    pass

# Functions/Variables: snake_case
def get_droplet_info():
    pass

user_count = 42
is_active = True

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
API_TIMEOUT = 30
REGISTRY_URL = "https://registry.fullpotential.ai"

# Private members: prefix with _
class MyClass:
    def __init__(self):
        self._private_var = "internal"
    
    def _private_method(self):
        pass
```

### Type Hints (Required)

```python
# Good - Clear types
async def get_droplet(droplet_id: int) -> dict[str, Any]:
    """Fetch droplet information from Registry"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{REGISTRY_URL}/droplet/{droplet_id}")
        return response.json()

# Good - Pydantic models for complex types
from pydantic import BaseModel

class DropletInfo(BaseModel):
    id: int
    name: str
    status: Literal["active", "inactive", "error"]
    endpoint: str

async def get_droplet(droplet_id: int) -> DropletInfo:
    # Returns validated DropletInfo object
    pass

# Bad - No type hints
async def get_droplet(droplet_id):
    # What type is droplet_id? What does this return?
    pass
```

### Async/Await (Always)

```python
# Good - Async I/O operations
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# Good - Async database operations
async def get_user(user_id: int):
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )

# Bad - Synchronous blocking calls
def fetch_data():
    response = requests.get(url)  # Blocks event loop!
    return response.json()
```

### Error Handling

```python
# Good - Specific exceptions with context
from fastapi import HTTPException

async def get_droplet(droplet_id: int) -> DropletInfo:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{REGISTRY_URL}/droplet/{droplet_id}")
            response.raise_for_status()
            return DropletInfo(**response.json())
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Registry timeout when fetching droplet {droplet_id}"
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Droplet {droplet_id} not found"
            )
        raise HTTPException(
            status_code=502,
            detail=f"Registry error: {e}"
        )
    except Exception as e:
        log.error("unexpected_error", droplet_id=droplet_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

# Bad - Generic catch-all
async def get_droplet(droplet_id: int):
    try:
        # ... code ...
    except Exception as e:
        print(f"Error: {e}")  # What error? Where? Why?
        return None  # Silent failure
```

### Documentation

```python
# Good - Clear docstrings
async def register_droplet(
    droplet_id: int,
    name: str,
    endpoint: str
) -> dict[str, Any]:
    """
    Register this droplet with the Registry.
    
    Args:
        droplet_id: Unique identifier assigned by Registry steward
        name: Human-readable droplet name (e.g., "Visibility Deck")
        endpoint: Public URL where this droplet is accessible
        
    Returns:
        Registration confirmation with JWT token
        
    Raises:
        HTTPException: If registration fails or Registry is unreachable
        
    Example:
        >>> result = await register_droplet(14, "Visibility", "https://vis.fp.ai")
        >>> print(result["token"])
    """
    # Implementation...

# Good - Inline comments for complex logic
# Calculate exponential backoff: 2^attempt seconds
wait_time = 2 ** attempt
await asyncio.sleep(wait_time)

# Bad - No documentation
async def register_droplet(droplet_id, name, endpoint):
    # What does this do? What are the types?
    pass

# Bad - Obvious comments
# Increment counter
counter = counter + 1  # This is obvious from the code
```

---

## 📝 TYPESCRIPT STANDARDS

### Naming Conventions

```typescript
// Files: PascalCase for components, camelCase for utilities
DropletMonitor.tsx
Button.tsx
api.ts
utils.ts

// Interfaces/Types: PascalCase
interface DropletInfo {
  id: number;
  name: string;
  status: "active" | "inactive" | "error";
}

type MessageHandler = (message: Message) => void;

// Functions/Variables: camelCase
function getDropletInfo(id: number): Promise<DropletInfo> { }

const isActive = true;
const userCount = 42;

// Constants: UPPER_SNAKE_CASE
const MAX_RETRIES = 3;
const API_TIMEOUT = 30;
```

### Type Safety (Strict)

```typescript
// Good - Explicit types
interface DropletInfo {
  id: number;
  name: string;
  status: "active" | "inactive" | "error";
  endpoint: string;
  updated_at: string;
}

async function getDroplet(id: number): Promise<DropletInfo> {
  const response = await fetch(`/api/droplets/${id}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch droplet: ${response.status}`);
  }
  return response.json();
}

// Good - Union types for precise values
type DropletStatus = "active" | "inactive" | "error";

function setStatus(status: DropletStatus) {
  // TypeScript ensures only valid values
}

// Bad - Any types (avoid)
function getDroplet(id: any): any {
  // Loses all type safety
}
```

### React Components

```typescript
// Good - Functional components with TypeScript
interface DropletCardProps {
  droplet: DropletInfo;
  onStatusChange: (id: number, status: DropletStatus) => void;
}

export function DropletCard({ droplet, onStatusChange }: DropletCardProps) {
  const [isLoading, setIsLoading] = useState(false);
  
  const handleClick = async () => {
    setIsLoading(true);
    try {
      await onStatusChange(droplet.id, "inactive");
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="p-4 border rounded">
      <h3>{droplet.name}</h3>
      <p>Status: {droplet.status}</p>
      <button onClick={handleClick} disabled={isLoading}>
        {isLoading ? "Loading..." : "Toggle Status"}
      </button>
    </div>
  );
}

// Bad - Untyped props
export function DropletCard({ droplet, onStatusChange }) {
  // No type checking
}
```

---

## 🧪 TESTING STANDARDS

### Test Organization

```python
# tests/test_health.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    """Health endpoint should return 200 OK"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_health_endpoint_includes_status():
    """Health endpoint should include status field"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ["active", "inactive", "error"]

@pytest.mark.asyncio
async def test_health_endpoint_includes_droplet_info():
    """Health endpoint should include droplet identification"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "steward" in data
        assert data["id"] == DROPLET_ID
```

### Test Naming

```python
# Good - Descriptive test names
def test_invalid_jwt_returns_401():
    pass

def test_missing_trace_id_returns_400():
    pass

def test_successful_message_returns_acknowledged():
    pass

# Bad - Vague test names
def test_endpoint():
    pass

def test_error():
    pass
```

---

## 📊 LOGGING STANDARDS

### Structured Logging

```python
import structlog

log = structlog.get_logger()

# Good - Structured logs with context
log.info(
    "droplet_registered",
    droplet_id=14,
    droplet_name="Visibility Deck",
    registry_url=REGISTRY_URL,
    duration_ms=234
)

log.error(
    "registration_failed",
    droplet_id=14,
    error=str(e),
    retry_attempt=attempt,
    max_retries=MAX_RETRIES
)

# Include trace_id in all request logs
log.info(
    "message_received",
    trace_id=message.trace_id,
    source=message.source,
    target=message.target,
    message_type=message.message_type
)

# Bad - Unstructured logs
print("Registered droplet 14")
print(f"Error: {e}")
```

### Log Levels

```python
# DEBUG - Development/troubleshooting only
log.debug("processing_step", step="validate_input", data=input_data)

# INFO - Normal operations
log.info("request_completed", endpoint="/health", duration_ms=23)

# WARNING - Recoverable issues
log.warning("retry_attempt", attempt=2, max_retries=3)

# ERROR - Errors requiring attention
log.error("dependency_unavailable", dependency="registry", error=str(e))

# CRITICAL - System-threatening issues
log.critical("startup_failed", error=str(e))
```

---

## 🚫 ANTI-PATTERNS (NEVER DO THIS)

### 1. Print Debugging in Production

```python
# BAD
print("Debug: user_id =", user_id)
print(f"Response: {response}")

# GOOD
log.debug("request_data", user_id=user_id, response=response)
```

### 2. Hardcoded Credentials

```python
# BAD
DATABASE_URL = "postgresql://user:password123@localhost/db"
API_KEY = "sk-1234567890abcdef"

# GOOD
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    api_key: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 3. Silent Failures

```python
# BAD
try:
    result = await dangerous_operation()
except Exception:
    pass  # What happened? Why did it fail?

# GOOD
try:
    result = await dangerous_operation()
except Exception as e:
    log.error("operation_failed", operation="dangerous_operation", error=str(e))
    raise  # Or handle appropriately
```

### 4. Synchronous I/O in Async Functions

```python
# BAD
async def fetch_data():
    response = requests.get(url)  # Blocks!
    return response.json()

# GOOD
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### 5. Missing Input Validation

```python
# BAD
@app.post("/message")
async def receive_message(data: dict):
    # What if trace_id is missing? What if source is wrong type?
    process_message(data)

# GOOD
from pydantic import BaseModel

class UDCMessage(BaseModel):
    trace_id: str
    source: int
    target: int
    message_type: str
    payload: dict

@app.post("/message")
async def receive_message(message: UDCMessage):
    # Pydantic validates all fields automatically
    process_message(message)
```

### 6. TODO/FIXME in Production

```python
# BAD
def process_payment():
    # TODO: Add error handling
    # FIXME: This breaks with negative amounts
    charge_card(amount)

# GOOD
# Either fix it before deploying, or create a proper issue and handle gracefully
def process_payment():
    if amount < 0:
        raise ValueError("Amount must be positive")
    try:
        charge_card(amount)
    except PaymentError as e:
        log.error("payment_failed", amount=amount, error=str(e))
        raise
```

---

## ✅ CODE REVIEW CHECKLIST

**Before submitting code:**

### Functionality
- [ ] All requirements from spec implemented
- [ ] Edge cases handled
- [ ] Error handling in place
- [ ] Input validation working

### Quality
- [ ] Type hints on all functions (Python) or strict types (TS)
- [ ] Complex logic has comments
- [ ] No print() or console.log() debugging statements
- [ ] Consistent formatting (black/prettier)

### Testing
- [ ] Tests written for new functionality
- [ ] All tests passing
- [ ] Coverage >80% for critical paths

### Security
- [ ] No hardcoded secrets
- [ ] Input sanitization present
- [ ] Authentication implemented
- [ ] SQL injection prevention (if applicable)

### UDC Compliance (if applicable)
- [ ] All required endpoints implemented
- [ ] Standard response format followed
- [ ] JWT authentication working
- [ ] Status uses exact enum values

### Documentation
- [ ] README updated if needed
- [ ] Docstrings on public functions
- [ ] .env.example updated with new vars
- [ ] No TODO/FIXME in production code

---

## 🎨 FORMATTING

### Python
```bash
# Use black for formatting
black app/ tests/

# Use ruff for linting
ruff check app/ tests/

# Use mypy for type checking
mypy app/
```

### TypeScript
```bash
# Use prettier for formatting
prettier --write "**/*.{ts,tsx}"

# Use eslint for linting
eslint "**/*.{ts,tsx}"
```

---

**END CODE_STANDARDS.md**
