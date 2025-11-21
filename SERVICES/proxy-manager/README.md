# Proxy Manager API

**Version:** 1.0.0
**Status:** Production Ready
**Port:** 8100

Automates NGINX reverse proxy and SSL management for the Full Potential AI droplet mesh.

## Purpose

The Proxy Manager API removes manual server work (port wiring, domains, SSL, reloads) by exposing a simple HTTP API that:
- Creates/updates NGINX reverse proxy configurations
- Manages SSL certificates via Let's Encrypt (certbot)
- Validates upstream droplet health before routing traffic
- Safely reloads NGINX with automatic rollback on failure

## Features

- ✅ **Automated Proxy Management** - Create/update/delete reverse proxy configs via API
- ✅ **SSL Automation** - One-command SSL certificate issuance and renewal
- ✅ **Health Checks** - Validate upstream services before routing traffic
- ✅ **Safe Rollback** - Automatic rollback if NGINX config test fails
- ✅ **Registry Integration** - Sync proxy configs from Registry droplet
- ✅ **UDC Compliant** - Follows Universal Droplet Contract standards

## Quick Start

### Prerequisites

- Python 3.11+
- NGINX installed (`/usr/sbin/nginx`)
- Certbot installed (`/usr/bin/certbot`)
- Write access to `/etc/nginx/sites-available` and `/etc/nginx/sites-enabled`

### Installation

```bash
# Clone repository
git clone <repository-url>
cd proxy-manager

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```bash
# Service
PROXY_MANAGER_PORT=8100

# NGINX paths (defaults usually work)
NGINX_SITES_AVAILABLE=/etc/nginx/sites-available
NGINX_SITES_ENABLED=/etc/nginx/sites-enabled
NGINX_BIN=/usr/sbin/nginx

# SSL
CERTBOT_BIN=/usr/bin/certbot
DEFAULT_SSL_EMAIL=admin@fullpotential.ai

# Registry integration (optional)
REGISTRY_URL=http://localhost:8000

# Health checks
HEALTH_CHECK_TIMEOUT_MS=1000
HEALTH_CHECK_PATH=/health
```

### Running

```bash
# Development
uvicorn app.main:app --reload --port 8100

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8100
```

### Docker

```bash
# Build
docker build -t proxy-manager:latest .

# Run
docker run -d \
  --name proxy-manager \
  -p 8100:8100 \
  -v /etc/nginx:/etc/nginx \
  -v /etc/letsencrypt:/etc/letsencrypt \
  proxy-manager:latest
```

## API Endpoints

### Create/Update Proxy

```bash
PUT /proxies/{droplet_name}
```

**Request Body:**
```json
{
  "domain": "orchestrator.fullpotential.ai",
  "upstream_host": "localhost",
  "upstream_port": 8001,
  "require_healthy": true,
  "enable_ssl": true
}
```

**Response:**
```json
{
  "droplet_name": "orchestrator",
  "domain": "orchestrator.fullpotential.ai",
  "upstream": "http://localhost:8001",
  "ssl_enabled": true,
  "status": "active"
}
```

### Delete Proxy

```bash
DELETE /proxies/{droplet_name}
```

**Response:**
```json
{
  "status": "deleted",
  "droplet_name": "orchestrator"
}
```

### List Proxies

```bash
GET /proxies
```

**Response:**
```json
[
  {
    "droplet_name": "orchestrator",
    "domain": "orchestrator.fullpotential.ai",
    "upstream": "http://localhost:8001",
    "ssl_enabled": true,
    "status": "active"
  }
]
```

### Get Proxy Details

```bash
GET /proxies/{droplet_name}
```

### Issue SSL Certificate

```bash
POST /proxies/{droplet_name}/ssl
```

**Request Body (optional):**
```json
{
  "email": "admin@fullpotential.ai",
  "force_renew": false
}
```

**Response:**
```json
{
  "domain": "orchestrator.fullpotential.ai",
  "status": "active",
  "expiry": "2024-12-31",
  "issuer": "Let's Encrypt"
}
```

### Health Check

```bash
GET /proxy-manager/health
```

**Response:**
```json
{
  "status": "healthy",
  "nginx": {
    "present": true,
    "config_test_ok": true,
    "last_reload_timestamp": "2024-11-14T00:00:00Z"
  },
  "ssl": {
    "certbot_present": true,
    "last_operation": "success"
  }
}
```

### Sync from Registry

```bash
GET /proxy-manager/sync-from-registry
```

**Response:**
```json
{
  "synced": ["orchestrator", "registry"],
  "synced_count": 2,
  "skipped": [],
  "skipped_count": 0
}
```

## Usage Examples

### Setup Orchestrator with Clean URL

```bash
# 1. Create proxy (HTTP first)
curl -X PUT http://localhost:8100/proxies/orchestrator \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "orchestrator.fullpotential.ai",
    "upstream_host": "localhost",
    "upstream_port": 8001,
    "require_healthy": true,
    "enable_ssl": false
  }'

# 2. Test HTTP works
curl http://orchestrator.fullpotential.ai/orchestrator/health

# 3. Issue SSL certificate
curl -X POST http://localhost:8100/proxies/orchestrator/ssl \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@fullpotential.ai"
  }'

# 4. Test HTTPS works
curl https://orchestrator.fullpotential.ai/orchestrator/health
```

### Bulk Setup from Registry

```bash
# Sync all droplets from Registry
curl http://localhost:8100/proxy-manager/sync-from-registry

# Then enable SSL for each
curl -X POST http://localhost:8100/proxies/orchestrator/ssl
curl -X POST http://localhost:8100/proxies/registry/ssl
curl -X POST http://localhost:8100/proxies/dashboard/ssl
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_nginx_manager.py

# Run with verbose output
pytest -v
```

## Architecture

```
proxy-manager/
├── app/
│   ├── main.py              # FastAPI app + routes
│   ├── config.py            # Settings from env vars
│   ├── models.py            # Pydantic models
│   ├── nginx_manager.py     # NGINX config + reload logic
│   ├── ssl_manager.py       # Certbot integration
│   └── registry_client.py   # Registry communication
├── tests/
│   ├── test_nginx_manager.py
│   └── test_api.py
├── Dockerfile
├── requirements.txt
├── SPEC_Proxy_Manager_API_v1.md
└── README.md
```

## UDC Compliance

This droplet follows the Universal Droplet Contract:

- ✅ `/proxy-manager/health` - Health check endpoint
- ✅ Structured error responses with error codes
- ✅ Correlation IDs in logs
- ✅ Safe rollback on failures
- ✅ Registry integration

## Error Handling

All errors follow UDC format:

```json
{
  "error": {
    "code": "NGINX_TEST_FAILED",
    "message": "NGINX configuration test failed",
    "details": {
      "nginx_output": "..."
    }
  }
}
```

**Error Codes:**
- `UPSTREAM_UNHEALTHY` - Upstream service health check failed
- `CONFIG_WRITE_FAILED` - Failed to write NGINX config
- `NGINX_TEST_FAILED` - NGINX config test failed (with rollback)
- `NGINX_RELOAD_FAILED` - NGINX reload failed
- `SSL_ISSUANCE_FAILED` - SSL certificate issuance failed
- `PROXY_NOT_FOUND` - Proxy configuration not found
- `REGISTRY_NOT_CONFIGURED` - Registry URL not set
- `REGISTRY_UNAVAILABLE` - Cannot reach Registry

## Production Deployment

### systemd Service

Create `/etc/systemd/system/proxy-manager.service`:

```ini
[Unit]
Description=Proxy Manager API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/apps/proxy-manager
Environment="PATH=/opt/fpai/apps/proxy-manager/.venv/bin"
ExecStart=/opt/fpai/apps/proxy-manager/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8100
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable proxy-manager
systemctl start proxy-manager
systemctl status proxy-manager
```

### SSL Auto-Renewal

Certbot creates a systemd timer for auto-renewal. Verify:

```bash
systemctl list-timers | grep certbot
```

## Security Notes

**v1 Security:**
- Bind to localhost (not exposed externally)
- Run behind VPN or firewall
- Root access required for NGINX management

**Future Enhancements (v2):**
- API token authentication
- Role-based access control
- Audit logging
- Rate limiting

## Troubleshooting

### NGINX config test fails

```bash
# Check NGINX config manually
nginx -t

# Check specific droplet config
nginx -t -c /etc/nginx/sites-available/fpai-{droplet_name}.conf
```

### SSL certificate fails

```bash
# Check certbot logs
cat /var/log/letsencrypt/letsencrypt.log

# Test manual certificate issuance
certbot certonly --nginx -d yourdomain.com
```

### Permissions issues

```bash
# Ensure directories exist and are writable
ls -la /etc/nginx/sites-available
ls -la /etc/nginx/sites-enabled

# Fix permissions if needed (careful!)
chmod 755 /etc/nginx/sites-available
chmod 755 /etc/nginx/sites-enabled
```

## Contributing

See `SPEC_Proxy_Manager_API_v1.md` for full specification.

## License

Full Potential AI - Internal Tool

---

**Built with ❤️ by Full Potential AI**
🌐 Building the Future
