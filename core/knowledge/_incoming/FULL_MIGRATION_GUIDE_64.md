# 🚀 Complete Migration: fullpotential.com + fullpotential.ai → .234

## Overview
Moving everything from outbounders.com server (.72) to your dedicated server (198.54.123.234):
- Email (james@fullpotential.com)
- fullpotential.com domain
- fullpotential.ai domain
- Membership platform

---

## Phase 1: Set Up Email Server on .234 ⏱️ 30 min

### Step 1: Run Email Setup Script
```bash
# SSH to server
ssh root@198.54.123.234

# Run setup script
cd /root/fpai-ops
./setup-email-server.sh
```

### Step 2: Create Email Password
```bash
# Generate password hash
dovecot pw -s SHA512-CRYPT
# Enter a strong password, copy the hash (starts with {SHA512-CRYPT}...)
```

### Step 3: Add Email User
```bash
# Replace {HASH} with the hash from step 2
echo 'james@fullpotential.com:{HASH}' > /etc/dovecot/users
chmod 600 /etc/dovecot/users

# Restart services
systemctl restart postfix
systemctl restart dovecot
systemctl enable postfix
systemctl enable dovecot
```

### Step 4: Test Email Server
```bash
# Test receiving (send email to yourself from another account)
# Check it arrived:
tail -f /var/log/mail.log

# Test IMAP access
telnet localhost 143
# Should see Dovecot ready message
```

---

## Phase 2: Configure DNS Records ⏱️ 15 min

### Current State
- Nameservers: ns1.outbounders.com, ns2.outbounders.com
- A record: fullpotential.com → old .72 server

### Option A: Change Nameservers (Recommended if you control .234 DNS)
**If you have cPanel/Plesk on .234:**
1. Set up DNS zone for fullpotential.com on .234
2. Update nameservers at registrar to point to .234 nameservers

### Option B: Keep Outbounders Nameservers, Update Records
**Update these records in outbounders.com control panel:**

```
# A Records (Point domains to new server)
fullpotential.com       A       198.54.123.234
*.fullpotential.com     A       198.54.123.234
fullpotential.ai        A       198.54.123.234
*.fullpotential.ai      A       198.54.123.234

# MX Records (Email routing)
fullpotential.com       MX  10  mail.fullpotential.com
mail.fullpotential.com  A       198.54.123.234

# TXT Records (Email security - add after testing)
fullpotential.com       TXT     "v=spf1 ip4:198.54.123.234 -all"
_dmarc.fullpotential.com TXT    "v=DMARC1; p=quarantine; rua=mailto:james@fullpotential.com"
```

**DNS Propagation:** Takes 1-24 hours (usually <1 hour)

---

## Phase 3: Configure Nginx for Both Domains ⏱️ 10 min

### Step 1: Create Nginx Config
```bash
ssh root@198.54.123.234

cat > /etc/nginx/sites-available/fullpotential << 'EOF'
# fullpotential.com - Main membership site
server {
    listen 80;
    listen [::]:80;
    server_name fullpotential.com www.fullpotential.com;

    # Redirect to HTTPS (will set up Let's Encrypt next)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name fullpotential.com www.fullpotential.com;

    # SSL certificates (placeholder - will get real certs)
    ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
    ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;

    # Proxy to Dashboard app
    location / {
        proxy_pass http://localhost:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# fullpotential.ai - System/infrastructure site
server {
    listen 80;
    listen [::]:80;
    server_name fullpotential.ai www.fullpotential.ai;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name fullpotential.ai www.fullpotential.ai;

    ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
    ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;

    # For now, redirect to fullpotential.com
    # Later: Point to system dashboard
    return 301 https://fullpotential.com$request_uri;
}

# Keep dashboard subdomain working
server {
    listen 80;
    server_name dashboard.fullpotential.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dashboard.fullpotential.com;

    ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
    ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;

    location / {
        proxy_pass http://localhost:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

### Step 2: Enable Config & Get SSL Certs
```bash
# Enable site
ln -sf /etc/nginx/sites-available/fullpotential /etc/nginx/sites-enabled/

# Test nginx config
nginx -t

# Install certbot if not already
apt install -y certbot python3-certbot-nginx

# Get SSL certificates for all domains
certbot --nginx -d fullpotential.com -d www.fullpotential.com \
                 -d fullpotential.ai -d www.fullpotential.ai \
                 -d dashboard.fullpotential.com

# Reload nginx
systemctl reload nginx
```

---

## Phase 4: Migrate Existing Emails (Optional) ⏱️ 15 min

### If you want to keep old emails:

```bash
# On OLD server (.72), export emails
ssh root@[OLD_SERVER_IP]
cd /var/mail/james
tar -czf james-emails.tar.gz Maildir/

# Transfer to new server
scp james-emails.tar.gz root@198.54.123.234:/tmp/

# On NEW server (.234), import emails
ssh root@198.54.123.234
cd /var/mail/vhosts/fullpotential.com/james
tar -xzf /tmp/james-emails.tar.gz
chown -R vmail:vmail /var/mail
```

---

## Phase 5: Update Gmail to Access New Server ⏱️ 5 min

### In Gmail Settings:
1. Go to Settings → Accounts → Add a mail account
2. **Email:** james@fullpotential.com
3. **Username:** james@fullpotential.com
4. **Password:** [password you set in Phase 1]
5. **IMAP Server:** 198.54.123.234
6. **Port:** 993
7. **Security:** SSL/TLS

### Or Update Existing Account:
- Settings → Accounts → Edit info → Change server to 198.54.123.234

---

## Phase 6: Test Everything ⏱️ 10 min

### Test Checklist:

```bash
# 1. Email sending
echo "Test from new server" | mail -s "Test" james@fullpotential.com

# 2. Email receiving
# Send email from external account (Gmail, etc.) to james@fullpotential.com
# Check it arrives

# 3. IMAP access
# Open Gmail app, should see new emails

# 4. Web access
curl https://fullpotential.com
curl https://fullpotential.ai
curl https://dashboard.fullpotential.com

# 5. SSL certificates
openssl s_client -connect fullpotential.com:443 -servername fullpotential.com
# Should show Let's Encrypt certificate
```

---

## 🎯 Migration Timeline

**Total Time: ~2 hours**

| Phase | Time | Can Do in Parallel |
|-------|------|-------------------|
| 1. Email Setup | 30 min | ✓ |
| 2. DNS Update | 15 min | ✓ (wait for propagation) |
| 3. Nginx Config | 10 min | ✓ |
| 4. Email Migration | 15 min | Optional |
| 5. Gmail Update | 5 min | After DNS |
| 6. Testing | 10 min | After all |

**Recommended Order:**
1. Set up email server on .234 (Phase 1)
2. Update DNS records (Phase 2) - then wait
3. Configure Nginx (Phase 3)
4. While DNS propagates, migrate emails (Phase 4)
5. Once DNS propagated, update Gmail (Phase 5)
6. Test everything (Phase 6)

---

## 🚨 Rollback Plan (If Something Goes Wrong)

### If email breaks:
```bash
# Point MX record back to old server temporarily
# In DNS: mail.fullpotential.com → [OLD_IP]
# Fix issue on new server
# Point back when ready
```

### If website breaks:
```bash
# Point A record back to old server
# In DNS: fullpotential.com → [OLD_IP]
# Debug nginx/app on new server
# Point back when ready
```

---

## 📋 Post-Migration Tasks

### Immediate (Within 24 hours):
- [ ] Monitor email delivery (/var/log/mail.log)
- [ ] Test sending to various providers (Gmail, Outlook, etc.)
- [ ] Verify SSL certificates renewed automatically

### Within 1 week:
- [ ] Set up DKIM signing (improves email deliverability)
- [ ] Configure SPF/DMARC records
- [ ] Set up email backups
- [ ] Monitor server resources

### Within 1 month:
- [ ] Consider moving to external email service (Google Workspace/Fastmail)
- [ ] Set up monitoring/alerts for email server
- [ ] Document email admin procedures

---

## 🎉 Success Criteria

✅ Can send email from james@fullpotential.com
✅ Can receive email at james@fullpotential.com
✅ Gmail app connects and syncs
✅ fullpotential.com shows membership platform (HTTPS)
✅ fullpotential.ai accessible (HTTPS)
✅ dashboard.fullpotential.com still works
✅ No email lost during migration

---

**Ready to migrate? Start with Phase 1!**

🌐⚡💎
