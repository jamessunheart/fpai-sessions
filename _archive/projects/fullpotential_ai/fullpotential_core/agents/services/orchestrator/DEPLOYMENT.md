# Orchestrator Deployment Guide

## Prerequisites on Server

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Install NGINX (if not already installed)
sudo apt-get install nginx

# Install Git
sudo apt-get install git
```

## Deployment Steps

### 1. Push Code to Server

**Option A: Direct Git Push (Recommended)**
```bash
# On your local machine, push to your Git remote
git add .
git commit -m "Production-ready Orchestrator v1.1 with optimizations"
git push origin main

# On the server
cd /opt/fpai
git clone https://github.com/yourusername/orchestrator.git
# OR if already cloned:
cd /opt/fpai/orchestrator
git pull origin main
```

**Option B: SCP/rsync**
```bash
# From local machine
rsync -avz --exclude .venv --exclude .git --exclude __pycache__ \
  ~/Development/orchestrator/ user@your-server:/opt/fpai/orchestrator/
```

### 2. Configure Environment Variables

```bash
# On server
cd /opt/fpai/orchestrator

# Create .env file
cat > .env <<EOF
# Service
ENVIRONMENT=production
LOG_LEVEL=INFO

# Registry
REGISTRY_URL=http://registry:8000
CACHE_DIR=/var/cache/fpai
REGISTRY_SYNC_INTERVAL=60
REGISTRY_TIMEOUT=5.0

# Tasks
TASK_TIMEOUT=30
TASK_MAX_RETRIES=3
TASK_MAX_HISTORY=10000

# Server
HOST=0.0.0.0
PORT=8001
EOF
```

### 3. Build and Start Container

```bash
# Build the image
docker compose build orchestrator

# Start the service
docker compose up -d orchestrator

# Check logs
docker compose logs -f orchestrator

# Verify it's running
docker compose ps
```

### 4. Configure NGINX Reverse Proxy

```bash
# Create NGINX config
sudo nano /etc/nginx/sites-available/orchestrator.conf
```

Add this configuration:

```nginx
# Orchestrator reverse proxy
server {
    listen 80;
    server_name b.fullpotential.ai;  # Replace with your domain

    # Orchestrator endpoints
    location /orchestrator/ {
        proxy_pass http://127.0.0.1:8001/orchestrator/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Extended timeouts for long-running tasks
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Health check (no /orchestrator prefix)
    location /health {
        proxy_pass http://127.0.0.1:8001/orchestrator/health;
        proxy_set_header Host $host;
    }
}
```

Enable the site:
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/orchestrator.conf /etc/nginx/sites-enabled/

# Test NGINX config
sudo nginx -t

# Reload NGINX
sudo systemctl reload nginx
```

### 5. Verify Deployment

```bash
# Test internal endpoint
curl http://localhost:8001/orchestrator/health

# Test external endpoint (through NGINX)
curl http://b.fullpotential.ai/orchestrator/health

# Check all endpoints
curl http://b.fullpotential.ai/orchestrator/info
curl http://b.fullpotential.ai/orchestrator/droplets
curl http://b.fullpotential.ai/orchestrator/metrics

# Submit a test task
curl -X POST http://b.fullpotential.ai/orchestrator/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "droplet_name": "registry",
    "method": "GET",
    "path": "/health"
  }'
```

### 6. Monitor and Maintain

```bash
# View logs
docker compose logs -f orchestrator

# View last 100 lines
docker compose logs --tail=100 orchestrator

# Restart service
docker compose restart orchestrator

# Stop service
docker compose stop orchestrator

# Update deployment
git pull origin main
docker compose build orchestrator
docker compose up -d orchestrator
```

## Production Checklist

- [ ] Code pushed to Git repository
- [ ] Environment variables configured in `.env`
- [ ] Docker container built and running
- [ ] NGINX reverse proxy configured
- [ ] Health endpoint returns 200
- [ ] Can reach `/orchestrator/health` externally
- [ ] Registry connection working (check `/orchestrator/droplets`)
- [ ] Metrics endpoint accessible
- [ ] Test task submission works
- [ ] Logs are being written
- [ ] Docker container set to restart automatically (`restart: unless-stopped`)

## Rollback Procedure

If something goes wrong:

```bash
# Stop new version
docker compose stop orchestrator

# Revert to previous code
git checkout <previous-commit-hash>

# Rebuild and restart
docker compose build orchestrator
docker compose up -d orchestrator
```

## SSL/HTTPS Setup (Optional but Recommended)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d b.fullpotential.ai

# Certbot will automatically update NGINX config
# Auto-renewal is configured by default
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker compose logs orchestrator

# Check if port is already in use
sudo lsof -i :8001

# Verify environment variables
docker compose config
```

### Can't reach through NGINX
```bash
# Check NGINX error logs
sudo tail -f /var/log/nginx/error.log

# Verify NGINX is running
sudo systemctl status nginx

# Test direct connection
curl http://localhost:8001/orchestrator/health
```

### Registry connection failing
```bash
# Ensure Registry container is running
docker compose ps registry

# Check Registry is accessible from Orchestrator
docker compose exec orchestrator curl http://registry:8000/health

# Check firewall rules
sudo ufw status
```

## Performance Tuning

### Docker Resource Limits
Edit `docker-compose.yml`:
```yaml
orchestrator:
  # ... existing config ...
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '0.5'
        memory: 512M
```

### NGINX Worker Processes
Edit `/etc/nginx/nginx.conf`:
```nginx
worker_processes auto;
worker_connections 1024;
```

## Backup Strategy

```bash
# Backup cache directory
sudo tar -czf orchestrator-cache-$(date +%Y%m%d).tar.gz /var/cache/fpai/

# Backup logs
docker compose logs orchestrator > orchestrator-logs-$(date +%Y%m%d).log
```
