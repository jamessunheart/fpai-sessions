# Developer Acceleration Kit

**AI-assisted rapid development patterns for Claude Code sessions**

---

## Overview

This guide helps Claude Code sessions build services faster by leveraging:
- Code generation patterns
- Rapid prototyping techniques
- Testing automation
- Deployment acceleration

**Goal:** Build production-quality services in hours, not days

---

## Rapid Service Bootstrap

### Quick Start Template
```bash
# 1. Create service from template (2 minutes)
cp -r SERVICES/_TEMPLATE SERVICES/my-service
cd SERVICES/my-service

# 2. Customize SPECS (5 minutes)
nano SPECS.md  # Define what you're building

# 3. Generate boilerplate (1 minute)
python3 << 'EOF'
# Auto-generate FastAPI boilerplate from SPECS
service_name = "my-service"
port = 8500

template = f"""
from fastapi import FastAPI
from datetime import datetime
import time

app = FastAPI(title="{service_name}", version="1.0.0")

@app.get("/health")
async def health():
    return {{"status": "active", "service": "{service_name}"}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port={port})
"""

with open("BUILD/src/main.py", "w") as f:
    f.write(template)
EOF

# 4. Run immediately
cd BUILD && python3 src/main.py
```

**Result:** Working service in <10 minutes

---

## Code Generation Patterns

### Pattern 1: CRUD API from Model
```python
# Define your model
from pydantic import BaseModel

class Resource(BaseModel):
    id: int
    name: str
    value: float

# Auto-generate CRUD endpoints
def generate_crud(model_class):
    """Generate CRUD endpoints for a Pydantic model."""

    @app.post(f"/api/{model_class.__name__.lower()}")
    async def create(item: model_class):
        # Store in database
        return {"id": 1, "status": "created"}

    @app.get(f"/api/{model_class.__name__.lower()}/{{id}}")
    async def read(id: int):
        # Fetch from database
        return model_class(id=id, name="Example", value=100.0)

    @app.put(f"/api/{model_class.__name__.lower()}/{{id}}")
    async def update(id: int, item: model_class):
        # Update in database
        return {"status": "updated"}

    @app.delete(f"/api/{model_class.__name__.lower()}/{{id}}")
    async def delete(id: int):
        # Delete from database
        return {"status": "deleted"}

generate_crud(Resource)
```

### Pattern 2: Test Generation
```python
# Auto-generate tests for CRUD endpoints
def generate_tests(model_name: str):
    """Generate pytest tests for CRUD operations."""

    template = f'''
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_create_{model_name}():
    response = client.post("/api/{model_name}", json={{"name": "test", "value": 100}})
    assert response.status_code == 200
    assert "id" in response.json()

def test_read_{model_name}():
    response = client.get("/api/{model_name}/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_update_{model_name}():
    response = client.put("/api/{model_name}/1", json={{"name": "updated", "value": 200}})
    assert response.status_code == 200

def test_delete_{model_name}():
    response = client.delete("/api/{model_name}/1")
    assert response.status_code == 200
'''

    with open(f"tests/test_{model_name}.py", "w") as f:
        f.write(template)

generate_tests("resource")
```

### Pattern 3: UDC Compliance Generator
```python
def add_udc_endpoints(app):
    """Add all 6 UDC-required endpoints to any FastAPI app."""
    import time
    from datetime import datetime

    start_time = time.time()
    request_count = {"value": 0}

    @app.middleware("http")
    async def count_requests(request, call_next):
        request_count["value"] += 1
        return await call_next(request)

    @app.get("/health")
    async def health():
        return {
            "status": "active",
            "service": app.title,
            "version": app.version,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    @app.get("/capabilities")
    async def capabilities():
        return {
            "version": app.version,
            "features": [],
            "dependencies": [],
            "udc_version": "1.0"
        }

    @app.get("/state")
    async def state():
        return {
            "uptime_seconds": int(time.time() - start_time),
            "requests_total": request_count["value"]
        }

    @app.get("/dependencies")
    async def dependencies():
        return {"required": [], "optional": [], "missing": []}

    @app.post("/message")
    async def message(msg: dict):
        return {"received": True, "trace_id": msg.get("trace_id")}

    @app.post("/send")
    async def send_message(request: dict):
        import uuid
        return {"sent": True, "trace_id": str(uuid.uuid4())}

    return app

# Use it:
app = FastAPI(title="My Service", version="1.0.0")
app = add_udc_endpoints(app)
```

---

## Rapid Prototyping

### Technique 1: Mock-First Development
```python
# Start with mocked responses, implement real logic later

@app.get("/api/complex-operation")
async def complex_operation():
    # TODO: Implement real logic
    return {
        "status": "success",
        "result": "MOCKED DATA - Replace with real implementation",
        "timestamp": datetime.utcnow().isoformat()
    }

# ✅ Service works immediately
# ✅ Can test integration with other services
# ✅ Replace mocks with real implementation later
```

### Technique 2: Progressive Enhancement
```python
# Version 1: Simple (10 minutes)
@app.post("/api/send-email")
async def send_email_v1(email: str, subject: str):
    # Just log for now
    print(f"Email to {email}: {subject}")
    return {"status": "logged"}

# Version 2: Real implementation (30 minutes)
@app.post("/api/send-email")
async def send_email_v2(email: EmailStr, subject: str, body: str):
    # Real email sending
    import smtplib
    # ... actual implementation
    return {"status": "sent"}

# Version 3: Production-ready (1 hour)
@app.post("/api/send-email")
async def send_email_v3(request: EmailRequest):
    # + Template rendering
    # + Error handling
    # + Retry logic
    # + Delivery tracking
    return EmailResponse(...)
```

---

## Testing Acceleration

### Auto-Test Generator
```python
def generate_endpoint_tests(app):
    """Auto-generate basic tests for all endpoints."""
    from fastapi.testclient import TestClient

    client = TestClient(app)

    for route in app.routes:
        if hasattr(route, "methods"):
            for method in route.methods:
                if method in ["GET", "POST", "PUT", "DELETE"]:
                    # Generate test
                    print(f"""
def test_{route.path.replace('/', '_')}_{method.lower()}():
    response = client.{method.lower()}("{route.path}")
    assert response.status_code in [200, 201, 204, 404]
""")

generate_endpoint_tests(app)
```

### Instant Coverage Report
```bash
# One command for full test + coverage report
pytest tests/ -v --cov=src --cov-report=html && open htmlcov/index.html
```

---

## Deployment Acceleration

### One-Command Deploy
```bash
# Create deploy script (do once)
cat > deploy.sh << 'EOF'
#!/bin/bash
set -e

SERVICE_NAME="my-service"
PORT=8500

echo "🚀 Deploying $SERVICE_NAME..."

# 1. Run tests
pytest tests/ -v || exit 1

# 2. Build if Dockerfile exists
if [ -f Dockerfile ]; then
    docker build -t $SERVICE_NAME .
fi

# 3. Deploy to server
rsync -avz --exclude 'venv' --exclude '__pycache__' \
    ./ root@198.54.123.234:/opt/fpai/services/$SERVICE_NAME/

# 4. Restart service
ssh root@198.54.123.234 << REMOTE
cd /opt/fpai/services/$SERVICE_NAME
pip3 install -r requirements.txt
systemctl restart $SERVICE_NAME
systemctl status $SERVICE_NAME
REMOTE

echo "✅ Deployment complete!"
echo "🔗 Health check: curl http://198.54.123.234:$PORT/health"
EOF

chmod +x deploy.sh

# Use it:
./deploy.sh
```

---

## AI Coding Patterns

### Pattern 1: Spec-to-Code
```markdown
<!-- In SPECS.md -->
## API Specs
GET /api/users - Returns list of users with pagination
POST /api/users - Creates new user, validates email uniqueness
```

```python
# AI generates implementation from spec:

@app.get("/api/users")
async def get_users(skip: int = 0, limit: int = 100):
    """Returns list of users with pagination."""
    users = await db.query("SELECT * FROM users LIMIT %s OFFSET %s", (limit, skip))
    return {"users": users, "skip": skip, "limit": limit}

@app.post("/api/users")
async def create_user(user: UserCreate):
    """Creates new user, validates email uniqueness."""
    existing = await db.query_one("SELECT id FROM users WHERE email = %s", (user.email,))
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    user_id = await db.execute(
        "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id",
        (user.name, user.email)
    )
    return {"id": user_id, "status": "created"}
```

### Pattern 2: Error-to-Fix
```python
# When test fails, use error message to generate fix

# Test error:
# "AssertionError: Expected 200, got 404"

# AI generates fix:
# 1. Check route exists
# 2. Check HTTP method matches
# 3. Check path parameters
# 4. Add route if missing
```

### Pattern 3: Docs-to-Implementation
```python
# From OpenAPI/Swagger docs, generate client:

async def call_external_api(endpoint: str, params: dict):
    """Auto-generated from external API docs."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.example.com{endpoint}", params=params)
        return response.json()
```

---

## Time-Saving Tools

### Tool 1: Live Reload
```python
# Use uvicorn's reload feature during development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8500,
        reload=True  # Auto-reload on code changes
    )
```

### Tool 2: API Documentation
```python
# FastAPI auto-generates docs at /docs
# No manual documentation needed!

# Access at: http://localhost:8500/docs
# Instant interactive API testing
```

### Tool 3: Database Migrations
```bash
# Quick SQLite for prototyping
import sqlite3

db = sqlite3.connect("dev.db")
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")

# Upgrade to PostgreSQL in production later
```

---

## Common Patterns Library

### Pattern: Retry Logic
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_unreliable_api():
    """Auto-retry on failure."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()
```

### Pattern: Caching
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_calculation(n: int) -> int:
    """Cached for performance."""
    return sum(range(n))
```

### Pattern: Background Tasks
```python
from fastapi import BackgroundTasks

def send_email_background(email: str, message: str):
    """Run in background, don't block response."""
    # Send email...
    pass

@app.post("/api/notify")
async def notify(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_email_background, email, "Hello!")
    return {"status": "queued"}
```

---

## Debugging Acceleration

### Technique 1: Request Logging
```python
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"→ {request.method} {request.url}")
    response = await call_next(request)
    print(f"← {response.status_code}")
    return response
```

### Technique 2: Error Details in Dev
```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    import traceback
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "traceback": traceback.format_exc(),  # Only in dev!
            "request": str(request.url)
        }
    )
```

---

## Speed Checklist

**To build service in <2 hours:**

- [ ] Copy _TEMPLATE (2 min)
- [ ] Write SPECS.md (15 min)
- [ ] Generate boilerplate code (5 min)
- [ ] Implement core logic (45 min)
- [ ] Add UDC endpoints (5 min)
- [ ] Write/generate tests (20 min)
- [ ] Deploy with one-command script (10 min)
- [ ] Register in service registry (2 min)
- [ ] Update README (5 min)

**Total:** ~2 hours for production-ready service

---

**Use these patterns → Build faster → Ship more value**
