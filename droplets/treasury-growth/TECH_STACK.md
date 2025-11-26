# 🛠️ TECH STACK - Standard Technology Choices

**Version:** 1.0
**Last Updated:** 2025-11-15
**Purpose:** Standardize technology choices across all droplets

---

## 1. PHILOSOPHY

**Boring Technology Wins**

We choose:
- ✅ Proven, stable technologies
- ✅ Strong community support
- ✅ Excellent documentation
- ✅ Active maintenance
- ✅ Clear migration paths

We avoid:
- ❌ Bleeding edge (high churn risk)
- ❌ Niche libraries (small community)
- ❌ Unmaintained projects
- ❌ Technology for technology's sake

**Rule:** Only deviate from this stack with explicit architectural approval.

---

## 2. CORE STACK

### 2.1 Backend Framework
**Choice:** FastAPI
**Version:** 0.104.0+

**Why FastAPI:**
- Modern async/await support (high performance)
- Automatic OpenAPI docs (self-documenting)
- Pydantic integration (type safety + validation)
- Excellent performance (on par with Node.js, Go)
- Large ecosystem and active community

**Example:**
```python
from fastapi import FastAPI

app = FastAPI(
    title="My Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/health")
def health():
    return {"status": "healthy"}
```

**When to deviate:**
- Real-time bidirectional: Use WebSockets (FastAPI supports)
- CPU-intensive batch processing: Consider separate worker service
- Never use Flask (legacy), Django (too heavy for microservices)

---

### 2.2 Database
**Choice:** PostgreSQL
**Version:** 15.0+

**Why PostgreSQL:**
- Industry standard for OLTP (transactional)
- ACID compliance (data integrity)
- Rich data types (JSON, arrays, etc.)
- Excellent performance and scalability
- Strong ecosystem (extensions, tools)

**Connection Library:** psycopg2 (production) or asyncpg (async)

**Example:**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("postgresql://user:pass@localhost/db")
SessionLocal = sessionmaker(bind=engine)
```

**When to deviate:**
- Time-series data: Consider TimescaleDB (Postgres extension)
- Analytics/OLAP: Consider separate analytics DB
- Document storage: Use JSONB in Postgres (don't add MongoDB)
- Never use SQLite in production (development only)

---

### 2.3 ORM/Database Layer
**Choice:** SQLAlchemy 2.0+

**Why SQLAlchemy:**
- Type-safe query construction
- Migration support via Alembic
- Connection pooling built-in
- Async support (with asyncpg)

**Example:**
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String

class Base(DeclarativeBase):
    pass

class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
```

**When to deviate:**
- Simple CRUD only: Raw SQL is acceptable
- Complex analytics: Raw SQL often clearer
- Never bypass ORM for user input (SQL injection risk)

---

### 2.4 Validation & Serialization
**Choice:** Pydantic 2.0+

**Why Pydantic:**
- Runtime type validation
- JSON serialization built-in
- FastAPI integration automatic
- Clear error messages

**Example:**
```python
from pydantic import BaseModel, Field

class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    port: int = Field(..., ge=1000, le=65535)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my-service",
                "port": 8010
            }
        }
```

**When to deviate:**
- Never. Always use Pydantic for validation.

---

### 2.5 HTTP Client
**Choice:** httpx (async) or requests (sync)

**Why httpx:**
- Async/await support
- HTTP/2 support
- Connection pooling
- Timeout management

**Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://service:8000/endpoint",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0
    )
```

**When to deviate:**
- Simple sync scripts: Use requests
- Never use urllib (too low-level)

---

### 2.6 Testing Framework
**Choice:** pytest

**Why pytest:**
- Simple, readable test syntax
- Excellent fixture system
- Great plugin ecosystem
- FastAPI has built-in TestClient

**Example:**
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

**Coverage Tool:** pytest-cov
**Target:** >80% coverage on business logic

---

### 2.7 Containerization
**Choice:** Docker

**Why Docker:**
- Industry standard
- Reproducible builds
- Easy deployment
- Excellent tooling

**Base Image:** python:3.11-slim
**Why:** Smaller size, security updates, official image

**Example Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Expose port
EXPOSE 8010

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8010/health')"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
```

**When to deviate:**
- Never. All droplets must be containerized.

---

### 2.8 Web Server
**Choice:** Uvicorn (ASGI server)

**Why Uvicorn:**
- High performance ASGI server
- FastAPI's recommended server
- Async/await support
- Production-ready

**Example:**
```python
# Development
uvicorn app.main:app --reload --port 8010

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8010 --workers 4
```

**When to deviate:**
- High load: Use Gunicorn with Uvicorn workers
- Never use development server in production

---

## 3. SUPPORTING LIBRARIES

### 3.1 Environment Variables
**Choice:** python-dotenv

```python
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
```

---

### 3.2 Date/Time
**Choice:** Standard library datetime + python-dateutil

```python
from datetime import datetime, timezone

# Always use UTC
now = datetime.now(timezone.utc)
```

**Never:** pytz (outdated), use zoneinfo instead

---

### 3.3 JSON
**Choice:** Standard library json + pydantic

```python
from pydantic import BaseModel

# Pydantic handles JSON automatically
class MyModel(BaseModel):
    name: str

# Serialize
model = MyModel(name="test")
json_str = model.model_dump_json()

# Deserialize
model = MyModel.model_validate_json(json_str)
```

---

### 3.4 Logging
**Choice:** Standard library logging + structlog (optional)

```python
import logging
import json

logger = logging.getLogger(__name__)

# Structured logging
logger.info(json.dumps({
    "event": "request_received",
    "path": "/health",
    "duration_ms": 23.4
}))
```

**Never:** print() statements in production code

---

### 3.5 Cryptography
**Choice:** cryptography library

```python
from cryptography.fernet import Fernet

# Symmetric encryption
key = Fernet.generate_key()
f = Fernet(key)
encrypted = f.encrypt(b"secret data")
decrypted = f.decrypt(encrypted)
```

**For JWT:** python-jose or PyJWT

---

### 3.6 Task Queue (if needed)
**Choice:** Celery + Redis

**Why:**
- Async task processing
- Scheduling support
- Retry logic built-in

**Alternative:** RQ (simpler, Redis-only)

**When to use:**
- Long-running tasks (>30s)
- Scheduled tasks (cron-like)
- Background processing

---

## 4. DEVELOPMENT TOOLS

### 4.1 Code Formatting
**Choice:** black

```bash
black app/ --line-length 100
```

**Config:** pyproject.toml
```toml
[tool.black]
line-length = 100
target-version = ['py311']
```

---

### 4.2 Linting
**Choice:** ruff (fast, modern)

```bash
ruff check app/
```

**Alternative:** flake8 (if team prefers)

---

### 4.3 Type Checking
**Choice:** mypy

```bash
mypy app/ --strict
```

**Config:** pyproject.toml
```toml
[tool.mypy]
python_version = "3.11"
strict = true
```

---

### 4.4 Dependency Management
**Choice:** pip + requirements.txt (simple) or Poetry (complex)

**requirements.txt:**
```
fastapi==0.104.0
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pydantic==2.5.0
python-dotenv==1.0.0
httpx==0.25.0
pytest==7.4.3
pytest-cov==4.1.0
```

**Split files:**
- requirements.txt (production)
- requirements-dev.txt (development tools)

---

## 5. PYTHON VERSION

**Choice:** Python 3.11+

**Why:**
- Modern async/await improvements
- Better performance
- Security updates
- Type hint improvements

**Minimum:** Python 3.10
**Maximum:** Python 3.12 (latest stable)

---

## 6. COMMON PATTERNS

### 6.1 Configuration Management

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    service_name: str
    service_port: int = 8010

    class Config:
        env_file = ".env"

settings = Settings()
```

---

### 6.2 Database Connection

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True  # Verify connections before use
)
SessionLocal = sessionmaker(bind=engine)

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### 6.3 JWT Authentication

```python
from jose import JWTError, jwt

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            registry_public_key,
            algorithms=["RS256"]
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

## 7. ANTI-PATTERNS

**Never do these:**

❌ **Global mutable state**
```python
# Bad
global_cache = {}

def get_data():
    return global_cache.get("key")
```

✅ **Use dependency injection**
```python
# Good
from functools import lru_cache

@lru_cache()
def get_cache():
    return {}
```

---

❌ **Print statements**
```python
# Bad
print("Request received")
```

✅ **Use structured logging**
```python
# Good
logger.info(json.dumps({"event": "request_received"}))
```

---

❌ **String concatenation for SQL**
```python
# Bad - SQL INJECTION RISK
query = f"SELECT * FROM users WHERE id = {user_id}"
```

✅ **Parameterized queries**
```python
# Good
query = "SELECT * FROM users WHERE id = :id"
result = session.execute(query, {"id": user_id})
```

---

❌ **Bare except clauses**
```python
# Bad
try:
    something()
except:
    pass
```

✅ **Specific exception handling**
```python
# Good
try:
    something()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise
```

---

## 8. PACKAGE STRUCTURE

**Standard structure for all droplets:**

```
my-service/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app
│   ├── config.py         # Settings
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   ├── crud.py           # Database operations
│   ├── dependencies.py   # FastAPI dependencies
│   └── routers/
│       ├── __init__.py
│       ├── health.py     # UDC endpoints
│       └── api.py        # Business logic
├── tests/
│   ├── __init__.py
│   ├── test_health.py
│   └── test_api.py
├── Dockerfile
├── requirements.txt
├── README.md
├── SPEC.md
└── .env.example
```

---

## 9. DECISION MATRIX

When choosing technology, ask:

1. **Is it in this stack?**
   - Yes → Use it
   - No → Continue to question 2

2. **Is it necessary?**
   - No → Don't add it
   - Yes → Continue to question 3

3. **Can existing stack solve it?**
   - Yes → Use existing stack
   - No → Continue to question 4

4. **Is it mature and maintained?**
   - No → Look for alternatives
   - Yes → Continue to question 5

5. **Will it reduce complexity?**
   - No → Don't add it
   - Yes → Propose to architect for approval

---

## 10. UPGRADE POLICY

**Minor versions:** Upgrade quarterly
**Major versions:** Upgrade when stable (6-12 months after release)
**Security patches:** Upgrade immediately

**Process:**
1. Check changelog for breaking changes
2. Update requirements.txt
3. Run full test suite
4. Deploy to development
5. Deploy to production after 1 week

---

**This stack is optimized for:**
- 🚀 Developer productivity
- 🔒 Security
- 📈 Performance
- 🛠️ Maintainability
- 📚 Learnability

**Follow it. Your future self will thank you.**

🛠️⚡💎
