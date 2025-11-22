# Registry - Service Registry and Identity Management

**Version:** 1.0.0
**Port:** 8000
**Status:** Production

## Purpose

The Registry is the Single Source of Truth (SSOT) for all services in the Full Potential AI system. It provides:

- Service registration and discovery
- Identity management
- JWT token issuance
- Endpoint directory
- Status tracking

## UDC Compliance

✅ Fully UDC-compliant with all 5 required endpoints:

- `GET /health` - Health check
- `GET /capabilities` - Service capabilities
- `GET /state` - Resource usage and metrics
- `GET /dependencies` - Dependent services
- `POST /message` - Inter-droplet messaging

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Test UDC endpoints
curl http://localhost:8000/health
curl http://localhost:8000/capabilities
curl http://localhost:8000/state
```

## Deployment

Registry runs on port 8000 on the production server (198.54.123.234).

Deploy path: `/opt/fpai/agents/services/registry`

## Architecture

Registry is Droplet #1 in the Full Potential AI system. It has no dependencies and is the foundational service that all other droplets connect to.
