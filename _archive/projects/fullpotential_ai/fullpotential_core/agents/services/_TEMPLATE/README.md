# [Service Name]

**Status**: Development | Testing | Production | Deprecated
**Version**: 0.1.0
**Port**: XXXX
**URL**: https://fullpotential.com/[service-path]
**Responsible Session**: #N
**Last Updated**: YYYY-MM-DD

---

## Overview

[Brief description of what this service does - 2-3 sentences]

**Purpose**: [What problem does this service solve?]
**Value Proposition**: [What value does it provide?]
**Revenue Impact**: [How does it contribute to revenue?]

---

## Quick Start

### Prerequisites
- Python 3.9+ (or other language/version)
- Required environment variables (see below)
- Dependencies listed in requirements.txt

### Local Development
```bash
# Clone and navigate
cd /Users/jamessunheart/Development/agents/services/[service-name]

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export API_KEY=your_key_here

# Run locally
python3 src/main.py

# Access at: http://localhost:XXXX
```

### Run Tests
```bash
pytest tests/
```

---

## API Endpoints

### Core Endpoints

**GET /health**
- Health check endpoint
- Returns: `{"status": "healthy", "service": "[service-name]"}`

**GET /api/[resource]**
- Description: [What this endpoint does]
- Parameters: [List parameters]
- Returns: [Response format]

[Add more endpoints as needed]

---

## Architecture

```
[service-name]/
├── src/
│   ├── main.py              # Entry point
│   ├── api/                 # API endpoints
│   ├── models/              # Data models
│   ├── services/            # Business logic
│   └── utils/               # Utilities
├── tests/                   # Test files
├── deploy/                  # Deployment scripts
└── docs/                    # Additional documentation
```

---

## Configuration

### Environment Variables
```bash
# Required
export API_KEY=xxx
export DATABASE_URL=xxx

# Optional
export DEBUG=false
export LOG_LEVEL=info
```

### Configuration Files
- `config.py` - Application configuration
- `deploy/nginx.conf` - Nginx configuration
- `deploy/systemd.service` - Systemd service file

---

## Status

### Completion Checklist
- [ ] Spec complete (SPEC.md)
- [ ] Core features implemented
- [ ] Tests written (>80% coverage)
- [ ] Documentation complete
- [ ] Deployed to staging
- [ ] Deployed to production
- [ ] Monitoring configured

### Current Phase
[Planning | Development | Testing | Deployment | Production]

**Progress**: X%

---

## Dependencies

### Core Dependencies
- [dependency-1]: [purpose]
- [dependency-2]: [purpose]

### External Services
- [service-1]: [what it's used for]
- [service-2]: [what it's used for]

---

## Deployment

### Deploy to Production
```bash
./deploy/deploy.sh production
```

### Deploy to Staging
```bash
./deploy/deploy.sh staging
```

### Manual Deployment
```bash
rsync -avz --exclude 'venv' \
  ./ root@198.54.123.234:/opt/fpai/services/[service-name]/
```

---

## Monitoring

### Health Check
```bash
curl https://fullpotential.com/[service-path]/health
```

### Logs
```bash
# On server
tail -f /var/log/[service-name].log

# Or via journalctl
journalctl -u [service-name] -f
```

### Metrics
- Uptime: [target %]
- Response time: [target ms]
- Error rate: [target %]

---

## Links

- **Specification**: [SPEC.md](SPEC.md)
- **Progress Tracker**: [PROGRESS.md](PROGRESS.md)
- **API Documentation**: [docs/API.md](docs/API.md)
- **Deployment Guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Session Coordination

**Responsible Session**: #N
**Contributors**: [List session numbers]
**Last Modified By**: Session #N on YYYY-MM-DD

### Handoff Protocol
When handing off this service:
1. Update PROGRESS.md with current status
2. Document blockers in "Current Issues" section
3. Update responsible_session in SERVICE_REGISTRY.json
4. Broadcast handoff to all sessions

---

## Support

For issues or questions:
- Check SPEC.md for technical details
- Check PROGRESS.md for current status
- Review docs/ for additional documentation
- Contact responsible session via broadcast

---

**Built with ❤️ by Full Potential AI**
**Part of the unified services ecosystem**
