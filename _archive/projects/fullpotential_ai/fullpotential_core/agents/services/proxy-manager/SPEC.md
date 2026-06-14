# proxy-manager - SPECS

**Created:** 2025-11-15
**Status:** Production Ready
**Port:** 8100

---

## Purpose

Automates NGINX reverse proxy and SSL management for the Full Potential AI droplet mesh. Removes manual server work (port wiring, domains, SSL, reloads) by exposing HTTP API for proxy config creation, SSL certificate management, and safe NGINX reloading.

---

## Requirements

### Functional Requirements
- [ ] Create/update/delete NGINX reverse proxy configurations via API
- [ ] Manage SSL certificates via Let's Encrypt (certbot)
- [ ] Validate upstream droplet health before routing traffic
- [ ] Safe NGINX reload with automatic rollback on failure
- [ ] Backup configs before changes
- [ ] Support both Docker and systemd deployments
- [ ] Registry integration for bulk proxy setup
- [ ] List all managed proxies
- [ ] SSL certificate auto-renewal support
- [ ] Custom domain mapping for services

### Non-Functional Requirements
- [ ] Safety: Always backup before changes, automatic rollback on NGINX test failure
- [ ] Reliability: Health check upstreams before routing, retry failed operations
- [ ] Security: Run behind VPN/firewall (v1), API token auth (v2)
- [ ] Performance: Config update < 2 seconds, NGINX reload < 1 second
- [ ] Logging: Complete audit trail of all proxy changes

---

## API Specs

### Endpoints

**PUT /proxies/{droplet_name}**
- **Purpose:** Create or update reverse proxy configuration
- **Input:** domain, upstream_host, upstream_port, require_healthy, enable_ssl
- **Output:** Proxy configuration details
- **Success:** 200 OK (updated) or 201 Created (new)
- **Errors:** 400 if invalid config, 500 if NGINX fails, 503 if upstream unhealthy

**DELETE /proxies/{droplet_name}**
- **Purpose:** Delete proxy configuration
- **Input:** droplet_name
- **Output:** Deletion confirmation
- **Success:** 200 OK
- **Errors:** 404 if not found, 500 if NGINX fails

**GET /proxies**
- **Purpose:** List all managed proxies
- **Input:** None
- **Output:** Array of proxy configurations
- **Success:** 200 OK
- **Errors:** 500 if query fails

**GET /proxies/{droplet_name}**
- **Purpose:** Get specific proxy details
- **Input:** droplet_name
- **Output:** Proxy configuration
- **Success:** 200 OK
- **Errors:** 404 if not found

**POST /proxies/{droplet_name}/ssl**
- **Purpose:** Issue SSL certificate for domain
- **Input:** Optional: email, force_renew
- **Output:** SSL certificate status
- **Success:** 200 OK
- **Errors:** 400 if invalid domain, 500 if certbot fails

**GET /proxy-manager/health**
- **Purpose:** Health check
- **Input:** None
- **Output:** {"status": "healthy", "nginx": {...}, "ssl": {...}}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

**GET /proxy-manager/sync-from-registry**
- **Purpose:** Sync all proxies from Registry
- **Input:** None
- **Output:** Sync results (synced, skipped counts)
- **Success:** 200 OK
- **Errors:** 500 if Registry unavailable

### Data Models

```python
class ProxyConfig:
    droplet_name: str
    domain: str
    upstream_host: str
    upstream_port: int
    require_healthy: bool
    enable_ssl: bool
    ssl_enabled: bool
    status: str  # "active", "inactive"
    created_at: datetime
    updated_at: datetime

class SSLCertificate:
    domain: str
    status: str  # "active", "pending", "expired"
    expiry: Optional[str]  # Date string
    issuer: str  # "Let's Encrypt"
    issued_at: datetime

class NginxStatus:
    present: bool
    config_test_ok: bool
    last_reload_timestamp: Optional[datetime]
    version: str

class ProxySyncResult:
    synced: List[str]  # Droplet names
    synced_count: int
    skipped: List[str]
    skipped_count: int
```

---

## Dependencies

### External Services
- NGINX: Reverse proxy server
- Certbot: SSL certificate management (Let's Encrypt)
- Registry (Optional): Service discovery for bulk setup

### APIs Required
- None (manages NGINX directly)

### System Requirements
- NGINX installed at /usr/sbin/nginx
- Certbot installed at /usr/bin/certbot
- Write access to /etc/nginx/sites-available and /etc/nginx/sites-enabled
- Root or sudo privileges

---

## Success Criteria

How do we know this works?

- [ ] Proxy configs created successfully
- [ ] NGINX config test passes before reload
- [ ] NGINX reloads without errors
- [ ] Upstream health checks work correctly
- [ ] SSL certificates issued via Let's Encrypt
- [ ] Automatic rollback on config test failure
- [ ] Backup created before every change
- [ ] Registry sync creates correct proxies
- [ ] Health endpoint returns accurate status
- [ ] At least 1 complete workflow: create proxy → enable SSL → verify traffic

---

## Proxy Creation Process

### 1. Validation
- Check upstream is reachable
- Validate domain format
- Test upstream /health endpoint (if require_healthy)

### 2. Backup
- Create timestamped backup of existing config (if exists)
- Store in /etc/nginx/backups/{droplet_name}-{timestamp}.conf

### 3. Write Config
- Generate NGINX config from template
- Write to /etc/nginx/sites-available/fpai-{droplet_name}.conf
- Create symlink in sites-enabled

### 4. Test Config
- Run: nginx -t
- If fails: Restore from backup, return error
- If succeeds: Proceed

### 5. Reload NGINX
- Run: systemctl reload nginx
- If fails: Restore from backup, return error

### 6. Verify
- Test proxy endpoint
- Confirm upstream accessible through proxy

---

## NGINX Config Template

```nginx
server {
    server_name {domain};

    location / {
        proxy_pass http://{upstream_host}:{upstream_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 80;
}
```

**With SSL:**
```nginx
server {
    server_name {domain};

    location / {
        proxy_pass http://{upstream_host}:{upstream_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
}

server {
    listen 80;
    server_name {domain};
    return 301 https://$server_name$request_uri;
}
```

---

## SSL Certificate Management

**Issue Certificate:**
```bash
certbot certonly --nginx -d {domain} --email {email} --agree-tos --non-interactive
```

**Auto-Renewal:**
- Certbot creates systemd timer automatically
- Verify: `systemctl list-timers | grep certbot`
- Certs renew 30 days before expiration

**Manual Renewal:**
```bash
certbot renew
```

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8100
- **Requires:** Root access for NGINX management
- **Resource limits:**
  - Memory: 256MB max
  - CPU: 0.5 cores
  - Storage: 100MB for configs and backups
- **Response time:** Config update < 2 seconds
- **Backup retention:** 7 days
- **Security:** Bind to localhost in v1, add auth in v2

---

## Error Codes

- `UPSTREAM_UNHEALTHY`: Health check failed
- `CONFIG_WRITE_FAILED`: Failed to write config
- `NGINX_TEST_FAILED`: Config test failed (with rollback)
- `NGINX_RELOAD_FAILED`: Reload failed
- `SSL_ISSUANCE_FAILED`: Certificate issuance failed
- `PROXY_NOT_FOUND`: Config not found
- `REGISTRY_UNAVAILABLE`: Cannot reach Registry

---

## Usage Example

```bash
# Create proxy for orchestrator
curl -X PUT http://localhost:8100/proxies/orchestrator \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "orchestrator.fullpotential.ai",
    "upstream_host": "localhost",
    "upstream_port": 8001,
    "require_healthy": true,
    "enable_ssl": false
  }'

# Issue SSL certificate
curl -X POST http://localhost:8100/proxies/orchestrator/ssl \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@fullpotential.ai"}'

# Verify traffic
curl https://orchestrator.fullpotential.ai/orchestrator/health
```

---

**Next Step:** Deploy to production, set up proxies for all services, enable SSL
