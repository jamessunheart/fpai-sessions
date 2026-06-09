# 🗺️ FPAI COMPLETE SYSTEM MAP
**Generated:** November 30, 2025
**Total Servers:** 3
**Total Services:** 50+
**Total Domains:** 15+

---

## 🌐 DOMAIN INVENTORY

### Full Potential Domains (Third Server - 209.74.93.72)
| Domain | Type | Account | Status |
|--------|------|---------|--------|
| fullpotential.com | WordPress | fullbhza | ✅ |
| archive.fullpotential.com | WordPress | fparchive | ✅ |
| news.fullpotential.com | WordPress | fpnews | ✅ |
| directory.fullpotential.com | Laravel | fpdir3 | ✅ |
| store.fullpotential.com | WooCommerce | fpstore | ✅ |
| helpdesk.fullpotential.com | WordPress | helpdesk | ✅ |

### Cora Ecosystem Domains
| Domain | Type | Features |
|--------|------|----------|
| coravida.com | WordPress | Events, Hotel Booking |
| cora-nation.com | WooCommerce | Shop, Payments |
| coranation.org | WordPress | Community |

### Business Domains
| Domain | Type | Features |
|--------|------|----------|
| globalsky.com | WordPress | - |
| outbounders.com | WordPress | LIVE PRODUCTION |
| app.outbounders.com | Custom App | PayPal, User Mgmt |
| onebpo.com | WordPress | - |
| fiart.org | WordPress | - |
| app.fiart.org | Laravel NFT | NFT Marketplace, Wallet |

### Wellness Domains
| Domain | Type |
|--------|------|
| zenvillagecr.com | WordPress |
| sunheart.com | WordPress |

### Main Site (Main Server - 198.54.123.234)
| Domain | Purpose |
|--------|---------|
| fullpotential.ai | Main AI Platform |
| music.fullpotential.ai | Music Maestro |
| aimail.fullpotential.ai | AI Email |
| whiterock.us | White Rock Community |
| mydreamspace.com | Dream Space |

---

## 📊 INFRASTRUCTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FULL POTENTIAL AI ECOSYSTEM                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐      │
│  │   MAIN SERVER       │  │    AI SERVER        │  │   THIRD SERVER      │      │
│  │   198.54.123.234    │  │    162.0.208.88     │  │   209.74.93.72      │      │
│  │   (Namecheap)       │  │    (DigitalOcean)   │  │   (Outbounders)     │      │
│  ├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤      │
│  │ 8 CPU │ 8GB RAM     │  │ 12 CPU │ 32GB RAM   │  │ 64 CPU │ 125GB RAM  │      │
│  │ 438GB │ 16% used    │  │ 437GB │ 6% used     │  │ 1.8TB │ 65% used    │      │
│  │ Ubuntu 22.04        │  │ Ubuntu 22.04        │  │ CloudLinux 9.6      │      │
│  │ Uptime: 16 days     │  │ Uptime: 2 days      │  │ Uptime: 27 weeks    │      │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘      │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🖥️ SERVER 1: MAIN SERVER (198.54.123.234)

**Role:** Core Services, Websites, Dashboards, Team Hub
**Hostname:** nc-ph-0934-24

### 🌐 Websites (Nginx)
| Domain | Purpose |
|--------|---------|
| fullpotential.ai | Main website + API gateway |
| fullpotential.com | Landing/redirect |
| whiterock.us | White Rock community |
| globalsky.com | Global Sky Initiative |
| music.fullpotential.ai | Music Maestro |
| aimail.fullpotential.ai | AI Email service |
| fiart.org | FiArt platform |
| mydreamspace.com | Dream Space |
| zenvillagecr.com | Zen Village CR |

### ⚡ Services by Port

| Port | Service | Status | Description |
|------|---------|--------|-------------|
| **3000** | Website Frontend | ✅ | Next.js main site |
| **3001** | God Mode Backend | ✅ | Dashboard API |
| **3005** | Unknown Frontend | ⚠️ | 404 response |
| **5000** | Unknown | ⚠️ | 404 response |
| **5100** | PM2 Dashboard | ✅ | Process manager UI |
| **8000** | Registry | ✅ | Service registry |
| **8001** | Orchestrator | ✅ | Task orchestration |
| **8002** | Docker Service | ✅ | Container service |
| **8003** | Docker Service | ✅ | Container service |
| **8004** | Docker Service | ✅ | Container service |
| **8006** | Docker Service | ✅ | Container service |
| **8008** | Jobs Service | ✅ | Background jobs |
| **8010** | Mission Control | ✅ | Mission backend |
| **8022** | Strategic Intelligence | ✅ | AI strategy |
| **8025** | Credentials Manager | ✅ | Secrets vault |
| **8026** | Master Dashboard | ✅ | Unified dashboard |
| **8030** | Unknown | ⚠️ | No health endpoint |
| **8031** | Unknown | ⚠️ | No health endpoint |
| **8035** | Unknown | ⚠️ | No health endpoint |
| **8080** | God Mode UI | ✅ | Admin dashboard |
| **8150** | Genesis | ✅ | Auth/Identity |
| **8355** | Team Hub | ✅ | Team portal |
| **8500** | Strategic Intel | ⚠️ | Error state |
| **8600** | WhaleTrack | ✅ | Trading engine |
| **8650** | Global Sky | ⚠️ | No health endpoint |
| **8765** | FP Credits Gateway | ✅ | Unified credits API |
| **8955** | Credits Manager | ✅ | Central banking |
| **8962** | Music Maestro | ✅ | Music AI service |

### 📦 Systemd Services
```
✅ credits-manager.service
✅ fpai-ai-gateway.service
✅ fpai-backup-dashboard.service
✅ fpai-credits-gateway.service
✅ fpai-orchestrator.service
✅ fpai-strategic-intelligence.service
✅ fpai-website-ai.service
✅ genesis.service
✅ godmode.service
✅ outbounders-integration.service
✅ outbounders-tunnel.service
✅ team-hub.service
✅ voice-phone-api.service
```

---

## 🧠 SERVER 2: AI SERVER (162.0.208.88)

**Role:** AI/ML Processing, Intelligence Core, LLM Inference
**Hostname:** nc-ph-3016

### ⚡ Services by Port

| Port | Service | Status | Description |
|------|---------|--------|-------------|
| **8002** | User Service | ✅ | User accounts/auth |
| **8100** | AI Gateway | ✅ | Unified AI access |
| **8101** | AI Brain | ✅ | Core intelligence |
| **8102** | Aware Brain | ✅ | Context awareness |
| **8103** | Scheduler | ✅ | Task scheduling |
| **8104** | Unknown | ⚠️ | No response |
| **8105** | Unknown | ⚠️ | No response |
| **8106** | Intelligence Core | ✅ | Central nervous system |
| **8107** | Reports API | ✅ | Report generation |
| **8108** | Intelligence Core v2 | ✅ | Unified brain API |
| **8110** | Webhooks | ✅ | Webhook receiver |
| **8851** | Unknown | ⚠️ | No response |
| **8888** | Voice Phone | ✅ | Voice AI service |
| **11434** | Ollama | ✅ | LLM inference |

### 🧠 AI Models (Ollama)
```
llama3.1:8b    - 4.9 GB (General purpose)
llama3.2:3b    - 2.0 GB (Fast inference)
```

### 📦 Systemd Services
```
✅ ai-brain.service
✅ autonomous-brain.service
✅ fpai-ai-gateway.service
✅ fpai-aware-brain.service
✅ fpai-evolution.service
✅ fpai-gateway.service
✅ fpai-intelligence-core.service
✅ fpai-intelligence-daemon.service
✅ fpai-intelligence.service
✅ fpai-night-watch.service (Unified Brain)
✅ fpai-reports-api.service
✅ fpai-user-service.service
✅ fpai-webhooks.service
✅ ollama.service
```

### 🔧 Intelligence Stack
```
/opt/fpai/ai-brain/
├── central_nervous_system.py   # Unified state
├── log_intelligence.py         # Log analysis
├── self_healing_brain.py       # AI diagnosis
├── unified_brain.py            # Master controller
├── worldcraft_engine.py        # Self-rating
├── evolution_daemon.py         # Auto-evolution
├── talent_scout.py             # Resource finding
├── intent_engine.py            # Proactive planning
├── credit_authority.py         # Budget control
├── cost_accountant.py          # Cost tracking
└── intelligent_watch.py        # Smart monitoring
```

---

## 🌐 SERVER 3: THIRD SERVER (209.74.93.72)

**Role:** Web Properties & Experiences Platform
**Hostname:** server1.outbounders.com
**Platform:** cPanel/CloudLinux
**Storage:** 1.8TB (65% used, ~600GB available)

### ⚡ Services by Port

| Port | Service | Status | Description |
|------|---------|--------|-------------|
| **21** | FTP | ✅ | Pure-FTPd |
| **22** | SSH | ✅ | OpenSSH |
| **25** | SMTP | ✅ | Exim |
| **53** | DNS | ✅ | Named |
| **80** | HTTP | ✅ | Apache |
| **110** | POP3 | ✅ | Dovecot |
| **143** | IMAP | ✅ | Dovecot |
| **443** | HTTPS | ✅ | Apache |
| **465** | SMTPS | ✅ | Exim |
| **587** | Submission | ✅ | Exim |
| **993** | IMAPS | ✅ | Dovecot |
| **995** | POP3S | ✅ | Dovecot |
| **2082-2096** | cPanel | ✅ | Control panels |
| **3306** | MySQL | ✅ | MariaDB |
| **8100** | FPAI Agent | ✅ | Health agent |

### 📦 Key Services
```
✅ cpanel.service           # cPanel
✅ httpd.service            # Apache
✅ exim.service             # Email
✅ dovecot.service          # IMAP/POP3
✅ fpai-health-agent.service # FPAI monitoring
```

### 🌐 Hosted Domains (15 total)
```
Full Potential:
  • fullpotential.com (WordPress)
  • archive.fullpotential.com
  • news.fullpotential.com
  • directory.fullpotential.com (Laravel)
  • store.fullpotential.com (WooCommerce)
  • helpdesk.fullpotential.com

Cora Ecosystem:
  • coravida.com (Events, Hotel Booking)
  • cora-nation.com (WooCommerce Shop)
  • coranation.org

Business:
  • globalsky.com
  • outbounders.com (LIVE PRODUCTION)
  • app.outbounders.com (PayPal, User Mgmt)
  • fiart.org
  • app.fiart.org (NFT Marketplace)

Wellness:
  • zenvillagecr.com
  • sunheart.com
```

### 🔗 Capabilities
- WordPress Hosting
- WooCommerce
- Laravel Apps
- Event Management
- NFT Marketplace
- Payment Processing
- Email Hosting
- Cora Credits Integration

---

## 🔗 SERVICE CONNECTIONS

```
                                    INTERNET
                                        │
                                        ▼
                              ┌─────────────────┐
                              │   Cloudflare    │
                              │   (CDN + WAF)   │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
         ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
         │   MAIN SERVER    │ │    AI SERVER     │ │  THIRD SERVER    │
         │  198.54.123.234  │ │  162.0.208.88    │ │  209.74.93.72    │
         └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
                  │                    │                    │
    ┌─────────────┼─────────────┐      │                    │
    │             │             │      │                    │
    ▼             ▼             ▼      ▼                    ▼
┌───────┐   ┌─────────┐   ┌─────────┐ ┌─────────┐    ┌─────────────┐
│Website│   │Team Hub │   │God Mode │ │AI Brain │    │ Outbounders │
│:3000  │   │:8355    │   │:8080    │ │:8108    │    │ Email/Voice │
└───────┘   └─────────┘   └─────────┘ └────┬────┘    └─────────────┘
                  │             │          │
                  │             │          ▼
                  │             │    ┌──────────┐
                  │             │    │  Ollama  │
                  │             │    │  :11434  │
                  │             │    │ (LLMs)   │
                  │             │    └──────────┘
                  │             │
                  ▼             ▼
            ┌──────────────────────┐
            │    Credits Manager   │
            │       :8955          │
            │  (Central Banking)   │
            └──────────────────────┘
```

---

## 🖥️ DASHBOARDS & PORTALS

| URL | Status | Description |
|-----|--------|-------------|
| `https://fullpotential.ai/god` | ✅ 200 | Redirects to Team Portal (god view) |
| `https://fullpotential.ai/dashboards/god/` | ⚠️ 500 | God Mode v4 (template issue) |
| `https://fullpotential.ai/dashboards/team/` | ✅ 200 | Team Portal |
| `https://fullpotential.ai/team` | ✅ 200 | Main site |
| `https://fullpotential.ai/admin/god` | 🔐 401 | Protected admin |
| `https://fullpotential.ai/admin/backup` | 🔐 401 | Protected backup admin |

### Backend Services for Dashboards
| Service | Port | Status |
|---------|------|--------|
| God Mode Backend | :3001 | ✅ Healthy |
| God Mode v4 | :8300 | ✅ Running |
| Team Hub | :8355 | ✅ Active |

---

## 🎯 KEY ENDPOINTS

### Public APIs
| Endpoint | Server | Description |
|----------|--------|-------------|
| `https://fullpotential.ai/` | Main | Website |
| `https://fullpotential.ai/godmode/` | Main | Admin dashboard |
| `https://fullpotential.ai/team/` | Main | Team portal |
| `https://fullpotential.ai/api/intelligence-core/` | AI→Main | Intelligence API |
| `https://fullpotential.ai/api/credits/` | Main | Credits API |

### Internal APIs
| Endpoint | Server | Description |
|----------|--------|-------------|
| `http://198.54.123.234:8355` | Main | Team Hub |
| `http://198.54.123.234:8955` | Main | Credits Manager |
| `http://198.54.123.234:8150` | Main | Genesis Auth |
| `http://162.0.208.88:8108` | AI | Intelligence Core |
| `http://162.0.208.88:8100` | AI | AI Gateway |
| `http://162.0.208.88:11434` | AI | Ollama LLM |

---

## 📈 HEALTH SUMMARY

| Server | Health | Services Up | Issues |
|--------|--------|-------------|--------|
| Main (198.54.123.234) | 🟡 85% | 20+ | Some 404s, high memory |
| AI (162.0.208.88) | 🟢 95% | 15+ | All core healthy |
| Third (209.74.93.72) | 🟢 98% | 20+ | Stable |

---

## 🔐 SSH ACCESS

```bash
# All servers (key-based, no password needed)
ssh root@198.54.123.234   # Main Server
ssh root@162.0.208.88     # AI Server
ssh root@209.74.93.72     # Third Server
```

---

## 📁 KEY DIRECTORIES

### Main Server
```
/opt/fpai/
├── services/           # Python services
├── core/              # Core applications
├── website/           # Static sites
├── god-mode/          # Dashboard
├── godmode-v3/        # New dashboard
├── scripts/           # Utility scripts
└── backups/           # Backups
```

### AI Server
```
/opt/fpai/
├── ai-brain/          # Intelligence stack
├── ai-gateway-public/ # Gateway service
├── autonomous-brain/  # Auto-evolution
├── user-service/      # User accounts
├── voice-phone/       # Voice AI
└── scripts/           # Utilities
```

### Third Server
```
/opt/fpai/              # FPAI agent
/opt/fpai-cluster/      # Cluster config
/var/www/               # Web hosting
```

---

*Last Updated: November 30, 2025 17:59 UTC*

