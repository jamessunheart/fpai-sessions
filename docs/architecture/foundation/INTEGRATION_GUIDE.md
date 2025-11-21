# 🔗 INTEGRATION GUIDE - How Droplets Connect to the System

**Version:** 1.0
**Last Updated:** 2025-11-15
**Purpose:** Standard integration patterns for all Full Potential AI droplets

---

## 1. INTEGRATION OVERVIEW

Every droplet in the Full Potential AI ecosystem follows a standard integration pattern:

```
┌──────────────┐
│   Registry   │  ← Central identity & discovery
└──────┬───────┘
       │
       ├─────→ Issues JWT tokens
       ├─────→ Tracks service health
       └─────→ Provides service directory
           │
    ┌──────┴──────┐
    │             │
┌───▼────┐   ┌───▼────────┐
│Service │   │Orchestrator│  ← Task routing & messaging
└────────┘   └─────┬──────┘
                   │
                   ├─────→ Routes tasks
                   ├─────→ Collects heartbeats
                   └─────→ Coordinates work

```

**Every droplet must:**
1. Register with Registry on startup
2. Send heartbeats to Orchestrator
3. Implement UDC endpoints
4. Use JWT for authentication
5. Handle messages via /message endpoint

---

## 2. STARTUP SEQUENCE

### 2.1 Standard Startup Flow

```python
from fastapi import FastAPI
import httpx
import asyncio

app = FastAPI()

# Global state
jwt_token: str = None
service_id: int = None

@app.on_event("startup")
async def startup():
    global jwt_token, service_id

    # Step 1: Register with Registry
    jwt_token, service_id = await register_with_registry()

    # Step 2: Start heartbeat task
    asyncio.create_task(heartbeat_loop())

    # Step 3: Ready to serve requests
    logger.info(f"Service started: ID={service_id}")

async def register_with_registry():
    """Register this service with Registry and get JWT token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://registry:8000/register",
            json={
                "name": "my-service",
                "droplet_id": 10,
                "port": 8010,
                "health_endpoint": "/health",
                "capabilities": ["task_processing"],
                "version": "1.0.0",
                "udc_compliant": True
            },
            timeout=10.0
        )

        if response.status_code != 201:
            raise RuntimeError(f"Registration failed: {response.text}")

        data = response.json()
        return data["token"], data["service_id"]

async def heartbeat_loop():
    """Send heartbeat every 60 seconds."""
    while True:
        try:
            await send_heartbeat()
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            await asyncio.sleep(60)  # Continue trying

async def send_heartbeat():
    """Send heartbeat to Orchestrator."""
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://orchestrator:8001/heartbeat",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={
                "service_id": service_id,
                "status": "active",
                "metrics": {
                    "requests_per_minute": get_current_rpm(),
                    "error_rate": get_error_rate()
                }
            },
            timeout=5.0
        )
```

---

## 3. SERVICE DISCOVERY

### 3.1 Finding Other Services

```python
async def get_service_endpoint(service_name: str) -> str:
    """Get endpoint for a service from Registry."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://registry:8000/services/by-name/{service_name}",
            headers={"Authorization": f"Bearer {jwt_token}"},
            timeout=5.0
        )

        if response.status_code == 404:
            raise ValueError(f"Service {service_name} not found")

        data = response.json()
        return f"http://{data['host']}:{data['port']}"

# Usage
async def call_other_service():
    verifier_url = await get_service_endpoint("verifier")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{verifier_url}/verify",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={"code": "def hello(): pass"}
        )
    return response.json()
```

---

## 4. AUTHENTICATION PATTERNS

### 4.1 Get Public Key from Registry

```python
from jose import jwt
from functools import lru_cache
import httpx

@lru_cache(maxsize=1)
def get_registry_public_key() -> str:
    """Get Registry's public key (cached)."""
    response = httpx.get("http://registry:8000/auth/public-key", timeout=5.0)
    return response.json()["public_key"]

def verify_jwt_token(token: str) -> dict:
    """Verify JWT token from another service."""
    try:
        public_key = get_registry_public_key()
        payload = jwt.decode(token, public_key, algorithms=["RS256"])

        # Verify expiration
        if payload["exp"] < time.time():
            raise ValueError("Token expired")

        return payload
    except Exception as e:
        raise ValueError(f"Invalid token: {e}")
```

### 4.2 FastAPI Dependency

```python
from fastapi import Depends, HTTPException, Header

def get_current_service(authorization: str = Header(None)) -> dict:
    """FastAPI dependency to verify JWT and extract service info."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")

        payload = verify_jwt_token(token)
        return payload

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

# Use in endpoints
@app.get("/protected")
def protected_endpoint(service: dict = Depends(get_current_service)):
    return {"message": f"Hello service {service['service_name']}"}
```

---

## 5. INTER-SERVICE COMMUNICATION

### 5.1 Synchronous Request/Response

```python
async def call_verifier(code: str) -> dict:
    """Call Verifier service synchronously."""
    verifier_url = await get_service_endpoint("verifier")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{verifier_url}/verify",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={
                "code": code,
                "language": "python"
            },
            timeout=30.0
        )

        if response.status_code != 200:
            raise RuntimeError(f"Verifier failed: {response.text}")

        return response.json()
```

### 5.2 Asynchronous Messaging

```python
async def send_message_to_service(
    target_service: str,
    message_type: str,
    payload: dict
) -> dict:
    """Send async message to another service via /message endpoint."""
    service_url = await get_service_endpoint(target_service)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{service_url}/message",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={
                "from_service": "my-service",
                "message_type": message_type,
                "payload": payload,
                "reply_to": "http://my-service:8010/callback"
            },
            timeout=10.0
        )

        return response.json()

# Implement callback endpoint
@app.post("/callback")
async def handle_callback(message: dict, service: dict = Depends(get_current_service)):
    """Receive async response from another service."""
    logger.info(f"Received callback: {message}")
    # Process response
    return {"received": True}
```

### 5.3 Through Orchestrator (Recommended)

```python
async def route_task_through_orchestrator(
    task_type: str,
    task_data: dict
) -> str:
    """Send task to Orchestrator for routing."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://orchestrator:8001/tasks",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={
                "task_type": task_type,
                "data": task_data,
                "priority": "normal"
            }
        )

        task_id = response.json()["task_id"]
        return task_id

# Poll for result
async def get_task_result(task_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://orchestrator:8001/tasks/{task_id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        return response.json()
```

---

## 6. DATABASE INTEGRATION

### 6.1 Connection Management

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# Create engine (do this once at startup)
engine = create_engine(
    os.getenv("DATABASE_URL"),
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,  # Verify connections
    echo=False  # Set to True for SQL logging
)

SessionLocal = sessionmaker(bind=engine)

# FastAPI dependency
def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Use in endpoints
@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### 6.2 Migrations with Alembic

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add users table"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 7. CACHING PATTERNS

### 7.1 Redis Integration

```python
import redis
from functools import wraps

# Connect to Redis
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

def cached(ttl: int = 300):
    """Decorator to cache function results in Redis."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            cached_value = redis_client.get(cache_key)
            if cached_value:
                return json.loads(cached_value)

            # Call function
            result = await func(*args, **kwargs)

            # Store in cache
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result)
            )

            return result
        return wrapper
    return decorator

# Usage
@cached(ttl=300)
async def get_expensive_data(user_id: int):
    # This will be cached for 5 minutes
    return await fetch_from_database(user_id)
```

---

## 8. CONFIGURATION MANAGEMENT

### 8.1 Environment-Specific Config

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Service identity
    service_name: str = "my-service"
    service_port: int = 8010
    droplet_id: int = 10

    # Registry & Orchestrator
    registry_url: str = "http://registry:8000"
    orchestrator_url: str = "http://orchestrator:8001"

    # Database
    database_url: str

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # External APIs
    anthropic_api_key: str | None = None

    # Environment
    environment: str = "production"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Get settings (cached)."""
    return Settings()

# Usage
settings = get_settings()
```

---

## 9. ERROR HANDLING PATTERNS

### 9.1 Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def call_external_api():
    """Retry up to 3 times with exponential backoff."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        response.raise_for_status()
        return response.json()
```

### 9.2 Circuit Breaker

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_flaky_service():
    """Circuit breaker: fail fast after 5 failures."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://flaky-service:8000/api")
        return response.json()
```

---

## 10. MONITORING & OBSERVABILITY

### 10.1 Metrics Collection

```python
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Middleware to collect metrics
@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response

# Metrics endpoint
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## 11. HEALTH CHECK IMPLEMENTATION

### 11.1 Comprehensive Health Check

```python
@app.get("/health")
async def health():
    """UDC-compliant health check."""
    # Check database
    db_healthy = await check_database()

    # Check Redis
    redis_healthy = await check_redis()

    # Check external dependencies
    external_healthy = await check_external_apis()

    # Determine overall status
    if db_healthy and redis_healthy and external_healthy:
        status = "healthy"
    elif db_healthy:  # Critical dependency OK
        status = "degraded"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": int(time.time() - startup_time),
        "version": "1.0.0",
        "checks": {
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
            "external_apis": "healthy" if external_healthy else "unhealthy"
        }
    }

async def check_database() -> bool:
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception:
        return False

async def check_redis() -> bool:
    try:
        redis_client.ping()
        return True
    except Exception:
        return False
```

---

## 12. INTEGRATION CHECKLIST

Before deploying a new droplet:

**Registry Integration:**
- [ ] Register on startup
- [ ] Store JWT token
- [ ] Use JWT for all service calls
- [ ] Handle registration failures gracefully

**Orchestrator Integration:**
- [ ] Send heartbeat every 60s
- [ ] Include current metrics
- [ ] Handle heartbeat failures
- [ ] Implement /message endpoint

**UDC Compliance:**
- [ ] Implement all 5 UDC endpoints
- [ ] Return correct JSON formats
- [ ] Include proper status values

**Authentication:**
- [ ] Verify JWT on protected endpoints
- [ ] Get public key from Registry
- [ ] Cache public key
- [ ] Handle token expiration

**Service Discovery:**
- [ ] Look up services via Registry
- [ ] Cache service endpoints
- [ ] Handle service unavailable

**Error Handling:**
- [ ] Retry transient failures
- [ ] Log all integration errors
- [ ] Fail gracefully when dependencies down

---

## 13. TESTING INTEGRATION

### 13.1 Mock Registry in Tests

```python
import pytest
from unittest.mock import patch, AsyncMock

@pytest.fixture
def mock_registry():
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=201,
            json=lambda: {"token": "test_token", "service_id": 999}
        )
        yield mock_post

def test_registration(mock_registry):
    # Test that service registers correctly
    token, service_id = await register_with_registry()
    assert token == "test_token"
    assert service_id == 999
```

---

**All droplets integrate the same way. Follow this guide.**

🔗⚡💎
