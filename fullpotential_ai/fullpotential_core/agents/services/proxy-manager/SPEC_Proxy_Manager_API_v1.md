# SPEC: Proxy Manager API (Droplet – Proxy Manager)

**Version:** 1.0
**Author:** Architect (James)
**Status:** Ready for Assembly
**Depends on:**
- Registry v2 (droplet SSOT)
- Deployed droplets exposing health endpoints
- NGINX installed on host
- Certbot available for SSL (Let's Encrypt)

---

## 1. Intent (Purpose)

The Proxy Manager API automates all NGINX reverse proxy and SSL management for the FPAI droplet mesh.

It removes manual server work (port wiring, domains, SSL, reloads) by exposing a simple HTTP API:
- Given a droplet record (hostname, internal port, external domain), create or update NGINX config
- Obtain and renew SSL certificates via Let's Encrypt
- Validate target droplet health before switching traffic
- Reload NGINX safely with rollback on failure

This turns NGINX + certbot into a programmable "network mesh droplet" that other services (Orchestrator, Coordinator, CI) can call.

---

## 2. Scope & Non-Scope

### In Scope
- HTTP API for:
  - Creating/updating a proxy route for a droplet
  - Deleting a proxy route
  - Listing current routes
  - Triggering SSL issuance/renewal
  - Validating upstream droplet health
  - Reporting proxy-level status/metrics
- NGINX config file generation and reload:
  - One config file per droplet (e.g. `/etc/nginx/sites-available/fpai-<droplet_name>.conf`)
  - Symlink to sites-enabled
- Let's Encrypt / certbot integration:
  - HTTP-01 challenge using NGINX
  - Auto-renewal via cron/systemd timer (documented)
- Registry integration (read-only):
  - Optionally read droplet metadata from Registry to pre-fill routes
- UDC-style error responses:
  - `{ "error": { "code": "...", "message": "...", "details": {...} } }`

### Out of Scope (v1)
- Managing the Registry itself (read only)
- Automatic DNS record creation (assume DNS already points to server IP)
- Multi-node NGINX cluster (single host only)
- Advanced traffic shaping (A/B, canary, rate limiting) — can be v2

---

## 3. Success Criteria

### Functional:
1. Given `domain=fpai.example.com` and `upstream=http://localhost:8001`, calling `POST /proxies`:
   - Writes NGINX config file
   - Tests config (`nginx -t`)
   - Reloads NGINX
   - Returns 201 + route details
2. Given `domain=fpai.example.com`, calling `POST /proxies/{id}/ssl`:
   - Obtains valid Let's Encrypt cert
   - Updates NGINX config to HTTPS
   - Reloads NGINX
   - Route is reachable via HTTPS with valid cert
3. Given a droplet is unhealthy, `POST /proxies`:
   - Performs upstream health check
   - If unhealthy and `require_healthy=true`, returns 422 and does not reload NGINX

### Operational:
4. NGINX reload is safe:
   - If `nginx -t` fails, route changes are rolled back and error is returned
5. All operations are logged with:
   - `correlation_id`, `droplet_name`, `domain`, `action`, `result`
6. Proxy Manager health endpoint:
   - `GET /proxy-manager/health` returns `healthy/degraded/unhealthy` based on:
     - NGINX executable present
     - Config directory writable
     - Last reload status

---

## 4. API Design

**Base path:** `http://<proxy-manager-host>:<port>/`

All responses JSON, with UDC-style errors:

```json
{
  "error": {
    "code": "PROXY_CONFIG_FAILED",
    "message": "NGINX config test failed",
    "details": {
      "nginx_output": "..."
    }
  }
}
```

### 4.1 Routes

#### 4.1.1 Create/Update Proxy
`PUT /proxies/{droplet_name}`

**Body:**
```json
{
  "domain": "orchestrator.fullpotential.ai",
  "upstream_host": "localhost",
  "upstream_port": 8001,
  "require_healthy": true,
  "enable_ssl": true
}
```

**Behavior:**
- Generate NGINX config for:
  - HTTP → HTTPS redirect (if `enable_ssl=true` and cert exists)
  - HTTPS proxy to upstream
- If `enable_ssl=true` and no cert yet:
  - Option A (v1): return 202 + instructions to call `POST /proxies/{droplet_name}/ssl`
  - Option B (optional): auto-trigger SSL issuance
- Perform `nginx -t` and reload if OK
- Return 200/201 with:

```json
{
  "droplet_name": "orchestrator",
  "domain": "orchestrator.fullpotential.ai",
  "upstream": "http://localhost:8001",
  "ssl_enabled": true,
  "status": "active"
}
```

#### 4.1.2 Delete Proxy
`DELETE /proxies/{droplet_name}`
- Remove config file + symlink
- `nginx -t` and reload
- Return 200 with `{ "status": "deleted" }`

#### 4.1.3 List Proxies
`GET /proxies`
- Returns all known configs:

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

#### 4.1.4 Get Proxy Details
`GET /proxies/{droplet_name}`
- Returns single config + last health check result.

#### 4.1.5 Trigger SSL Issuance/Renewal
`POST /proxies/{droplet_name}/ssl`

**Body (optional):**
```json
{
  "email": "admin@fullpotential.ai",
  "force_renew": false
}
```

**Behavior:**
- Uses certbot with `--nginx` (or `--webroot` with known path) for domain associated with droplet
- On success:
  - Updates config to use SSL
  - Reloads NGINX
  - Returns 200 with certificate metadata (expiry, issuer)

#### 4.1.6 Health
`GET /proxy-manager/health`
- Returns:

```json
{
  "status": "healthy",
  "nginx": {
    "present": true,
    "config_test_ok": true,
    "last_reload_timestamp": "..."
  },
  "ssl": {
    "certbot_present": true,
    "last_operation": "success"
  }
}
```

---

## 5. Data & Configuration

### 5.1 Environment Variables
- `PROXY_MANAGER_PORT` (default 8100)
- `NGINX_SITES_AVAILABLE` (default `/etc/nginx/sites-available`)
- `NGINX_SITES_ENABLED` (default `/etc/nginx/sites-enabled`)
- `NGINX_BIN` (default `/usr/sbin/nginx`)
- `CERTBOT_BIN` (default `/usr/bin/certbot`)
- `DEFAULT_SSL_EMAIL` (default `admin@fullpotential.ai`)
- `REGISTRY_URL` (optional; e.g. `http://localhost:8000`)
- `HEALTH_CHECK_TIMEOUT_MS` (default 1000)
- `HEALTH_CHECK_PATH` (default `/health`)

### 5.2 Internal Models

**ProxyConfig**
- `droplet_name`: str
- `domain`: str
- `upstream_host`: str
- `upstream_port`: int
- `ssl_enabled`: bool
- `last_health_status`: Optional[str]
- `last_health_checked_at`: Optional[datetime]

Configs stored in filesystem only (no DB) for v1; can later add YAML/JSON index if needed.

---

## 6. Non-Functional Requirements
- **Language:** Python 3.11
- **Framework:** FastAPI or equivalent
- **Performance:**
  - Typical operations < 1s (excluding certbot, which may be longer)
- **Security:**
  - Bind to localhost or behind VPN in v1
  - Require API token header if exposed externally later (design hook)
- **Resilience:**
  - Rollback on failed NGINX test
  - Don't leave NGINX in broken state
- **Logging:**
  - Structured logs with:
    - `timestamp`, `level`, `droplet_name`, `action`, `result`, `error_code`, `correlation_id`

---

## 7. Integration Points

### 7.1 Registry

Optional helper endpoint:
- `GET /proxy-manager/sync-from-registry`
  - Fetches active droplets from `REGISTRY_URL/droplets`
  - For each droplet that includes `domain` + `internal_port`, proposes or creates proxy configs
  - Returns a summary of synced routes

**Schema expectation from Registry droplet:**
```json
[
  {
    "name": "orchestrator",
    "host": "localhost",
    "port": 8001,
    "domain": "orchestrator.fullpotential.ai",
    "status": "active"
  }
]
```

(If your actual Registry schema differs, adjust mapping but keep this behavior.)

### 7.2 Orchestrator / Coordinator
- They should call:
  - `PUT /proxies/{droplet_name}` when a droplet is deployed or updated
  - `POST /proxies/{droplet_name}/ssl` after DNS is confirmed and initial route is working

---

## 8. Testing Strategy

### 8.1 Unit Tests
- **Config rendering:**
  - Given a `ProxyConfig`, produce valid NGINX config text
- **NGINX command wrapper:**
  - Mock `subprocess.run` to simulate success/failure of `nginx -t` and reload
- **SSL command wrapper:**
  - Mock certbot calls with fake success/failure

### 8.2 Integration Tests (local or CI)
- Use a throwaway NGINX config directory (e.g. `/tmp/nginx-test`) and mocked `NGINX_BIN` that writes logs instead of really reloading
- Validate:
  - `PUT /proxies/{droplet_name}`:
    - Writes file
    - Runs `nginx -t` (mock)
  - `DELETE /proxies/{droplet_name}`:
    - Removes file and symlink
  - **Error path:** `nginx -t` returns non-zero → response is error + no reload

### 8.3 Manual Acceptance

On dev/dedicated server with real NGINX:
1. Map `orchestrator.fullpotential.ai` DNS to server
2. Call `PUT /proxies/orchestrator` with upstream `localhost:8001`
3. Confirm HTTP works
4. Call `POST /proxies/orchestrator/ssl`
5. Confirm HTTPS works with valid cert

---

## 9. Deliverables
- **Repo:** `fpai-track-b/proxy-manager` (or similar)
- **Files:**
  - `app/main.py` – FastAPI app, routes, health
  - `app/models.py` – Pydantic models
  - `app/config.py` – Settings/env handling
  - `app/nginx_manager.py` – NGINX file + reload logic
  - `app/ssl_manager.py` – Certbot integration
  - `app/registry_client.py` – Optional Registry helper
  - `tests/` – Unit + integration tests
  - `Dockerfile` – Container for deployment
  - `SPEC_Proxy_Manager_API_v1.md` – this file
- **CI:**
  - pytest green
  - Basic lint (optional)
