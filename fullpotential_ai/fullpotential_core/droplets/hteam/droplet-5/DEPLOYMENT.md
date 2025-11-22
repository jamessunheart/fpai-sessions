# Deployment Guide - Droplet #5 Dashboard

## 🚀 Quick Deploy on VPS

### Option 1: Automated Script (Recommended)

```bash
# SSH into your VPS
ssh root@drop5.fullpotential.ai

# Navigate to project directory
cd /path/to/droplet-5

# Run deployment script
chmod +x deploy.sh
./deploy.sh
```

### Option 2: Manual Steps

```bash
# SSH into your VPS
ssh root@drop5.fullpotential.ai

# Navigate to project directory
cd /path/to/droplet-5

# Pull latest code
git pull origin main

# Stop containers
docker-compose down

# Rebuild with no cache (forces fresh build)
docker-compose build --no-cache

# Start containers
docker-compose up -d

# Check logs
docker-compose logs -f
```

---

## 🔍 Verify Deployment

### Check Container Status
```bash
docker-compose ps
```

Expected output:
```
NAME                COMMAND                  SERVICE             STATUS              PORTS
droplet-5-app-1     "docker-entrypoint.s…"   app                 running             0.0.0.0:3000->3000/tcp
```

### Check Logs
```bash
# Follow logs in real-time
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100
```

### Test Endpoints
```bash
# Health check
curl http://localhost:3000/health

# Multi-cloud API (should fetch fresh token)
curl http://localhost:3000/api/multi-cloud?endpoint=/multi/list
```

---

## 🐛 Troubleshooting

### Container won't start
```bash
# Check Docker logs
docker-compose logs app

# Check if port 3000 is in use
netstat -tulpn | grep 3000

# Kill process using port 3000
kill -9 $(lsof -t -i:3000)
```

### Old code still running
```bash
# Force remove all containers and images
docker-compose down --rmi all --volumes --remove-orphans

# Rebuild from scratch
docker-compose build --no-cache
docker-compose up -d
```

### Environment variables not loading
```bash
# Check .env file exists
ls -la .env

# Restart containers to reload env
docker-compose restart
```

### Multi-cloud showing empty data
```bash
# Check if REGISTRY_API_KEY is set
docker-compose exec app printenv | grep REGISTRY

# Test token fetching manually
curl -X POST "https://drop18.fullpotential.ai/auth/token?droplet_id=drop4.fullpotential.ai" \
  -H "X-Registry-Key: YOUR_REGISTRY_KEY"
```

---

## 📦 Docker Commands Reference

### View running containers
```bash
docker ps
```

### Stop all containers
```bash
docker-compose down
```

### Start containers
```bash
docker-compose up -d
```

### Restart containers
```bash
docker-compose restart
```

### View logs
```bash
docker-compose logs -f
```

### Execute command in container
```bash
docker-compose exec app sh
```

### Remove all stopped containers
```bash
docker system prune -a
```

---

## 🔄 CI/CD Setup (Optional)

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to VPS

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to VPS
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /path/to/droplet-5
            git pull origin main
            docker-compose down
            docker-compose build --no-cache
            docker-compose up -d
```

Add secrets in GitHub:
- `VPS_HOST`: Your VPS IP or domain
- `VPS_USER`: SSH username (usually `root`)
- `VPS_SSH_KEY`: Your private SSH key

---

## 🎯 Post-Deployment Checklist

- [ ] Container is running (`docker-compose ps`)
- [ ] Health endpoint responds (`curl http://localhost:3000/health`)
- [ ] Multi-cloud page loads with data
- [ ] Dashboard shows all droplets
- [ ] Sprints page displays data
- [ ] Dark/light mode works
- [ ] No errors in logs (`docker-compose logs`)

---

## 🔐 Security Notes

1. **Never commit .env file** - It contains sensitive keys
2. **Use SSH keys** - Don't use password authentication
3. **Keep Docker updated** - Run `docker --version` and update if needed
4. **Monitor logs** - Check for suspicious activity
5. **Backup regularly** - Keep backups of .env and data

---

## 📊 Monitoring

### Check resource usage
```bash
docker stats
```

### Check disk space
```bash
df -h
```

### Check memory usage
```bash
free -h
```

### Check Docker disk usage
```bash
docker system df
```

---

## 🆘 Emergency Rollback

If new deployment breaks:

```bash
# Stop current version
docker-compose down

# Checkout previous commit
git log --oneline  # Find previous commit hash
git checkout <previous-commit-hash>

# Rebuild and start
docker-compose build --no-cache
docker-compose up -d
```

---

**Last Updated**: 2025-01-14  
**Docker Version**: 24.0+  
**Docker Compose Version**: 2.0+
