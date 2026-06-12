# Multi-Cloud Droplet Manager — Quick Ops Doc

Base URL (default): `http://localhost:8010`  
Auth header for all requests:
```
-H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1"
```

## 1) Environment (.env)

```env
# App
API_TOKEN=secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1
PORT=8010

# Optional: Heartbeat to Core/Orchestrator (safe to omit)
HEARTBEAT_URL=https://drop1.fullpotential.ai/registry/heartbeat
HEARTBEAT_KEY=test123
HEARTBEAT_ID=do-multi-manager
HEARTBEAT_INTERVAL=60

# Optional: Core Registry Register endpoint (safe to omit)
REGISTRY_URL=https://drop1.fullpotential.ai/registry/register
REGISTRY_KEY=test123

# Optional: Airtable (only if you still want local logging)
AIRTABLE_TOKEN=pat_*********************
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXXX
AIRTABLE_EVENTS_TABLE=tbl_events_or_name
AIRTABLE_LOGS_TABLE=tbl_logs_or_name

# DigitalOcean
DO_TOKEN=dop_v1_************************

# Hetzner
HETZNER_TOKEN=htz_************************

# Vultr
VULTR_TOKEN=vl_***************************
```

Notes
- Leave Airtable vars blank if you’re skipping Airtable (per James).
- Heartbeat/Registry are optional. If unset, the service simply skips them.

---

## 2) Health check

```bash
curl -s http://localhost:8010/health | jq .
```

# List all routes your service exposes
curl -s http://localhost:8010/openapi.json | jq '.paths | keys[]'


---

## 3) DigitalOcean

### List
```bash
curl -s http://localhost:8010/do/list \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" | jq .
```

### Create (register)
Minimal with SSH keys:
```bash
curl -s -X POST http://localhost:8010/do/register \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" -H "Content-Type: application/json" \
  -d '{
    "name": "do-poc-1",
    "region": "sfo3",
    "size": "s-1vcpu-1gb",
    "image": "ubuntu-22-04-x64",
    "ssh_keys": [51739658]
  }' | jq .
```

No SSH key, set root password via cloud-init:
```bash
curl -s -X POST http://localhost:8010/do/register \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" -H "Content-Type: application/json" \
  -d '{
    "name": "do-poc-pass",
    "region": "sfo3",
    "size": "s-1vcpu-1gb",
    "image": "ubuntu-22-04-x64",
    "user_data": "#cloud-config\nchpasswd:\n  list: |\n    root:W7taBbzeJku$h\n  expire: False"
  }' | jq .
```

### Power actions
```bash
# reboot | power_off | power_on
curl -s -X POST "http://localhost:8010/do/action/<DROPLET_ID>?action=reboot" \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" | jq .
```

### Delete
```bash
curl -s -X DELETE http://localhost:8010/do/delete/<DROPLET_ID> \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" | jq .
```

---

## 4) Hetzner

### List
```bash
curl -s http://localhost:8010/hetzner/list \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" | jq .
```

### Create (register)
```bash
curl -s -X POST http://localhost:8010/hetzner/register \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" -H "Content-Type: application/json" \
  -d '{
    "name": "hetzner-poc-1",
    "region": "fsn1",
    "size": "cpx11",
    "image": "ubuntu-22.04",
    "user_data": "#cloud-config\nruncmd:\n - echo hetzner > /root/hello.txt"
  }' | jq .
```

### Power actions
```bash
# reboot | power_off | power_on
curl -s -X POST "http://localhost:8010/hetzner/action/<SERVER_ID>?action=power_off" \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" | jq .
```

### Delete
```bash
curl -s -X DELETE http://localhost:8010/hetzner/delete/<SERVER_ID> \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" | jq .
```

---

## 5) Vultr

### List
```bash
curl -s http://localhost:8010/vultr/list \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" | jq .
```

### Create (register)
Example payload (use values valid for your Vultr account/region):
```bash
curl -s -X POST http://localhost:8010/vultr/register \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "vultr-poc-pass",
    "region": "sea",
    "size": "vc2-1c-1gb",
    "image": "1743",
    "user_data": "#cloud-config\nchpasswd:\n  list: |\n    root:W7taBbzeJku$h\n  expire: False"
  }' | jq .

```

### Power actions
```bash
# reboot | power_off | power_on
curl -s -X POST "http://localhost:8010/vultr/action/<INSTANCE_ID>?action=reboot" \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" | jq .
```

### Delete
```bash
curl -s -X DELETE http://localhost:8010/vultr/delete/<INSTANCE_ID> \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" | jq .
```

> Tip: Exact `size/plan`, `image`, and `region` values vary by account. If a create call returns 4xx, check the provider’s console for the valid slugs/IDs and plug them in.

---

## 6) Unified multi-cloud list (for the dashboard)

```bash
curl -s http://localhost:8010/multi/list \
  -H "Authorization: Bearer secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1" | jq .
```

This returns a JSON object with `do`, `hetzner`, and `vultr` arrays when each provider is configured. Hamza’s dashboard can consume this directly.

---

## 7) Heartbeat & Registry quick tests

### Heartbeat (server sends this in background if configured)
To simulate a manual heartbeat:
```bash
curl -i -L -X POST "https://drop1.fullpotential.ai/registry/heartbeat" \
  -H "X-Registry-Key: test123" \
  -H "Content-Type: application/json" \
  -d '{"id": "do-multi-manager"}'
```

### Registry register (optional, on create)
```bash
curl -i -L -X POST "https://drop1.fullpotential.ai/registry/register" \
  -H "X-Registry-Key: test123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "poc-sync-test",
    "fqdn": "poc-sync-test.fullpotential.ai",
    "ip": "1.2.3.4",
    "role": "api",
    "env": "dev",
    "version": "2025.11.1",
    "cost_hour": 0.02
  }'
```
If you see `{"error":"attempt to write a readonly database"}`, that’s on the server side. Share it with the team; your request is fine.

---

## 8) Common errors and fixes

- `{"detail":"<provider> not configured"}`  
  The provider token is missing in `.env`.

- DO returns 422 at create  
  Often invalid `region/size/image` or droplet limit reached.

- 403 on delete/action  
  Token lacks permissions for that project/resource.

- Airtable not writing  
  Skip Airtable unless explicitly requested. If you do use it, the token must have base access and the table names/IDs must match.

---






docker stop do-multi && docker rm do-multi
docker build -t do-multi:latest .
docker run -d --name do-multi --restart=always \
  --env-file .env -p 8010:8010 do-multi:latest

