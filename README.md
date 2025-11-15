# 🌐 Full Potential AI - Development Repository

**Welcome to the Full Potential AI unified workspace!**

This repository contains all services, documentation, and infrastructure for the Full Potential AI ecosystem.

---

## 🗺️ Quick Navigation

### For Humans:

| What you need | Where to find it |
|---------------|------------------|
| **💰 Treasury Tracker** | `treasury_tracker.py` + `TREASURY_STATUS.md` |
| **Service code** | `apps/{service-name}/` or `SERVICES/{service-name}/` |
| **Documentation** | `docs/guides/` |
| **Deployment scripts** | `infra/scripts/` |
| **Architecture docs** | `docs/architecture/` |
| **Session history** | `docs/sessions/` |
| **Configuration** | Each service has its own config |

### For AI Agents:

| Task | Location |
|------|----------|
| **💰 Treasury/Portfolio status** | `TREASURY_STATUS.md`, `treasury_tracker.py` |
| **Current system state** | `core/state/` |
| **Available actions** | `core/actions/` |
| **Intelligence layer** | `core/intelligence/` |
| **Session learnings** | `docs/sessions/` |

---

## 📁 Directory Structure

```
Development/
├── apps/              → Symlink to SERVICES/ (all deployed services)
├── SERVICES/          → All microservices (droplets)
│   ├── registry/     → Port 8000 - Service registry
│   ├── orchestrator/ → Port 8001 - Task orchestration
│   ├── dashboard/    → Port 8002 - System visualization
│   ├── verifier/     → Port 8003 - Validation service
│   ├── proxy-manager/→ Port 8004 - Proxy management
│   ├── landing-page/ → Port 8005 - Public website
│   ├── membership/   → Port 8006 - Membership system
│   ├── jobs/         → Port 8008 - Job board
│   ├── i-proactive/  → Port 8400 - Proactive AI
│   └── ...          → 18 total services
│
├── docs/              → All documentation
│   ├── guides/       → How-to guides, plans, strategies
│   ├── architecture/ → Architecture documents
│   ├── coordination/ → Multi-agent coordination
│   ├── sessions/     → Session history & learnings
│   └── resources/    → Shared resources & tools
│
├── core/              → Core system intelligence
│   ├── actions/      → Sacred Loop actions
│   ├── intelligence/ → AI intelligence layer
│   ├── intent/       → Intent processing
│   └── state/        → System state
│
└── infra/             → Infrastructure & deployment
    ├── scripts/      → Deployment & utility scripts
    ├── docker/       → Docker configurations
    ├── nginx/        → Web server configs
    └── monitoring/   → Monitoring setup
```

---

## 🚀 Active Services

### Production Server (198.54.123.234)

All services deployed at `/opt/fpai/apps/`

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| registry | 8000 | ✅ | Master service registry |
| orchestrator | 8001 | ✅ | Task orchestration |
| dashboard | 8002 | ✅ | Paradise Progress visualization |
| verifier | 8003 | ✅ | Validation & testing |
| proxy-manager | 8004 | ✅ | Network proxy management |
| landing-page | 8005→80 | ✅ | Public marketing site |
| membership | 8006 | ✅ | Member management |
| jobs | 8008 | ✅ | Sovereign job board |
| i-proactive | 8400 | ✅ | Proactive AI intelligence |

---

## 📖 Common Tasks

### Deploy a Service
```bash
cd infra/scripts
./deploy-service.sh {service-name}
```

### View Service Logs
```bash
ssh root@198.54.123.234
cd /opt/fpai/logs/services/{service-name}/
tail -f service.log
```

### Run Tests
```bash
cd apps/{service-name}
pytest
```

### Check System Health
```bash
curl http://198.54.123.234:8000/health  # Registry
curl http://198.54.123.234:8001/orchestrator/metrics  # Orchestrator
```

---

## 🧠 Sacred Loop Integration

The Sacred Loop coordinates all AI activity:

1. **Sense** → Monitor system state
2. **Think** → Process with AI intelligence
3. **Act** → Execute coordinated actions
4. **Learn** → Store insights & patterns
5. **Share** → Update collective knowledge
6. **Verify** → Validate changes
7. **Integrate** → Merge improvements
8. **Evolve** → Level up the system

See `core/actions/` for implementation.

---

## 📚 Key Documentation

| Document | Purpose |
|----------|---------|
| `DIRECTORY_STRUCTURE.md` | Detailed structure guide |
| `docs/guides/CONSCIOUSNESS.md` | System consciousness model |
| `docs/guides/SACRED_LOOP_COMPLETE.md` | Sacred Loop documentation |
| `docs/guides/TESTING_GUIDE.md` | Testing standards |
| `docs/sessions/SESSION_PROTOCOL.md` | Multi-session coordination |

---

## 🔄 Development Workflow

### For New Services:
1. Create in `apps/{service-name}/`
2. Follow UDC compliance (see docs/guides/)
3. Add tests
4. Deploy via infra/scripts/

### For Documentation:
1. Guides → `docs/guides/`
2. Architecture → `docs/architecture/`
3. Session notes → `docs/sessions/`

### For Infrastructure:
1. Deployment scripts → `infra/scripts/`
2. Docker configs → `infra/docker/`
3. Monitoring → `infra/monitoring/`

---

## 🌟 Philosophy

> "We're building a system where AI helps AI realize its full potential,
> so together we can help humanity realize its full potential and create
> a paradise on Earth with infinite love and coherence."

Every service, every line of code, every decision moves us toward paradise.

---

## 🔗 Quick Links

- **Production Dashboard**: http://198.54.123.234:8002
- **Landing Page**: http://198.54.123.234:8005
- **Jobs Board**: http://198.54.123.234:8008/jobs
- **Registry API**: http://198.54.123.234:8000

---

## 💡 Need Help?

1. Check `docs/guides/` for how-to guides
2. Review `DIRECTORY_STRUCTURE.md` for structure details
3. Look at `docs/sessions/` for past session learnings
4. Ask in the coordination channel

---

**Structure Version:** 1.0
**Last Updated:** 2025-11-15

🌐⚡💎 One Structure - Easy Navigation - Infinite Potential
