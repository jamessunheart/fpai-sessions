# Quick Deployment Reference

## 🚀 Deploy to Server (3 Steps)

### 1️⃣ Push Code to Server
```bash
# On local machine
git add .
git commit -m "Deploy Orchestrator v1.1"
git push origin main

# On server
ssh user@b.fullpotential.ai
cd /opt/fpai/orchestrator
git pull origin main
```

### 2️⃣ Deploy with Script
```bash
# On server
./deploy.sh production
```

That's it! The script automatically:
- ✅ Runs tests
- ✅ Builds Docker image
- ✅ Stops old container
- ✅ Starts new container
- ✅ Runs health checks
- ✅ Shows logs

### 3️⃣ Verify External Access
```bash
# Test through NGINX
curl http://b.fullpotential.ai/orchestrator/health
```

---

## 📋 Common Commands

### View Logs
```bash
docker compose logs -f orchestrator          # Follow logs
docker compose logs --tail=100 orchestrator  # Last 100 lines
```

### Restart Service
```bash
docker compose restart orchestrator
```

### Check Status
```bash
docker compose ps orchestrator
curl http://localhost:8001/orchestrator/health
```

### Update Deployment
```bash
git pull origin main
./deploy.sh production
```

### Rollback
```bash
git log --oneline                  # Find previous commit
git checkout <commit-hash>
./deploy.sh production
```

---

## 🔧 Manual Deployment (Without Script)

```bash
# 1. Build
docker compose build orchestrator

# 2. Start
docker compose up -d orchestrator

# 3. Check
curl http://localhost:8001/orchestrator/health
docker compose logs orchestrator
```

---

## 🆘 Troubleshooting

### Container won't start
```bash
docker compose logs orchestrator
docker compose down && docker compose up -d orchestrator
```

### Can't reach through NGINX
```bash
# Check NGINX logs
sudo tail -f /var/log/nginx/error.log

# Test direct connection
curl http://localhost:8001/orchestrator/health

# Reload NGINX
sudo nginx -t && sudo systemctl reload nginx
```

### Registry not connecting
```bash
# Check Registry is running
docker compose ps registry

# Test connection from Orchestrator
docker compose exec orchestrator curl http://registry:8000/health
```

---

## 📊 Monitoring

### Check Metrics
```bash
curl http://localhost:8001/orchestrator/metrics | jq
```

### Check Task Status
```bash
curl http://localhost:8001/orchestrator/tasks | jq
```

### Check Droplets
```bash
curl http://localhost:8001/orchestrator/droplets | jq
```

---

## 🔐 Production Tips

1. **Always test locally first:**
   ```bash
   ./deploy.sh development
   ```

2. **Use SSL in production:**
   ```bash
   sudo certbot --nginx -d b.fullpotential.ai
   ```

3. **Monitor disk usage:**
   ```bash
   du -sh /var/cache/fpai/
   docker system df
   ```

4. **Backup before updates:**
   ```bash
   docker compose logs orchestrator > backup-$(date +%Y%m%d).log
   sudo tar -czf cache-backup-$(date +%Y%m%d).tar.gz /var/cache/fpai/
   ```

5. **Set up log rotation:**
   ```bash
   # Add to /etc/logrotate.d/orchestrator
   /var/lib/docker/containers/*/*.log {
       rotate 7
       daily
       compress
       missingok
   }
   ```
