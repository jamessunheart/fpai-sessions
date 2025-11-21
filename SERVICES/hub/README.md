# Full Potential Hub - Main Landing Page

**Central directory for all Full Potential services**

## What This Is

The main hub serves as the central landing page for fullpotential.com, directing visitors to all Full Potential services:
- I MATCH Marketplace
- Personal Coaching (White Rock Ministry)
- Treasury Optimization
- AI Services
- Church Community
- About Us

## Features

- Beautiful gradient design
- Services grid with 6 services
- Status badges (Live, Coming Soon)
- Detailed service descriptions
- Clear CTAs to each service
- Responsive design
- Professional corporate structure

## Local Development

### 1. Install Dependencies

```bash
pip install fastapi uvicorn
```

### 2. Run Server

```bash
cd /Users/jamessunheart/Development/SERVICES/hub
python main.py
```

Server runs on: `http://localhost:8500`

## Deployment to Production

### Option 1: Direct Deployment (Recommended)

1. Deploy hub service to server:
```bash
scp -r /Users/jamessunheart/Development/SERVICES/hub root@198.54.123.234:/opt/fpai/
```

2. Create systemd service:
```bash
ssh root@198.54.123.234

cat > /etc/systemd/system/fpai-hub.service << 'EOF'
[Unit]
Description=Full Potential Hub - Main Landing Page
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/hub
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8500
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable fpai-hub
systemctl start fpai-hub
systemctl status fpai-hub
```

3. Update Nginx configuration:
```bash
# Edit fullpotential.com nginx config
nano /etc/nginx/sites-available/fullpotential.com
```

Add this configuration:
```nginx
server {
    server_name fullpotential.com www.fullpotential.com;

    # Main hub (NEW - serves root)
    location / {
        proxy_pass http://localhost:8500;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # I MATCH Marketplace (existing)
    location /match {
        proxy_pass http://localhost:8401;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # White Rock Coaching (moved to /coaching)
    location /coaching {
        proxy_pass http://localhost:8000;  # Current fullpotential.com
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Treasury (future)
    location /treasury {
        proxy_pass http://localhost:8600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # AI Services (future)
    location /ai {
        proxy_pass http://localhost:8700;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Church (future)
    location /church {
        proxy_pass http://localhost:8800;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # SSL configuration (existing)
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/fullpotential.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fullpotential.com/privkey.pem;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name fullpotential.com www.fullpotential.com;
    return 301 https://$server_name$request_uri;
}
```

4. Test and reload Nginx:
```bash
nginx -t
systemctl reload nginx
```

5. Verify:
```bash
curl http://localhost:8500/health
curl https://fullpotential.com
```

### Option 2: Phased Rollout

If you want to test before making hub the root:

1. Deploy hub to `/hub` path first:
```nginx
location /hub {
    proxy_pass http://localhost:8500;
}
```

2. Test at `https://fullpotential.com/hub`

3. Once satisfied, move to root (`/`) as shown in Option 1

## Migration Checklist

### Pre-Migration
- [ ] Backup current nginx config
- [ ] Deploy hub service to server
- [ ] Test hub at localhost:8500
- [ ] Prepare redirect rules

### Migration
- [ ] Update nginx config
- [ ] Move White Rock to /coaching
- [ ] Make hub serve root /
- [ ] Test all paths
- [ ] Reload nginx

### Post-Migration
- [ ] Test fullpotential.com (should show hub)
- [ ] Test fullpotential.com/coaching (White Rock)
- [ ] Test fullpotential.com/match (I MATCH)
- [ ] Monitor analytics
- [ ] Update sitemap
- [ ] Notify users if needed

## Service URLs After Migration

| Service | Old URL | New URL |
|---------|---------|---------|
| **Hub** | N/A | https://fullpotential.com |
| **White Rock Coaching** | https://fullpotential.com | https://fullpotential.com/coaching |
| **I MATCH** | https://fullpotential.com/match | https://fullpotential.com/match |
| **Treasury** | N/A | https://fullpotential.com/treasury |
| **AI** | N/A | https://fullpotential.com/ai |
| **Church** | N/A | https://fullpotential.com/church |

## Redirects for Old URLs

Add these to nginx to redirect old coaching URLs:

```nginx
# Redirect old coaching paths
rewrite ^/sessions /coaching/sessions permanent;
rewrite ^/membership /coaching/membership permanent;
rewrite ^/login /coaching/login permanent;
rewrite ^/dashboard /coaching/dashboard permanent;
```

## Architecture Overview

```
fullpotential.com (Nginx)
  │
  ├── / → Hub (port 8500)
  ├── /coaching → White Rock (port 8000)
  ├── /match → I MATCH (port 8401)
  ├── /treasury → Treasury (port 8600)
  ├── /ai → AI Services (port 8700)
  └── /church → Church (port 8800)
```

## Support

For issues or questions:
- Check logs: `journalctl -u fpai-hub -f`
- Verify service: `systemctl status fpai-hub`
- Test endpoint: `curl http://localhost:8500/health`

---

🌐⚡💎 **Full Potential Hub - Infrastructure for Human Flourishing**
