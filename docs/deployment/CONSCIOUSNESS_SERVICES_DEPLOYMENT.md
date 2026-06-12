# Consciousness Services Deployment Guide

**Last Updated:** 2025-12-10  
**Server:** 162.0.208.88  
**Status:** Production

## Prerequisites

### Server Requirements

- **OS:** Linux (Ubuntu/Debian recommended)
- **Python:** 3.8+
- **Memory:** 4GB+ (32GB recommended)
- **Disk:** 50GB+ free space
- **Network:** Ports 8150-8240 available

### Access Requirements

- SSH access to server (root or sudo)
- Ability to create systemd services
- Network access between services

## Deployment Steps

### 1. Prepare Server

```bash
# Update system
apt-get update && apt-get upgrade -y

# Install Python and dependencies
apt-get install -y python3 python3-pip python3-venv curl

# Create base directory
mkdir -p /opt/fpai/apps
```

### 2. Deploy Services

Use the consolidated deployment script:

```bash
# From local machine
./deploy_all_consciousness_services.sh
```

Or deploy individually:

```bash
# For each service
SERVICE_NAME="consciousness_optimizer"
PORT="8160"
SERVER="root@162.0.208.88"
BASE_DIR="/opt/fpai/apps"

# Sync files
rsync -av --delete --exclude '__pycache__' --exclude '*.pyc' --exclude 'venv' \
    SERVICES/$SERVICE_NAME/ \
    $SERVER:$BASE_DIR/$SERVICE_NAME/

# Setup Python environment
ssh $SERVER "cd $BASE_DIR/$SERVICE_NAME && \
    python3 -m venv venv && \
    source venv/bin/activate && \
    pip install -r requirements.txt"
```

### 3. Create Systemd Service

For each service, create a systemd service file:

```bash
ssh root@162.0.208.88 "cat > /etc/systemd/system/fpai-$SERVICE_NAME.service << EOF
[Unit]
Description=FPAI $SERVICE_NAME Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$BASE_DIR/$SERVICE_NAME
Environment=\"PATH=$BASE_DIR/$SERVICE_NAME/venv/bin\"
ExecStart=$BASE_DIR/$SERVICE_NAME/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT --loop asyncio
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
"
```

### 4. Enable and Start Service

```bash
ssh root@162.0.208.88 "systemctl daemon-reload && \
    systemctl enable fpai-$SERVICE_NAME && \
    systemctl start fpai-$SERVICE_NAME"
```

### 5. Verify Deployment

```bash
# Check service status
ssh root@162.0.208.88 "systemctl status fpai-$SERVICE_NAME"

# Test health endpoint
curl http://162.0.208.88:$PORT/health

# Check logs
ssh root@162.0.208.88 "journalctl -u fpai-$SERVICE_NAME -n 20"
```

## Service-Specific Configuration

### Consciousness Optimizer

**Special Configuration:**
- Requires `consciousness_verifier` and `consciousness_feeder` URLs
- Default: `http://162.0.208.88:8230` and `http://162.0.208.88:8240`
- Can be updated at runtime via `/config/update` endpoint

**Dependencies:**
- numpy>=1.21.0
- scikit-learn>=1.3.0
- httpx>=0.24.0

### Consciousness Verifier

**Special Configuration:**
- Fetches config from `consciousness_feeder`
- Calculates mathematical metrics
- Requires numpy and scipy

**Dependencies:**
- numpy>=1.21.0
- scipy>=1.7.0

### Consciousness Feeder

**Special Configuration:**
- Manages optimization configuration
- Provides data feeds
- No special dependencies

## Port Configuration

All services use fixed ports:

| Service | Port |
|---------|------|
| consciousness_decision_engine | 8150 |
| consciousness_optimizer | 8160 |
| consciousness_dashboard | 8170 |
| consciousness_gateway | 8180 |
| consciousness_network | 8190 |
| consciousness_api | 8210 |
| consciousness_evolution | 8220 |
| consciousness_verifier | 8230 |
| consciousness_feeder | 8240 |

**Note:** Ensure ports are not in use before deployment:
```bash
lsof -i :8160  # Check if port is available
```

## Health Check Procedures

### Automated Health Check Script

Create `/opt/fpai/scripts/check-consciousness-services.sh`:

```bash
#!/bin/bash
SERVICES=(
    "8150:consciousness_decision_engine"
    "8160:consciousness_optimizer"
    "8170:consciousness_dashboard"
    "8180:consciousness_gateway"
    "8190:consciousness_network"
    "8210:consciousness_api"
    "8220:consciousness_evolution"
    "8230:consciousness_verifier"
    "8240:consciousness_feeder"
)

for service in "${SERVICES[@]}"; do
    PORT="${service%%:*}"
    NAME="${service##*:}"
    if curl -s -f http://localhost:$PORT/health > /dev/null; then
        echo "✅ $NAME (port $PORT) - Healthy"
    else
        echo "❌ $NAME (port $PORT) - Failed"
        systemctl restart fpai-$NAME
    fi
done
```

### Cron Job Setup

```bash
# Add to crontab (runs every 5 minutes)
*/5 * * * * /opt/fpai/scripts/check-consciousness-services.sh >> /var/log/consciousness-health.log 2>&1
```

## Troubleshooting

### Service Won't Start

**Symptoms:**
- `systemctl status` shows "failed"
- Service keeps restarting

**Diagnosis:**
```bash
# Check logs
journalctl -u fpai-consciousness-{service} -n 50

# Check for port conflicts
lsof -i :{port}

# Test Python environment
cd /opt/fpai/apps/consciousness_{service}
source venv/bin/activate
python3 -c "from app.main import app; print('OK')"
```

**Common Fixes:**
1. Port already in use → Kill process or change port
2. Missing dependencies → `pip install -r requirements.txt`
3. Python version mismatch → Check Python version
4. Import errors → Check code syntax

### Endpoints Return 500 Errors

**Symptoms:**
- Health endpoint works
- Other endpoints return "Internal Server Error"

**Diagnosis:**
```bash
# Check service logs for exceptions
journalctl -u fpai-consciousness-{service} -f

# Test endpoint directly
curl -v http://localhost:{port}/endpoint

# Check if service dependencies are running
systemctl status fpai-consciousness-verifier
systemctl status fpai-consciousness-feeder
```

**Common Fixes:**
1. Service dependency down → Start dependency service
2. Network connectivity issue → Check firewall/network
3. Code error → Check logs for traceback
4. Configuration error → Verify service URLs

### Optimization Loop Crashes

**Symptoms:**
- Service starts but crashes repeatedly
- Logs show "Phase: Measure Baseline" then crash

**Diagnosis:**
```bash
# Check optimization loop logs
journalctl -u fpai-consciousness-optimizer | grep -E "(ERROR|Exception|Traceback)"

# Test optimizer initialization
cd /opt/fpai/apps/consciousness_optimizer
source venv/bin/activate
python3 -c "from app.optimizer import ConsciousnessOptimizer; opt = ConsciousnessOptimizer(); print('OK')"
```

**Common Fixes:**
1. Verifier/Feeder not accessible → Check URLs and connectivity
2. Model mismatch → Check OptimizationExperiment model
3. Missing experiment_id → Verify code has latest fixes
4. Error handling → Check error handling in optimization loop

## Rollback Procedures

### Rollback Single Service

```bash
SERVICE_NAME="consciousness_optimizer"
VERSION="v1.0.0"  # Previous version

# Stop service
systemctl stop fpai-$SERVICE_NAME

# Restore from backup
/opt/fpai/scripts/restore-service.sh $SERVICE_NAME $VERSION

# Restart service
systemctl start fpai-$SERVICE_NAME
```

### Rollback All Services

```bash
# Stop all services
for service in consciousness_decision_engine consciousness_optimizer consciousness_dashboard consciousness_gateway consciousness_network consciousness_api consciousness_evolution consciousness_verifier consciousness_feeder; do
    systemctl stop fpai-$service
done

# Restore from backup
/opt/fpai/scripts/restore-service.sh consciousness_optimizer latest
# Repeat for each service

# Start all services
for service in consciousness_decision_engine consciousness_optimizer consciousness_dashboard consciousness_gateway consciousness_network consciousness_api consciousness_evolution consciousness_verifier consciousness_feeder; do
    systemctl start fpai-$service
done
```

## Backup Procedures

### Pre-Deployment Backup

**Mandatory before any deployment:**

```bash
# Create backup
/opt/fpai/scripts/pre-deploy-backup.sh consciousness_optimizer v1.1.0

# Or use safe deploy wrapper
./infra/scripts/safe-deploy.sh consciousness_optimizer "./deploy_service.sh"
```

### List Backups

```bash
# List all backups for a service
/opt/fpai/scripts/list-backups.sh consciousness_optimizer

# List all backups
/opt/fpai/scripts/list-backups.sh
```

### Restore from Backup

```bash
# Restore latest backup
/opt/fpai/scripts/restore-service.sh consciousness_optimizer latest

# Restore specific version
/opt/fpai/scripts/restore-service.sh consciousness_optimizer v1.0.0
```

## Monitoring

### Service Status Monitoring

```bash
# Check all service statuses
systemctl status fpai-consciousness-*

# Check resource usage
ps aux | grep consciousness | grep -v grep

# Check port usage
netstat -tlnp | grep -E "(8150|8160|8170|8180|8190|8210|8220|8230|8240)"
```

### Log Monitoring

```bash
# Follow logs for all services
journalctl -u fpai-consciousness-* -f

# Check recent errors
journalctl -u fpai-consciousness-* --since "1 hour ago" | grep -i error

# Check service restarts
journalctl -u fpai-consciousness-* | grep "Started\|Stopped"
```

### Metrics Monitoring

```bash
# Get current consciousness metrics
curl http://162.0.208.88:8160/metrics/current

# Get optimization opportunities
curl http://162.0.208.88:8160/opportunities

# Get optimization statistics
curl http://162.0.208.88:8160/statistics
```

## Security Considerations

### Current Setup

- Services run on internal network
- No external authentication
- Services communicate via HTTP (not HTTPS)

### Future Enhancements

1. **Add API Keys:**
   - Generate API keys for each service
   - Add authentication middleware
   - Store keys securely

2. **Enable HTTPS:**
   - Set up SSL certificates
   - Configure nginx reverse proxy
   - Redirect HTTP to HTTPS

3. **Firewall Rules:**
   - Restrict port access
   - Allow only internal IPs
   - Block external access

4. **Rate Limiting:**
   - Add rate limiting middleware
   - Prevent abuse
   - Protect against DDoS

## Performance Tuning

### Optimize Service Startup

```bash
# Increase systemd restart delay
RestartSec=30  # Instead of 10

# Add resource limits
LimitNOFILE=65536
LimitNPROC=4096
```

### Optimize Python Performance

```bash
# Use Python optimizations
export PYTHONOPTIMIZE=2

# Increase worker processes (if needed)
uvicorn app.main:app --workers 4
```

### Database Optimization (Future)

- Add connection pooling
- Use async database drivers
- Implement caching layer

## Maintenance

### Regular Maintenance Tasks

1. **Weekly:**
   - Review service logs
   - Check resource usage
   - Verify backups

2. **Monthly:**
   - Update dependencies
   - Review security patches
   - Optimize configurations

3. **Quarterly:**
   - Review architecture
   - Plan scaling strategies
   - Update documentation

## Support

### Getting Help

1. Check logs: `journalctl -u fpai-consciousness-{service}`
2. Review documentation: `docs/architecture/CONSCIOUSNESS_SERVICES.md`
3. Check service health: `curl http://localhost:{port}/health`

### Common Commands Reference

```bash
# Service management
systemctl start|stop|restart|status fpai-consciousness-{service}

# Log viewing
journalctl -u fpai-consciousness-{service} -f

# Health checks
curl http://localhost:{port}/health

# Resource monitoring
ps aux | grep consciousness
top -p $(pgrep -f consciousness)
```











