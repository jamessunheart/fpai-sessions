# Landing Page Service (Droplet #XX)

**Status:** 🟡 Development
**Version:** 1.0.0
**Port:** 8006
**UDC Compliant:** ✅ Yes

---

## 📋 Overview

The Landing Page Service hosts the public-facing landing page for Full Potential AI. It provides information about the platform, user registration, and marketing content.

**Key Capabilities:**
- Serve static and dynamic content for the landing page
- User registration and lead capture
- Integration with marketing tools and analytics
- SEO optimization

---

## 🚀 Quick Start

### Prerequisites
- Docker installed
- Access to Registry (port 8000)
- Access to Orchestrator (port 8001)

### Environment Setup

1. **Copy environment template:**
```bash
cp .env.example .env
```

2. **Edit .env with your values:**
```bash
# Required
REGISTRY_URL=http://registry:8000
ORCHESTRATOR_URL=http://orchestrator:8001

# Optional
LOG_LEVEL=INFO
ANALYTICS_ID=UA-XXXXX-Y
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

### Running Locally

**Development mode:**
```bash
uvicorn app.main:app --reload --port 8006
```

**With Docker:**
```bash
# Build
docker build -t fpai/landing-page:latest .

# Run
docker run -d \
  --name landing-page \
  --network fpai-network \
  -p 8006:8006 \
  --env-file .env \
  fpai/landing-page:latest
```

### Verify It's Working

```bash
# Health check
curl http://localhost:8006/health

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
| `/` | GET | No | Landing page HTML |
| `/api/v1/contact` | POST | No | Submit contact form |
| `/api/v1/subscribe` | POST | No | Subscribe to newsletter |

**Full API documentation:** See [SPEC.md](./SPEC.md) or visit `/docs` when running

---

## 🏗️ Architecture

### Dependencies

**Required:**
- Registry (droplet #1) - Authentication & service discovery

**External:**
- Email Service (optional) - For sending notifications
- Analytics Provider (optional) - Google Analytics, etc.

### Directory Structure

```
landing-page/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings & configuration
│   ├── models.py            # Data models
│   ├── schemas.py           # Pydantic schemas
│   ├── static/              # Static assets (CSS, JS, Images)
│   ├── templates/           # HTML templates (Jinja2)
│   ├── dependencies.py      # FastAPI dependencies
│   └── routers/
│       ├── health.py        # UDC endpoints
│       └── api.py           # Business logic endpoints
├── tests/
│   ├── test_health.py       # UDC endpoint tests
│   ├── test_api.py          # Business logic tests
│   └── conftest.py          # Pytest fixtures
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
pytest tests/test_api.py::test_subscribe
```

**Coverage target:** >80% on business logic

---

## 🐳 Docker

### Build Image

```bash
docker build -t fpai/landing-page:1.0.0 .
```

### Run Container

```bash
docker run -d \
  --name landing-page \
  --network fpai-network \
  -p 8006:8006 \
  -e REGISTRY_URL=http://registry:8000 \
  fpai/landing-page:1.0.0
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f landing-page

# Stop services
docker-compose down
```

---

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8006/health
```

### Metrics

Prometheus metrics available at `/metrics`:

```bash
curl http://localhost:8006/metrics
```

**Key Metrics:**
- `http_requests_total` - Total HTTP requests
- `page_views_total` - Total page views
- `conversions_total` - Total form submissions

### Logs

**View logs:**
```bash
# Docker
docker logs -f landing-page

# Local
tail -f logs/app.log
```

**Log format:** Structured JSON

---

## 🔒 Security

### Authentication

- Public endpoints are open
- Management endpoints (if any) require JWT token
- Token verified using Registry's public key

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
    "service_path": "/path/to/landing-page",
    "service_name": "landing-page",
    "droplet_id": [XX],
    "service_port": 8006,
    "deployment_method": "docker",
    "auto_register": true
  }'
```

### Manual Deployment

1. **Build and push Docker image:**
```bash
docker build -t fpai/landing-page:1.0.0 .
docker push fpai/landing-page:1.0.0
```

2. **Deploy on server:**
```bash
ssh root@server
docker pull fpai/landing-page:1.0.0
docker run -d \
  --name landing-page \
  --network fpai-network \
  --restart unless-stopped \
  -p 8006:8006 \
  --env-file /opt/fpai/.env \
  fpai/landing-page:1.0.0
```

3. **Verify deployment:**
```bash
curl http://server:8006/health
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
1. Registry available: `curl http://registry:8000/health`
2. Environment variables set: `cat .env`
3. Logs: `docker logs landing-page`

### Page Rendering Issues

**Issue:** Templates not rendering correctly

**Check:**
1. Template paths correct?
2. Static files accessible?
3. Jinja2 syntax errors in logs?

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
- Landing page templates
- Contact form API

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






