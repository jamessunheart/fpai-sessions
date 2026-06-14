# Tech Stack - Standard Technologies

**Standardized stack for all Full Potential AI services**

---

## Core Technologies

### Backend
- **Python 3.9+** - Primary language
- **FastAPI** - API framework (async, fast, auto docs)
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation

### Database
- **PostgreSQL** - Primary database (relational)
- **SQLite** - Local dev/testing
- **Redis** - Caching layer (optional)

### Frontend
- **React** - UI framework
- **TypeScript** - Type safety
- **TailwindCSS** - Styling
- **Vite** - Build tool

### Deployment
- **Docker** - Containerization
- **Nginx** - Reverse proxy
- **Systemd** - Service management
- **SSH** - Server access

---

## Standard Ports

**Local Development:**
- 8000-8999: Services
- 3000-3999: Frontend dev servers

**Production Server (198.54.123.234):**
- 8000: Registry
- 8001: Orchestrator
- 8002: Dashboard
- 8005: Landing Page
- 8006: Membership
- 8008: Jobs
- 8020: White Rock Ministry
- 8025: Credential Vault
- 8026: Master Dashboard
- 8030-8031: Coordination Dashboards
- 8XXX: Your new service

---

## File Structure

**Every service follows:**
```
service-name/
├── SPECS.md              # Requirements & API specs
├── README.md             # Progress & status
├── BUILD/                # Development
│   ├── src/
│   │   ├── main.py      # FastAPI app
│   │   ├── models.py    # Pydantic models
│   │   └── services/    # Business logic
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
└── PRODUCTION/           # Deployed artifacts
    ├── deployed_config.json
    └── deployment_log.md
```

---

## Required Dependencies

**Every Python service:**
```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
httpx>=0.25.0
python-dotenv>=1.0.0
```

**Optional but recommended:**
```txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
redis>=5.0.0
psycopg2-binary>=2.9.0
```

---

## Environment Variables

**Standard env vars every service should support:**
```bash
# Required
SERVICE_NAME=my-service
SERVICE_PORT=8XXX
SERVICE_VERSION=1.0.0

# Optional
DEBUG=false
LOG_LEVEL=info
REGISTRY_URL=http://198.54.123.234:8000
```

---

## API Standards

**All APIs use:**
- RESTful conventions
- JSON for data exchange
- ISO 8601 for timestamps
- HTTP status codes correctly
- OpenAPI/Swagger docs at `/docs`

---

## Testing Standards

**Every service must have:**
- Unit tests (pytest)
- >80% code coverage
- API endpoint tests
- UDC compliance tests

```bash
# Run tests
pytest tests/ -v --cov=src --cov-report=html
```

---

## Security Standards

**All services must:**
- Use HTTPS in production
- Validate all inputs (Pydantic)
- Never log secrets
- Use environment variables for credentials
- Implement rate limiting

---

## Deployment Standards

**Every service must have:**
- Dockerfile for containerization
- Health check endpoint
- Graceful shutdown handling
- Logging to stdout/stderr
- Environment-based configuration

---

## Documentation Standards

**Required docs:**
- SPECS.md - Technical specification
- README.md - Quick start & status
- API docs - Auto-generated via FastAPI `/docs`

---

## Version Control

**Git standards:**
- Main branch for production
- Feature branches for development
- Meaningful commit messages
- Tag releases (v1.0.0)

---

## Monitoring

**All services should:**
- Expose `/health` endpoint
- Log errors and warnings
- Track request metrics
- Report to centralized dashboard

---

**This stack is standardized across all services for consistency and ease of coordination.**
