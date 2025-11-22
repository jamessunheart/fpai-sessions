# TECH_STACK.md
**Full Potential AI - Technology Standards**
**Version:** 1.0
**Last Updated:** November 2025

---

## 🎯 PHILOSOPHY

**Integration-first:** Use existing enterprise tools for 96% of functionality. Build custom only when necessary.

**Compression:** Achieve 5-10x development speed through AI-generated code + human verification.

**Consistency:** All droplets use compatible tech stacks for seamless integration.

---

## 🐍 BACKEND (Default: Python)

### Core Framework
**Primary:** FastAPI
**Why:** Native async, automatic API docs, fast execution, excellent type support

**Alternative:** Node.js + Express (if developer preference)

### Language Version
**Python:** 3.11+
**Node:** 18+ LTS

### Async Pattern
**ALWAYS use async/await**
```python
# Good
async def get_droplet_status():
    async with httpx.AsyncClient() as client:
        return await client.get(url)

# Avoid
def get_droplet_status():
    return requests.get(url)  # Blocking
```

### Data Validation
**Library:** Pydantic
**Why:** Type safety + automatic validation + clear error messages

```python
from pydantic import BaseModel, Field

class DropletStatus(BaseModel):
    id: int
    name: str
    status: Literal["active", "inactive", "error"]
    updated_at: datetime
```

### HTTP Client
**Library:** httpx (async) or aiohttp
**Why:** Native async support, connection pooling

**Avoid:** requests (synchronous, blocks)

### Authentication
**Method:** JWT
**Library:** PyJWT (Python) or jsonwebtoken (Node)

**Pattern:**
```python
from jose import jwt, JWTError

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            REGISTRY_PUBLIC_KEY,
            algorithms=["RS256"],
            audience="fullpotential.droplets"
        )
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid token")
```

---

## 🗄️ DATABASE

### Primary Choice
**Database:** PostgreSQL 15+
**Why:** Proven reliability, JSON support, excellent performance

### Driver
**Python:** asyncpg (async) or psycopg3
**Node:** pg or Prisma

### Migrations
**Python:** Alembic
**Node:** Prisma Migrate or Knex

### ORM (Optional)
**Python:** SQLAlchemy 2.0 (async mode)
**Node:** Prisma or TypeORM

**Pattern:** Direct SQL for performance-critical paths, ORM for convenience

### Lightweight Alternative
**Database:** SQLite
**When:** Development, single-instance droplets, <10K records

---

## 🎨 FRONTEND (When Needed)

### Framework
**Primary:** Next.js 14+ (App Router)
**Why:** Built-in SSR, excellent DX, Vercel deployment

### Language
**TypeScript (strict mode)**
```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitAny": true
  }
}
```

### Styling
**Primary:** Tailwind CSS
**Why:** Utility-first, consistent design system, fast iteration

**Component Library:** shadcn/ui (if complex UI needed)

### State Management
**Server State:** React Query (TanStack Query)
**Client State:** Zustand or React Context
**Forms:** React Hook Form

### Real-time Updates
**Method:** WebSockets or Server-Sent Events
**Library:** Socket.io (if WebSocket) or native EventSource (if SSE)

---

## 🐳 DEPLOYMENT

### Containerization
**Method:** Docker
**Why:** Consistent environments, easy deployment, portable

**Dockerfile Pattern:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Orchestration
**Development:** Docker Compose
**Production:** Consider per droplet (most are single-container)

### Web Server
**Python:** Uvicorn (ASGI server)
**Node:** Native Node cluster or PM2

**Configuration:**
```bash
# Production settings
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

### Hosting
**Recommended:** DigitalOcean, Hetzner VPS, or Render
**Why:** Cost-effective, simple deployment, good performance

**Avoid:** Overengineered Kubernetes for single-droplet services

---

## 🔐 SECURITY

### Environment Variables
**Management:** .env files + python-dotenv or pydantic-settings

**Required in `.env.example`:**
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Authentication
JWT_SECRET=your-secret-key-here
REGISTRY_URL=https://registry.fullpotential.ai

# API Keys (if needed)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Environment
ENVIRONMENT=development|production
```

**NEVER commit `.env` to git**

### Secrets Management
**Development:** .env files (gitignored)
**Production:** Environment variables or secret management service

### Input Validation
**ALWAYS validate ALL inputs:**
```python
from pydantic import BaseModel, validator

class MessageInput(BaseModel):
    content: str
    
    @validator('content')
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Content cannot be empty')
        return v
```

---

## 🧪 TESTING

### Framework
**Python:** pytest + pytest-asyncio
**Node:** Jest or Vitest

### Coverage
**Tool:** pytest-cov or c8
**Target:** >80% for critical paths

### Test Structure
```python
# test_health.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["active", "inactive", "error"]
```

---

## 📦 PACKAGE MANAGEMENT

### Python
**Method:** pip + requirements.txt
**Why:** Simple, standard, works everywhere

**Alternative:** Poetry (if team prefers)

**requirements.txt pattern:**
```txt
# Core
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0

# Database
asyncpg==0.29.0

# HTTP
httpx==0.25.1

# Auth
python-jose[cryptography]==3.3.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
```

### Node
**Method:** npm
**Alternative:** yarn or pnpm

---

## 🔧 DEVELOPMENT TOOLS

### Code Quality

**Linting (Python):**
```bash
pip install ruff
ruff check .
```

**Formatting (Python):**
```bash
pip install black
black .
```

**Type Checking (Python):**
```bash
pip install mypy
mypy .
```

**Linting (TypeScript):**
```bash
npm install -D eslint
eslint .
```

**Formatting (TypeScript):**
```bash
npm install -D prettier
prettier --write .
```

### Pre-commit Hooks (Recommended)
```bash
pip install pre-commit
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
  - repo: https://github.com/psf/black
    hooks:
      - id: black
```

---

## 🔌 INTEGRATION LIBRARIES

### Registry Communication
```python
import httpx

async def register_with_registry():
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{REGISTRY_URL}/register",
            json={
                "id": DROPLET_ID,
                "name": DROPLET_NAME,
                "endpoint": DROPLET_URL
            },
            headers={"Authorization": f"Bearer {JWT_TOKEN}"}
        )
```

### Monitoring
**Method:** Prometheus metrics endpoint (optional)
**Library:** prometheus_client (Python) or prom-client (Node)

### Logging
**Format:** Structured JSON logs
**Library:** structlog (Python) or winston (Node)

**Pattern:**
```python
import structlog

log = structlog.get_logger()

log.info(
    "request_processed",
    trace_id=trace_id,
    endpoint="/health",
    duration_ms=23,
    status_code=200
)
```

---

## 🎯 QUICK START TEMPLATE

### Create New Droplet

**1. Clone base template:**
```bash
git clone https://github.com/fullpotential/droplet-template
cd droplet-template
```

**2. Setup environment:**
```bash
cp .env.example .env
# Edit .env with your values
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Customize:**
- Edit `app/main.py` for your droplet logic
- Update `udc_config.json` with your droplet info
- Implement specific endpoints in `app/routes/`

**5. Test:**
```bash
pytest
```

**6. Run:**
```bash
uvicorn app.main:app --reload
```

**7. Deploy:**
```bash
docker build -t droplet-14 .
docker run -p 8000:8000 droplet-14
```

---

## ⚡ PERFORMANCE GUIDELINES

### Response Time Targets
- `/health`: <500ms
- `/capabilities`: <200ms
- `/state`: <300ms
- Other endpoints: <1000ms

### Optimization Tips
1. **Use async everywhere** - Never block the event loop
2. **Connection pooling** - Reuse database/HTTP connections
3. **Cache wisely** - Cache expensive computations, not fast queries
4. **Index databases** - All foreign keys + frequently queried fields
5. **Batch operations** - Combine multiple queries when possible

---

## 🚫 ANTI-PATTERNS TO AVOID

**DON'T:**
- ❌ Use synchronous I/O (requests, time.sleep)
- ❌ Hardcode credentials
- ❌ Skip input validation
- ❌ Return unstructured errors
- ❌ Ignore security headers
- ❌ Deploy without tests
- ❌ Use `print()` instead of proper logging
- ❌ Leave TODO/FIXME in production code

---

## 📚 LEARNING RESOURCES

**FastAPI:** https://fastapi.tiangolo.com
**Pydantic:** https://docs.pydantic.dev
**asyncio:** https://docs.python.org/3/library/asyncio.html
**PostgreSQL:** https://www.postgresql.org/docs
**Docker:** https://docs.docker.com

---

**END TECH_STACK.md**
