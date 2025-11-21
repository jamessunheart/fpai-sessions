# 🎛️ Dashboard Structure

**Last Updated:** 2025-11-15
**Status:** ✅ PRODUCTION

---

## 🌐 Path-Based Dashboard Architecture

All dashboards are now organized under a unified path structure to prevent conflicts and enable easy expansion.

### Base URL
```
https://fullpotential.com/dashboard/
```

---

## 📍 Current Dashboards

### 1. Dashboard Hub
**URL:** https://fullpotential.com/dashboard/

Landing page that lists all available dashboards with descriptions and quick access links.

**Features:**
- Auto-generated dashboard directory
- Visual card-based interface
- Direct links to all dashboards
- Status indicators

### 2. Coordination Dashboard (Visual)
**URL:** https://fullpotential.com/dashboard/coordination

**Backend Port:** 8031
**Service:** `coordination-dashboard.service`
**Refresh Rate:** 3 seconds

Real-time visualization of Claude Code multi-session coordination:
- Animated session cards with pulse effects
- Server health monitoring (6 ports)
- Active/idle session tracking
- Registered vs unregistered sessions
- Git status tracking
- WebSocket support for live updates

### 3. Coordination Dashboard (Simple)
**URL:** https://fullpotential.com/dashboard/coordination-simple

**Backend Port:** 8030
**Service:** `coordination-simple.service`
**Refresh Rate:** 5 seconds

Lightweight tabular view:
- Minimal UI for quick checks
- Session table with all details
- Server status grid
- Lower resource usage

---

## 🏗️ Adding New Dashboards

To add a new dashboard category:

### 1. Deploy Your Dashboard Service

```bash
# Deploy to server on a unique port (e.g., 8032)
scp -r /path/to/dashboard root@198.54.123.234:/opt/dashboards/[name]

# Create systemd service
cat > /tmp/[name]-dashboard.service << EOF
[Unit]
Description=[Name] Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/dashboards/[name]
ExecStart=/usr/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

scp /tmp/[name]-dashboard.service root@198.54.123.234:/etc/systemd/system/
ssh root@198.54.123.234 "systemctl enable [name]-dashboard && systemctl start [name]-dashboard"
```

### 2. Update Nginx Configuration

Add to `/etc/nginx/sites-available/fullpotential.com`:

```nginx
# [Name] Dashboard
location /dashboard/[name]/ {
    rewrite ^/dashboard/[name]/(.*) /$1 break;
    proxy_pass http://127.0.0.1:[PORT];
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}

location = /dashboard/[name] {
    proxy_pass http://127.0.0.1:[PORT]/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### 3. Update Dashboard Hub

Edit the hub's HTML in the nginx config to add a new card:

```html
<div class="dashboard-card">
    <span class="status">LIVE</span>
    <h2>[Dashboard Name]</h2>
    <p>[Description of what this dashboard does]</p>
    <a href="/dashboard/[name]">Open Dashboard →</a>
</div>
```

### 4. Test and Deploy

```bash
# Test nginx config
nginx -t

# Reload nginx
systemctl reload nginx

# Test access
curl https://fullpotential.com/dashboard/[name]
```

---

## 🔧 Port Allocations

| Dashboard | Port | Service Name | Status |
|-----------|------|--------------|--------|
| Coordination (Visual) | 8031 | coordination-dashboard | ✅ Running |
| Coordination (Simple) | 8030 | coordination-simple | ✅ Running |
| [Future Dashboard] | 8032+ | TBD | 📋 Available |

**Port Range:** 8030-8099 reserved for dashboards

---

## 📊 Architecture Benefits

### Path-Based Routing
✅ **No DNS conflicts** - All under one domain
✅ **Easy to remember** - Consistent URL structure
✅ **Scalable** - Add unlimited dashboards
✅ **SSL by default** - Inherits fullpotential.com certificate

### Hub Page
✅ **Discoverability** - Single place to find all dashboards
✅ **Documentation** - Built-in descriptions
✅ **User-friendly** - Visual cards vs URL guessing

### Service Management
✅ **Systemd services** - Auto-start on boot
✅ **Auto-recovery** - Services restart on failure
✅ **Centralized logs** - journalctl for all dashboards
✅ **Resource limits** - Can be configured per service

---

## 🛡️ Security

All dashboards:
- ✅ HTTPS enforced via nginx
- ✅ SSL certificate (Let's Encrypt)
- ✅ Proxy headers for real IP tracking
- ✅ WebSocket support for real-time updates
- ⚠️ Currently no authentication (consider adding)

---

## 📝 Examples

```bash
# Access dashboard hub
open https://fullpotential.com/dashboard/

# Access specific dashboards
open https://fullpotential.com/dashboard/coordination
open https://fullpotential.com/dashboard/coordination-simple

# Check dashboard service status
ssh root@198.54.123.234 "systemctl status coordination-dashboard"

# View dashboard logs
ssh root@198.54.123.234 "journalctl -u coordination-dashboard -f"

# Restart a dashboard
ssh root@198.54.123.234 "systemctl restart coordination-dashboard"
```

---

## 🎯 Future Dashboards

Potential additions:
- `/dashboard/analytics` - Business metrics
- `/dashboard/treasury` - Financial tracking
- `/dashboard/deployment` - CI/CD status
- `/dashboard/health` - System health monitoring
- `/dashboard/users` - User activity
- `/dashboard/revenue` - Revenue dashboard

Each can be added independently without affecting existing dashboards!

---

**Generated:** 2025-11-15 20:30 UTC
**Architecture:** Path-based nginx reverse proxy
**Domain:** fullpotential.com
