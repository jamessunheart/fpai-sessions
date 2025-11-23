# Jobs Service (Droplet #XX)

**Status:** 🟡 Development
**Version:** 1.0.0
**Port:** 8005
**UDC Compliant:** ✅ Yes

---

## 📋 Overview

The Jobs Service manages background task execution and job scheduling across the Full Potential AI ecosystem. It provides a reliable way to schedule recurring tasks, execute long-running processes, and track job status.

**Key Capabilities:**
- Schedule recurring jobs (cron-style)
- Execute one-off background tasks
- Track job status and execution history
- Retry failed jobs with backoff strategies

---

## 🚀 Quick Start

### Prerequisites
- Docker installed
- Access to Registry (port 8000)
- Access to Orchestrator (port 8001)
- PostgreSQL database

### Environment Setup

1. **Copy environment template:**
```bash
cp .env.example .env
```

2. **Edit .env with your values:**
```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost/jobs_db
REGISTRY_URL=http://registry:8000
ORCHESTRATOR_URL=http://orchestrator:8001

# Optional
LOG_LEVEL=INFO
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run database migrations:**
```bash
alembic upgrade head
```

### Running Locally

**Development mode:**
```bash
uvicorn app.main:app --reload --port 8005
```

**With Docker:**
```bash
# Build
docker build -t fpai/jobs:latest .

# Run
docker run -d \
  --name jobs \
  --network fpai-network \
  -p 8005:8005 \
  --env-file .env \
  fpai/jobs:latest
```

### Verify It's Working

```bash
# Health check
curl http://localhost:8005/health

# Expected response
{
  "status": "healthy",
  "timestamp": "2025-11-23T12:00:00Z",
  "uptime_seconds": 10,
  "version": "1.0.0"
}
```

---

## 📚 API Documentation

### UDC Endpoints (Standard)

All Full Potential AI services implement these 5 standard endpoints:

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/health` | GET | No | Health check |
| `/capabilities` | GET | No | Service capabilities |
| `/state` | GET | JWT | Current state |
| `/dependencies` | GET | JWT | Dependencies status |
| `/message` | POST | JWT | Inter-service messaging |

### Business Logic Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/v1/jobs` | GET | JWT | List jobs |
| `/api/v1/jobs` | POST | JWT | Create/Schedule job |
| `/api/v1/jobs/{id}` | GET | JWT | Get job details |
| `/api/v1/jobs/{id}/cancel` | POST | JWT | Cancel job |
| `/api/v1/jobs/{id}/logs` | GET | JWT | Get job logs |

**Full API documentation:** See [SPEC.md](./SPEC.md) or visit `/docs` when running

---

## 🏗️ Architecture

### Dependencies

**Required:**
- Registry (droplet #1) - Authentication & service discovery
- Orchestrator (droplet #2) - Task coordination

**External:**
- PostgreSQL (database) - Job state and history
- Redis (optional) - Job queue (if using Celery/RQ)

### Directory Structure

```
jobs/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings & configuration
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── crud.py              # Database operations
│   ├── dependencies.py      # FastAPI dependencies
│   └── routers/
│       ├── health.py        # UDC endpoints
│       └── api.py           # Business logic endpoints
├── tests/
│   ├── test_health.py       # UDC endpoint tests
│   ├── test_api.py          # Business logic tests
│   └── conftest.py          # Pytest fixtures
├── alembic/                 # Database migrations
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md                # This file
└── SPEC.md                  # Detailed specification
```

---

## 🔧 Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks (optional)
pre-commit install
```

### Code Quality

**Format code:**
```bash
black app/ tests/
isort app/ tests/
```

**Lint code:**
```bash
ruff check app/ tests/
```

**Type check:**
```bash
mypy app/ --strict
```

**Run all checks:**
```bash
./scripts/lint.sh
```

### Testing

**Run all tests:**
```bash
pytest
```

**With coverage:**
```bash
pytest --cov=app --cov-report=html tests/
```

**Run specific test:**
```bash
pytest tests/test_api.py::test_create_job
```

**Coverage target:** >80% on business logic

---

## 🐳 Docker

### Build Image

```bash
docker build -t fpai/jobs:1.0.0 .
```

### Run Container

```bash
docker run -d \
  --name jobs \
  --network fpai-network \
  -p 8005:8005 \
  -e DATABASE_URL=postgresql://user:pass@postgres/jobs_db \
  -e REGISTRY_URL=http://registry:8000 \
  fpai/jobs:1.0.0
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f jobs

# Stop services
docker-compose down
```

---

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8005/health
```

### Metrics

Prometheus metrics available at `/metrics`:

```bash
curl http://localhost:8005/metrics
```

**Key Metrics:**
- `http_requests_total` - Total HTTP requests
- `jobs_active_count` - Number of currently running jobs
- `jobs_failed_total` - Total number of failed jobs
- `jobs_completed_total` - Total number of completed jobs

### Logs

**View logs:**
```bash
# Docker
docker logs -f jobs

# Local
tail -f logs/app.log
```

**Log format:** Structured JSON

---

## 🔒 Security

### Authentication

- All endpoints (except `/health`) require JWT token
- Token obtained from Registry
- Token verified using Registry's public key

**Example:**
```bash
# Get token from Registry
TOKEN=$(curl -X POST http://registry:8000/auth/token \
  -d '{"service_name":"jobs"}' | jq -r .token)

# Use token
curl http://localhost:8005/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN"
```

### Secrets Management

**Never commit:**
- `.env` files
- API keys
- Passwords
- Private keys

**Use:**
- Environment variables
- credentials-manager service (for shared secrets)
- `.env.example` for templates

---

## 🚀 Deployment

### Production Deployment

```bash
# Using deployer service
curl -X POST http://deployer:8007/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "service_path": "/path/to/jobs",
    "service_name": "jobs",
    "droplet_id": [XX],
    "service_port": 8005,
    "deployment_method": "docker",
    "auto_register": true
  }'
```

### Manual Deployment

1. **Build and push Docker image:**
```bash
docker build -t fpai/jobs:1.0.0 .
docker push fpai/jobs:1.0.0
```

2. **Deploy on server:**
```bash
ssh root@server
docker pull fpai/jobs:1.0.0
docker run -d \
  --name jobs \
  --network fpai-network \
  --restart unless-stopped \
  -p 8005:8005 \
  --env-file /opt/fpai/.env \
  fpai/jobs:1.0.0
```

3. **Verify deployment:**
```bash
curl http://server:8005/health
```

---

## 📖 Documentation

- **SPEC.md** - Complete technical specification
- **API Docs** - Available at `/docs` when running (Swagger UI)
- **ReDoc** - Available at `/redoc` when running
- **Foundation Files** - Located in `/ARCHITECTURE/foundation/`
  - UDC_COMPLIANCE.md
  - TECH_STACK.md
  - SECURITY_REQUIREMENTS.md
  - CODE_STANDARDS.md
  - INTEGRATION_GUIDE.md

---

## 🐛 Troubleshooting

### Service Won't Start

**Issue:** Service crashes on startup

**Check:**
1. Database connection: `DATABASE_URL` correct?
2. Registry available: `curl http://registry:8000/health`
3. Environment variables set: `cat .env`
4. Logs: `docker logs jobs`

### Job Execution Failures

**Issue:** Jobs are failing or not starting

**Check:**
1. Job definition valid?
2. Worker resources sufficient?
3. Database connectivity during execution?

### Database Errors

**Issue:** SQLAlchemy errors or connection failures

**Check:**
1. Migrations applied: `alembic upgrade head`
2. Database accessible: `psql $DATABASE_URL`
3. Connection string format: `postgresql://user:pass@host:port/db`

---

## 🤝 Contributing

### Development Workflow

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes
3. Format code: `black app/ tests/ && isort app/ tests/`
4. Run tests: `pytest --cov=app tests/`
5. Commit: `git commit -m "Add feature"`
6. Push: `git push origin feature/my-feature`
7. Create pull request

### Code Standards

- Follow PEP 8 (use Black for formatting)
- Type hints on all functions
- Tests for all new features
- Update SPEC.md if changing API

---

## 📝 Changelog

### [1.0.0] - 2025-11-23

**Added:**
- Initial release
- Job scheduling
- Job execution engine

---

## 📄 License

[License information]

---

## 👥 Authors

- Full Potential AI Team

---

## 🆘 Support

- **Issues:** Create issue in GitHub repository
- **Questions:** Ask in [team channel]
- **Documentation:** See SPEC.md and Foundation Files

---

**Part of the Full Potential AI ecosystem** 🌐⚡💎

