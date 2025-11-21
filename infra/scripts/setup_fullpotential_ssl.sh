#!/bin/bash
# One-command setup for fullpotential.ai with SSL

set -e

echo "🌐 Setting up fullpotential.ai with SSL..."

# Step 1: Create nginx config
echo "📝 Creating nginx config..."
cat > /etc/nginx/sites-available/fullpotential.ai << 'ENDCONFIG'
server {
    listen 80;
    server_name fullpotential.ai www.fullpotential.ai;

    location / {
        proxy_pass http://localhost:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
ENDCONFIG

# Step 2: Enable the site
echo "✅ Enabling site..."
ln -sf /etc/nginx/sites-available/fullpotential.ai /etc/nginx/sites-enabled/fullpotential.ai

# Step 3: Test and reload nginx
echo "🔧 Testing nginx..."
nginx -t
systemctl reload nginx

# Step 4: Test HTTP
echo "🧪 Testing HTTP..."
curl -I http://fullpotential.ai | head -1

# Step 5: Install SSL
echo "🔒 Installing SSL certificate..."
certbot --nginx -d fullpotential.ai -d www.fullpotential.ai \
  --non-interactive \
  --agree-tos \
  --email james@fullpotential.com \
  --redirect

# Step 6: Test HTTPS
echo "✨ Testing HTTPS..."
curl -I https://fullpotential.ai | head -1

echo ""
echo "🎉 Done! fullpotential.ai is now live with HTTPS!"
echo "🌐 Visit: https://fullpotential.ai"
