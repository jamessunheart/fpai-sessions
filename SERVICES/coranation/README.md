# Cora Nation - Church of Consciousness Community Hub

**Private Member Association & 508(c)(1)(a) Tax-Exempt Church**

---

## What This Is

Cora Nation is the community hub for:
- **Private Member Association** (PMA) - Cora Nation
- **Church of Consciousness** - 508(c)(1)(a) tax-exempt church
- **White Rock Ministry** - Church guidance arm
- **Conscious Circulation** - Philosophy and practice

## Features

- Beautiful spiritual/community design (gold consciousness theme)
- Philosophy of conscious circulation
- Community offerings and benefits
- Church information
- Membership portal (coming)
- Donation system (coming)
- Links to Full Potential services

## Local Development

### 1. Install Dependencies

```bash
pip install fastapi uvicorn
```

### 2. Run Server

```bash
cd /Users/jamessunheart/Development/SERVICES/coranation
python main.py
```

Server runs on: `http://localhost:8900`

## Production Deployment

### 1. Deploy to Server

```bash
scp -r /Users/jamessunheart/Development/SERVICES/coranation root@198.54.123.234:/opt/fpai/
```

### 2. Create Systemd Service

```bash
ssh root@198.54.123.234

cat > /etc/systemd/system/fpai-coranation.service << 'EOF'
[Unit]
Description=Cora Nation - Church of Consciousness Community Hub
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/coranation
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8900
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable fpai-coranation
systemctl start fpai-coranation
systemctl status fpai-coranation
```

### 3. Configure Nginx

Create `/etc/nginx/sites-available/coranation.org`:

```nginx
server {
    server_name coranation.org www.coranation.org;

    location / {
        proxy_pass http://127.0.0.1:8900;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSL will be added by certbot
    listen 80;
}

# HTTP to HTTPS redirect (after SSL)
# Uncomment after getting SSL certificate
# server {
#     listen 80;
#     server_name coranation.org www.coranation.org;
#     return 301 https://$server_name$request_uri;
# }
```

Enable the site:

```bash
ln -s /etc/nginx/sites-available/coranation.org /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### 4. Get SSL Certificate

```bash
certbot --nginx -d coranation.org -d www.coranation.org
```

### 5. Configure DNS at Namecheap

**Domain:** coranation.org

**DNS Records to Add:**

```
Type    Host    Value                   TTL
A       @       198.54.123.234         Automatic
A       www     198.54.123.234         Automatic
```

**How to Update:**
1. Go to Namecheap Dashboard
2. Click "Manage" next to coranation.org
3. Go to "Advanced DNS" tab
4. Add the two A records above
5. Wait 5-30 minutes for DNS propagation

### 6. Verify Deployment

```bash
# Test local
curl http://localhost:8900/health

# Test domain (after DNS propagates)
curl http://coranation.org
curl https://coranation.org
```

## Architecture

```
coranation.org (Nginx)
  │
  └── / → Cora Nation Hub (port 8900)
      ├── Homepage (community, philosophy, church)
      ├── /membership → Membership application (coming)
      ├── /donate → Donation portal (coming)
      ├── /portal → Member portal (coming)
      └── Links to:
          ├── fullpotential.com (services)
          └── whiterock.us (ministry)
```

## Complete Ecosystem

```
┌─────────────────────────────────────────┐
│  TIER 1: SPIRITUAL/COMMUNITY            │
│  • coranation.org (THIS SITE)           │
│  • whiterock.us (ministry)              │
└─────────────────────────────────────────┘
                    ↓
         Benefits from revenues
                    ↓
┌─────────────────────────────────────────┐
│  TIER 2: ASSET HOLDING                  │
│  • Sunheart Private Trust (private)     │
└─────────────────────────────────────────┘
                    ↑
           Receives profits
                    ↑
┌─────────────────────────────────────────┐
│  TIER 3: OPERATING SERVICES             │
│  • fullpotential.com (services hub)     │
└─────────────────────────────────────────┘
```

## Port Assignments

- **8900** - Cora Nation (coranation.org)
- **8500** - Full Potential Hub (fullpotential.com)
- **8401** - I MATCH (fullpotential.com/match)
- **8006** - White Rock Coaching (fullpotential.com/coaching)

## Future Enhancements

### Phase 1 (Weeks 1-2) ✅
- [x] Beautiful homepage
- [x] Philosophy section
- [x] Church information
- [x] Basic deployment

### Phase 2 (Weeks 3-4)
- [ ] Membership application form
- [ ] Donation processing (Stripe)
- [ ] Member portal authentication
- [ ] Event calendar

### Phase 3 (Month 2)
- [ ] Community forums
- [ ] Member directory
- [ ] Impact reporting
- [ ] Email newsletters

## Support

For issues or questions:
- Check logs: `journalctl -u fpai-coranation -f`
- Verify service: `systemctl status fpai-coranation`
- Test endpoint: `curl http://localhost:8900/health`

---

🌐⚡💎 **Cora Nation - Conscious Circulation for Human Flourishing**
